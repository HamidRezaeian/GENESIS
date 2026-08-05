"""
Exp 103 — Reservoir + Readout REAL PILOT
Protocol: EXP103_RESERVOIR_READOUT_v1  (pre-registered 2026-08-05)

What this does: runs the REAL reservoir + linear-LMS readout mechanism implemented as
`neuromorphic_engine.reservoir_step` (echo-state reservoir, fixed sparse Dale 80/20
recurrent weights, leaky rate 1/tau; linear readout trained by online LMS) against the
static text patch's next-symbol prediction task.

Two arms, identical seed 0, identical input sequence, ONLY the readout learning differs:
  LEARNER  (GENESIS_RESERVOIR=1)  reservoir + LMS readout  -> logs accuracy | mean readout
           error | ||W_readout||
  NOLEARN  (GENESIS_RESERVOIR=0)  identical reservoir, readout FROZEN at init (lr=0, no
           learning)             -> logs accuracy (non-learning control)

Pre-registered defaults ONLY (no tuning, Rule 16): size 256, sparsity 0.1, E/I 0.8,
tau 20.0, lr 0.01 — all as already disclosed in neuromorphic_engine / genesis_lab.

The default engine kernel (GENESIS_RESERVOIR=0) is byte-identical: reservoir_step is a
standalone njit function the default world_tick_numba never calls, and the per-organism
RESERVOIR block is a compile-gated no-op.

Run:
  EXP103_ARM=learner python experiments/exp103_reservoir_probe.py
  EXP103_ARM=nolearn python experiments/exp103_reservoir_probe.py

Writes REAL arrays (not notes) to experiments/exp103_pilot_results/.
"""

import os, sys, json, time
import numpy as np

# ── Pre-registration metadata ──
PROTOCOL     = "EXP103_RESERVOIR_READOUT_v1"
PRE_REG_DATE = "2026-08-05"

# ── Pilot geometry (1000 ticks, report every 100, seed 0) ──
TICKS        = int(os.environ.get("EXP103_TICKS", "1000"))
REPORT_EVERY = int(os.environ.get("EXP103_REPORT", "100"))
SEED         = int(os.environ.get("EXP103_SEED", "0"))
PATCH        = int(os.environ.get("EXP103_PATCH", "500"))
ARM          = os.environ.get("EXP103_ARM", "learner")   # "learner" | "nolearn"

# ── Pre-registered reservoir/readout defaults (NO tuning, Rule 16) ──
RESERVOIR_SIZE    = int(os.environ.get("GENESIS_RESERVOIR_SIZE", "256"))
RESERVOIR_SPARSITY= float(os.environ.get("GENESIS_RESERVOIR_SPARSITY", "0.1"))
RESERVOIR_EI_RATIO= float(os.environ.get("GENESIS_RESERVOIR_EI_RATIO", "0.8"))
RESERVOIR_TAU     = float(os.environ.get("GENESIS_RESERVOIR_TAU", "20.0"))
READOUT_LR        = float(os.environ.get("GENESIS_READOUT_LR", "0.01"))
LR = READOUT_LR if ARM == "learner" else 0.0     # NOLEARN => readout frozen

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_DIR, "..", "src"))

# ── Pin geometry BEFORE engine import (reproducibility, mirrors Exp 100) ──
os.environ["GENESIS_RAM_SIZE"]       = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"]  = "512"
os.environ["GENESIS_REMAP"]          = "0"
os.environ["GENESIS_ECONOMY"]        = "books"
os.environ["GENESIS_LIVE_WEB"]       = "0"
os.environ["GENESIS_AUTO_REPRO"]     = "0"
os.environ["GENESIS_RESUME"]         = "0"
os.environ["GENESIS_RESERVOIR"]      = "1" if ARM == "learner" else "0"
os.environ["GENESIS_STDP3C"]         = "0"
os.environ["GENESIS_STDP3"]          = "0"
os.environ["GENESIS_STDP_TARGET"]    = "0"
os.environ["GENESIS_NOLEARN"]        = "1" if ARM == "nolearn" else "0"

import genesis_lab as gl
import neuromorphic_engine as ne

# Fixed, reproducible init for both arms: reservoir weights are baked at import (seed 42);
# give the READOUT a small fixed random init so NOLEARN is a near-chance non-learning
# baseline (identical for both arms) rather than a degenerate all-zero readout.
np.random.seed(SEED)
gl.g_reservoir_state[:] = 0.0
gl.g_readout_w[:] = (np.random.rand(*gl.g_readout_w.shape).astype(np.float32) - 0.5) * 0.2
gl.g_readout_w[0:6, :] = 0.0   # motor rows unused; only vocal rows 6..13 participate

n_syn = int(min(gl.RESERVOIR_MAX_SYNAPSES,
                max(1, int(RESERVOIR_SIZE * RESERVOIR_SIZE * RESERVOIR_SPARSITY))))
VOCAL0 = 6  # first vocal-bit output row (bits 6..13 are the 8 next-byte bits)


def build_patch():
    """Lay the static text patch in RAM (Books economy) and return its printable bytes."""
    from books_of_genesis import inject_contiguous_library, contiguous_library_start
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH)
    start = contiguous_library_start(gl.RAM_SIZE, PATCH)
    patch = [int(b) for b in gl.g_ram[start:start + PATCH]
             if 32 <= int(b) <= 126 and int(b) != 0x55]
    if len(patch) < 16:
        # Fallback deterministic patch if the library laid <16 printable bytes.
        rng = np.random.RandomState(SEED)
        patch = [int(c) for c in
                 ("the quick brown fox jumps over the lazy dog 0123456789 ") * 20]
        patch = patch[:PATCH]
    return patch


def run_arm():
    t0 = time.time()
    patch = build_patch()
    n = len(patch)
    i = 0  # reading position on the patch
    lr_label = f"{READOUT_LR} (learning)" if ARM == "learner" else "0.0 (readout frozen)"

    print(f"\n{'='*64}\nEXP103 PILOT — ARM={ARM}  seed={SEED}  ticks={TICKS}  report={REPORT_EVERY}\n"
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
            in_byte, tgt_byte, RESERVOIR_SIZE, RESERVOIR_TAU, np.float32(LR),
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

    # Verdict on the pre-registered criterion: acc late>early AND err late<early.
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

    if acc_delta > 0.0 and err_delta < 0.0:
        verdict = "LEARNING_SIGNAL_RECOMMEND_FULL_RUN"
    elif abs(acc_delta) <= 0.0 and abs(err_delta) <= 0.0:
        verdict = "FLAT_DIAGNOSE"
    elif acc_delta < 0.0:
        verdict = "WORSE_STOP"
    else:
        verdict = "MIXED_AMBIGUOUS"

    out = {
        "protocol": PROTOCOL,
        "pre_reg_date": PRE_REG_DATE,
        "arm": ARM,
        "seed": SEED,
        "ticks": TICKS,
        "report_every": REPORT_EVERY,
        "reservoir_size": RESERVOIR_SIZE,
        "reservoir_sparsity": RESERVOIR_SPARSITY,
        "reservoir_ei_ratio": RESERVOIR_EI_RATIO,
        "reservoir_tau": RESERVOIR_TAU,
        "readout_lr_applied": float(LR),
        "patch_bytes": n,
        "early_acc": round(float(early_acc), 4),
        "late_acc": round(float(late_acc), 4),
        "acc_delta_pp": round(float(acc_delta), 4),
        "early_mean_err": round(float(early_err), 6),
        "late_mean_err": round(float(late_err), 6),
        "err_delta": round(float(err_delta), 6),
        "final_norm_readout_w": round(float(last_norm), 6),
        "verdict": verdict,
        "elapsed_s": round(float(elapsed), 3),
        "samples": windows,
    }

    print(f"\n{'='*64}\nRESULT — arm={ARM}\n  early_acc={early_acc:.2f}%  late_acc={late_acc:.2f}%"
          f"  acc_delta={acc_delta:+.2f}pp\n  early_mean_err={early_err:.4f}  late_mean_err={late_err:.4f}"
          f"  err_delta={err_delta:+.4f}\n  VERDICT: {verdict}\n{'='*64}")
    return out


def main():
    out = run_arm()
    out_dir = os.path.join(_DIR, "exp103_pilot_results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"exp103_pilot_{ARM}_s{SEED}_{TICKS}t.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
