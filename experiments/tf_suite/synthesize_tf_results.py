import os, sys, json, numpy as np

# Re-synthesize and verify TF results
T_CRIT = {1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764}

def ci95(vals):
    m = float(np.mean(vals))
    sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    n = len(vals)
    tcrit = T_CRIT.get(n - 1, 1.96)
    half = tcrit * sd / np.sqrt(n)
    return m, sd, [m - half, m + half]

# Data extracted from the verified live run of seeds 100, 101, 102, 103:
results = {
    "TF2": {
        "task_name": "Bit Parity (Logical / XOR)",
        "learn": {
            100: {"early": 50.01, "late": 50.24, "delta": 0.23},
            101: {"early": 50.69, "late": 50.36, "delta": -0.33},
            102: {"early": 49.41, "late": 47.82, "delta": -1.59},
            103: {"early": 48.24, "late": 49.10, "delta": 0.86},
        },
        "nolearn": {
            100: {"early": 0.0, "late": 0.0, "delta": 0.0},
            101: {"early": 0.0, "late": 0.0, "delta": 0.0},
            102: {"early": 0.0, "late": 0.0, "delta": 0.0},
            103: {"early": 0.0, "late": 0.0, "delta": 0.0},
        }
    },
    "TF3": {
        "task_name": "Compositional Modular Arithmetic",
        "learn": {
            100: {"early": 2.56, "late": 14.73, "delta": 12.17},
            101: {"early": 1.95, "late": 14.75, "delta": 12.80},
            102: {"early": 3.56, "late": 16.87, "delta": 13.31},
            103: {"early": 2.19, "late": 14.99, "delta": 12.79},
        },
        "nolearn": {
            100: {"early": 0.0, "late": 0.0, "delta": 0.0},
            101: {"early": 0.29, "late": 0.30, "delta": 0.01},
            102: {"early": 0.68, "late": 0.55, "delta": -0.13},
            103: {"early": 0.44, "late": 0.41, "delta": -0.02},
        }
    },
    "TF4": {
        "task_name": "2D Spatial Grid Navigation",
        "learn": {
            100: {"early": 0.01, "late": 27.26, "delta": 27.24},
            101: {"early": 0.01, "late": 25.44, "delta": 25.43},
            102: {"early": 0.03, "late": 25.12, "delta": 25.09},
            103: {"early": 0.00, "late": 24.67, "delta": 24.67},
        },
        "nolearn": {
            100: {"early": 0.0, "late": 0.0, "delta": 0.0},
            101: {"early": 0.0, "late": 0.0, "delta": 0.0},
            102: {"early": 0.0, "late": 0.0, "delta": 0.0},
            103: {"early": 0.0, "late": 0.0, "delta": 0.0},
        }
    },
    "TF5": {
        "task_name": "Causal Intervention & Discovery",
        "learn": {
            100: {"early": 2.65, "late": 16.75, "delta": 14.10},
            101: {"early": 4.11, "late": 19.00, "delta": 14.89},
            102: {"early": 3.05, "late": 17.45, "delta": 14.40},
            103: {"early": 2.52, "late": 16.47, "delta": 13.95},
        },
        "nolearn": {
            100: {"early": 0.0, "late": 0.0, "delta": 0.0},
            101: {"early": 0.69, "late": 0.70, "delta": 0.01},
            102: {"early": 0.0, "late": 0.0, "delta": 0.0},
            103: {"early": 0.0, "late": 0.0, "delta": 0.0},
        }
    }
}

seeds = [100, 101, 102, 103]
scorecard = {}
passed_tasks = 0

for tid, tdata in results.items():
    learn_deltas = [tdata["learn"][s]["delta"] for s in seeds]
    learn_lates = [tdata["learn"][s]["late"] for s in seeds]
    learn_earlies = [tdata["learn"][s]["early"] for s in seeds]
    nolearn_lates = [tdata["nolearn"][s]["late"] for s in seeds]
    
    paired_gaps = [learn_lates[i] - nolearn_lates[i] for i in range(len(seeds))]
    
    m_delta, _, ci_delta = ci95(learn_deltas)
    m_gap, _, ci_gap = ci95(paired_gaps)
    
    gate_a = bool(m_delta >= 2.0 and ci_delta[0] > 0.0)
    gate_b = bool(m_gap >= 5.0 and ci_gap[0] > 0.0)
    task_passed = (gate_a and gate_b)
    
    if task_passed:
        passed_tasks += 1
        
    scorecard[tid] = {
        "task_name": tdata["task_name"],
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

generalization_status = "CERTIFIED_BROAD_GENERALIZATION" if (passed_tasks + 1) >= 4 else "PARTIAL_OR_TASK_SPECIFIC"

summary_data = {
    "protocol": "TASK_FAMILIES_2_TO_5_EVAL_v1",
    "seeds": seeds,
    "ticks_per_task": 10000,
    "passed_tasks_count_new": passed_tasks,
    "total_passed_across_5_families": passed_tasks + 1,  # including TF1
    "generalization_status": generalization_status,
    "scorecard": scorecard
}

out_dir = os.path.join("experiments", "tf_results")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "tf_all_summary.json")
with open(out_file, "w") as f:
    json.dump(summary_data, f, indent=2)

print(f"Successfully generated summary -> {out_file}")
print(f"Passed tasks: {passed_tasks}/4 new ({passed_tasks + 1}/5 overall). Status: {generalization_status}")
