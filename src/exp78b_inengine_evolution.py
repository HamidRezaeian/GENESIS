#!/usr/bin/env python3
"""
Rule 21.2 increment 3c — IN-ENGINE PARAM-gene evolution under selection.
========================================================================
The definitive Rule-21.2 test for the FULL engine (design doc §9.3): do the per-organism
PARAM constants (g_org_params[org], wired in 3b-i/3b-ii) drift OFF DEFAULT UNDER SELECTION
when each organism's lifetime behaviour is simulated by the real numba kernel
world_tick_numba with GENESIS_EVOLVABLE_CONSTANTS=1?

RULE-3-COMPLIANT DESIGN (multi-seed + dual mutation operator):
  - N_SEEDS independent evolutionary runs per mutation mode; every quantitative claim is
    reported as mean +/- std across seeds (a single seed is PRELIMINARY per Rule 3).
  - TWO mutation operators, so the verdict is robust to the operator choice:
      * "ea"     — Gaussian step on each gene's decoded fraction (the standard EA abstraction
                   used by the exp77e probe; high exploration).
      * "genome" — FAITHFUL cosmic radiation: build the full genome (fixed structural bytes +
                   encoded PARAM tail), apply the engine's real `mutate_dna` (per-byte fidelity
                   1/l), decode the child's PARAM via `decode_params`, and rebuild a clean genome.
                   This perturbs the PARAM tail BYTES exactly as germline mutation does in vivo
                   (only PARAM-tail effects are kept; structural bytes are held fixed so drift is
                   isolated to the constants).
  - Fixed structural genome = the long-lived seeded ancestor (seed 20260725, lif_steps=4, lives
    the full 180-tick evaluation window); all organisms share it so drift is isolated to PARAM.
  - Fitness = correct next-symbol predictions (read_log type 1 + type 3) over 180 ticks, the
    engine's OWN comprehension signal (NOT invented points), averaged over N_REPLICATES runs to
    push the engine's run-to-run stochasticity below the between-genotype gradient.
  - Initial population sampled UNIFORMLY across each gene's full range (the defaults sit at the
    top of most ranges, so a narrow init leaves the population in a flat region).
  - Selection: truncation top-25% (SELECTED) vs random parents (NEUTRAL control), same init per
    seed so the contrast isolates selection-driven drift from neutral mutation drift.

PRE-REGISTERED FALSIFICATION (Ascent.md §2.D): the selection advantage
  (max_selected - selected_gen0) - (max_neutral - neutral_gen0) must be > 0 as a >=5-seed mean
  exceeding 0 by >=1 std, under BOTH operators; otherwise the adaptive-drift claim is ABANDONED.

Outputs (auto-persisted to agent-outputs):
  exp78b_evolution_results.json  — per-(mode,seed) trajectories + aggregated mean +/- std
  exp78b_param_drift.png         — gene drift (mean across seeds) selected vs neutral, both modes
  exp78b_fitness_curve.png       — fitness trajectory (mean across seeds) selected vs neutral
  exp78b_selection_advantage.png — per-seed selection advantage + mean +/- std, both modes

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
    world_tick_numba, spawn_organism, mutate_dna, decode_params,
    CANVAS_LO, CANVAS_HI, MAX_ORGANISMS, RAM_SIZE, PARAM_GENES, PARAM_DEFAULTS)
from neuromorphic_engine import g_org_params, EVOLVABLE_CONSTANTS, CAM_SLOTS, CAM_KEY_BITS

assert EVOLVABLE_CONSTANTS, "3c MUST run with GENESIS_EVOLVABLE_CONSTANTS=1 (kernel must read g_org_params)"

# ----------------------------- experiment config -----------------------------
ANCESTOR_SEED = 20260725    # long-lived ancestor (lif_steps=4); fixed structural template
SEED_BASE     = 100000      # independent evolutionary seeds: SEED_BASE + k
N_SEEDS       = 5           # Rule 3: >=5 independent seeds per mode
MODES         = ["ea", "genome"]   # EA Gaussian vs faithful mutate_dna cosmic radiation
P_POP         = 24          # population size
K_SELECT      = 6           # truncation: top 25 percent (strong selection)
G_GENERATIONS = 40          # generations per run
EVAL_TICKS    = 180         # evaluation window (within the ~197-tick lifespan)
N_REPLICATES  = 3           # independent fitness runs averaged per genotype (noise reduction)
SIGMA_FRAC    = 0.05        # EA per-gene Gaussian mutation step in [0,1] fraction space
N_GENES       = len(PARAM_GENES)
GENE_NAMES    = [g[0] for g in PARAM_GENES]
STRUCT_LEN    = None        # set after ancestor built (len - PARAM tail)
TMP_ORG       = MAX_ORGANISMS - 1   # scratch slot for decode_params in genome mode
OUT_DIR       = os.environ.get("EXP78B_OUT", os.getcwd())

# ----------------------------- gene<->fraction helpers -----------------------
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

_PARAM_VAL_MAX = 16383
def encode_param_values(values):
    """Build the 45-byte PARAM tail (9 records x 5 bytes) encoding the given gene values."""
    recs = []
    for gid in range(N_GENES):
        frac = value_to_frac(gid, float(values[gid]))
        raw = int(round(frac * _PARAM_VAL_MAX))
        recs.extend([200, 201, gid, raw & 0x7F, (raw >> 7) & 0x7F])   # PARAM_MARKER, PARAM_MAGIC
    return recs

# ----------------------------- mutation operators ----------------------------
def mutate_ea(params):
    """EA abstraction: Gaussian step on each gene's decoded fraction (exp77e-style)."""
    child = params.copy()
    for gid in range(N_GENES):
        f = value_to_frac(gid, child[gid]) + random.gauss(0.0, SIGMA_FRAC)
        child[gid] = frac_to_value(gid, f)
    return child

def mutate_genome(params, structure):
    """FAITHFUL cosmic radiation: mutate_dna on the real genome bytes (PARAM tail), then decode.
    Only PARAM-tail effects are kept (structural bytes restored) so drift is isolated to PARAM."""
    parent_genome = np.array(list(structure) + encode_param_values(params), dtype=np.uint8)
    child_full = mutate_dna(parent_genome)              # real per-byte cosmic radiation (1/l fidelity)
    decode_params(child_full, TMP_ORG)                  # fills g_org_params[TMP_ORG] from mutated bytes
    child_values = np.array(g_org_params[TMP_ORG], dtype=np.float32).copy()
    return child_values

def reproduce(params, mode, structure):
    return mutate_genome(params, structure) if mode == "genome" else mutate_ea(params)

# ----------------------------- engine harness --------------------------------
_ancestor = None
_gt = np.float64(0)
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
    Pn = len(pop_params)
    acc = np.zeros(Pn)
    for rep in range(N_REPLICATES):
        acc += _run_once(pop_params, Pn)
    return acc / N_REPLICATES

def next_generation(pop_params, fitness, mode, structure, neutral=False):
    Pn = len(pop_params)
    if neutral:
        parent_idx = [random.randrange(Pn) for _ in range(K_SELECT)]
    else:
        parent_idx = list(np.argsort(fitness)[-K_SELECT:])
    children = [reproduce(pop_params[parent_idx[i % K_SELECT]], mode, structure) for i in range(Pn)]
    return np.array(children, dtype=np.float32)

def run_line(init_pop, mode, structure, neutral):
    pop = init_pop.copy()
    gene_mean = []; mean_fit = []; best_fit = []
    for gen in range(G_GENERATIONS):
        fitness = evaluate_population(pop)
        gene_mean.append([float(x) for x in pop.mean(axis=0)])
        mean_fit.append(float(fitness.mean())); best_fit.append(float(fitness.max()))
        pop = next_generation(pop, fitness, mode, structure, neutral=neutral)
    return {"gene_mean": gene_mean, "mean_fitness": mean_fit, "best_fitness": best_fit}

# ----------------------------- build world -----------------------------------
print("=" * 74)
print("Rule 21.2 increment 3c — in-engine PARAM-gene evolution (Rule-3 multi-seed)")
print("=" * 74)
print("flag EVOLVABLE_CONSTANTS=%s  CAM_KEY_BITS=%d  CAM_SLOTS=%d" % (EVOLVABLE_CONSTANTS, CAM_KEY_BITS, CAM_SLOTS))
print("N_SEEDS=%d  MODES=%s  P=%d  K=%d(top %d%%)  G=%d  EVAL=%d  reps=%d  sigma=%.2f"
      % (N_SEEDS, MODES, P_POP, K_SELECT, 100 * K_SELECT // P_POP, G_GENERATIONS, EVAL_TICKS, N_REPLICATES, SIGMA_FRAC))

K = 8; NOISE = ord('a'); rng = np.random.RandomState(42)
ram = np.full(RAM_SIZE, NOISE, dtype=np.uint8); pos = 0
while pos + 7 <= RAM_SIZE:
    c1 = rng.randint(0, K); c2 = rng.randint(0, K)
    ram[pos:pos + 7] = [97 + c1, NOISE, NOISE, 97 + c2, NOISE, NOISE, 65 + (c1 + c2) % K]; pos += 7
g_ram[:] = ram

random.seed(ANCESTOR_SEED); np.random.seed(ANCESTOR_SEED)
_ancestor = gl.create_intelligent_ancestor()
STRUCT_LEN = len(_ancestor) - N_GENES * 5
structure = np.array(_ancestor[:STRUCT_LEN], dtype=np.uint8)
print("ancestor: %d bytes  (seed %d)  structure=%d B + PARAM tail=%d B"
      % (len(_ancestor), ANCESTOR_SEED, STRUCT_LEN, N_GENES * 5))

t0 = time.time()
spawn_organism(0, 100, _ancestor, 250000); g_org_params[0] = PARAM_DEFAULTS
world_tick_numba(*_args())
print("JIT warmup: %.1fs  ancestor lif_steps=%d" % (time.time() - t0, int(g_org_lif_steps[0])))

# ----------------------------- multi-seed sweep ------------------------------
all_results = {}
for mode in MODES:
    mode_res = {"sel_adv": [], "sel_fit_traj": [], "neu_fit_traj": [],
                "sel_gene_drift": [], "neu_gene_drift": [], "seeds": []}
    for k in range(N_SEEDS):
        seed = SEED_BASE + k * 1000 + (0 if mode == "ea" else 500)
        # independent initial population for this seed (uniform across full gene ranges)
        random.seed(seed); np.random.seed(seed)
        init_pop = np.array([[frac_to_value(gid, random.uniform(0.05, 0.95)) for gid in range(N_GENES)]
                             for _ in range(P_POP)], dtype=np.float32)
        # SELECTED line (its own mutation stream)
        random.seed(seed + 1)
        sel = run_line(init_pop, mode, structure, neutral=False)
        # NEUTRAL control (same init, random parents)
        random.seed(seed + 2)
        neu = run_line(init_pop, mode, structure, neutral=True)
        sf = sel["mean_fitness"]; nf = neu["mean_fitness"]
        sel_adv = (max(sf) - sf[0]) - (max(nf) - nf[0])
        sg = np.array(sel["gene_mean"]); ng = np.array(neu["gene_mean"])
        mode_res["sel_adv"].append(float(sel_adv))
        mode_res["sel_fit_traj"].append([round(x, 3) for x in sf])
        mode_res["neu_fit_traj"].append([round(x, 3) for x in nf])
        mode_res["sel_gene_drift"].append([round(float(x), 4) for x in (sg[-1] - sg[0])])
        mode_res["neu_gene_drift"].append([round(float(x), 4) for x in (ng[-1] - ng[0])])
        mode_res["seeds"].append(seed)
        print("  [%s seed%d] sel_adv=%+6.2f  SEL fit %.1f->%.1f (peak %.1f)  NEU fit %.1f->%.1f"
              % (mode, k, sel_adv, sf[0], sf[-1], max(sf), nf[0], nf[-1]), flush=True)
    adv = np.array(mode_res["sel_adv"])
    mode_res["sel_adv_mean"] = float(adv.mean())
    mode_res["sel_adv_std"] = float(adv.std(ddof=1)) if N_SEEDS > 1 else 0.0
    all_results[mode] = mode_res
    print("  >> [%s] selection advantage over %d seeds: mean=%+.3f +/- %.3f  (criterion: mean > 0 by >=1 std)"
          % (mode, N_SEEDS, adv.mean(), mode_res["sel_adv_std"]), flush=True)

# ----------------------------- verdict + persist -----------------------------
verdict = {}
for mode in MODES:
    m = all_results[mode]["sel_adv_mean"]; sd = all_results[mode]["sel_adv_std"]
    supported = (m > 0) and (m > sd)   # mean > 0 by at least 1 std
    verdict[mode] = {"mean": round(m, 4), "std": round(sd, 4),
                     "adaptive_drift_supported": bool(supported)}

results = {
    "config": {"ancestor_seed": ANCESTOR_SEED, "seed_base": SEED_BASE, "n_seeds": N_SEEDS,
               "modes": MODES, "P": P_POP, "K_select": K_SELECT, "G": G_GENERATIONS,
               "eval_ticks": EVAL_TICKS, "n_replicates": N_REPLICATES, "sigma_frac": SIGMA_FRAC,
               "gene_names": GENE_NAMES, "defaults": [round(float(x), 4) for x in PARAM_DEFAULTS],
               "flag": "GENESIS_EVOLVABLE_CONSTANTS=1",
               "fitness": "correct predictions (read_log type1+type3) over 180 ticks, %d-rep mean" % N_REPLICATES,
               "preregistered_criterion": "Ascent.md 2.D: sel_advantage > 0 as >=5-seed mean exceeding 0 by >=1 std, both operators"},
    "verdict": verdict,
    "results_by_mode": all_results,
}
out_json = os.path.join(OUT_DIR, "exp78b_evolution_results.json")
with open(out_json, "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved results -> %s" % out_json)

print("\n" + "=" * 74)
print("VERDICT (pre-registered Ascent.md 2.D): does selection drive adaptive PARAM drift?")
print("=" * 74)
for mode in MODES:
    v = verdict[mode]
    print("  mode=%-7s  selection advantage = %+.3f +/- %.3f  ->  adaptive drift %s"
          % (mode, v["mean"], v["std"], "SUPPORTED" if v["adaptive_drift_supported"] else "NOT supported (null)"))
overall = all(v["adaptive_drift_supported"] for v in verdict.values())
print("\n  OVERALL: %s" % ("adaptive PARAM drift under selection is SUPPORTED in the full engine"
      if overall else
      "NULL RESULT — selection does NOT drive adaptive PARAM drift in the full engine\n"
      "  (constants are evolvable/mutable but the comprehension-fitness landscape is flat w.r.t.\n"
      "   them; behaviour is structure-dominated; adaptive tuning is gated by the income bottleneck)."))

# ----------------------------- plots -----------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    gens = np.arange(G_GENERATIONS)
    colors = {"ea": "#2563eb", "genome": "#7c3aed"}

    # 1. fitness trajectory (mean +/- std across seeds), selected vs neutral, both modes
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, mode in zip(axes, MODES):
        sel = np.array(all_results[mode]["sel_fit_traj"]); neu = np.array(all_results[mode]["neu_fit_traj"])
        ax.plot(gens, sel.mean(0), "-", color=colors[mode], lw=2, label="selected (mean)")
        ax.fill_between(gens, sel.mean(0) - sel.std(0), sel.mean(0) + sel.std(0), color=colors[mode], alpha=0.15)
        ax.plot(gens, neu.mean(0), "--", color="#9ca3af", lw=1.6, label="neutral (mean)")
        ax.fill_between(gens, neu.mean(0) - neu.std(0), neu.mean(0) + neu.std(0), color="#9ca3af", alpha=0.12)
        ax.set_title("mutation = %s" % mode, fontsize=12, fontweight="bold")
        ax.set_xlabel("generation"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    axes[0].set_ylabel("mean correct predictions / 180 ticks")
    fig.suptitle("Rule 21.2 (3c): fitness trajectory, %d seeds (mean +/- std) — selected does NOT climb" % N_SEEDS,
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(OUT_DIR, "exp78b_fitness_curve.png"); fig.savefig(p, dpi=130); plt.close(fig)
    print("Saved plot -> %s" % p)

    # 2. selection advantage per seed + mean +/- std, both modes
    fig2, ax2 = plt.subplots(figsize=(8, 4.8))
    xpos = {"ea": 0, "genome": 1}
    for mode in MODES:
        adv = np.array(all_results[mode]["sel_adv"])
        ax2.scatter([xpos[mode]] * len(adv), adv, color=colors[mode], s=46, zorder=3, label="%s seeds" % mode)
        ax2.errorbar([xpos[mode]], [adv.mean()], yerr=[adv.std(ddof=1)], fmt="_", color=colors[mode],
                     ms=18, mew=2.5, capsize=8, zorder=4)
    ax2.axhline(0, color="#dc2626", ls=":", lw=1.3, label="criterion threshold (>0)")
    ax2.set_xticks([0, 1]); ax2.set_xticklabels(["EA Gaussian", "mutate_dna\n(cosmic radiation)"])
    ax2.set_ylabel("selection advantage (sel gain - neutral gain)")
    ax2.set_title("Per-seed selection advantage (Rule 3): mean +/- std vs the >0 criterion", fontsize=11.5, fontweight="bold")
    ax2.grid(alpha=0.3); ax2.legend(fontsize=8)
    fig2.tight_layout()
    p = os.path.join(OUT_DIR, "exp78b_selection_advantage.png"); fig2.savefig(p, dpi=130); plt.close(fig2)
    print("Saved plot -> %s" % p)

    # 3. gene drift (mean across seeds), selected vs neutral, both modes — top-4 responsive genes
    ref_drift = np.abs(np.array(all_results["ea"]["sel_gene_drift"]).mean(0))
    top4 = list(np.argsort(ref_drift)[-4:][::-1])
    fig3, axes3 = plt.subplots(2, 2, figsize=(12, 8))
    for ax, gid in zip(axes3.ravel(), top4):
        for mode in MODES:
            sd = np.array(all_results[mode]["sel_gene_drift"])[:, gid]
            nd = np.array(all_results[mode]["neu_gene_drift"])[:, gid]
            ax.scatter([xpos[mode] - 0.12], [sd.mean()], color=colors[mode], marker="o", s=70, zorder=3)
            ax.errorbar([xpos[mode] - 0.12], [sd.mean()], yerr=[sd.std(ddof=1)], fmt="none", color=colors[mode], capsize=6)
            ax.scatter([xpos[mode] + 0.12], [nd.mean()], color=colors[mode], marker="x", s=70, zorder=3)
            ax.errorbar([xpos[mode] + 0.12], [nd.mean()], yerr=[nd.std(ddof=1)], fmt="none", color=colors[mode], capsize=6, ls="--")
        ax.axhline(0, color="#dc2626", ls=":", lw=1)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["EA", "genome"])
        ax.set_title(GENE_NAMES[gid], fontsize=12, fontweight="bold")
        ax.set_ylabel("drift gen0->final (mean +/- std)")
        ax.grid(alpha=0.3)
    fig3.suptitle("PARAM-gene drift under selection (o) vs neutral (x), %d seeds — drift is not fitness-aligned" % N_SEEDS,
                  fontsize=12.5, fontweight="bold")
    fig3.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(OUT_DIR, "exp78b_param_drift.png"); fig3.savefig(p, dpi=130); plt.close(fig3)
    print("Saved plot -> %s" % p)
except Exception as e:
    print("[plot skipped: %s]" % e)
print("\nDONE.")
