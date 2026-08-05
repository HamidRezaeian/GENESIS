"""
Exp 100 — Direct Learning Probe: Does STDP improve prediction over repeated exposure?

THE QUESTION (the one 99 experiments never asked directly):
  If a single organism sees the SAME pattern repeatedly, does its accuracy IMPROVE over time?
  This is the minimal test of "learning = improvement with experience".

NO ecology. NO survival. NO reproduction. NO remap. NO Ark. NO catastrophic forgetting test.
Just: pattern → predict → STDP update → repeat. Does accuracy go up?

Two arms, single frozen organism each:
  LEARNER:  STDP3C active — weights update via Hebbian learning
  NOLEARN:  STDP ablated — weights fixed at birth

If LEARNER accuracy rises over NOLEARN across repeated exposure:
  → STDP works. The substrate CAN learn. Problem was in task design (remap creates forgetting).
  → Next step: design a task where learning and stability are not in conflict.

If LEARNER accuracy stays at or below NOLEARN:
  → STDP is mechanistically broken or too weak on this substrate.
  → Next step: sexual reproduction / fundamentally different learning rule.

Run:
  python experiments/exp100_direct_learning_probe.py

Pre-registered (binding): this file was committed BEFORE any results were collected.
Protocol: EXP100_DIRECT_LEARNING_v1
"""

import os, sys, json, time, random as _pyrandom
import numpy as np

# ── Pre-registration metadata ──
PROTOCOL      = "EXP100_DIRECT_LEARNING_v1"
PRE_REG_DATE  = "2026-08-04"
HYPOTHESIS    = "STDP3C improves per-pattern accuracy over repeated exposure vs NOLEARN ablation"

# ── Geometry (pinned, Rule reproducibility) ──
TICKS         = int(os.environ.get("EXP100_TICKS",   "20000"))  # total exposure ticks
REPORT_EVERY  = int(os.environ.get("EXP100_REPORT",   "1000"))   # print cadence
SEED          = int(os.environ.get("EXP100_SEED",       "0"))

_pyrandom.seed(SEED)
np.random.seed(SEED)

# ── Path setup ──
_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_DIR, "..", "src"))

# ── Pin geometry BEFORE engine import (reproducibility) ──
os.environ["GENESIS_RAM_SIZE"]       = str(2 * 1024 * 1024)  # 2 MiB
os.environ["GENESIS_MAX_ORGANISMS"]  = "512"
os.environ["GENESIS_REMAP"]         = "0"    # NO remap — static world, no forgetting pressure
os.environ["GENESIS_ECONOMY"]        = "books"
os.environ["GENESIS_STDP3C"]         = "1"
os.environ["GENESIS_LIVE_WEB"]       = "0"
os.environ["GENESIS_AUTO_REPRO"]     = "0"   # NO reproduction
os.environ["GENESIS_RESUME"]         = "0"

# Will override NOLEARN per-arm below
_ARM = os.environ.get("EXP100_ARM", "learner")   # "learner" or "nolearn"
if _ARM == "nolearn":
    os.environ["GENESIS_STDP3C"] = "0"
    os.environ["GENESIS_NOLEARN"] = "1"

import genesis_lab as gl
import neuromorphic_engine as ne
ne.seed_kernel_rng(SEED)

N_ORG   = 60          # frozen cohort size — enough for statistics, not survival
PATCH   = 500         # small text patch, repeated exposure guaranteed


def build_patch():
    """Inject a small fixed text patch and place the cohort on it."""
    from books_of_genesis import inject_contiguous_library
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH)
    start = gl.contiguous_library_start(gl.RAM_SIZE, PATCH)
    dna = gl.create_intelligent_ancestor(None)
    placed = 0
    p = start
    while placed < N_ORG and p < start + PATCH:
        if gl.g_org_grid[p] == -1:
            if gl.spawn_organism(placed, p, dna, initial_energy=gl.SEED_ENERGY):
                placed += 1
        p += 5
    return placed, start


def pin_to_patch(start):
    """Keep frozen cohort on the text patch (position pin from Exp-92b instrument repair)."""
    alive = np.nonzero(gl.g_alive)[0]
    if alive.size == 0:
        return
    pos = gl.g_positions[alive]
    newpos = start + ((pos - start) % PATCH)
    for oid, old, new in zip(alive, pos, newpos):
        if old == new:
            continue
        if gl.g_org_grid[new] != -1:
            continue
        if gl.g_org_grid[old] == oid:
            gl.g_org_grid[old] = -1
        gl.g_org_grid[new] = oid
        gl.g_positions[oid] = new


HI_ENERGY = None   # set after module load in main()


def pin_energy():
    """Keep all organisms alive — no survival pressure (mirrors remap_sandbox_probe)."""
    gl.g_energy[gl.g_alive] = np.float32(HI_ENERGY)


def measure_and_drain():
    """Drain the read_log, compute total correct bits / total bits."""
    rl = gl.g_read_log
    n = int(rl[0])
    correct = total = 0
    idx = 1
    while idx < n:
        t = int(rl[idx])
        if t == 1:
            total += 8; correct += 8          # full solve → all 8 bits correct
            idx += 3
        elif t == 2:
            tgt   = int(rl[idx + 2]) & 0xFF
            emit  = int(rl[idx + 3]) & 0xFF
            total += 8
            correct += bin(~(tgt ^ emit) & 0xFF).count("1")
            idx += 4
        elif t in (3, 4, 5):
            idx += 3
        else:
            break
    rl[0] = 1   # drain
    return correct, total


def tick_world(global_time: int):
    """Call world_tick_numba with the full arg list (matches remap_sandbox_probe)."""
    return gl.world_tick_numba(
        gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
        gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
        gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight, gl.g_global_conn_elig, gl.g_global_conn_elig_t,
        gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
        gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
        gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
        gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
        gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
        gl.g_viscosity, global_time, gl.g_org_lif_steps,
        gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
        gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
        gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
        gl.CANVAS_LO, gl.CANVAS_HI, gl.g_org_reward, gl.g_org_elig,
        gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
        gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch, gl.g_ram_bank_access, gl.g_ram_bank_access_next,
        gl.g_curriculum_delay, gl.g_conn_w_dna, gl.g_conn_w_slow,
        gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick,
        gl.g_clear_count, gl.g_org_run, gl.g_lump_acc, gl.g_race_state, gl.g_race_attempt_q,
        g_eligibility, g_baseline_acc, g_spikes_used,
        g_reservoir_state, g_readout_w,
        g_ne_bytes)  # Option 3 fitness counter (DCE'd when GENESIS_NEUROEVOLUTION=0)


def run_arm(arm_name: str) -> list:
    """Run one arm and return list of (tick, accuracy_pct) samples."""
    global HI_ENERGY
    HI_ENERGY = float(gl.ATP_MAX) * 0.5

    print(f"\n{'='*60}")
    print(f"EXP100 ARM: {arm_name}  | seed={SEED} | ticks={TICKS}")
    print(f"{'='*60}")

    placed, start = build_patch()
    print(f"Placed {placed} organisms on patch [{start}, {start+PATCH})")

    results = []
    window_correct = window_total = 0

    for global_time in range(TICKS):
        # Freeze cohort: pin energy (no death) and position (no drift)
        pin_to_patch(start)
        pin_energy()

        # Run one world tick
        n_alive, _ = tick_world(global_time)

        # Accumulate read log
        c, t = measure_and_drain()
        window_correct += c
        window_total   += t

        if (global_time + 1) % REPORT_EVERY == 0:
            acc = 100.0 * window_correct / window_total if window_total > 0 else 0.0
            t_display = global_time + 1
            print(f"  tick={t_display:6d}  reads={window_total:6d}  acc={acc:6.2f}%")
            results.append({"tick": t_display, "acc": acc,
                            "reads": window_total, "correct": window_correct})
            window_correct = window_total = 0

    return results


def main():
    print(f"\n{'#'*60}")
    print(f"# EXP100 Direct Learning Probe")
    print(f"# Protocol:    {PROTOCOL}")
    print(f"# Pre-reg:     {PRE_REG_DATE}")
    print(f"# Hypothesis:  {HYPOTHESIS}")
    print(f"# Arm:         {_ARM}")
    print(f"{'#'*60}")

    t0 = time.time()
    arm_results = run_arm(_ARM)
    elapsed = time.time() - t0

    if len(arm_results) < 2:
        print("ERROR: not enough data points — probe failed")
        return

    # Simple analysis: compare first-third vs last-third accuracy
    n3 = max(1, len(arm_results) // 3)
    early_acc = np.mean([r["acc"] for r in arm_results[:n3]])
    late_acc  = np.mean([r["acc"] for r in arm_results[-n3:]])
    delta     = late_acc - early_acc

    print(f"\n{'='*60}")
    print(f"RESULT SUMMARY  (arm={_ARM}, seed={SEED})")
    print(f"{'='*60}")
    print(f"  Early accuracy (first {n3} windows): {early_acc:.2f}%")
    print(f"  Late  accuracy (last  {n3} windows): {late_acc:.2f}%")
    print(f"  Delta (late - early):                {delta:+.2f}%")
    print(f"  Elapsed: {elapsed:.1f}s")

    verdict = "LEARNING_SIGNAL" if delta > 2.0 else ("FLAT" if abs(delta) <= 2.0 else "DEGRADED")
    print(f"\n  VERDICT: {verdict}")
    if verdict == "LEARNING_SIGNAL":
        print("  → STDP improves accuracy with repeated exposure.")
        print("  → Substrate CAN learn. Issue was in task design (remap+forgetting conflict).")
    elif verdict == "FLAT":
        print("  → No improvement. STDP weight changes do not help on this pattern.")
        print("  → Consider: sexual reproduction, reward signal, or different learning rule.")
    else:
        print("  → STDP makes things WORSE — catastrophic interference even without remap.")
        print("  → Strong signal to pivot substrate entirely.")

    out = {
        "protocol": PROTOCOL,
        "pre_reg_date": PRE_REG_DATE,
        "hypothesis": HYPOTHESIS,
        "arm": _ARM,
        "seed": SEED,
        "ticks": TICKS,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta": delta,
        "verdict": verdict,
        "elapsed_s": elapsed,
        "samples": arm_results,
    }
    out_path = os.path.join(_DIR, f"exp100_result_{_ARM}_s{SEED}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Saved → {out_path}")


if __name__ == "__main__":
    main()
