"""Substrate 4 Extended — Confirmatory Driver (Fresh Seeds 100–107).

Protocol ID: SUBSTRATE_4_EXTENDED_20K_CONFIRMATORY_v1
Amendment:   Docs/Architecture/SUBSTRATE_4_LEARNING_CURVE_v1.md

Evaluates fresh seeds 100–107 under the corrected Gate A/B battery:
  - T: OLS slope of window accuracy across ticks (95% CI > 0)
  - M: Relative error reduction rho = (E0 - E1) / E0 (rho >= 0.25, 95% CI > 0)
  - B: Paired LEARN - NOLEARN late gap (95% CI > 0)
  - Monte-Carlo paired permutation test (10,000 draws)

Outputs:
  - experiments/sub4_results/sub4_20k_confirmatory_summary.json
"""

import os
import sys
import json
import time
import math
import argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, _DIR)

os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"

from sub4_small_transformer import SmallTransformerAgent, build_patch

TICKS = 20000
REPORT_EVERY = 1000
PATCH_SIZE = 500
N_ORGS = 60
RHO_BAR = 0.25

T_CRIT = {
    1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706,
    6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281,
    11: 2.2010, 12: 2.1788, 13: 2.1604, 14: 2.1448, 15: 2.1314,
    16: 2.1199, 17: 2.1098, 18: 2.1009, 19: 2.0930, 20: 2.0860,
    21: 2.0796, 22: 2.0739, 23: 2.0687, 24: 2.0639, 25: 2.0595,
    26: 2.0555, 27: 2.0518, 28: 2.0484, 29: 2.0452, 30: 2.0423,
}

def ci95(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None, None, [None, None]
    m = float(np.mean(v))
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    n = len(v)
    if n < 2:
        return m, sd, [m, m]
    tcrit = T_CRIT.get(n - 1, 1.96)
    half = tcrit * sd / math.sqrt(n)
    return m, sd, [m - half, m + half]

def compute_slope(windows):
    accs = [w["acc"] for w in windows]
    n = len(accs)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=np.float64)
    y = np.array(accs, dtype=np.float64)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    slope = num / den if den != 0 else 0.0
    return float(slope)

def worker_run_arm(args):
    seed, is_learn = args
    arm_name = "LEARN" if is_learn else "NOLEARN"
    t0 = time.time()
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

    elapsed = time.time() - t0
    early_acc = float(np.mean([w["acc"] for w in windows[:3]]))
    late_acc = float(np.mean([w["acc"] for w in windows[-3:]]))
    delta_pp = late_acc - early_acc
    slope = compute_slope(windows)
    
    print(f"[{arm_name} seed={seed}] early={early_acc:5.2f}% late={late_acc:5.2f}% delta={delta_pp:+5.2f}pp elapsed={elapsed:.1f}s")
    
    return {
        "seed": seed,
        "is_learn": is_learn,
        "arm": arm_name,
        "windows": windows,
        "early_acc": early_acc,
        "late_acc": late_acc,
        "delta_pp": delta_pp,
        "slope": slope,
        "elapsed_s": elapsed
    }

def run_confirmatory(seeds, max_workers=4):
    results_dir = os.path.join(ROOT, "experiments", "sub4_results")
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 72)
    print("SUBSTRATE 4 CONFIRMATORY RUN — FRESH SEEDS")
    print(f"Seeds: {seeds} | Ticks: {TICKS} | Report: {REPORT_EVERY} | Workers: {max_workers}")
    print("=" * 72)

    tasks = []
    for s in seeds:
        tasks.append((s, True))   # LEARN
        tasks.append((s, False))  # NOLEARN

    results_by_arm = {"learn": {}, "nolearn": {}}

    t_start = time.time()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_run_arm, t): t for t in tasks}
        for fut in as_completed(futures):
            res = fut.result()
            seed = res["seed"]
            if res["is_learn"]:
                results_by_arm["learn"][seed] = res
            else:
                results_by_arm["nolearn"][seed] = res

    total_wall_time = time.time() - t_start
    print(f"\nAll worker tasks complete in {total_wall_time:.1f}s.")

    # ── Statistical Analysis Battery ──
    learn_deltas = [results_by_arm["learn"][s]["delta_pp"] for s in seeds]
    learn_slopes = [results_by_arm["learn"][s]["slope"] for s in seeds]
    learn_lates = [results_by_arm["learn"][s]["late_acc"] for s in seeds]
    learn_earlies = [results_by_arm["learn"][s]["early_acc"] for s in seeds]

    nolearn_lates = [results_by_arm["nolearn"][s]["late_acc"] for s in seeds]
    nolearn_earlies = [results_by_arm["nolearn"][s]["early_acc"] for s in seeds]
    nolearn_deltas = [results_by_arm["nolearn"][s]["delta_pp"] for s in seeds]

    # Paired Late Gap
    paired_gaps = [learn_lates[i] - nolearn_lates[i] for i in range(len(seeds))]

    # Relative Error Reduction rho = (E0 - E1) / E0
    rho_vals = []
    for s in seeds:
        w_learn = results_by_arm["learn"][s]["windows"]
        e0 = 100.0 - float(np.mean([w["acc"] for w in w_learn[:3]]))
        e1 = 100.0 - float(np.mean([w["acc"] for w in w_learn[-3:]]))
        rho_s = (e0 - e1) / e0 if e0 > 0 else 0.0
        rho_vals.append(rho_s)

    # 95% CIs
    m_delta, sd_delta, ci_delta = ci95(learn_deltas)
    m_slope, sd_slope, ci_slope = ci95(learn_slopes)
    m_gap, sd_gap, ci_gap = ci95(paired_gaps)
    m_rho, sd_rho, ci_rho = ci95(rho_vals)

    # Gate evaluations
    T_pass = bool(ci_slope[0] > 0.0)
    M_pass = bool(m_rho >= RHO_BAR and ci_rho[0] > 0.0)
    B_pass = bool(ci_gap[0] > 0.0)

    # Paired Permutation Test on LEARN late vs NOLEARN late
    diffs = np.array(paired_gaps)
    observed_mean = np.mean(diffs)
    rng = np.random.RandomState(42)
    n_draws = 10000
    perm_means = []
    for _ in range(n_draws):
        signs = rng.choice([-1, 1], size=len(diffs))
        perm_means.append(np.mean(diffs * signs))
    perm_p = float(np.mean([abs(pm) >= abs(observed_mean) for pm in perm_means]))

    if T_pass and M_pass and B_pass:
        verdict = "GATE_A_SCREEN_PASS_CONFIRMED"
    elif T_pass and B_pass and not M_pass:
        verdict = "REAL_BUT_NEGLIGIBLE_F2"
    elif B_pass and not T_pass:
        verdict = "STATIC_ONLY_F3"
    else:
        verdict = "NULL_OR_DEGRADED"

    summary = {
        "protocol": "SUBSTRATE_4_EXTENDED_20K_CONFIRMATORY_v1",
        "amendment": "SUBSTRATE_4_LEARNING_CURVE_v1",
        "seeds": seeds,
        "n_seeds": len(seeds),
        "ticks": TICKS,
        "report_every": REPORT_EVERY,
        "wall_time_s": round(total_wall_time, 2),
        "metrics": {
            "mean_learn_early_acc": round(float(np.mean(learn_earlies)), 4),
            "mean_learn_late_acc": round(float(np.mean(learn_lates)), 4),
            "mean_learn_delta_pp": round(m_delta, 4),
            "delta_ci95": [round(ci_delta[0], 4), round(ci_delta[1], 4)],
            "mean_slope_pp_per_window": round(m_slope, 6),
            "slope_ci95": [round(ci_slope[0], 6), round(ci_slope[1], 6)],
            "mean_nolearn_late_acc": round(float(np.mean(nolearn_lates)), 4),
            "mean_paired_gap_pp": round(m_gap, 4),
            "gap_ci95": [round(ci_gap[0], 4), round(ci_gap[1], 4)],
            "mean_rho": round(m_rho, 4),
            "rho_ci95": [round(ci_rho[0], 4), round(ci_rho[1], 4)],
            "perm_p_value": perm_p,
            "T_slope_pass": T_pass,
            "M_magnitude_pass": M_pass,
            "B_gate_gap_pass": B_pass,
            "verdict": verdict
        },
        "per_seed": {
            str(s): {
                "learn_early_acc": round(results_by_arm["learn"][s]["early_acc"], 4),
                "learn_late_acc": round(results_by_arm["learn"][s]["late_acc"], 4),
                "learn_delta_pp": round(results_by_arm["learn"][s]["delta_pp"], 4),
                "learn_slope": round(results_by_arm["learn"][s]["slope"], 6),
                "nolearn_early_acc": round(results_by_arm["nolearn"][s]["early_acc"], 4),
                "nolearn_late_acc": round(results_by_arm["nolearn"][s]["late_acc"], 4),
                "paired_gap_pp": round(results_by_arm["learn"][s]["late_acc"] - results_by_arm["nolearn"][s]["late_acc"], 4),
                "rho": round(rho_vals[i], 4)
            }
            for i, s in enumerate(seeds)
        }
    }

    out_file = os.path.join(results_dir, "sub4_20k_confirmatory_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 72)
    print("SUBSTRATE 4 CONFIRMATORY REPORT (FRESH SEEDS)")
    print("=" * 72)
    print(f"Seeds Evaluated      : {seeds} (n={len(seeds)})")
    print(f"Mean Early LEARN Acc : {np.mean(learn_earlies):6.2f}%")
    print(f"Mean Late LEARN Acc  : {np.mean(learn_lates):6.2f}%")
    print(f"In-Lifetime Delta    : {m_delta:+6.2f} pp [95% CI: {ci_delta[0]:+.2f}, {ci_delta[1]:+.2f}]")
    print(f"Slope (T Test)       : {m_slope:+.4f} pp/k [95% CI: {ci_slope[0]:+.4f}, {ci_slope[1]:+.4f}] -> {'PASS' if T_pass else 'FAIL'}")
    print(f"Relative Error (M)   : {m_rho*100:5.2f}% [95% CI: {ci_rho[0]*100:+.2f}%, {ci_rho[1]*100:+.2f}%] (bar: 25%) -> {'PASS' if M_pass else 'FAIL'}")
    print(f"Late Ablation Gap (B): {m_gap:+6.2f} pp [95% CI: {ci_gap[0]:+.2f}, {ci_gap[1]:+.2f}] (p={perm_p:.5f}) -> {'PASS' if B_pass else 'FAIL'}")
    print(f"Final Rule-18 Verdict: {verdict}")
    print(f"Summary Saved        : {out_file}")
    print("=" * 72)

    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Substrate 4 Confirmatory Runner")
    parser.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102, 103],
                        help="List of seeds to evaluate (default: 100 101 102 103)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel worker processes (default: 4)")
    args = parser.parse_args()

    run_confirmatory(seeds=args.seeds, max_workers=args.workers)
