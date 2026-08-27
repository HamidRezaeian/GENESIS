"""
Experiment 81: Deep Temporal Credit Assignment Driver (Rule 3, Rule 8, Rule 18, Rule 20)
========================================================================================
Runs a 5-seed x 3-arm A/B/C benchmark across separate sub-processes to isolate Numba JIT cache.

Arm 1 (Control): NOLEARN (plasticity OFF baseline)
Arm 2 (Baseline): STDP_TARGET (1-tick immediate error rule)
Arm 3 (Proposed): STDP_TD_ELIG (Decaying Eligibility Trace + TD Neuromodulator)

Measures: Mean, Std, Delta (Arm 3 vs Arm 2), and Z-score across 5 independent seeds.
"""

import os
import sys
import json
import subprocess
import time
import numpy as np

# Rule 8: Discover repo root and add <root>/src to sys.path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

SEEDS = [42, 101, 2024, 777, 999]
ARMS = [
    {"name": "Arm 1: NOLEARN", "env": {"GENESIS_NOLEARN": "1", "GENESIS_STDP_TARGET": "0", "GENESIS_TD_ELIG": "0"}},
    {"name": "Arm 2: STDP_TARGET", "env": {"GENESIS_NOLEARN": "0", "GENESIS_STDP_TARGET": "1", "GENESIS_TD_ELIG": "0"}},
    {"name": "Arm 3: STDP_TD_ELIG", "env": {"GENESIS_NOLEARN": "0", "GENESIS_STDP_TARGET": "1", "GENESIS_TD_ELIG": "1"}},
]

SUBWORKER_CODE = """
import os, sys, json, time
import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

seed = int(sys.argv[1])
np.random.seed(seed)

import genesis_lab as gl
import neuromorphic_engine as ne
from genesis_lab import (
    g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
    g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
    g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
    g_neuron_map, g_synapse_map, g_genome_map, g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
    g_global_genome, g_org_g_ptr, g_org_g_count, o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
    o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e, g_viscosity, g_org_lif_steps,
    g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
    g_oracle_val, g_oracle_target, voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
    g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI, g_org_reward, g_org_elig,
    g_global_sense_type, g_global_sense_meta, g_global_act_drive, g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
    g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay, g_conn_w_dna, g_conn_w_slow, g_conn_w_slow, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    g_clear_count, g_org_run, g_lump_acc, g_race_state, g_race_attempt_q,
    world_tick_numba, spawn_organism, mutate_dna, find_birth_pos, MAX_ORGANISMS, RAM_SIZE
)

# Initialize RAM
K = 8; NOISE = ord('a')
rng = np.random.RandomState(seed)
ram = np.full(RAM_SIZE, NOISE, dtype=np.uint8)
pos = 0
while pos + 7 <= RAM_SIZE:
    c1 = rng.randint(0, K); c2 = rng.randint(0, K)
    ram[pos:pos+7] = [97+c1, NOISE, NOISE, 97+c2, NOISE, NOISE, 65+(c1+c2)%K]
    pos += 7
g_ram[:] = ram

ancestor = gl.create_intelligent_ancestor()
spawn_organism(0, 100, ancestor, 250000)

global_time = np.float64(0)
N_TICKS = 2000

for tick_idx in range(N_TICKS):
    n_alive, n_births = world_tick_numba(
        g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
        g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
        g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
        g_neuron_map, g_synapse_map, g_genome_map,
        g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
        g_global_genome, g_org_g_ptr, g_org_g_count,
        o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
        o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,
        g_viscosity, global_time, g_org_lif_steps,
        g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
        g_oracle_val, g_oracle_target, voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
        g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI,
        g_org_reward, g_org_elig,
        g_global_sense_type, g_global_sense_meta, g_global_act_drive,
        g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
        g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay,
        g_conn_w_dna,
        g_conn_w_slow,
        g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
        g_clear_count,
        g_org_run, g_lump_acc,
        g_race_state, g_race_attempt_q,
    )
    for i in range(n_births):
        child_dna = mutate_dna(g_b_genomes[i, :g_b_g_count[i]])
        for j in range(MAX_ORGANISMS):
            if not g_alive[j]:
                spawn_organism(j, find_birth_pos(g_b_pos[i]), child_dna, float(g_b_energy[i]))
                break
    global_time += 1

final_pop = int(g_alive[:MAX_ORGANISMS].sum())
total_reads = int(g_read_log.sum()) if hasattr(g_read_log, 'sum') else 0
mean_energy = float(g_energy[np.where(g_alive[:MAX_ORGANISMS])[0]].mean()) if final_pop > 0 else 0.0

res = {
    "seed": seed,
    "final_pop": final_pop,
    "total_reads": total_reads,
    "mean_energy": mean_energy
}
print("JSON_RESULT:" + json.dumps(res))
"""

def main():
    worker_script = os.path.join(REPO_ROOT, "exp81_worker.py")
    with open(worker_script, "w", encoding="utf-8") as f:
        f.write(SUBWORKER_CODE)

    print("==========================================================================")
    print("Experiment 81: Deep Temporal Credit Assignment Multi-Seed Driver (Rule 3)")
    print("==========================================================================")

    results = {}

    for arm in ARMS:
        arm_name = arm["name"]
        print(f"\nRunning {arm_name} across {len(SEEDS)} seeds...")
        results[arm_name] = []

        for seed in SEEDS:
            env = os.environ.copy()
            env.update(arm["env"])
            env["GENESIS_WMEM"] = "1"
            env["GENESIS_CAM"] = "1"
            env["GENESIS_CAM_KEY_BITS"] = "8"
            env["GENESIS_ECONOMY"] = "books"

            cmd = [sys.executable, worker_script, str(seed)]
            t0 = time.time()
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            elapsed = time.time() - t0

            output = proc.stdout
            res_data = None
            for line in output.splitlines():
                if line.startswith("JSON_RESULT:"):
                    res_data = json.loads(line[12:])
                    break

            if res_data is None:
                print(f"  Seed {seed}: ERROR running worker. Output:\n{output}\nStderr:\n{proc.stderr}")
            else:
                res_data["elapsed"] = elapsed
                results[arm_name].append(res_data)
                print(f"  Seed {seed:4d}: Pop={res_data['final_pop']:3d}, Energy={res_data['mean_energy']:6.1f}, Reads={res_data['total_reads']:6d} ({elapsed:.1f}s)")

    # Clean up worker script
    if os.path.exists(worker_script):
        os.remove(worker_script)

    # Statistical Evaluation per Rule 3 & Rule 20
    print("\n==========================================================================")
    print("STATISTICAL SUMMARY & RULE-3 EVALUATION")
    print("==========================================================================")

    arm_stats = {}
    for arm_name, seed_runs in results.items():
        pops = [r["final_pop"] for r in seed_runs]
        energies = [r["mean_energy"] for r in seed_runs]
        arm_stats[arm_name] = {
            "mean_pop": float(np.mean(pops)),
            "std_pop": float(np.std(pops)),
            "mean_energy": float(np.mean(energies)),
            "std_energy": float(np.std(energies))
        }
        print(f"{arm_name:<20}: Mean Pop = {arm_stats[arm_name]['mean_pop']:.1f} ± {arm_stats[arm_name]['std_pop']:.1f} | Mean Energy = {arm_stats[arm_name]['mean_energy']:.1f} ± {arm_stats[arm_name]['std_energy']:.1f}")

    arm2_pop = arm_stats["Arm 2: STDP_TARGET"]["mean_pop"]
    arm3_pop = arm_stats["Arm 3: STDP_TD_ELIG"]["mean_pop"]
    arm3_std = arm_stats["Arm 3: STDP_TD_ELIG"]["std_pop"]

    delta_pop = arm3_pop - arm2_pop
    z_score = delta_pop / arm3_std if arm3_std > 0 else 0.0

    print("--------------------------------------------------------------------------")
    print(f"Experimental Delta (Arm 3 vs Arm 2): Δ Pop = {delta_pop:+.1f}")
    print(f"Z-Score / Effect Size: Z = {z_score:+.2f} σ")

    passed = (delta_pop > 0) and (z_score >= 1.0)
    verdict = "CONFIRMED (Selection Advantage > 1σ)" if passed else "NULL / FALSIFIED (Selection Advantage <= 1σ)"
    print(f"BINDING VERDICT (Rule 2 / Rule 18): {verdict}")

    out_file = os.path.join(REPO_ROOT, "exp81_results.json")
    summary = {
        "arms": results,
        "stats": arm_stats,
        "delta_pop": delta_pop,
        "z_score": z_score,
        "verdict": verdict
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved detailed JSON results to: {out_file}")

if __name__ == "__main__":
    main()
