"""
Experiment 91: Rapid Non-Stationary Selection Benchmark (REMAP_PERIOD=500)
(Rule 2, Rule 3, Rule 6, Rule 7, Rule 14, Rule 16, Rule 18, Rule 20)
================================================================================================
Tests whether accelerating target rotation to REMAP_PERIOD=500 ticks forces natural selection
to favor plastic in-lifetime learners (STDP3C + MULTISCALE) over fixed reflexes.

Arm 1 (Control):  REMAP=1, REMAP_PERIOD=500, AUTO_REPRO=1, FOOTPRINT=1, MULTISCALE=0, STDP3C=0 (Fixed Reflex)
Arm 2 (Proposed): REMAP=1, REMAP_PERIOD=500, AUTO_REPRO=1, FOOTPRINT=1, MULTISCALE=1, STDP3C=1 (Plastic Learner)

5 seeds x 10,000 continuous ticks.
Measures: Mean Pop, Mean Energy, Total Births, Birth Rate, Delta Pop, Z-score (Rule 18 finish line).
"""

import os
import sys
import json
import subprocess
import time
import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

SEEDS = [42, 101, 2024, 777, 999]
AUTO_REPRO_THRESH = "250000.0"

ARMS = [
    {
        "name": "Arm 1: Control (REMAP-500, Fixed Reflex, No Plasticity)",
        "env": {
            "GENESIS_REMAP": "1",
            "GENESIS_REMAP_PERIOD": "500",
            "GENESIS_DIGESTION": "1",
            "GENESIS_PEER": "1",
            "GENESIS_INCOME_FOOTPRINT": "1",
            "GENESIS_AUTO_REPRO": "1",
            "GENESIS_AUTO_REPRO_THRESH": AUTO_REPRO_THRESH,
            "GENESIS_CAM": "0",
            "GENESIS_MULTISCALE": "0",
            "GENESIS_STDP3C": "0",
        }
    },
    {
        "name": "Arm 2: Proposed (REMAP-500, Plastic MULTISCALE+STDP3C)",
        "env": {
            "GENESIS_REMAP": "1",
            "GENESIS_REMAP_PERIOD": "500",
            "GENESIS_DIGESTION": "1",
            "GENESIS_PEER": "1",
            "GENESIS_INCOME_FOOTPRINT": "1",
            "GENESIS_AUTO_REPRO": "1",
            "GENESIS_AUTO_REPRO_THRESH": AUTO_REPRO_THRESH,
            "GENESIS_CAM": "0",
            "GENESIS_MULTISCALE": "1",
            "GENESIS_STDP3C": "1",
        }
    },
]

SUBWORKER_CODE = """
import os, sys, json
import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

seed = int(sys.argv[1])
np.random.seed(seed)

import genesis_lab as gl
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
    g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay, g_conn_w_dna, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    g_clear_count, g_org_run, g_lump_acc, g_race_state, g_race_attempt_q,
    world_tick_numba, spawn_organism, mutate_dna, find_birth_pos, MAX_ORGANISMS, RAM_SIZE
)

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
for org_idx in range(50):
    spawn_organism(org_idx, (org_idx * 1200) % RAM_SIZE, ancestor, 250000)

global_time = np.float64(0)
N_TICKS = 10000

pop_samples = []
energy_samples = []
total_births = 0
total_deaths = 0
prev_alive = int(g_alive[:MAX_ORGANISMS].sum())

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
        g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
        g_clear_count, g_org_run, g_lump_acc,
        g_race_state, g_race_attempt_q,
    )
    total_births += int(n_births)
    for i in range(n_births):
        child_dna = mutate_dna(g_b_genomes[i, :g_b_g_count[i]])
        for j in range(MAX_ORGANISMS):
            if not g_alive[j]:
                spawn_organism(j, find_birth_pos(g_b_pos[i]), child_dna, float(g_b_energy[i]))
                break
    cur_alive = int(g_alive[:MAX_ORGANISMS].sum())
    if cur_alive < prev_alive:
        total_deaths += (prev_alive - cur_alive)
    prev_alive = cur_alive
    global_time += 1

    if (tick_idx + 1) % 100 == 0:
        pop_samples.append(cur_alive)
        if cur_alive > 0:
            energy_samples.append(float(g_energy[np.where(g_alive[:MAX_ORGANISMS])[0]].mean()))

mean_pop = float(np.mean(pop_samples)) if pop_samples else 0.0
mean_energy = float(np.mean(energy_samples)) if energy_samples else 0.0

res = {
    "seed": seed,
    "mean_pop": mean_pop,
    "mean_energy": mean_energy,
    "total_births": total_births,
    "total_deaths": total_deaths,
}
print("JSON_RESULT:" + json.dumps(res))
"""

def main():
    worker_script = os.path.join(REPO_ROOT, "exp91_worker.py")
    with open(worker_script, "w", encoding="utf-8") as f:
        f.write(SUBWORKER_CODE)

    print("==========================================================================")
    print("Experiment 91: Rapid Non-Stationary Selection Benchmark (REMAP_PERIOD=500)")
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
            env["GENESIS_ECONOMY"] = "books"

            cmd = [sys.executable, worker_script, str(seed)]
            t0 = time.time()
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            elapsed = time.time() - t0

            res_data = None
            for line in proc.stdout.splitlines():
                if line.startswith("JSON_RESULT:"):
                    res_data = json.loads(line[12:])
                    break

            if res_data is None:
                print(f"  Seed {seed}: ERROR\n{proc.stdout[-400:]}\nSTDERR:{proc.stderr[-200:]}")
            else:
                res_data["elapsed"] = elapsed
                results[arm_name].append(res_data)
                print(f"  Seed {seed:4d}: Pop={res_data['mean_pop']:.2f}, E={res_data['mean_energy']:.0f}, Births={res_data['total_births']}, Deaths={res_data['total_deaths']} ({elapsed:.1f}s)")

    if os.path.exists(worker_script):
        os.remove(worker_script)

    print("\n==========================================================================")
    print("STATISTICAL SUMMARY (Rule 3, Rule 14/16, Rule 18, Rule 20)")
    print("==========================================================================")

    arm_stats = {}
    for arm_name, seed_runs in results.items():
        pops = [r["mean_pop"] for r in seed_runs]
        energies = [r["mean_energy"] for r in seed_runs]
        births = [r["total_births"] for r in seed_runs]
        arm_stats[arm_name] = {
            "mean_pop": float(np.mean(pops)),
            "std_pop": float(np.std(pops)),
            "mean_energy": float(np.mean(energies)),
            "mean_births": float(np.mean(births)),
            "std_births": float(np.std(births)),
        }
        print(f"{arm_name[:48]:<48}: Pop={arm_stats[arm_name]['mean_pop']:.2f}±{arm_stats[arm_name]['std_pop']:.2f} | E={arm_stats[arm_name]['mean_energy']:.0f} | Births={arm_stats[arm_name]['mean_births']:.1f}±{arm_stats[arm_name]['std_births']:.1f}")

    arm1 = arm_stats["Arm 1: Control (REMAP-500, Fixed Reflex, No Plasticity)"]
    arm2 = arm_stats["Arm 2: Proposed (REMAP-500, Plastic MULTISCALE+STDP3C)"]

    delta_pop = arm2["mean_pop"] - arm1["mean_pop"]
    delta_births = arm2["mean_births"] - arm1["mean_births"]
    z_pop = delta_pop / arm2["std_pop"] if arm2["std_pop"] > 0 else 0.0

    print("--------------------------------------------------------------------------")
    print(f"Arm2 vs Arm1: ΔPop={delta_pop:+.2f}, Z_pop={z_pop:+.2f}σ | ΔBirths={delta_births:+.1f}")

    passed = (delta_pop > 0) and (z_pop >= 1.0) and (arm2["mean_births"] > arm1["mean_births"])

    if passed:
        verdict = "🟢 MULTI-GENERATIONAL ASCENT CONFIRMED: Plasticity Selection Advantage (Z >= 1.0σ under Rapid REMAP)"
    else:
        verdict = f"VERDICT: ΔPop Z={z_pop:+.2f}σ, ΔBirths={delta_births:+.1f}"

    print(f"BINDING VERDICT: {verdict}")

    out_file = os.path.join(REPO_ROOT, "exp91_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"arms": results, "stats": arm_stats,
                   "delta_pop": delta_pop, "z_pop": z_pop,
                   "delta_births": delta_births,
                   "verdict": verdict}, f, indent=2)
    print(f"Saved: {out_file}")

if __name__ == "__main__":
    main()
