"""Substrate 4 — Staged Deep-Time 250,000-Tick Pilot.

Protocol ID: SUBSTRATE_4_DEEP_TIME_250K_v1
Scope: Evaluates multi-hundred-thousand-tick continuous cognitive stability,
asymptotic weight norm convergence, and non-forgetting across deep time under Rule 18 & Rule 24.

Outputs:
  - experiments/sub4_results/sub4_250k_summary.json
"""

import os
import sys
import json
import time
import math
import argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

TICKS = 250000
REPORT_EVERY = 5000
SEEDS = [100, 101, 102, 103]
PATCH_SIZE = 500
N_ORGS = 20

D_MODEL = 32
CONTEXT_LEN = 16
VOCAB = 256
LR = 0.005

_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_DIR, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, _DIR)

# Standalone Deep-Time Runner
from sub4_small_transformer import SmallTransformerAgent, build_patch

T_CRIT = {
    1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706,
    6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281,
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

def run_single_arm(args):
    seed, is_learn, ticks, report_every, n_orgs = args
    arm_str = "LEARN" if is_learn else "NOLEARN"
    t0 = time.time()
    
    patch = build_patch(seed)
    n = len(patch)

    agents = [SmallTransformerAgent(seed * 100 + o) for o in range(n_orgs)]
    cursors = [rng.randint(0, n - 20) for rng in [np.random.RandomState(seed + o) for o in range(n_orgs)]]

    windows = []
    initial_w_head_norm = float(np.mean([np.linalg.norm(a.W_head) for a in agents]))
    initial_w_emb_norm = float(np.mean([np.linalg.norm(a.tok_embed) for a in agents]))
    
    prev_w_head = [np.copy(a.W_head) for a in agents]

    for tick in range(ticks):
        total_correct = 0
        total_bits = 0
        total_err = 0.0

        for org in range(n_orgs):
            pos = cursors[org]
            in_byte = int(patch[pos])
            tgt_byte = int(patch[(pos + 1) % n])

            pred_byte, err_sum = agents[org].step(in_byte, tgt_byte, is_learn)

            xb = int(pred_byte) ^ tgt_byte
            correct = 8 - bin(xb & 0xFF).count("1")
            total_correct += correct
            total_bits += 8
            total_err += float(err_sum)

            if np.random.rand() < 0.7:
                cursors[org] = (cursors[org] + 1) % n
            else:
                cursors[org] = (cursors[org] + np.random.randint(1, 4)) % n

        if (tick + 1) % report_every == 0:
            acc = 100.0 * total_correct / total_bits if total_bits else 0.0
            mean_err = total_err / float(n_orgs) if n_orgs else 0.0
            
            curr_w_head_norm = float(np.mean([np.linalg.norm(a.W_head) for a in agents]))
            curr_w_emb_norm = float(np.mean([np.linalg.norm(a.tok_embed) for a in agents]))
            
            displacement = float(np.mean([np.linalg.norm(a.W_head - prev_w_head[i]) for i, a in enumerate(agents)]))
            prev_w_head = [np.copy(a.W_head) for a in agents]
            
            rec = {
                "tick": tick + 1,
                "acc": round(acc, 4),
                "loss": round(mean_err, 4),
                "w_head_norm": round(curr_w_head_norm, 4),
                "w_emb_norm": round(curr_w_emb_norm, 4),
                "w_displacement": round(displacement, 4)
            }
            windows.append(rec)
            
            if (tick + 1) % (report_every * 5) == 0:
                print(f"  [{arm_str} s={seed}] Tick {tick+1:6d}/{ticks} | Acc: {acc:6.2f}% | Loss: {mean_err:6.3f} | ||W_head||: {curr_w_head_norm:5.2f} | dW: {displacement:5.3f}")

    if len(windows) == 0:
        acc = 100.0 * total_correct / total_bits if total_bits else 0.0
        windows.append({"tick": ticks, "acc": round(acc, 4), "loss": 0.0, "w_head_norm": 0.0, "w_emb_norm": 0.0, "w_displacement": 0.0})

    elapsed = time.time() - t0
    
    accs = [w["acc"] for w in windows]
    xs = np.arange(len(accs))
    if len(accs) > 1:
        slope, intercept = np.polyfit(xs, accs, 1)
    else:
        slope = 0.0
    
    early_acc = float(np.mean([w["acc"] for w in windows[:max(1, len(windows)//3)]]))
    late_acc = float(np.mean([w["acc"] for w in windows[-max(1, len(windows)//3):]]))
    delta_pp = late_acc - early_acc
    
    denom = max(100.0 - early_acc, 1e-6)
    rho = float((late_acc - early_acc) / denom * 100.0)
    
    print(f"[{arm_str} s={seed} COMPLETE] Early={early_acc:5.2f}% Late={late_acc:5.2f}% Delta={delta_pp:+5.2f}pp Slope={slope:+5.4f}pp/epoch rho={rho:5.2f}% ({elapsed:.1f}s)")
    
    return {
        "seed": seed,
        "is_learn": is_learn,
        "ticks": ticks,
        "elapsed_s": round(elapsed, 2),
        "early_acc": round(early_acc, 4),
        "late_acc": round(late_acc, 4),
        "delta_pp": round(delta_pp, 4),
        "slope_pp_per_epoch": round(float(slope), 4),
        "rho_pct": round(rho, 4),
        "initial_head_norm": round(initial_w_head_norm, 4),
        "final_head_norm": round(float(np.mean([np.linalg.norm(a.W_head) for a in agents])), 4),
        "windows": windows
    }

def main():
    parser = argparse.ArgumentParser(description="Substrate 4 250k-Tick Deep-Time Pilot Runner")
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--ticks", type=int, default=TICKS)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    out_dir = os.path.join(ROOT, "experiments", "sub4_results")
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 72)
    print("SUBSTRATE 4 — STAGED DEEP-TIME 250,000-TICK PILOT (Rule 18 / Rule 24)")
    print(f"Seeds: {args.seeds} | Ticks: {args.ticks} | Workers: {args.workers}")
    print("=" * 72)

    rep_every = min(REPORT_EVERY, max(100, args.ticks // 50))
    work_items = []
    for s in args.seeds:
        work_items.append((s, True, args.ticks, rep_every, N_ORGS))   # LEARN
        work_items.append((s, False, args.ticks, rep_every, N_ORGS))  # NOLEARN

    t_start = time.time()
    results = {"learn": {}, "nolearn": {}}

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_single_arm, w): w for w in work_items}
        for fut in as_completed(futures):
            r = fut.result()
            arm_key = "learn" if r["is_learn"] else "nolearn"
            results[arm_key][r["seed"]] = r

    total_time = time.time() - t_start

    learn_res = [results["learn"][s] for s in args.seeds]
    nolearn_res = [results["nolearn"][s] for s in args.seeds]

    learn_lates = [r["late_acc"] for r in learn_res]
    nolearn_lates = [r["late_acc"] for r in nolearn_res]
    learn_deltas = [r["delta_pp"] for r in learn_res]
    learn_rhos = [r["rho_pct"] for r in learn_res]
    ablation_gaps = [learn_lates[i] - nolearn_lates[i] for i in range(len(args.seeds))]

    m_gap, _, ci_gap = ci95(ablation_gaps)
    m_delta, _, ci_delta = ci95(learn_deltas)
    m_rho, _, ci_rho = ci95(learn_rhos)

    final_norms = [r["final_head_norm"] for r in learn_res]
    norm_pass = all(n < 100.0 for n in final_norms)
    b_pass = (m_gap >= 20.0 and ci_gap[0] > 0)
    t_pass = (ci_delta[0] > 0 or np.mean(learn_lates) >= 90.0)

    all_passed = b_pass and norm_pass

    print("\n" + "=" * 72)
    print("250,000-TICK DEEP-TIME PILOT SYNTHESIS SCORECARD")
    print("=" * 72)
    print(f"  Mean LEARN Late Acc:      {np.mean(learn_lates):6.2f}%")
    print(f"  Mean NOLEARN Late Acc:    {np.mean(nolearn_lates):6.2f}%")
    print(f"  Ablation Gap (B-Screen):  {m_gap:+6.2f} pp [95% CI: {ci_gap[0]:+.2f}, {ci_gap[1]:+.2f}] -> {'PASS' if b_pass else 'FAIL'}")
    print(f"  In-Run Delta (A-Screen):  {m_delta:+6.2f} pp [95% CI: {ci_delta[0]:+.2f}, {ci_delta[1]:+.2f}]")
    print(f"  Weight Norm Stability:    mean={np.mean(final_norms):.2f} (max={max(final_norms):.2f}) -> {'PASS' if norm_pass else 'FAIL'}")
    print("=" * 72)
    print(f"Overall 250k Pilot Verdict: {'CERTIFIED_DEEP_TIME_STABILITY_PASS' if all_passed else 'DEEP_TIME_WARNING'}")
    print(f"Total Elapsed Time:         {total_time:.1f}s")
    print("=" * 72)

    summary_data = {
        "protocol": "SUBSTRATE_4_DEEP_TIME_250K_v1",
        "seeds": args.seeds,
        "ticks": args.ticks,
        "cohort_size": N_ORGS,
        "total_wall_time_s": round(total_time, 2),
        "mean_learn_late": round(float(np.mean(learn_lates)), 4),
        "mean_nolearn_late": round(float(np.mean(nolearn_lates)), 4),
        "ablation_gap": {
            "mean": round(m_gap, 4),
            "ci95": [round(ci_gap[0], 4), round(ci_gap[1], 4)],
            "pass": b_pass
        },
        "weight_norm_stability": {
            "mean_final_norm": round(float(np.mean(final_norms)), 4),
            "max_final_norm": round(float(max(final_norms)), 4),
            "pass": norm_pass
        },
        "overall_deep_time_pass": all_passed,
        "learn_runs": {str(s): results["learn"][s] for s in args.seeds},
        "nolearn_runs": {str(s): results["nolearn"][s] for s in args.seeds}
    }

    out_file = os.path.join(out_dir, "sub4_250k_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nFull summary saved -> {out_file}")

if __name__ == "__main__":
    main()
