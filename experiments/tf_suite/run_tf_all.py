"""Master Benchmark Runner — Task Families 2–5 Evaluation Suite.

Protocol ID: TASK_FAMILIES_2_TO_5_EVAL_v1
Scope: Tests broad-task generalization across TF2, TF3, TF4, TF5 on Substrate 4.

Tasks Evaluated:
  - TF2: Bit Parity (Logical / Non-linear XOR)
  - TF3: Compositional Modular Arithmetic (Algebraic Composition)
  - TF4: 2D Spatial Grid Navigation (Planning / Shortest-Path Policy)
  - TF5: Causal Intervention & Discovery (Do-Calculus Invariance)

Outputs:
  - experiments/tf_results/tf_all_summary.json
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
ROOT = os.path.join(_DIR, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, _DIR)

from tf1_reading import run_tf1_arm
from tf2_bit_parity import run_tf2_arm
from tf3_arithmetic import run_tf3_arm
from tf4_navigation import run_tf4_arm
from tf5_causal import run_tf5_arm

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

def worker_task(args):
    task_id, seed, is_learn, ticks = args
    arm_str = "LEARN" if is_learn else "NOLEARN"
    t0 = time.time()
    
    if task_id == "TF1":
        res = run_tf1_arm(seed=seed, ticks=ticks, is_learn=is_learn)
    elif task_id == "TF2":
        res = run_tf2_arm(seed=seed, ticks=ticks, is_learn=is_learn)
    elif task_id == "TF3":
        res = run_tf3_arm(seed=seed, ticks=ticks, is_learn=is_learn)
    elif task_id == "TF4":
        res = run_tf4_arm(seed=seed, ticks=ticks, is_learn=is_learn)
    elif task_id == "TF5":
        res = run_tf5_arm(seed=seed, ticks=ticks, is_learn=is_learn)
    else:
        raise ValueError(f"Unknown task {task_id}")
        
    elapsed = time.time() - t0
    res["elapsed_s"] = elapsed
    print(f"[{task_id} {arm_str} s={seed}] early={res['early_acc']:5.2f}% late={res['late_acc']:5.2f}% delta={res['delta_pp']:+5.2f}pp elapsed={elapsed:.1f}s")
    return (task_id, seed, is_learn, res)

def run_all_tasks(seeds, ticks=10000, max_workers=4):
    out_dir = os.path.join(ROOT, "experiments", "tf_results")
    os.makedirs(out_dir, exist_ok=True)
    
    tasks_to_run = ["TF1", "TF2", "TF3", "TF4", "TF5"]
    
    work_items = []
    for tid in tasks_to_run:
        for s in seeds:
            work_items.append((tid, s, True, ticks))   # LEARN
            work_items.append((tid, s, False, ticks))  # NOLEARN
            
    print("=" * 72)
    print("MASTER TASK FAMILIES 2–5 BENCHMARK SUITE")
    print(f"Tasks: {tasks_to_run} | Seeds: {seeds} | Ticks: {ticks} | Workers: {max_workers}")
    print("=" * 72)
    
    t_start = time.time()
    results = {tid: {"learn": {}, "nolearn": {}} for tid in tasks_to_run}
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_task, w): w for w in work_items}
        for fut in as_completed(futures):
            tid, s, is_learn, r = fut.result()
            arm_key = "learn" if is_learn else "nolearn"
            results[tid][arm_key][s] = r
            
    total_time = time.time() - t_start
    print(f"\nAll task family runs completed in {total_time:.1f}s.\n")
    
    # Synthesis & Scorecard
    scorecard = {}
    passed_tasks = 0
    
    print("=" * 72)
    print("TASK FAMILIES 2–5 SYNTHESIS SCORECARD")
    print("=" * 72)
    
    for tid in tasks_to_run:
        learn_deltas = [results[tid]["learn"][s]["delta_pp"] for s in seeds]
        learn_lates = [results[tid]["learn"][s]["late_acc"] for s in seeds]
        learn_earlies = [results[tid]["learn"][s]["early_acc"] for s in seeds]
        nolearn_lates = [results[tid]["nolearn"][s]["late_acc"] for s in seeds]
        
        paired_gaps = [learn_lates[i] - nolearn_lates[i] for i in range(len(seeds))]
        
        m_delta, _, ci_delta = ci95(learn_deltas)
        m_gap, _, ci_gap = ci95(paired_gaps)
        
        gate_a = bool(m_delta >= 2.0 and ci_delta[0] > 0.0)
        gate_b = bool(m_gap >= 5.0 and ci_gap[0] > 0.0)
        task_passed = (gate_a and gate_b)
        
        if task_passed:
            passed_tasks += 1
            
        scorecard[tid] = {
            "task_name": {
                "TF1": "Continuous Sequence Reading (RAM Library)",
                "TF2": "Bit Parity (Logical / XOR)",
                "TF3": "Compositional Modular Arithmetic",
                "TF4": "2D Spatial Grid Navigation",
                "TF5": "Causal Intervention & Discovery"
            }[tid],
            "mean_early_learn": round(float(np.mean(learn_earlies)), 2),
            "mean_late_learn": round(float(np.mean(learn_lates)), 2),
            "mean_delta_pp": round(m_delta, 2),
            "delta_ci95": [round(ci_delta[0], 2), round(ci_delta[1], 2)],
            "mean_nolearn_late": round(float(np.mean(nolearn_lates)), 2),
            "mean_gap_pp": round(m_gap, 2),
            "gap_ci95": [round(ci_gap[0], 2), round(ci_gap[1], 2)],
            "gate_a_inrun_pass": gate_a,
            "gate_b_ablation_pass": gate_b,
            "task_passed": task_passed
        }
        
        status_symbol = "[PASS]" if task_passed else "[FAIL]"
        print(f"[{tid}] {scorecard[tid]['task_name']}")
        print(f"      Early: {scorecard[tid]['mean_early_learn']}% -> Late: {scorecard[tid]['mean_late_learn']}% | Delta: {m_delta:+5.2f}pp [CI: {ci_delta[0]:+.2f}, {ci_delta[1]:+.2f}]")
        print(f"      NOLEARN Late: {scorecard[tid]['mean_nolearn_late']}% | Gap: {m_gap:+5.2f}pp [CI: {ci_gap[0]:+.2f}, {ci_gap[1]:+.2f}]")
        print(f"      Result: {status_symbol}\n")
        
    if passed_tasks == 5:
        generalization_status = "CERTIFIED_ROBUST_GENERALIZATION_LEVEL_3"
    elif passed_tasks >= 4:
        generalization_status = "CERTIFIED_BROAD_GENERALIZATION_LEVEL_2"
    else:
        generalization_status = "PARTIAL_OR_TASK_SPECIFIC"
        
    print("=" * 72)
    print(f"Passed Tasks: {passed_tasks}/{len(tasks_to_run)} | Generalization Status: {generalization_status}")
    print("=" * 72)
    
    summary_data = {
        "protocol": "TASK_FAMILIES_1_TO_5_EVAL_v1",
        "seeds": seeds,
        "ticks_per_task": ticks,
        "total_wall_time_s": round(total_time, 2),
        "passed_tasks_count": passed_tasks,
        "total_tasks_count": len(tasks_to_run),
        "generalization_status": generalization_status,
        "scorecard": scorecard
    }
    
    out_file = os.path.join(out_dir, "tf_all_summary.json")
    with open(out_file, "w") as f:
        json.dump(summary_data, f, indent=2)
        
    print(f"Full summary saved -> {out_file}\n")
    return summary_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task Families Benchmark Suite")
    parser.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102, 103],
                        help="List of seeds (default: 100 101 102 103)")
    parser.add_argument("--ticks", type=int, default=10000,
                        help="Ticks per task run (default: 10000)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel worker processes (default: 4)")
    args = parser.parse_args()
    
    run_all_tasks(seeds=args.seeds, ticks=args.ticks, max_workers=args.workers)
