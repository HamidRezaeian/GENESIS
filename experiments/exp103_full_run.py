"""
Exp 103 — Reservoir + Readout FULL RUN
Protocol: EXP103_RESERVOIR_READOUT_v1  (pre-registered 2026-08-05)

What this does: runs the REAL reservoir + linear-LMS readout mechanism implemented as
`neuromorphic_engine.reservoir_step` (echo-state reservoir, fixed sparse Dale 80/20
recurrent weights, leaky rate 1/tau; linear readout trained by online Normalized LMS) against
the static text patch's next-symbol prediction task.

Full Run Geometry:
  4 seeds (0, 1, 2, 3) × 20,000 ticks
  Both arms:
    LEARNER (GENESIS_RESERVOIR=1, lr=0.01)
    NOLEARN (GENESIS_RESERVOIR=0, lr=0.0)
  Reports every 1000 ticks: acc | mean err | ||W_readout||

Pre-registered defaults ONLY (no tuning, Rule 16): size 256, sparsity 0.1, E/I 0.8,
tau 20.0, lr 0.01.

Writes individual JSONs per seed and arm to experiments/exp103_results/ as well as
exp103_full_summary.json.
"""

import os, sys, json, time
import numpy as np

# ── Pre-registration metadata ──
PROTOCOL     = "EXP103_RESERVOIR_READOUT_v1"
PRE_REG_DATE = "2026-08-05"

# ── Full-run geometry ──
TICKS        = 20000
REPORT_EVERY = 1000
SEEDS        = [0, 1, 2, 3]
ARMS         = ["learner", "nolearn"]
PATCH        = 500

# ── Pre-registered reservoir/readout defaults (NO tuning, Rule 16) ──
RESERVOIR_SIZE     = int(os.environ.get("GENESIS_RESERVOIR_SIZE", "256"))
RESERVOIR_SPARSITY = float(os.environ.get("GENESIS_RESERVOIR_SPARSITY", "0.1"))
RESERVOIR_EI_RATIO = float(os.environ.get("GENESIS_RESERVOIR_EI_RATIO", "0.8"))
RESERVOIR_TAU      = float(os.environ.get("GENESIS_RESERVOIR_TAU", "20.0"))
READOUT_LR         = float(os.environ.get("GENESIS_READOUT_LR", "0.01"))

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_DIR, "..", "src"))

# ── Pin geometry BEFORE engine import (reproducibility, mirrors Exp 100/103 pilot) ──
os.environ["GENESIS_RAM_SIZE"]      = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"]         = "0"
os.environ["GENESIS_ECONOMY"]       = "books"
os.environ["GENESIS_LIVE_WEB"]      = "0"
os.environ["GENESIS_AUTO_REPRO"]    = "0"
os.environ["GENESIS_RESUME"]        = "0"
os.environ["GENESIS_STDP3C"]        = "0"
os.environ["GENESIS_STDP3"]         = "0"
os.environ["GENESIS_STDP_TARGET"]   = "0"

import genesis_lab as gl
import neuromorphic_engine as ne

n_syn = int(min(gl.RESERVOIR_MAX_SYNAPSES,
                max(1, int(RESERVOIR_SIZE * RESERVOIR_SIZE * RESERVOIR_SPARSITY))))
VOCAL0 = 6  # first vocal-bit output row (bits 6..13 are the 8 next-byte bits)


def init_run(seed):
    """Fixed, reproducible init for each run."""
    np.random.seed(seed)
    gl.g_reservoir_state[:] = 0.0
    gl.g_readout_w[:] = (np.random.rand(*gl.g_readout_w.shape).astype(np.float32) - 0.5) * 0.2
    gl.g_readout_w[0:6, :] = 0.0   # motor rows unused; only vocal rows 6..13 participate


def build_patch(seed):
    """Lay the static text patch in RAM (Books economy) and return its printable bytes."""
    from books_of_genesis import inject_contiguous_library, contiguous_library_start
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH)
    start = contiguous_library_start(gl.RAM_SIZE, PATCH)
    patch = [int(b) for b in gl.g_ram[start:start + PATCH]
             if 32 <= int(b) <= 126 and int(b) != 0x55]
    if len(patch) < 16:
        # Fallback deterministic patch if the library laid <16 printable bytes.
        rng = np.random.RandomState(seed)
        patch = [int(c) for c in
                 ("the quick brown fox jumps over the lazy dog 0123456789 ") * 20]
        patch = patch[:PATCH]
    return patch


def run_arm(arm, seed):
    t0 = time.time()
    init_run(seed)
    patch = build_patch(seed)
    n = len(patch)
    i = 0  # reading position on the patch
    lr = READOUT_LR if arm == "learner" else 0.0
    lr_label = f"{READOUT_LR} (learning)" if arm == "learner" else "0.0 (readout frozen)"

    print(f"\n{'='*64}\nEXP103 FULL RUN — ARM={arm}  seed={seed}  ticks={TICKS}  report={REPORT_EVERY}\n"
          f"reservoir: size={RESERVOIR_SIZE} sparsity={RESERVOIR_SPARSITY} EI={RESERVOIR_EI_RATIO} "
          f"tau={RESERVOIR_TAU}  lr={lr_label}\n"
          f"patch_bytes={n}  n_syn={n_syn}\n{'='*64}")

    windows = []
    wc = wt = 0          # window correct-bits / total-bits
    werr = 0.0           # window sum of per-bit |err|
    wevt = 0             # window event count
    last_norm = 0.0

    for tick in range(TICKS):
        in_byte = int(patch[i])
        tgt_byte = int(patch[(i + 1) % n])
        pred_byte, err_sum = ne.reservoir_step(
            gl.g_reservoir_state, gl.g_reservoir_src, gl.g_reservoir_dst,
            gl.g_reservoir_weight, gl.g_readout_w, n_syn,
            in_byte, tgt_byte, RESERVOIR_SIZE, RESERVOIR_TAU, np.float32(lr),
            gl.N_OUTPUT, VOCAL0)

        xb = int(pred_byte) ^ tgt_byte
        wc += 8 - bin(xb & 0xFF).count("1")
        wt += 8
        werr += float(err_sum)
        wevt += 1
        i = (i + 1) % n

        if (tick + 1) % REPORT_EVERY == 0:
            acc = 100.0 * wc / wt if wt else 0.0
            mean_err = werr / (8.0 * wevt) if wevt else 0.0
            wnorm = float(np.linalg.norm(gl.g_readout_w[VOCAL0:VOCAL0 + 8, :]))
            last_norm = wnorm
            rec = {"tick": tick + 1, "acc": round(acc, 4),
                   "mean_readout_err": round(mean_err, 6), "norm_readout_w": round(wnorm, 6)}
            windows.append(rec)
            print(f"  tick={tick+1:5d}  acc={acc:6.2f}%  mean_err={mean_err:.4f}  ||Wr||={wnorm:.4f}")
            wc = wt = 0
            werr = 0.0
            wevt = 0

    elapsed = time.time() - t0

    if len(windows) >= 2:
        third = max(1, len(windows) // 3)
        early = windows[:third]
        late = windows[-third:]
        early_acc = np.mean([w["acc"] for w in early])
        late_acc = np.mean([w["acc"] for w in late])
        early_err = np.mean([w["mean_readout_err"] for w in early])
        late_err = np.mean([w["mean_readout_err"] for w in late])
    else:
        early_acc = late_acc = 0.0
        early_err = late_err = 0.0

    acc_delta = late_acc - early_acc
    err_delta = late_err - early_err

    out = {
        "protocol": PROTOCOL,
        "pre_reg_date": PRE_REG_DATE,
        "arm": arm,
        "seed": seed,
        "ticks": TICKS,
        "report_every": REPORT_EVERY,
        "reservoir_size": RESERVOIR_SIZE,
        "reservoir_sparsity": RESERVOIR_SPARSITY,
        "reservoir_ei_ratio": RESERVOIR_EI_RATIO,
        "reservoir_tau": RESERVOIR_TAU,
        "readout_lr_applied": float(lr),
        "patch_bytes": n,
        "early_acc": round(float(early_acc), 4),
        "late_acc": round(float(late_acc), 4),
        "acc_delta_pp": round(float(acc_delta), 4),
        "early_mean_err": round(float(early_err), 6),
        "late_mean_err": round(float(late_err), 6),
        "err_delta": round(float(err_delta), 6),
        "final_norm_readout_w": round(float(last_norm), 6),
        "elapsed_s": round(float(elapsed), 3),
        "samples": windows,
    }
    return out


def main():
    out_dir = os.path.join(_DIR, "exp103_results")
    os.makedirs(out_dir, exist_ok=True)

    results_by_arm = {"learner": [], "nolearn": []}

    print(f"\n{'='*70}\nEXP103 FULL RUN — 4 SEEDS × 20,000 TICKS\n{'='*70}")

    for seed in SEEDS:
        for arm in ARMS:
            res = run_arm(arm, seed)
            results_by_arm[arm].append(res)
            out_path = os.path.join(out_dir, f"exp103_full_{arm}_s{seed}_20000t.json")
            with open(out_path, "w") as f:
                json.dump(res, f, indent=2)
            print(f"Saved -> {out_path}")

    # ── Aggregate Summary & Verdict ──
    learner_lates = [r["late_acc"] for r in results_by_arm["learner"]]
    learner_earlies = [r["early_acc"] for r in results_by_arm["learner"]]
    learner_deltas = [r["acc_delta_pp"] for r in results_by_arm["learner"]]

    nolearn_lates = [r["late_acc"] for r in results_by_arm["nolearn"]]
    nolearn_earlies = [r["early_acc"] for r in results_by_arm["nolearn"]]
    nolearn_deltas = [r["acc_delta_pp"] for r in results_by_arm["nolearn"]]

    mean_learner_late = float(np.mean(learner_lates))
    mean_learner_early = float(np.mean(learner_earlies))
    mean_learner_delta = float(np.mean(learner_deltas))

    mean_nolearn_late = float(np.mean(nolearn_lates))
    mean_nolearn_early = float(np.mean(nolearn_earlies))

    gap_pp = mean_learner_late - mean_nolearn_late

    # Check monotonic decline across late windows
    no_monotonic_decline = True
    for r in results_by_arm["learner"]:
        accs = [w["acc"] for w in r["samples"]]
        if len(accs) >= 4 and accs[-1] < accs[0] - 5.0:
            no_monotonic_decline = False

    if gap_pp > 3.0 and abs(mean_learner_delta) <= 1.0 and no_monotonic_decline:
        verdict = "RESERVOIR_HELPS_STATICALLY_BUT_INRUN_LEARNING_WEAK"
    elif gap_pp > 3.0 and mean_learner_delta > 2.0:
        verdict = "RESERVOIR_ROBUST_INRUN_LEARNING"
    else:
        verdict = "NULL_OR_DEGRADED"

    summary = {
        "protocol": PROTOCOL,
        "pre_reg_date": PRE_REG_DATE,
        "ticks": TICKS,
        "report_every": REPORT_EVERY,
        "seeds": SEEDS,
        "mean_learner_late_acc": round(mean_learner_late, 4),
        "mean_learner_early_acc": round(mean_learner_early, 4),
        "mean_learner_delta_pp": round(mean_learner_delta, 4),
        "mean_nolearn_late_acc": round(mean_nolearn_late, 4),
        "mean_nolearn_early_acc": round(mean_nolearn_early, 4),
        "gap_late_pp": round(gap_pp, 4),
        "no_monotonic_decline": no_monotonic_decline,
        "verdict": verdict,
        "per_seed_learner": [
            {"seed": r["seed"], "early_acc": r["early_acc"], "late_acc": r["late_acc"],
             "delta_pp": r["acc_delta_pp"]}
            for r in results_by_arm["learner"]
        ],
        "per_seed_nolearn": [
            {"seed": r["seed"], "early_acc": r["early_acc"], "late_acc": r["late_acc"],
             "delta_pp": r["acc_delta_pp"]}
            for r in results_by_arm["nolearn"]
        ],
    }

    summary_path = os.path.join(out_dir, "exp103_full_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n{'='*70}")
    print(f"EXP 103 FULL RUN SUMMARY (4 seeds × {TICKS} ticks)")
    print(f"  LEARNER late_acc:  {mean_learner_late:.2f}% (early: {mean_learner_early:.2f}%, delta: {mean_learner_delta:+.2f}pp)")
    print(f"  NOLEARN late_acc:  {mean_nolearn_late:.2f}% (early: {mean_nolearn_early:.2f}%)")
    print(f"  Gap (late-late):   {gap_pp:+.2f}pp")
    print(f"  No monotonic dec.: {no_monotonic_decline}")
    print(f"  VERDICT:           {verdict}")
    print(f"{'='*70}")
    print(f"Summary saved -> {summary_path}\n")


if __name__ == "__main__":
    main()
