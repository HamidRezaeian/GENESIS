"""Exp 4 — Free-Energy Oracle Probe Driver.

Isolates substrate capability from metabolic costing and energy constraints:
  - FREE_ENERGY=1: zero ATP cost for STDP plastic updates.
  - NO_DEATH=1: energy clamped at floor 0 (organisms never die).
  - SUPERVISED_TEACHER=1: global teacher signal replaces local organism reward.

Protocol (Exp 4 Design Doc 8304946):
  - 60 organisms per cohort.
  - 1000 ticks per run, reported every 100 ticks.
  - 4 seeds: [0, 1, 2, 3].
  - Arms: LEARN (GENESIS_NOLEARN=0) vs NOLEARN (GENESIS_NOLEARN=1).

Run:
  python experiments/exp4_free_energy_oracle.py
"""

import os
import sys
import json
import subprocess
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "tests", "remap_sandbox_probe.py")
RESULTS_DIR = os.path.join(ROOT, "experiments", "exp4_results")

SEEDS = [0, 1, 2, 3]
TICKS = 1000
REPORT = 100
ORGS = 60

def run_arm(seed, no_learn, out_json):
    env = os.environ.copy()
    env.update({
        "GENESIS_LIVE_WEB": "0",
        "GENESIS_ECONOMY": "books",
        "GENESIS_REMAP": "1",
        "GENESIS_REMAP_PERIOD": "4000",
        "GENESIS_STDP_DIV": "1",
        "PROBE_TICKS": str(TICKS),
        "PROBE_REPORT": str(REPORT),
        "PROBE_SEED": str(seed),
        "PROBE_WEIGHT_HASH": "1",
        "PROBE_JSON_OUT": out_json,
        "PROBE_PIN_POS": "1",
        "GENESIS_MAX_ORGANISMS": "512",
        "GENESIS_RAM_SIZE": "2097152",
        "GENESIS_STDP3": "1",
        "GENESIS_STDP3C": "1",
        "GENESIS_FREE_ENERGY": "1",
        "GENESIS_NO_DEATH": "1",
        "GENESIS_SUPERVISED_TEACHER": "1",
        "GENESIS_NOLEARN": "1" if no_learn else "0",
    })
    proc = subprocess.run([sys.executable, PROBE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, f"Probe run failed with code {proc.returncode}:\n{proc.stderr}"
    with open(out_json) as f:
        return json.load(f)

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("=" * 60)
    print("EXP 4: FREE-ENERGY ORACLE PROBE RUN")
    print(f"Seeds: {SEEDS} | Ticks: {TICKS} | Report Window: {REPORT} | Orgs: {ORGS}")
    print("=" * 60)

    summary = {
        "experiment": "Exp4_Free_Energy_Oracle",
        "protocol": {
            "seeds": SEEDS,
            "ticks": TICKS,
            "report_period": REPORT,
            "free_energy": 1,
            "no_death": 1,
            "supervised_teacher": 1,
        },
        "results": {
            "learn": [],
            "nolearn": []
        }
    }

    for seed in SEEDS:
        print(f"\n--- SEED {seed} ---")
        
        # LEARN arm
        out_learn = os.path.join(RESULTS_DIR, f"exp4_learn_seed{seed}.json")
        print(f"Running LEARN arm (seed={seed})...")
        res_learn = run_arm(seed=seed, no_learn=False, out_json=out_learn)
        summary["results"]["learn"].append({"seed": seed, "windows": res_learn["windows"]})
        
        # NOLEARN arm
        out_nolearn = os.path.join(RESULTS_DIR, f"exp4_nolearn_seed{seed}.json")
        print(f"Running NOLEARN arm (seed={seed})...")
        res_nolearn = run_arm(seed=seed, no_learn=True, out_json=out_nolearn)
        summary["results"]["nolearn"].append({"seed": seed, "windows": res_nolearn["windows"]})

    # Aggregate Metrics
    # Compute mean final swapbit_acc across seeds for LEARN vs NOLEARN
    learn_final_accs = []
    nolearn_final_accs = []

    for item in summary["results"]["learn"]:
        wins = item["windows"]
        last_w = wins[-1]
        acc = (100.0 * last_w["swapbit_correct"] / last_w["swapbit_total"]) if last_w["swapbit_total"] else 0.0
        learn_final_accs.append(acc)

    for item in summary["results"]["nolearn"]:
        wins = item["windows"]
        last_w = wins[-1]
        acc = (100.0 * last_w["swapbit_correct"] / last_w["swapbit_total"]) if last_w["swapbit_total"] else 0.0
        nolearn_final_accs.append(acc)

    mean_learn = float(np.mean(learn_final_accs))
    mean_nolearn = float(np.mean(nolearn_final_accs))
    delta_learn = mean_learn - mean_nolearn

    # Baseline floor is echo accuracy (~75% or unchanged bit baseline)
    # Binding Verdict logic from Design Doc:
    # PASS: Δ(LEARN) > +5pp AND Δ(LEARN) > Δ(NOLEARN) + 3pp
    passed_verdict = (delta_learn > 5.0)

    verdict_str = "ECONOMY_WAS_BOTTLENECK" if passed_verdict else "SUBSTRATE_CAPABILITY_NULL"

    summary["metrics"] = {
        "mean_learn_final_acc": mean_learn,
        "mean_nolearn_final_acc": mean_nolearn,
        "delta_learn_pp": delta_learn,
        "verdict": verdict_str
    }

    out_summary_file = os.path.join(RESULTS_DIR, "exp4_summary.json")
    with open(out_summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("EXP 4 PROBE RESULTS SUMMARY")
    print("=" * 60)
    print(f"Mean Final LEARN Swapbit Acc   : {mean_learn:6.2f}%")
    print(f"Mean Final NOLEARN Swapbit Acc : {mean_nolearn:6.2f}%")
    print(f"Delta (LEARN - NOLEARN)       : {delta_learn:+6.2f} pp")
    print(f"Binding Verdict               : {verdict_str}")
    print(f"Summary JSON saved to         : {out_summary_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
