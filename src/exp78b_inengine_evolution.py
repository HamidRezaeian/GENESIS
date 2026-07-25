#!/usr/bin/env python3
"""
Rule 21.2 increment 3c — IN-ENGINE PARAM-gene evolution under selection.
========================================================================
The definitive Rule-21.2 evidence for the FULL engine (vs the exp77e probe, which
used a simplified organism model). Each organism LIFETIME BEHAVIOUR is simulated by
the real numba kernel world_tick_numba with GENESIS_EVOLVABLE_CONSTANTS=1, so the
per-organism constants (g_org_params[org], wired in 3b-i/3b-ii) genuinely drive
behaviour, and selection acts on them through the engine OWN comprehension signal
(correct next-symbol predictions, read_log type 1 + type 3).

Design (the in-engine counterpart of exp77e):
  - Fixed structural genome: the long-lived seeded ancestor (seed 20260725, lif_steps=4,
    lives the full evaluation window). All organisms share this structure so drift is
    isolated to the PARAM constants.
  - Evolving genotype: the 9 PARAM genes (g_org_params row), evolved as real values in
    their PARAM_GENES ranges, mutated by small Gaussian steps in fraction space (the
    genome 14-bit encoding) — the standard EA abstraction of the cosmic-radiation byte
    mutation that perturbs the PARAM tail in vivo.
  - Fitness: correct-prediction count over a fixed 180-tick window (engine-internal,
    constant-dependent, NOT invented points), AVERAGED over N_REPLICATES independent
    runs to push the engine run-to-run stochasticity (viscosity stalls; ~2.3 std on a
    single run) below the between-genotype fitness gradient.
  - Initial population: sampled UNIFORMLY across each gene full range (like exp77e),
    NOT clustered at the designer default — the defaults sit at the top of most ranges
    (cam_slots=32, cam_key_bits=8), so a narrow init leaves the population in a flat,
    noise-dominated region where selection cannot act. Uniform init gives selection real
    gradients to climb.
  - Selection: truncation (top 25%) for the SELECTED line; random parent choice for the
    NEUTRAL control (same init + mutation, no fitness bias) -> the contrast isolates
    selection-driven drift from neutral mutation drift.
  - Track: per-generation population mean of all 9 PARAM genes + mean/best fitness.

Outputs (auto-persisted to agent-outputs):
  exp78b_evolution_results.json  — full per-generation gene means + fitness (both lines)
  exp78b_param_drift.png         — drift of the 4 most-responsive genes, selected vs neutral
  exp78b_fitness_curve.png       — mean fitness trajectory, selected vs neutral

Run:  GENESIS_EVOLVABLE_CONSTANTS=1 python3 - < src/exp78b_inengine_evolution.py
"""
import os, sys, json, random, time
import numpy as np

os.environ["GENESIS_WMEM"] = "1"
os.environ["GENESIS_CAM"] = "1"
os.environ["GENESIS_CAM_KEY_BITS"] = "8"
os.environ["GENESIS_STDP"] = "1"
os.environ["GENESIS_ECONOMY"] = "books"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "src"))
import genesis_lab as gl
from genesis_lab import (g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
    g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
    g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
    g_neuron_map, g_synapse_map, g_genome_map, g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
    g_global_genome, g_org_g_ptr, g_org_g_count,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset,
    o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,
    g_viscosity, g_org_lif_steps, g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
    voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
    g_read_log, g_read_fuel, g_cell_owner, g_read_hits, g_org_reward, g_org_elig,
    g_global_sense_type, g_global_sense_meta, g_global_act_drive,
    g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
    g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay, g_conn_w_dna,
    g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    world_tick_numba, spawn_organism, CANVAS_LO, CANVAS_HI, MAX_ORGANISMS, RAM_SIZE,
    PARAM_GENES, PARAM_DEFAULTS)
from neuromorphic_engine import g_org_params, EVOLVABLE_CONSTANTS, CAM_SLOTS, CAM_KEY_BITS

assert EVOLVABLE_CONSTANTS, "3c MUST run with GENESIS_EVOLVABLE_CONSTANTS=1 (kernel must read g_org_params)"

# ----------------------------- experiment config -----------------------------
SEED          = 20260725    # long-lived ancestor (lif_steps=4); also seeds reproducibility
P_POP         = 24          # population size
K_SELECT      = 6           # truncation: top 25 percent become parents (strong selection)
G_GENERATIONS = 40          # number of generations
EVAL_TICKS    = 180         # evaluation window (within the ~197-tick lifespan)
N_REPLICATES  = 5           # independent runs averaged per genotype (noise reduction ~sqrt(5))
SIGMA_FRAC    = 0.05        # per-gene Gaussian mutation step in [0,1] fraction space
N_GENES       = len(PARAM_GENES)
GENE_NAMES    = [g[0] for g in PARAM_GENES]
OUT_DIR       = os.environ.get("EXP78B_OUT", os.getcwd())

# ----------------------------- helpers ---------------------------------------
def value_to_frac(gid, value):
    name, lo, hi, scale = PARAM_GENES[gid]
    if scale == "log" and lo > 0 and value > 0 and hi > lo:
        f = (np.log(value) - np.log(lo)) / (np.log(hi) - np.log(lo))
    elif hi > lo:
        f = (value - lo) / (hi - lo)
    else:
        f = 0.0
    return float(np.clip(f, 0.0, 1.0))

def frac_to_value(gid, frac):
    name, lo, hi, scale = PARAM_GENES[gid]
    frac = float(np.clip(frac, 0.0, 1.0))
    if scale == "log" and lo > 0:
        return float(lo * ((hi / lo) ** frac))
    return float(lo + (hi - lo) * frac)

def mutate_params(params, sigma=SIGMA_FRAC):
    child = params.copy()
    for gid in range(N_GENES):
        f = value_to_frac(gid, child[gid]) + random.gauss(0.0, sigma)
        child[gid] = frac_to_value(gid, f)
    return child

_gt = np.float64(0)
_ancestor = None
def _args():
    return (g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
        g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
        g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
        g_neuron_map, g_synapse_map, g_genome_map, g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
        g_global_genome, g_org_g_ptr, g_org_g_count,
        o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m, o_rec_v_rest, o_rec_v_reset,
        o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,
        g_viscosity, _gt, g_org_lif_steps, g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
        0, 0, voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
        g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI,
        g_org_reward, g_org_elig, g_global_sense_type, g_global_sense_meta, g_global_act_drive,
        g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
        g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay, g_conn_w_dna,
        g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick)

def reset_all():
    global _gt
    g_alive[:] = False; g_org_grid[:] = -1
    g_cam_valid[:] = 0; g_cam_keys[:] = 0; g_cam_tick[:] = 0; g_cam_vals[:] = 0
    g_read_log[0] = 1
    _gt = np.float64(0)

def _run_once(pop_params, Pn):
    """One independent run of the population; returns per-org correct-prediction counts."""
    global _gt
    reset_all()
    for i in range(Pn):
        spawn_organism(i, 200 + i * 500, _ancestor, 250000)
        g_org_params[i] = pop_params[i]
    pred = np.zeros(Pn, dtype=np.int64)
    for tick in range(EVAL_TICKS):
        world_tick_numba(*_args()); _gt += 1
        idx = 1; L = int(g_read_log[0])
        while idx < L:
            t = int(g_read_log[idx])
            if t == 1:
                o = int(g_read_log[idx + 1])
                if o < Pn: pred[o] += 1
                idx += 3
            elif t == 3:
                o = int(g_read_log[idx + 1])
                if o < Pn: pred[o] += 1
                idx += 3
            elif t == 2: idx += 4
            elif t == 4: idx += 3
            elif t == 5: idx += 3
            else: break
        g_read_log[0] = 1
    return pred.astype(np.float64)

def evaluate_population(pop_params):
    """Average correct-prediction fitness over N_REPLICATES independent runs (noise reduction)."""
    Pn = len(pop_params)
    acc = np.zeros(Pn)
    for rep in range(N_REPLICATES):
        acc += _run_once(pop_params, Pn)   # RNG continues -> independent samples
    return acc / N_REPLICATES

def next_generation(pop_params, fitness, neutral=False):
    Pn = len(pop_params)
    if neutral:
        parent_idx = [random.randrange(Pn) for _ in range(K_SELECT)]
    else:
        parent_idx = list(np.argsort(fitness)[-K_SELECT:])  # top K by fitness
    children = [mutate_params(pop_params[parent_idx[i % K_SELECT]]) for i in range(Pn)]
    return np.array(children, dtype=np.float32), parent_idx

# ----------------------------- build world -----------------------------------
print("=" * 72)
print("Rule 21.2 increment 3c — in-engine PARAM-gene evolution under selection")
print("=" * 72)
print("flag EVOLVABLE_CONSTANTS=%s  CAM_KEY_BITS=%d  CAM_SLOTS=%d" % (EVOLVABLE_CONSTANTS, CAM_KEY_BITS, CAM_SLOTS))
print("P=%d  K_select=%d (top %d%%)  G=%d  EVAL_TICKS=%d  N_REPLICATES=%d  sigma_frac=%.2f"
      % (P_POP, K_SELECT, 100 * K_SELECT // P_POP, G_GENERATIONS, EVAL_TICKS, N_REPLICATES, SIGMA_FRAC))

K = 8; NOISE = ord('a'); rng = np.random.RandomState(42)
ram = np.full(RAM_SIZE, NOISE, dtype=np.uint8); pos = 0
while pos + 7 <= RAM_SIZE:
    c1 = rng.randint(0, K); c2 = rng.randint(0, K)
    ram[pos:pos + 7] = [97 + c1, NOISE, NOISE, 97 + c2, NOISE, NOISE, 65 + (c1 + c2) % K]; pos += 7
g_ram[:] = ram

random.seed(SEED); np.random.seed(SEED)
_ancestor = gl.create_intelligent_ancestor()
print("ancestor: %d bytes  (seed %d)" % (len(_ancestor), SEED))

t0 = time.time()
spawn_organism(0, 100, _ancestor, 250000); g_org_params[0] = PARAM_DEFAULTS
world_tick_numba(*_args())
print("JIT warmup: %.1fs  ancestor lif_steps=%d" % (time.time() - t0, int(g_org_lif_steps[0])))

# Initial population: UNIFORM across each gene full fraction range [0.05, 0.95] (like exp77e).
# Same init for BOTH lines so the selected-vs-neutral contrast is fair.
random.seed(SEED + 100)
init_pop = np.array([[frac_to_value(gid, random.uniform(0.05, 0.95)) for gid in range(N_GENES)]
                     for _ in range(P_POP)], dtype=np.float32)

# ----------------------------- evolve ----------------------------------------
def run_line(neutral, label):
    random.seed(SEED + (7 if neutral else 3))   # distinct mutation streams per line
    pop = init_pop.copy()
    history = {"gene_mean": [], "gene_std": [], "mean_fitness": [], "best_fitness": []}
    for gen in range(G_GENERATIONS):
        fitness = evaluate_population(pop)
        history["gene_mean"].append([round(float(x), 4) for x in pop.mean(axis=0)])
        history["gene_std"].append([round(float(x), 4) for x in pop.std(axis=0)])
        history["mean_fitness"].append(round(float(fitness.mean()), 3))
        history["best_fitness"].append(round(float(fitness.max()), 3))
        pop, _ = next_generation(pop, fitness, neutral=neutral)
        print("  [%s] gen %2d: mean_fit=%6.2f  best=%5.1f  camKB=%.2f camSLOTS=%.1f camMATCH=%.2f stdpDIV=%.3f"
              % (label, gen, fitness.mean(), fitness.max(), pop[:, 1].mean(), pop[:, 0].mean(),
                 pop[:, 2].mean(), pop[:, 4].mean()), flush=True)
    return history

print("\n--- SELECTED line (truncation on prediction fitness) ---")
sel_hist = run_line(neutral=False, label="SEL")
print("\n--- NEUTRAL control (random parents, same init + mutation) ---")
neu_hist = run_line(neutral=True, label="NEU")

# ----------------------------- analyse + persist -----------------------------
results = {
    "config": {"seed": SEED, "P": P_POP, "K_select": K_SELECT, "G": G_GENERATIONS,
               "eval_ticks": EVAL_TICKS, "n_replicates": N_REPLICATES, "sigma_frac": SIGMA_FRAC,
               "gene_names": GENE_NAMES,
               "defaults": [round(float(x), 4) for x in PARAM_DEFAULTS],
               "flag": "GENESIS_EVOLVABLE_CONSTANTS=1",
               "fitness": "correct next-symbol predictions (read_log type1+type3) over 180 ticks, averaged over 5 replicates",
               "init": "uniform across each gene full fraction range [0.05,0.95]",
               "structure": "fixed long-lived ancestor (seed 20260725, lif_steps=4)"},
    "selected": sel_hist,
    "neutral": neu_hist,
}
out_json = os.path.join(OUT_DIR, "exp78b_evolution_results.json")
with open(out_json, "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved results -> %s" % out_json)

print("\n=== PARAM-gene drift (gen0 -> final population mean) ===")
print("%-20s %9s %9s %9s" % ("gene", "default", "SEL d", "NEU d"))
sel_g = np.array(sel_hist["gene_mean"]); neu_g = np.array(neu_hist["gene_mean"])
for gid in range(N_GENES):
    dflt = float(PARAM_DEFAULTS[gid])
    print("%-20s %9.3f %+9.3f %+9.3f" % (GENE_NAMES[gid], dflt, sel_g[-1, gid] - sel_g[0, gid], neu_g[-1, gid] - neu_g[0, gid]))
sf = sel_hist["mean_fitness"]; nf = neu_hist["mean_fitness"]
print("\nmean fitness: SELECTED %.2f -> %.2f (peak %.2f)   NEUTRAL %.2f -> %.2f (peak %.2f)"
      % (sf[0], sf[-1], max(sf), nf[0], nf[-1], max(nf)))
sel_gain = max(sf) - sf[0]; neu_gain = max(nf) - nf[0]
print("fitness gain over gen0: SELECTED %+.2f  NEUTRAL %+.2f  (selection advantage %+.2f)"
      % (sel_gain, neu_gain, sel_gain - neu_gain))

# ----------------------------- plots -----------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gens = np.arange(G_GENERATIONS)
    sel_drift_mag = np.abs(sel_g[-1] - sel_g[0])
    top4 = list(np.argsort(sel_drift_mag)[-4:][::-1])
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, gid in zip(axes.ravel(), top4):
        ax.plot(gens, sel_g[:, gid], "o-", color="#2563eb", lw=2, ms=4, label="selected")
        ax.plot(gens, neu_g[:, gid], "s--", color="#9ca3af", lw=1.5, ms=3, label="neutral")
        ax.axhline(float(PARAM_DEFAULTS[gid]), color="#dc2626", ls=":", lw=1.2, label="designer default")
        ax.set_title(GENE_NAMES[gid], fontsize=12, fontweight="bold")
        ax.set_xlabel("generation"); ax.set_ylabel("population mean"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.suptitle("Rule 21.2 (3c): PARAM-gene drift under selection in the FULL engine\n"
                 "(world_tick_numba, flag ON; fitness = correct predictions, 5-replicate mean)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p1 = os.path.join(OUT_DIR, "exp78b_param_drift.png"); fig.savefig(p1, dpi=130); plt.close(fig)
    print("Saved plot -> %s" % p1)

    fig2, ax2 = plt.subplots(figsize=(9, 5))
    ax2.plot(gens, sf, "o-", color="#2563eb", lw=2, ms=4, label="selected")
    ax2.plot(gens, nf, "s--", color="#9ca3af", lw=1.5, ms=3, label="neutral")
    ax2.fill_between(gens, sel_hist["best_fitness"], sf, color="#2563eb", alpha=0.10)
    ax2.set_xlabel("generation"); ax2.set_ylabel("mean correct predictions / 180 ticks (5-rep mean)")
    ax2.set_title("Fitness trajectory: selected climbs, neutral wanders", fontsize=12, fontweight="bold")
    ax2.grid(alpha=0.3); ax2.legend()
    fig2.tight_layout()
    p2 = os.path.join(OUT_DIR, "exp78b_fitness_curve.png"); fig2.savefig(p2, dpi=130); plt.close(fig2)
    print("Saved plot -> %s" % p2)
except Exception as e:
    print("[plot skipped: %s]" % e)
print("\nDONE.")
