"""
Experiment 101 — R-STDP with Surprise-Based Reward
===================================================

Pre-registered: 2026-08-04
Protocol: EXP101_RSTDP_SURPRISE_REWARD_v1

HYPOTHESIS
----------
R-STDP (Reward-modulated STDP) with surprise-based reward signal will enable
in-lifetime learning that improves over time, solving the static-advantage
problem diagnosed in Exp 100.

RATIONALE
---------
Exp 100 showed STDP3C provides only a static +5pp advantage, not improving
with experience. Root cause: Hebbian STDP only strengthens synapses that
already fire (Δw ∝ pre × post).

R-STDP solves this by:
1. Adding a global reward signal R(t) that broadcasts to ALL synapses
2. Using eligibility traces to mark recently-active synapses
3. Updating even silent synapses: Δw ∝ eligibility × R(t)

The key innovation: reward = SURPRISE × EFFICIENCY, not raw accuracy.
- Surprise = (1 - baseline_accuracy): learn only on novel/hard patterns
- Efficiency = 1/spikes_used: prefer sparse solutions

This is autotelic (Rule 9): reward derives from the organism's own
performance relative to its recent baseline, not an external label.

DESIGN
------
Two arms, frozen cohort (like Exp 100):
- LEARNER_RSTDP: R-STDP with surprise×efficiency reward
- NOLEARN: STDP ablated (control)

If LEARNER_RSTDP shows TIME-DECREASING loss (accuracy rises over ticks):
  → R-STDP solves the static-advantage problem
  → Substrate can learn; proceed to ecological validation
  
If LEARNER_RSTDP shows FLAT or DECREASING accuracy:
  → R-STDP insufficient; need structural change (e.g., sexual reproduction)

MEASUREMENT
-----------
- Early accuracy: first 5000 ticks (warmup)
- Late accuracy: last 5000 ticks (steady state)
- Delta = late - early
- Verdict:
  - LEARNING_SIGNAL: delta > +2.0pp
  - FLAT: |delta| <= 2.0pp
  - DEGRADED: delta < -2.0pp

SUCCESS CRITERIA
----------------
1. LEARNER_RSTDP shows positive delta (improves over time)
2. LEARNER_RSTDP late_acc > NOLEARN late_acc by > 3pp
3. NO monotonic decline in LEARNER_RSTDP (no catastrophic forgetting)

Run:
  python experiments/exp101_rstdp_probe.py
"""

import os, sys, json, time, random as _pyrandom
import numpy as np

# ── Pre-registration metadata ──
PROTOCOL = "EXP101_RSTDP_SURPRISE_REWARD_v1"
PRE_REG_DATE = "2026-08-04"
HYPOTHESIS = "R-STDP with surprise×efficiency reward enables time-improving learning"

# ── Geometry (pinned, Rule reproducibility) ──
TICKS = int(os.environ.get("EXP101_TICKS", "20000"))
REPORT_EVERY = int(os.environ.get("EXP101_REPORT", "1000"))
SEED = int(os.environ.get("EXP101_SEED", "0"))

_pyrandom.seed(SEED)
np.random.seed(SEED)

# ── Path setup ──
_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_DIR, "..", "src"))

# ── Pin geometry BEFORE engine import (reproducibility) ──
os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"  # NO remap — static world
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"
os.environ["GENESIS_AUTO_REPRO"] = "0"  # NO reproduction
os.environ["GENESIS_RESUME"] = "0"

# ── R-STDP configuration ──
os.environ["GENESIS_RSTDP"] = "1"  # NEW: Enable R-STDP
os.environ["GENESIS_RSTDP_SURPRISE"] = "1"  # NEW: Surprise-based reward
os.environ["GENESIS_RSTDP_EFFICIENCY"] = "1"  # NEW: Efficiency weighting

_ARM = os.environ.get("EXP101_ARM", "learner")
if _ARM == "nolearn":
    os.environ["GENESIS_RSTDP"] = "0"
    os.environ["GENESIS_NOLEARN"] = "1"

import genesis_lab as gl
import neuromorphic_engine as ne
ne.seed_kernel_rng(SEED)

N_ORG = 60
PATCH = 500

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
    """Keep frozen cohort on the text patch."""
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

HI_ENERGY = None

def pin_energy():
    """Keep all organisms alive."""
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
            total += 8; correct += 8
            idx += 3
        elif t == 2:
            tgt = int(rl[idx + 2]) & 0xFF
            emit = int(rl[idx + 3]) & 0xFF
            total += 8
            correct += bin(~(tgt ^ emit) & 0xFF).count("1")
            idx += 4
        elif t in (3, 4, 5):
            idx += 3
        else:
            break
    rl[0] = 1
    return correct, total

def tick_world(global_time: int):
    """Call world_tick_numba."""
    return gl.world_tick_numba(
        # ... (full argument list as in exp100)
    )

def run_arm(arm_name: str) -> list:
    """Run one arm and return list of (tick, accuracy_pct) samples."""
    global HI_ENERGY
    HI_ENERGY = float(gl.ATP_MAX) * 0.5

    print(f"\n{'='*60}")
    print(f"EXP101 ARM: {arm_name} | seed={SEED} | ticks={TICKS}")
    print(f"{'='*60}")

    placed, start = build_patch()
    print(f"Placed {placed} organisms on patch [{start}, {start+PATCH})")

    results = []
    window_correct = window_total = 0

    for global_time in range(TICKS):
        pin_to_patch(start)
        pin_energy()
        n_alive, _ = tick_world(global_time)
        c, t = measure_and_drain()
        window_correct += c
        window_total += t

        if (global_time + 1) % REPORT_EVERY == 0:
            acc = 100.0 * window_correct / window_total if window_total > 0 else 0.0
            t_display = global_time + 1
            print(f"  tick={t_display:6d} reads={window_total:6d} acc={acc:6.2f}%")
            results.append({"tick": t_display, "acc": acc,
                          "reads": window_total, "correct": window_correct})
            window_correct = window_total = 0

    return results

def main():
    print(f"\n{'#'*60}")
    print(f"# EXP101 R-STDP Surprise Reward Probe")
    print(f"# Protocol: {PROTOCOL}")
    print(f"# Pre-reg: {PRE_REG_DATE}")
    print(f"# Hypothesis: {HYPOTHESIS}")
    print(f"# Arm: {_ARM}")
    print(f"{'#'*60}")

    t0 = time.time()
    arm_results = run_arm(_ARM)
    elapsed = time.time() - t0

    if len(arm_results) < 2:
        print("ERROR: not enough data points")
        return

    n3 = max(1, len(arm_results) // 3)
    early_acc = np.mean([r["acc"] for r in arm_results[:n3]])
    late_acc = np.mean([r["acc"] for r in arm_results[-n3:]])
    delta = late_acc - early_acc

    print(f"\n{'='*60}")
    print(f"RESULT SUMMARY (arm={_ARM}, seed={SEED})")
    print(f"{'='*60}")
    print(f"  Early accuracy (first {n3} windows): {early_acc:.2f}%")
    print(f"  Late accuracy (last {n3} windows): {late_acc:.2f}%")
    print(f"  Delta (late - early): {delta:+.2f}%")
    print(f"  Elapsed: {elapsed:.1f}s")

    verdict = "LEARNING_SIGNAL" if delta > 2.0 else ("FLAT" if abs(delta) <= 2.0 else "DEGRADED")
    print(f"\n  VERDICT: {verdict}")
    if verdict == "LEARNING_SIGNAL":
        print("  → R-STDP with surprise reward enables TIME-IMPROVING learning.")
        print("  → Substrate CAN learn; proceed to ecological validation.")
    elif verdict == "FLAT":
        print("  → No improvement. R-STDP insufficient on this task.")
        print("  → Consider: sexual reproduction or different substrate.")
    else:
        print("  → R-STDP makes things WORSE.")
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
    out_path = os.path.join(_DIR, f"exp101_result_{_ARM}_s{SEED}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Saved → {out_path}")

if __name__ == "__main__":
    main()
