"""Exp 5 — Metabolic Cost Threshold Scan Driver.

Protocol ID: EXP5_COST_THRESHOLD_SCAN_v1 (pre-registered in Docs/Exp5_Protocol.md)

Scans plasticity cost factor theta in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0] under NO_DEATH=1
to identify the exact metabolic threshold theta* where in-lifetime learning becomes viable.

Run:
  python experiments/exp5_cost_threshold_scan.py
"""

import os
import sys
import json
import time
import numpy as np

# Protocol Parameters
TICKS = 2000
REPORT_EVERY = 200
SEEDS = [0, 1, 2, 3]
THETA_POINTS = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
NOLEARN_THETA_POINTS = [0.0, 0.5, 1.0]
PATCH_SIZE = 500
N_ORGS = 60

RESERVOIR_SIZE = 256
RESERVOIR_SPARSITY = 0.1
RESERVOIR_TAU = 20.0
READOUT_LR = 0.01
CYCLES_PER_STDP_UPDATE = 10.0

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

# Environment Setup
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

def run_arm(seed, theta, is_learn):
    np.random.seed(seed)
    patch = build_patch(seed)
    n = len(patch)
    lr = READOUT_LR if is_learn else 0.0

    gl.g_reservoir_state[:] = 0.0
    gl.g_energy[gl.g_alive] = np.float32(100.0)

    org_cursors = np.random.RandomState(seed).randint(0, n, size=N_ORGS)
    org_states = [np.zeros(RESERVOIR_SIZE, dtype=np.float32) for _ in range(N_ORGS)]
    org_readouts = [(np.random.rand(8, RESERVOIR_SIZE).astype(np.float32) - 0.5) * 0.2 for _ in range(N_ORGS)]
    org_energies = np.full(N_ORGS, 100.0, dtype=np.float32)

    windows = []
    
    for tick in range(TICKS):
        total_correct = 0
        total_bits = 0
        total_err = 0.0

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

            # Apply energy charge proportional to theta if learning
            if is_learn and theta > 0.0:
                cost = CYCLES_PER_STDP_UPDATE * theta * 0.01
                org_energies[org] = max(0.0, org_energies[org] - cost)

            if np.random.rand() < 0.7:
                org_cursors[org] = (org_cursors[org] + 1) % n
            else:
                org_cursors[org] = (org_cursors[org] + np.random.randint(1, 4)) % n

        if (tick + 1) % REPORT_EVERY == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_err = total_err / (8.0 * N_ORGS) if N_ORGS else 0.0
            mean_energy = float(np.mean(org_energies))
            rec = {
                "tick": tick + 1,
                "acc": round(acc, 4),
                "mean_err": round(mean_err, 6),
                "mean_energy": round(mean_energy, 4)
            }
            windows.append(rec)

    return windows

def main():
    results_dir = os.path.join(ROOT, "experiments", "exp5_results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 64)
    print("EXP 5: METABOLIC COST THRESHOLD SCAN")
    print(f"Thetas: {THETA_POINTS} | Seeds: {SEEDS} | Ticks: {TICKS} | Report: {REPORT_EVERY}")
    print("=" * 64)

    summary = {
        "protocol": "EXP5_COST_THRESHOLD_SCAN_v1",
        "theta_points": THETA_POINTS,
        "seeds": SEEDS,
        "ticks": TICKS,
        "results": {"learn": {}, "nolearn": {}}
    }

    # Store aggregated theta metrics
    theta_summary = {}

    for theta in THETA_POINTS:
        print(f"\n=================== THETA = {theta} ===================")
        summary["results"]["learn"][str(theta)] = []
        
        learn_early_accs = []
        learn_late_accs = []
        learn_energies = []

        for seed in SEEDS:
            w_learn = run_arm(seed, theta, is_learn=True)
            summary["results"]["learn"][str(theta)].append({"seed": seed, "windows": w_learn})
            
            # early acc: ticks 1-600 (indices 0..2); late acc: ticks 1400-2000 (indices 6..9)
            early = np.mean([w["acc"] for w in w_learn[:3]])
            late = np.mean([w["acc"] for w in w_learn[6:]])
            energy = w_learn[-1]["mean_energy"]
            
            learn_early_accs.append(early)
            learn_late_accs.append(late)
            learn_energies.append(energy)
            print(f"  [LEARN seed={seed}] early={early:5.2f}% late={late:5.2f}% delta={late-early:+5.2f}pp energy={energy:6.2f}")

        mean_early = float(np.mean(learn_early_accs))
        mean_late = float(np.mean(learn_late_accs))
        mean_delta = mean_late - mean_early
        mean_energy = float(np.mean(learn_energies))

        theta_summary[str(theta)] = {
            "learn_early_acc": round(mean_early, 2),
            "learn_late_acc": round(mean_late, 2),
            "learn_delta_pp": round(mean_delta, 2),
            "mean_energy": round(mean_energy, 2)
        }

    # Run NOLEARN controls at selected points
    for theta in NOLEARN_THETA_POINTS:
        summary["results"]["nolearn"][str(theta)] = []
        nolearn_lates = []
        for seed in SEEDS:
            w_nolearn = run_arm(seed, theta, is_learn=False)
            summary["results"]["nolearn"][str(theta)].append({"seed": seed, "windows": w_nolearn})
            late = np.mean([w["acc"] for w in w_nolearn[6:]])
            nolearn_lates.append(late)
        theta_summary[str(theta)]["nolearn_late_acc"] = round(float(np.mean(nolearn_lates)), 2)

    # Compute theta* (largest theta where LEARN delta > +5.0 pp)
    theta_star = None
    for theta in sorted(THETA_POINTS, reverse=True):
        if theta_summary[str(theta)]["learn_delta_pp"] > 5.0:
            theta_star = theta
            break

    summary["metrics"] = {
        "theta_summary": theta_summary,
        "theta_star": theta_star
    }

    out_file = os.path.join(results_dir, "exp5_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 64)
    print("EXP 5 RESULTS TABLE")
    print("=" * 64)
    print(f"{'theta':>6} | {'LEARN delta':>11} | {'LEARN late':>11} | {'NOLEARN late':>12} | {'mean energy':>11}")
    print("-" * 64)
    for theta in THETA_POINTS:
        ts = theta_summary[str(theta)]
        nl_str = f"{ts.get('nolearn_late_acc', '-'):>12}" if 'nolearn_late_acc' in ts else f"{'-':>12}"
        print(f"{theta:6.2f} | {ts['learn_delta_pp']:+10.2f}pp | {ts['learn_late_acc']:10.2f}% | {nl_str} | {ts['mean_energy']:11.2f}")
    print("=" * 64)
    print(f"Critical Cost Threshold theta* : {theta_star}")
    print(f"Summary saved to               : {out_file}")
    print("=" * 64)

if __name__ == "__main__":
    main()
