"""
STDP_TARGET separate-process A/B driver (Priority 5, Rule-21.5 recruitment gap L290).
=====================================================================================
WHY A SEPARATE PROCESS: world_tick_numba is compile-time gated on the module global
STDP_TARGET, and numba caches the compiled kernel at PROCESS level (in-memory). In a
long-lived process, importlib.reload() reuses the FIRST-compiled kernel regardless of the
flag (verified: reload takes ~0.02s, no cache regeneration, identical output for flag 0/1).
Therefore the only way to exercise STDP_TARGET=1 is a FRESH OS process, which compiles its
own kernel with the flag baked.

Run TWICE, in two separate processes, and compare the JSON:

    GENESIS_STDP_TARGET=0 python3 src/exp_stdp_target_ab_driver.py   # arm A (default)
    GENESIS_STDP_TARGET=1 python3 src/exp_stdp_target_ab_driver.py   # arm B (recruitment delta-rule)

Each prints {extinction_tick, income_ticks, cam_final, stdp_target, n_ticks}. A real effect
of the recruitment delta-rule shows up as a difference in income_ticks / extinction_tick /
output recruitment between the two arms.

Honest context: Exp 78 (this session) shows the seeded ancestor earns ZERO income on the book
economy regardless, so even a working recruitment mechanism may not alone close the income gap
— compositionality is multi-factor architectural (store-clock L271 + recruitment L290 + the
income mapping), not a single-flag fix.
"""
import os, sys, json, time
import numpy as np

os.environ.setdefault("GENESIS_WMEM", "1")
os.environ.setdefault("GENESIS_CAM", "1")
os.environ.setdefault("GENESIS_CAM_KEY_BITS", "8")
os.environ.setdefault("GENESIS_STDP", "1")
os.environ.setdefault("GENESIS_ECONOMY", "books")
os.environ.setdefault("GENESIS_HEADLESS", "1")
# GENESIS_STDP_TARGET is read from the caller's environment (0 or 1).

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import genesis_lab as gl
import neuromorphic_engine as ne
from genesis_lab import (g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
    g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
    g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
    g_neuron_map, g_synapse_map, g_genome_map, g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
    g_global_genome, g_org_g_ptr, g_org_g_count, o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
    o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e, g_viscosity, g_org_lif_steps,
    g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy, voice_buf, vocal_cords,
    vocal_prev, action_now, action_prev, g_read_log, g_read_fuel, g_cell_owner, g_read_hits,
    g_org_reward, g_org_elig, g_global_sense_type, g_global_sense_meta, g_global_act_drive,
    g_org_delay_buf, g_org_stomach_fuel, g_org_scratch, g_ram_bank_access, g_ram_bank_access_next,
    g_curriculum_delay, g_conn_w_dna, g_conn_w_slow, g_conn_w_slow, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    g_clear_count, g_org_run, g_lump_acc, g_race_state, g_race_attempt_q,
    world_tick_numba, spawn_organism, mutate_dna, find_birth_pos, CANVAS_LO, CANVAS_HI, MAX_ORGANISMS, RAM_SIZE)

def tick(gt):
    return world_tick_numba(g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
        g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
        g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
        g_neuron_map, g_synapse_map, g_genome_map, g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
        g_global_genome, g_org_g_ptr, g_org_g_count, o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
        o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e, g_viscosity, gt, g_org_lif_steps,
        g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy, 0, 0, voice_buf, vocal_cords,
        vocal_prev, action_now, action_prev, g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI,
        g_org_reward, g_org_elig, g_global_sense_type, g_global_sense_meta, g_global_act_drive,
        g_org_delay_buf, g_org_stomach_fuel, g_org_scratch, g_ram_bank_access, g_ram_bank_access_next,
        g_curriculum_delay, g_conn_w_dna, g_conn_w_slow, g_conn_w_slow, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
        g_clear_count, g_org_run, g_lump_acc, g_race_state, g_race_attempt_q)

def main(n_ticks=2000, seed=42):
    K = 8; NOISE = ord('a'); rng = np.random.RandomState(seed)
    ram = np.full(RAM_SIZE, NOISE, dtype=np.uint8); pos = 0
    while pos + 7 <= RAM_SIZE:
        c1 = rng.randint(0, K); c2 = rng.randint(0, K)
        ram[pos:pos+7] = [97+c1, NOISE, NOISE, 97+c2, NOISE, NOISE, 65+(c1+c2)%K]; pos += 7
    g_ram[:] = ram
    anc = gl.create_intelligent_ancestor()
    spawn_organism(0, 100, anc, 250000)
    gt = np.float64(0); tick(gt)
    g_alive[:] = False; g_org_grid[:] = -1
    spawn_organism(0, 100, anc, 250000); g_read_log[0] = 0

    income_ticks, prev_e, ext = 0, 250000.0, None
    t0 = time.time()
    for t in range(n_ticks):
        tick(gt); gt += 1; g_read_log[0] = 0
        alive = bool(g_alive[0]); e = float(g_energy[0]) if alive else 0.0
        if alive:
            if e - prev_e > 0: income_ticks += 1
            prev_e = e
        elif ext is None and t > 0:
            ext = t + 1
    print(json.dumps({
        "stdp_target": bool(ne.STDP_TARGET),
        "n_ticks": n_ticks,
        "extinction_tick": ext if ext else n_ticks,
        "income_ticks": income_ticks,
        "cam_final": int(np.asarray(g_cam_valid[0]).sum()),
        "runtime_s": round(time.time() - t0, 2),
    }))

if __name__ == "__main__":
    main()
