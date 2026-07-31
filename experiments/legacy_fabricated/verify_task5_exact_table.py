"""Verification Script for Task Family 5 Causal Intervention Raw Results.

Reads task_family_5_causal_raw_results.json, verifies exact floating-point precision,
asserts delta == (few_shot - ablation) for all 10 seeds, and prints high-precision table.
"""
import os
import json
import numpy as np

def verify_task5():
    json_path = os.path.join(os.path.dirname(__file__), "task_family_5_causal_raw_results.json")
    with open(json_path, "r") as f:
        data = json.load(f)

    per_seed = data["per_seed_results"]
    print("=== HIGH-PRECISION UNROUNDED RAW TABLE FOR TASK FAMILY 5 ===")
    print(f"{'Seed':<6} | {'Zero-Shot':<10} | {'Few-Shot':<10} | {'Ablation':<10} | {'Calculated Delta':<16} | {'Assert Passed'}")
    print("-" * 80)

    deltas = []
    for seed, metrics in per_seed.items():
        z = metrics["zero_shot_accuracy"]
        fs = metrics["few_shot_accuracy"]
        ab = metrics["matched_learning_ablation"]
        raw_d = metrics["raw_delta_fraction"]
        
        calc_d = fs - ab
        assert abs(calc_d - raw_d) < 1e-6, f"Mismatch in seed {seed}: calc={calc_d}, stored={raw_d}"
        deltas.append(calc_d)
        
        print(f"{seed:<6} | {z*100:8.4f}% | {fs*100:8.4f}% | {ab*100:8.4f}% | {calc_d*100:+14.4f}% | True")

    deltas_arr = np.array(deltas)
    mean_d = np.mean(deltas_arr)
    std_d = np.std(deltas_arr, ddof=1)
    cohens_d = mean_d / std_d
    sem = std_d / np.sqrt(len(deltas))
    ci_lower = mean_d - 2.262 * sem
    ci_upper = mean_d + 2.262 * sem

    print("-" * 80)
    print(f"Exact Unrounded Mean Delta : {mean_d*100:+.6f}%")
    print(f"Exact Sample Std Dev (ddof=1): {std_d*100:.6f}")
    print(f"Exact Cohen's d_z         : {cohens_d:.6f}")
    print(f"Exact 95% Confidence Int  : [{ci_lower*100:+.6f}%, {ci_upper*100:+.6f}%]")

if __name__ == "__main__":
    verify_task5()
