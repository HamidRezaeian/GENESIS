"""Substrate 4 Extended — 20,000 Ticks Training Driver.

Protocol ID: SUBSTRATE_4_EXTENDED_20K_v1

Evaluates if longer sequence exposure (20k ticks instead of 2k) pushes
Substrate 4 mean in-lifetime learning delta above the +5.0 pp Gate A threshold.

Outputs:
  - experiments/sub4_results/sub4_20k_summary.json
"""

import os
import sys
import json
import time
import numpy as np

TICKS = 20000
REPORT_EVERY = 1000
SEEDS = [0, 1, 2, 3]
PATCH_SIZE = 500
N_ORGS = 60

D_MODEL = 32
CONTEXT_LEN = 16
VOCAB = 256
LR = 0.005

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"

import genesis_lab as gl
from sub4_small_transformer import SmallTransformerAgent, build_patch

def run_arm(seed, is_learn):
    patch = build_patch(seed)
    n = len(patch)

    agents = [SmallTransformerAgent(seed * 100 + o) for o in range(N_ORGS)]
    cursors = np.random.RandomState(seed).randint(0, n, size=N_ORGS)

    windows = []

    for tick in range(TICKS):
        total_correct = 0
        total_bits = 0
        total_err = 0.0
        total_norm = 0.0

        for org in range(N_ORGS):
            pos = cursors[org]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n])

            pred_byte, err_sum = agents[org].step(in_byte, tgt_byte, is_learn)

            xb = int(pred_byte) ^ tgt_byte
            correct = 8 - bin(xb & 0xFF).count("1")
            total_correct += correct
            total_bits += 8
            total_err += float(err_sum)
            total_norm += float(np.linalg.norm(agents[org].W_head))

            if np.random.rand() < 0.7:
                cursors[org] = (cursors[org] + 1) % n
            else:
                cursors[org] = (cursors[org] + np.random.randint(1, 4)) % n

        if (tick + 1) % REPORT_EVERY == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_err = total_err / float(N_ORGS) if N_ORGS else 0.0
            mean_norm = total_norm / float(N_ORGS) if N_ORGS else 0.0
            rec = {
                "tick": tick + 1,
                "acc": round(acc, 4),
                "mean_err": round(mean_err, 6),
                "norm_w": round(mean_norm, 6)
            }
            windows.append(rec)

    return windows

def main():
    results_dir = os.path.join(ROOT, "experiments", "sub4_results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 64)
    print("SUBSTRATE 4 EXTENDED: 20,000 TICKS RUN")
    print(f"Seeds: {SEEDS} | Ticks: {TICKS} | Report: {REPORT_EVERY} | Orgs: {N_ORGS}")
    print("=" * 64)

    summary = {
        "substrate": "Substrate4_Small_Transformer_Extended_20k",
        "protocol": "SUBSTRATE_4_EXTENDED_20K_v1",
        "seeds": SEEDS,
        "ticks": TICKS,
        "results": {"learn": {}, "nolearn": {}}
    }

    learn_early_accs = []
    learn_late_accs = []
    nolearn_early_accs = []
    nolearn_late_accs = []

    for seed in SEEDS:
        print(f"\n--- SEED {seed} ---")
        print("Running LEARN arm (20k ticks)...")
        w_learn = run_arm(seed, is_learn=True)
        summary["results"]["learn"][str(seed)] = w_learn
        early_l = np.mean([w["acc"] for w in w_learn[:3]])
        late_l = np.mean([w["acc"] for w in w_learn[-3:]])
        learn_early_accs.append(early_l)
        learn_late_accs.append(late_l)
        print(f"  LEARN   early acc: {early_l:6.2f}% | late acc: {late_l:6.2f}% | delta: {late_l-early_l:+6.2f}pp")

        print("Running NOLEARN arm (20k ticks)...")
        w_nolearn = run_arm(seed, is_learn=False)
        summary["results"]["nolearn"][str(seed)] = w_nolearn
        early_nl = np.mean([w["acc"] for w in w_nolearn[:3]])
        late_nl = np.mean([w["acc"] for w in w_nolearn[-3:]])
        nolearn_early_accs.append(early_nl)
        nolearn_late_accs.append(late_nl)
        print(f"  NOLEARN early acc: {early_nl:6.2f}% | late acc: {late_nl:6.2f}% | delta: {late_nl-early_nl:+6.2f}pp")

    mean_learn_early = float(np.mean(learn_early_accs))
    mean_learn_late = float(np.mean(learn_late_accs))
    learn_delta = mean_learn_late - mean_learn_early

    mean_nolearn_late = float(np.mean(nolearn_late_accs))
    gap_late = mean_learn_late - mean_nolearn_late

    gate_a_pass = (learn_delta >= 5.0)
    gate_b_pass = (gap_late > 3.0)

    verdict_str = "SUBSTRATE_PASSED" if (gate_a_pass and gate_b_pass) else "SUBSTRATE_NULL_OR_DEGRADED"

    summary["metrics"] = {
        "mean_learn_early_acc": round(mean_learn_early, 4),
        "mean_learn_late_acc": round(mean_learn_late, 4),
        "learn_delta_pp": round(learn_delta, 4),
        "mean_nolearn_late_acc": round(mean_nolearn_late, 4),
        "gap_late_pp": round(gap_late, 4),
        "gate_a_pass": gate_a_pass,
        "gate_b_pass": gate_b_pass,
        "verdict": verdict_str
    }

    out_file = os.path.join(results_dir, "sub4_20k_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 64)
    print("SUBSTRATE 4 EXTENDED (20K) SUMMARY & VERDICT")
    print("=" * 64)
    print(f"Mean Early LEARN Acc : {mean_learn_early:6.2f}%")
    print(f"Mean Late LEARN Acc  : {mean_learn_late:6.2f}%")
    print(f"In-Lifetime Delta    : {learn_delta:+6.2f} pp (Gate A: {'PASS' if gate_a_pass else 'FAIL'})")
    print(f"Mean Late NOLEARN Acc: {mean_nolearn_late:6.2f}%")
    print(f"Static/Ablation Gap  : {gap_late:+6.2f} pp (Gate B: {'PASS' if gate_b_pass else 'FAIL'})")
    print(f"Rule 18 Verdict      : {verdict_str}")
    print(f"Summary saved to     : {out_file}")
    print("=" * 64)

if __name__ == "__main__":
    main()
