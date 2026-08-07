"""Substrate 4 Novel Sequence Task Driver.

Protocol ID: SUBSTRATE_4_NOVEL_SEQUENCE_v1

Evaluates Substrate 4 (Small Transformer) on a transfer task:
  - Pattern A (train context): Ticks 0 to 10,000
  - Pattern B (novel, unseen pattern): Ticks 10,000 to 20,000

Goal: Measure transfer and online adaptation delta on Pattern B.

Outputs:
  - experiments/sub4_results/sub4_novel_summary.json
"""

import os
import sys
import json
import time
import numpy as np

TICKS = 20000
SWITCH_TICK = 10000
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
from sub4_small_transformer import SmallTransformerAgent, softmax

def generate_pair(seed):
    pA = [ord(c) for c in ("the quick brown fox jumps over the lazy dog 0123456789 ") * 10][:PATCH_SIZE]
    pB = [ord(c) for c in ("complex adaptive systems embody thermodynamic non-equilibrium ") * 10][:PATCH_SIZE]
    return pA, pB

def run_arm(seed, is_learn):
    pA, pB = generate_pair(seed)
    agents = [SmallTransformerAgent(seed * 100 + o) for o in range(N_ORGS)]
    cursors = np.random.RandomState(seed).randint(0, PATCH_SIZE, size=N_ORGS)

    windows = []

    for tick in range(TICKS):
        patch = pA if tick < SWITCH_TICK else pB
        n = len(patch)

        total_correct = 0
        total_bits = 0
        total_err = 0.0
        total_norm = 0.0

        for org in range(N_ORGS):
            pos = cursors[org] % n
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
                "pattern": "A" if tick < SWITCH_TICK else "B",
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
    print("SUBSTRATE 4 NOVEL SEQUENCE TASK RUN")
    print(f"Seeds: {SEEDS} | Ticks: {TICKS} | Switch Tick: {SWITCH_TICK} | Orgs: {N_ORGS}")
    print("=" * 64)

    summary = {
        "substrate": "Substrate4_Novel_Sequence_Task",
        "protocol": "SUBSTRATE_4_NOVEL_SEQUENCE_v1",
        "seeds": SEEDS,
        "ticks": TICKS,
        "switch_tick": SWITCH_TICK,
        "results": {"learn": {}, "nolearn": {}}
    }

    learn_post_switch_early = []
    learn_post_switch_late = []
    nolearn_post_switch_late = []

    for seed in SEEDS:
        print(f"\n--- SEED {seed} ---")
        print("Running LEARN arm...")
        w_learn = run_arm(seed, is_learn=True)
        summary["results"]["learn"][str(seed)] = w_learn
        
        # Post-switch window: ticks 11000-13000 (early post switch) vs 18000-20000 (late post switch)
        early_b = np.mean([w["acc"] for w in w_learn[10:13]])
        late_b = np.mean([w["acc"] for w in w_learn[17:]])
        learn_post_switch_early.append(early_b)
        learn_post_switch_late.append(late_b)
        print(f"  LEARN   Pattern B early: {early_b:6.2f}% | late: {late_b:6.2f}% | delta: {late_b-early_b:+6.2f}pp")

        print("Running NOLEARN arm...")
        w_nolearn = run_arm(seed, is_learn=False)
        summary["results"]["nolearn"][str(seed)] = w_nolearn
        late_nl_b = np.mean([w["acc"] for w in w_nolearn[17:]])
        nolearn_post_switch_late.append(late_nl_b)

    mean_early_b = float(np.mean(learn_post_switch_early))
    mean_late_b = float(np.mean(learn_post_switch_late))
    delta_b = mean_late_b - mean_early_b

    mean_nolearn_late_b = float(np.mean(nolearn_post_switch_late))
    gap_b = mean_late_b - mean_nolearn_late_b

    gate_a_pass = (delta_b >= 5.0)
    gate_b_pass = (gap_b > 3.0)

    verdict_str = "SUBSTRATE_PASSED" if (gate_a_pass and gate_b_pass) else "SUBSTRATE_NULL_OR_DEGRADED"

    summary["metrics"] = {
        "mean_pattern_b_early_acc": round(mean_early_b, 4),
        "mean_pattern_b_late_acc": round(mean_late_b, 4),
        "pattern_b_delta_pp": round(delta_b, 4),
        "mean_nolearn_late_acc_b": round(mean_nolearn_late_b, 4),
        "gap_late_pp_b": round(gap_b, 4),
        "gate_a_pass": gate_a_pass,
        "gate_b_pass": gate_b_pass,
        "verdict": verdict_str
    }

    out_file = os.path.join(results_dir, "sub4_novel_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 64)
    print("SUBSTRATE 4 NOVEL SEQUENCE SUMMARY & VERDICT")
    print("=" * 64)
    print(f"Mean Pattern B Early Acc: {mean_early_b:6.2f}%")
    print(f"Mean Pattern B Late Acc : {mean_late_b:6.2f}%")
    print(f"Novel Pattern B Delta   : {delta_b:+6.2f} pp (Gate A: {'PASS' if gate_a_pass else 'FAIL'})")
    print(f"Mean NOLEARN Late Acc B : {mean_nolearn_late_b:6.2f}%")
    print(f"Static/Ablation Gap B   : {gap_b:+6.2f} pp (Gate B: {'PASS' if gate_b_pass else 'FAIL'})")
    print(f"Rule 18 Verdict         : {verdict_str}")
    print(f"Summary saved to        : {out_file}")
    print("=" * 64)

if __name__ == "__main__":
    main()
