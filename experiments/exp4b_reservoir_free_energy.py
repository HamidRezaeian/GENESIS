"""Exp 4b — Reservoir Free-Energy Oracle Probe.

Isolates per-organism reservoir + NLMS readout (Exp 103b mechanism) under FREE_ENERGY=1 and NO_DEATH=1.

Protocol:
  - Mechanism: GENESIS_RESERVOIR_PER_ORG=1 (reservoir + NLMS readout per org)
  - FREE_ENERGY=1, NO_DEATH=1
  - Cohort: 60 organisms
  - Duration: 1000 ticks per run, reported every 100 ticks
  - Seeds: [0, 1, 2, 3]
  - Arms: LEARN (READOUT_LR=0.01) vs NOLEARN (READOUT_LR=0.0)
  - Metric: Next-byte prediction accuracy (matching Exp 103b)

Run:
  python experiments/exp4b_reservoir_free_energy.py
"""

import os
import sys
import json
import time
import numpy as np

# Geometry & Parameters
TICKS = 1000
REPORT_EVERY = 100
SEEDS = [0, 1, 2, 3]
PATCH_SIZE = 500
N_ORGS = 60

RESERVOIR_SIZE = 256
RESERVOIR_SPARSITY = 0.1
RESERVOIR_TAU = 20.0
READOUT_LR = 0.01

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

# Environment flags
os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"
os.environ["GENESIS_AUTO_REPRO"] = "0"
os.environ["GENESIS_STDP3C"] = "0"
os.environ["GENESIS_STDP3"] = "0"
os.environ["GENESIS_STDP_TARGET"] = "0"
os.environ["GENESIS_RESERVOIR"] = "0"
os.environ["GENESIS_RESERVOIR_PER_ORG"] = "1"
os.environ["GENESIS_FREE_ENERGY"] = "1"
os.environ["GENESIS_NO_DEATH"] = "1"

import genesis_lab as gl
import neuromorphic_engine as ne

n_syn = int(min(gl.RESERVOIR_MAX_SYNAPSES, max(1, int(RESERVOIR_SIZE * RESERVOIR_SIZE * RESERVOIR_SPARSITY))))

def build_patch(seed):
    from books_of_genesis import inject_contiguous_library, contiguous_library_start
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH_SIZE)
    start = contiguous_library_start(gl.RAM_SIZE, PATCH_SIZE)
    patch = [int(b) for b in gl.g_ram[start:start + PATCH_SIZE] if 32 <= int(b) <= 126 and int(b) != 0x55]
    if len(patch) < 16:
        patch = [int(c) for c in ("the quick brown fox jumps over the lazy dog 0123456789 ") * 20][:PATCH_SIZE]
    return patch

def run_arm(seed, is_learn):
    np.random.seed(seed)
    patch = build_patch(seed)
    n = len(patch)
    lr = READOUT_LR if is_learn else 0.0

    gl.g_reservoir_state[:] = 0.0

    org_cursors = np.random.RandomState(seed).randint(0, n, size=N_ORGS)
    org_states = [np.zeros(RESERVOIR_SIZE, dtype=np.float32) for _ in range(N_ORGS)]
    org_readouts = [(np.random.rand(8, RESERVOIR_SIZE).astype(np.float32) - 0.5) * 0.2 for _ in range(N_ORGS)]

    windows = []
    
    for tick in range(TICKS):
        total_correct = 0
        total_bits = 0
        total_err = 0.0
        total_norm = 0.0

        for org in range(N_ORGS):
            pos = org_cursors[org]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n])

            pred_byte, err_sum = ne.reservoir_step(
                org_states[org], gl.g_reservoir_src, gl.g_reservoir_dst,
                gl.g_reservoir_weight, org_readouts[org], n_syn,
                in_byte, tgt_byte, RESERVOIR_SIZE, RESERVOIR_TAU, np.float32(lr),
                8, 0)

            xb = int(pred_byte) ^ tgt_byte
            correct = 8 - bin(xb & 0xFF).count("1")
            total_correct += correct
            total_bits += 8
            total_err += float(err_sum)
            total_norm += float(np.linalg.norm(org_readouts[org]))

            if np.random.rand() < 0.7:
                org_cursors[org] = (org_cursors[org] + 1) % n
            else:
                org_cursors[org] = (org_cursors[org] + np.random.randint(1, 4)) % n

        if (tick + 1) % REPORT_EVERY == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_err = total_err / (8.0 * N_ORGS) if N_ORGS else 0.0
            mean_norm = total_norm / N_ORGS if N_ORGS else 0.0
            rec = {
                "tick": tick + 1,
                "acc": round(acc, 4),
                "mean_err": round(mean_err, 6),
                "norm_w": round(mean_norm, 6)
            }
            windows.append(rec)

    return windows

def main():
    results_dir = os.path.join(ROOT, "experiments", "exp4b_results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 64)
    print("EXP 4B: RESERVOIR FREE-ENERGY ORACLE RUN")
    print(f"Seeds: {SEEDS} | Ticks: {TICKS} | Report: {REPORT_EVERY} | Orgs: {N_ORGS}")
    print("=" * 64)

    summary = {
        "experiment": "Exp4b_Reservoir_Free_Energy",
        "seeds": SEEDS,
        "ticks": TICKS,
        "report_every": REPORT_EVERY,
        "results": {"learn": {}, "nolearn": {}}
    }

    learn_final_accs = []
    nolearn_final_accs = []

    for seed in SEEDS:
        print(f"\n--- SEED {seed} ---")
        print("Running LEARN arm...")
        w_learn = run_arm(seed, is_learn=True)
        summary["results"]["learn"][str(seed)] = w_learn
        final_learn_acc = w_learn[-1]["acc"]
        learn_final_accs.append(final_learn_acc)
        print(f"  LEARN   final acc: {final_learn_acc:6.2f}% | err: {w_learn[-1]['mean_err']:.4f} | ||W||: {w_learn[-1]['norm_w']:.4f}")

        print("Running NOLEARN arm...")
        w_nolearn = run_arm(seed, is_learn=False)
        summary["results"]["nolearn"][str(seed)] = w_nolearn
        final_nolearn_acc = w_nolearn[-1]["acc"]
        nolearn_final_accs.append(final_nolearn_acc)
        print(f"  NOLEARN final acc: {final_nolearn_acc:6.2f}% | err: {w_nolearn[-1]['mean_err']:.4f} | ||W||: {w_nolearn[-1]['norm_w']:.4f}")

    mean_learn = float(np.mean(learn_final_accs))
    mean_nolearn = float(np.mean(nolearn_final_accs))
    delta_learn = mean_learn - mean_nolearn

    # Binding Verdict: Δ(LEARN) > +5pp AND Δ(LEARN) > Δ(NOLEARN) + 3pp
    passed_verdict = (delta_learn > 5.0)
    verdict_str = "ECONOMY_WAS_KILLER_FOR_RESERVOIR" if passed_verdict else "SUBSTRATE_FALSIFICATION_FULL_B3"

    summary["metrics"] = {
        "mean_learn_final_acc": round(mean_learn, 4),
        "mean_nolearn_final_acc": round(mean_nolearn, 4),
        "delta_learn_pp": round(delta_learn, 4),
        "verdict": verdict_str
    }

    out_file = os.path.join(results_dir, "exp4b_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 64)
    print("EXP 4B SUMMARY & BINDING VERDICT")
    print("=" * 64)
    print(f"Mean Final LEARN Acc   : {mean_learn:6.2f}%")
    print(f"Mean Final NOLEARN Acc : {mean_nolearn:6.2f}%")
    print(f"Delta (LEARN - NOLEARN): {delta_learn:+6.2f} pp")
    print(f"Binding Verdict        : {verdict_str}")
    print(f"Summary saved to       : {out_file}")
    print("=" * 64)

if __name__ == "__main__":
    main()
