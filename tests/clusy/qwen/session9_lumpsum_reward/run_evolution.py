#!/usr/bin/env python3
"""
Session 9 — Lump-Sum Multi-Byte Reward (built on the Exp 87 metabolic-ceiling driver).
Exp 87 — Metabolic-Ceiling Evolution: does STRUCTURE evolve under the EXISTING
grounded income pressure (Rule 7 emergent efficiency), and do the PARAM genes then
drift adaptively once viability is achievable?
================================================================================

WHY THIS EXPERIMENT (measured, session 7 — see the audit notebook + Docs/Result.md):
  The seeded ancestor (create_intelligent_ancestor, seed 20260725: 65 neurons / 93
  synapses / lif_steps=4) is STRUCTURALLY BANKRUPT. Measured per-tick economics:
    - income quantum (one full correct prediction) = CELL_STATES = 256 cycles
    - PURE-IDLE cost (brain merely existing, zero income possible) = 436 cycles/tick
    - cost on no-prediction ticks = 724 cycles/tick ; predicting ticks ~880 cycles/tick
    - fraction of ticks net-positive = 0.000 in EVERY condition, including pure-repeat
      content where the ancestor predicts 250/250 correctly.
  Idle cost is dominated by `total_atp += n_count * CYCLES_PER_NEURON_UPDATE` (engine
  ~L1329) plus one CYCLES_PER_SYNAPSE_READ per synapse per tick — i.e. STRUCTURE
  (n_neurons, n_synapses), which the 9 PARAM genes do NOT move. exp78b froze this
  expensive structure and evolved only the constants, so it searched a constant-space
  that contains NO viable point: no tuning of constants makes a 436-cycle/tick brain
  survive on 256 cycles/tick. Its flat fitness is a structural bankruptcy, not a missing
  income gradient and not a constants problem.

  The income mechanism is ALREADY Rule-21-grounded (gain = (net/8)*CELL_STATES drawn from
  finite per-cell fuel; cost = measured CYCLES_PER_*; death at energy<=0; reproduction
  spends energy). It must NOT be "boosted" — a fiat income multiplier or cost discount is
  exactly the rigged game mechanic Rule 7 / Rule 21 forbid (and the engine's DIGESTION
  comment already bans "a magic multiplier").

  NON-RIGGED RESOLUTION tested here = Rule 7 itself: let STRUCTURE evolve under the
  EXISTING grounded income/survival/reproduction pressure so selection discovers cheap
  brains whose idle cost fits under the 256/tick budget. The genesis_lab colony already
  SUSTAINS (pop 596-600, refuge=0) on 00_Graded via cheaper brains than the 65n ancestor,
  proving such brains are reachable. We additionally A/B the documented recruitment lever
  STDP_TARGET (Exp 35 dendritic-error delta rule — autotelic, constant-free, "the
  recruitment gradient STDP3C structurally cannot" supply), default-OFF, which gates the
  substrate's ability to learn novel predictions (echo -> comprehension).

DESIGN (faithful to genesis_lab.sim_loop; NO kernel change; NO income/cost scaling):
  - Real survival: death at energy <= 0 (kernel).
  - Real reproduction: kernel sets b_energy[i] = energy/2 when energy >= copy_cost
    (engine L2181-2187); the driver applies the engine's real `mutate_dna` to the FULL
    genome (structure + PARAM tail) and spawns the child (genesis_lab L1616-1633).
    Lineages that fail to earn bleed out (energy halves every reproduction).
  - Architecture-derived seed energy (SEED_ENERGY = -1 sentinel): a founder is born
    holding (genome_bytes + neurons + synapses) * CELL_STATES — the matter-energy it is
    built from. No hand-set bankroll (Rule 17 clean).
  - Contiguous 00_Graded scroll (the bootstrap curriculum genesis_lab reports sustains).
  - Continuous reading-fuel regrow toward CELL_STATES (genesis_lab DEPLETE regrow).
  - Minimal Rule-10/14 refugium: if n_alive < REFUGE_FLOOR, germinate from the fossil
    gene bank (genesis_lab seed_refuge); the germination rate is REPORTED so the Rule-14
    survivorship confound is visible (flag if > 5% of ticks).
  - GENESIS_EVOLVABLE_CONSTANTS=1 so the PARAM genes are live and decoded at spawn.
  - A/B STDP_TARGET via compile-time env flag -> run as two separate processes.

IDLE-COST METRIC (validated): idle_cost ~= n_neurons*CYCLES_PER_NEURON_UPDATE
  + n_synapses*CYCLES_PER_SYNAPSE_READ. For the ancestor this gives 428 vs the measured
  Cond-C value of 436 (ratio 0.98) — the synapse fabric is read once per world-tick, not
  per LIF substep. Both terms are MEASURED native cycles (physical_cost_model), so the
  metric is hardware-grounded, not a fitted score.

PRE-REGISTERED FALSIFICATION:
  H1 (Rule-7 efficiency): the living-population mean idle-cost estimate DECREASES over
     generations toward/under the 256/tick income quantum (brains get cheaper). If it does
     not move, structure is not evolving toward viability -> the ceiling is harder than
     hypothesised (record as a negative result).
  H2 (adaptive PARAM drift): once the population sustains, the living-population PARAM-gene
     means show a sustained directional trend (|linear slope| > 2x the per-interval std),
     i.e. drift that is NOT a random walk. If flat, constants remain neutral even under a
     real income gradient (a stronger null than exp78b's proxy).
  H3 (recruitment lever): STDP_TARGET=1 raises comprehension income (correct preds/tick)
     and/or viability (n_alive, lower refugium rate) vs STDP_TARGET=0.

RULE 3: N_SEEDS independent seeds per arm; every quantitative claim is mean +/- std.

USAGE:
  python exp87_metabolic_ceiling_evolution.py <STDP_TARGET 0|1> [N_SEEDS] [N_TICKS] [OUT_DIR]
"""
import os, sys, json, time, random


def _find_repo_root():
    """Walk up from this script to the GENESIS repo root (the dir holding src/ and Books/).
    Makes the driver location-independent (it lives under tests/clusy/qwen/exp87_metabolic_ceiling/)."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "src")) and os.path.isdir(os.path.join(d, "Books")):
            return d
        d = os.path.dirname(d)
    return "/home/user/repos/GENESIS"  # fallback (matches the exp30_ablation convention)


_REPO_ROOT = _find_repo_root()
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- compile-time flags MUST be set before importing the engine ----
_STDP_TARGET = sys.argv[1] if len(sys.argv) > 1 else "0"
assert _STDP_TARGET in ("0", "1"), "arg1 must be STDP_TARGET 0|1"
os.environ["GENESIS_WMEM"] = "1"
os.environ["GENESIS_CAM"] = "1"
os.environ["GENESIS_CAM_KEY_BITS"] = "8"
os.environ["GENESIS_STDP"] = "1"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_EVOLVABLE_CONSTANTS"] = "1"
os.environ.setdefault("GENESIS_DEPLETE", "1")   # Session 9: env-controllable (DEPLETE=0 isolates the lump-sum timing change from the finite-fuel cap)
# ---- Session 9 lump-sum income (feature-flagged, default OFF = Exp-87-identical baseline) ----
os.environ.setdefault("GENESIS_INCOME_FOOTPRINT", "0")
os.environ.setdefault("GENESIS_INCOME_LUMP_SUM", "0")
os.environ.setdefault("GENESIS_LUMPSUM_K", "8")
os.environ.setdefault("GENESIS_STDP3", "0")
os.environ.setdefault("GENESIS_STDP3C", "0")
os.environ["GENESIS_STDP_TARGET"] = _STDP_TARGET   # the A/B recruitment lever (compile-time)

N_SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
N_TICKS = int(sys.argv[3]) if len(sys.argv) > 3 else 20000
OUT_DIR = sys.argv[4] if len(sys.argv) > 4 else os.path.join(_SCRIPT_DIR, "results")
os.makedirs(OUT_DIR, exist_ok=True)

# ---- experiment constants (documented, Rule-17 disclosed in the header) ----
POP_SIZE      = 200     # seeded founders (genesis_lab seed_universe scale)
SAMPLE_EVERY  = 200     # metric snapshot cadence (ticks)
REFUGE_FLOOR  = 30      # genesis_lab Phase-1 (learning) floor: a COLD-START run needs a viable
                        # population for selection to act on; Phase-4 (=5, near-zero safety net) is
                        # for MATURE colonies after 1.5M ticks of evolution. Germs still must earn
                        # (SEED_ENERGY), so death stays a gradient, not abolished (Rule 10/14).
SEED          = 20260725
SCROLL_PATH   = os.path.join(_REPO_ROOT, "Books", "English", "00_Graded.txt")

import numpy as np
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))
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
    g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay, g_conn_w_dna, g_conn_w_slow,
    g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick, g_clear_count,
    g_org_run, g_lump_acc,   # Session 9 lump-sum work-unit state
    world_tick_numba, spawn_organism, mutate_dna, create_intelligent_ancestor,
    remember_fossil, seed_refuge, free_block,
    CANVAS_LO, CANVAS_HI, RAM_SIZE, MAX_ORGANISMS, CELL_STATES, SEED_ENERGY,
    DEPLETE_REGROW, PARAM_GENES, N_PARAM_GENES)
from neuromorphic_engine import (g_org_params, EVOLVABLE_CONSTANTS, STDP_TARGET,
    CYCLES_PER_NEURON_UPDATE, CYCLES_PER_SYNAPSE_READ,
    INCOME_FOOTPRINT, INCOME_LUMP_SUM, LUMPSUM_K, FOOTPRINT_QUANTUM, CLEAR_THRESHOLD)
assert EVOLVABLE_CONSTANTS, "Exp 87 requires GENESIS_EVOLVABLE_CONSTANTS=1"
PARAM_NAMES = [pg[0] for pg in PARAM_GENES]
# Session 10 fix: MAX_ORGANISMS is now SUBSTRATE-DERIVED (Session 9: <=1/4 RAM / 12.1 MB-per-org).
# On an 8 GiB host that is 164, which is below the Exp-87-era literal POP_SIZE=200 -> spawning founder
# #164 indexed out of bounds. Clamp the founding population to the derived capacity (Rule-17 disclosed).
POP_SIZE = min(POP_SIZE, MAX_ORGANISMS)

print("=" * 78)
print("Exp 87 — Metabolic-Ceiling Evolution")
print("  STDP_TARGET = %s   N_SEEDS = %d   N_TICKS = %d   POP_SIZE = %d"
      % (_STDP_TARGET, N_SEEDS, N_TICKS, POP_SIZE))
print("  CELL_STATES(income quantum) = %.0f   CYCLES_PER_NEURON_UPDATE = %.3f"
      % (float(CELL_STATES), float(CYCLES_PER_NEURON_UPDATE)))
print("  CYCLES_PER_SYNAPSE_READ = %.3f   DEPLETE_REGROW = %.3f"
      % (float(CYCLES_PER_SYNAPSE_READ), float(DEPLETE_REGROW)))
print("=" * 78, flush=True)

_gt = np.float64(0)
def _args():
    """Exact world_tick_numba argument tuple (oracle slots passed as 0,0 = oracle OFF,
    identical to the validated audit harness)."""
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
        g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay, g_conn_w_dna, g_conn_w_slow,
        g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick, g_clear_count,
        g_org_run, g_lump_acc)

def idle_cost_estimate(n_count, s_count):
    """Per-tick idle-cost proxy from the MEASURED cost terms the kernel actually accrues:
    the viscous step maintains ALL neurons every tick (n_count*CYCLES_PER_NEURON_UPDATE,
    engine ~L1329) plus one synapse-read per synapse per world-tick. Validated against the
    Cond-C no-income measurement: ancestor 65n/93s -> 428 estimate vs 436 measured (0.98)."""
    return (float(n_count) * float(CYCLES_PER_NEURON_UPDATE)
            + float(s_count) * float(CYCLES_PER_SYNAPSE_READ))

def lay_scroll():
    """Lay the 00_Graded curriculum as ONE CONTIGUOUS scroll (genesis_lab Exp-11 structure:
    a saccading reader walks +1 along text it decodes and almost never steps into vacuum).
    Pure world structure — no reward constant touched."""
    with open(SCROLL_PATH, "rb") as f:
        gb = list(f.read())
    g_ram[:] = 0
    n = len(gb)
    for i in range(RAM_SIZE):
        g_ram[i] = gb[i % n]
    g_read_fuel[:] = np.float32(CELL_STATES)   # every cell starts full
    g_cell_owner[:] = -1
    g_read_hits[:] = 0

def reset_world():
    global _gt
    g_alive[:] = False
    g_org_grid[:] = -1
    g_cam_valid[:] = 0; g_cam_keys[:] = 0; g_cam_tick[:] = 0; g_cam_vals[:] = 0
    g_read_log[0] = 1
    lay_scroll()
    _gt = np.float64(0)
    gl.fossil_pool.clear()   # each seed starts from an independent cold gene bank

def drain_read_log():
    """Drain this tick's read_log; return (correct, miss) next-symbol prediction counts
    summed over the whole population. correct = type1 (stationary full match) + type3
    (correct prediction while moving); miss = type2. Resets the log for the next tick."""
    idx = 1; L = int(g_read_log[0]); correct = 0; miss = 0
    while idx < L:
        t = int(g_read_log[idx])
        if t == 1 or t == 3:
            correct += 1; idx += 3
        elif t == 2:
            miss += 1; idx += 4
        elif t == 4 or t == 5:
            idx += 3
        else:
            break
    g_read_log[0] = 1
    return correct, miss

def living_idx():
    return np.where(g_alive)[0]

def snapshot(tick, correct_acc, miss_acc, refuge_acc, frac_net_pos=0.0, max_run=0):
    """One metric sample over the LIVING population."""
    liv = living_idx()
    n = len(liv)
    rec = {"tick": int(tick), "n_alive": int(n),
           "refuge_germ_cum": int(refuge_acc),
           "correct_per_tick": float(correct_acc), "miss_per_tick": float(miss_acc),
           "frac_net_pos": float(frac_net_pos), "max_run": int(max_run)}   # Session 9
    if n > 0:
        nc = g_org_n_count[liv]; sc = g_org_s_count[liv]; ls = g_org_lif_steps[liv]
        ice = np.array([idle_cost_estimate(int(nc[k]), int(sc[k])) for k in range(n)])
        rec["n_neurons_mean"] = float(nc.mean()); rec["n_neurons_min"] = float(nc.min())
        rec["n_syn_mean"] = float(sc.mean()); rec["lif_steps_mean"] = float(ls.mean())
        rec["idle_cost_mean"] = float(ice.mean()); rec["idle_cost_min"] = float(ice.min())
        rec["energy_mean"] = float(g_energy[liv].mean())
        pm = g_org_params[liv].mean(axis=0)
        for g in range(N_PARAM_GENES):
            rec["param_%s" % PARAM_NAMES[g]] = float(pm[g])
    else:
        rec["n_neurons_mean"] = rec["idle_cost_mean"] = rec["idle_cost_min"] = float("nan")
    return rec

def validate_idle_estimate():
    """Run the seeded ancestor on a no-income scroll (byte=1, excluded by the reading gate)
    and confirm the idle-cost estimate matches the measured per-tick energy loss."""
    global _gt
    random.seed(SEED); np.random.seed(SEED)   # validate the SAME ancestor run_seed(SEED) uses
    reset_world()
    g_ram[:] = 1                      # byte=1 < 32 -> excluded from reading income
    g_read_fuel[:] = np.float32(CELL_STATES)
    anc = create_intelligent_ancestor()
    spawn_organism(0, 200, anc, -1.0) # architecture-derived seed
    nc = int(g_org_n_count[0]); sc = int(g_org_s_count[0]); ls = int(g_org_lif_steps[0])
    e0 = float(g_energy[0]); g_read_log[0] = 1
    T = 150
    for _ in range(T):
        world_tick_numba(*_args()); _gt += 1; g_read_log[0] = 1
        if not g_alive[0]:
            break
    e1 = float(g_energy[0])
    measured = (e0 - e1) / T
    est = idle_cost_estimate(nc, sc)
    print("[validate] ancestor %dn/%ds/lif%d  seed_energy=%.0f" % (nc, sc, ls, e0))
    print("[validate] idle cost  measured=%.1f  estimate=%.1f  (ratio %.2f)"
          % (measured, est, est / measured if measured else float('nan')), flush=True)
    reset_world()
    return {"n_neurons": nc, "n_syn": sc, "lif_steps": ls, "seed_energy": e0,
            "idle_measured": measured, "idle_estimate": est}

def run_seed(seed):
    """One evolutionary run under real survival/reproduction. Returns the metric series."""
    global _gt
    random.seed(seed); np.random.seed(seed)
    reset_world()
    anc = create_intelligent_ancestor()
    spawned = 0
    for i in range(POP_SIZE):
        pos = -1
        for _ in range(2000):
            p = random.randint(0, RAM_SIZE - 1)
            if g_org_grid[p] == -1 and 32 <= g_ram[p] <= 126 and g_ram[p] != 0x55:
                pos = p; break
        if pos < 0:
            pos = random.randint(0, RAM_SIZE - 1)
        if spawn_organism(i, pos, anc, SEED_ENERGY):
            spawned += 1
    print("  [seed %d] spawned %d founders" % (seed, spawned), flush=True)

    series = []
    correct_acc = 0.0; miss_acc = 0.0; refuge_acc = 0
    net_pos_acc = 0; max_run_run = 0; prev_E_sum = float(np.sum(g_energy[g_alive]))   # Session 9
    t0 = time.time()
    for tick in range(N_TICKS):
        n_alive, n_births = world_tick_numba(*_args())
        _gt += 1
        # ---- Session 9 ceiling metrics: population net-positive tick + longest work-unit run ----
        E_sum = float(np.sum(g_energy[g_alive]))
        if E_sum > prev_E_sum:
            net_pos_acc += 1
        prev_E_sum = E_sum
        mr = int(np.max(g_org_run)) if g_org_run.size else 0
        if mr > max_run_run:
            max_run_run = mr
        # ---- real reproduction: full-genome mutation of each child (genesis_lab L1616-1633) ----
        for i in range(n_births):
            child_dna = mutate_dna(g_b_genomes[i, :g_b_g_count[i]])
            slot = -1
            for j in range(MAX_ORGANISMS):
                if not g_alive[j]:
                    slot = j; break
            if slot != -1:
                child_pos = gl.find_birth_pos(g_b_pos[i])
                spawn_organism(slot, child_pos, child_dna, initial_energy=g_b_energy[i])
        # ---- comprehension signal: drain the read_log (correct vs miss predictions) ----
        c, m = drain_read_log()
        correct_acc += c; miss_acc += m
        # ---- continuous reading-fuel regrow toward CELL_STATES (genesis_lab DEPLETE regrow) ----
        np.minimum(g_read_fuel + np.float32(DEPLETE_REGROW), np.float32(CELL_STATES), out=g_read_fuel)
        # ---- bank a few living genomes into the fossil gene bank (Rule 14 material) ----
        if tick % 100 == 0:
            liv = living_idx()
            for k in liv[:8]:
                gp = int(g_org_g_ptr[k]); gc = int(g_org_g_count[k])
                remember_fossil(np.array(g_global_genome[gp:gp + gc], dtype=np.uint8), age=int(g_age[k]))
        # ---- minimal Rule-10/14 refugium: gradient not cliff ----
        n_now = int(np.sum(g_alive))
        if n_now < REFUGE_FLOOR:
            born = seed_refuge(REFUGE_FLOOR - n_now)
            refuge_acc += born
        # ---- metric snapshot ----
        if (tick + 1) % SAMPLE_EVERY == 0:
            rec = snapshot(tick + 1, correct_acc / SAMPLE_EVERY, miss_acc / SAMPLE_EVERY, refuge_acc,
                             net_pos_acc / SAMPLE_EVERY, max_run_run)
            series.append(rec)
            correct_acc = 0.0; miss_acc = 0.0; net_pos_acc = 0
            if (tick + 1) % (SAMPLE_EVERY * 10) == 0:
                print("    [seed %d] tick %6d  n_alive=%4d  n_neurons=%.1f  idle=%.1f  "
                      "correct/tick=%.2f  refuge_cum=%d  (%.0fs)"
                      % (seed, tick + 1, rec["n_alive"], rec.get("n_neurons_mean", float('nan')),
                         rec.get("idle_cost_mean", float('nan')), rec["correct_per_tick"],
                         rec["refuge_germ_cum"], time.time() - t0), flush=True)
    for i in range(MAX_ORGANISMS):
        if g_alive[i]:
            g_alive[i] = False
            g_org_grid[g_positions[i]] = -1
            free_block(g_org_n_ptr[i], g_org_n_count[i], g_neuron_map)
            free_block(g_org_s_ptr[i], g_org_s_count[i], g_synapse_map)
            free_block(g_org_g_ptr[i], g_org_g_count[i], g_genome_map)
    return series

def main():
    val = validate_idle_estimate()
    all_series = []
    for s in range(N_SEEDS):
        print("[arm STDP_TARGET=%s] running seed %d/%d ..." % (_STDP_TARGET, s + 1, N_SEEDS), flush=True)
        all_series.append(run_seed(SEED + s))
    out = {
        "experiment": "exp87_metabolic_ceiling_evolution",
        "stdp_target": int(_STDP_TARGET),
        "n_seeds": N_SEEDS, "n_ticks": N_TICKS, "pop_size": POP_SIZE,
        "sample_every": SAMPLE_EVERY, "refuge_floor": REFUGE_FLOOR,
        "income_quantum": float(CELL_STATES),
        "cycles_per_neuron_update": float(CYCLES_PER_NEURON_UPDATE),
        "cycles_per_synapse_read": float(CYCLES_PER_SYNAPSE_READ),
        "deplete_regrow": float(DEPLETE_REGROW),
        "income_footprint": bool(INCOME_FOOTPRINT), "income_lump_sum": bool(INCOME_LUMP_SUM),
        "lumpsum_k": int(LUMPSUM_K), "footprint_quantum": float(FOOTPRINT_QUANTUM),
        "deplete": os.environ.get("GENESIS_DEPLETE", "1") == "1",
        "param_names": PARAM_NAMES,
        "validation": val,
        "series": all_series,
    }
    fn = os.path.join(OUT_DIR, "exp87_stdp_target_%s.json" % _STDP_TARGET)
    with open(fn, "w") as f:
        json.dump(out, f, indent=2)
    print("\n[arm STDP_TARGET=%s] saved -> %s" % (_STDP_TARGET, fn), flush=True)

if __name__ == "__main__":
    main()
