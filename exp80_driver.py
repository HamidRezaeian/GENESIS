
import os, sys, time, random
import numpy as np

# NOTE: Don't set GENESIS_WMEM=1 — engine defaults to 1, ancestor shift register is disabled
os.environ["GENESIS_CAM"] = "1"
os.environ["GENESIS_CAM_KEY_BITS"] = "8"
os.environ["GENESIS_STDP"] = "1"
os.environ["GENESIS_ECONOMY"] = "books"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
import genesis_lab as gl
from genesis_lab import (
    g_ram, g_org_grid, g_positions, g_alive, g_energy, g_age,
    g_global_v, g_global_ref, g_global_t_last, g_global_thresh, g_global_tau, g_global_rec_id,
    g_global_conn_src, g_global_conn_dst, g_global_conn_weight, g_global_conn_elig, g_global_conn_elig_t,
    g_neuron_map, g_synapse_map, g_genome_map,
    g_org_n_ptr, g_org_n_count, g_org_s_ptr, g_org_s_count,
    g_global_genome, g_org_g_ptr, g_org_g_count,
    o_rec_a_plus, o_rec_a_minus, o_rec_tau_p, o_rec_tau_m,
    o_rec_v_rest, o_rec_v_reset, o_rec_tau_def, o_rec_spk_max, o_rec_tau_e,
    g_viscosity, g_org_lif_steps,
    g_b_pos, g_b_parent, g_b_g_start, g_b_g_count, g_b_genomes, g_b_energy,
    voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
    g_read_log, g_read_fuel, g_cell_owner, g_read_hits,
    g_org_reward, g_org_elig,
    g_global_sense_type, g_global_sense_meta, g_global_act_drive,
    g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
    g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay,
    g_conn_w_dna, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    world_tick_numba, spawn_organism, mutate_dna, find_birth_pos,
    CANVAS_LO, CANVAS_HI, MAX_ORGANISMS, RAM_SIZE,
)

# Build Latin-square RAM
K = 8; NOISE = ord('a')
rng = np.random.RandomState(42)
ram = np.full(RAM_SIZE, NOISE, dtype=np.uint8)
pos = 0
while pos + 7 <= RAM_SIZE:
    c1 = rng.randint(0, K); c2 = rng.randint(0, K)
    ram[pos:pos+7] = [97+c1, NOISE, NOISE, 97+c2, NOISE, NOISE, 65+(c1+c2)%K]
    pos += 7
g_ram[:] = ram

# Spawn
ancestor = gl.create_intelligent_ancestor()
print(f"Ancestor: {len(ancestor)} bytes", flush=True)
spawn_organism(0, 100, ancestor, 250000)
print(f"  alive={g_alive[0]}, E={g_energy[0]:.0f}, n={g_org_n_count[0]}, s={g_org_s_count[0]}, depth={g_org_lif_steps[0]}", flush=True)

global_time = np.float64(0)

# JIT warmup
print("JIT warmup...", flush=True)
t0 = time.time()
world_tick_numba(
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
    0, 0, voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
    g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI,
    g_org_reward, g_org_elig,
    g_global_sense_type, g_global_sense_meta, g_global_act_drive,
    g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
    g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay,
    g_conn_w_dna, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
)
print(f"  Warmup: {time.time()-t0:.1f}s, alive={g_alive[0]}, E={g_energy[0]:.0f}", flush=True)

# Reset and re-spawn
g_alive[:] = False; g_org_grid[:] = -1
spawn_organism(0, 100, ancestor, 250000)
g_read_log[0] = 0

# Run 5000 ticks
N_TICKS = 5000
print(f"Running {N_TICKS} ticks...", flush=True)
t0 = time.time()
for tick in range(N_TICKS):
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
        0, 0, voice_buf, vocal_cords, vocal_prev, action_now, action_prev,
        g_read_log, g_read_fuel, g_cell_owner, g_read_hits, CANVAS_LO, CANVAS_HI,
        g_org_reward, g_org_elig,
        g_global_sense_type, g_global_sense_meta, g_global_act_drive,
        g_org_delay_buf, g_org_stomach_fuel, g_org_scratch,
        g_ram_bank_access, g_ram_bank_access_next, g_curriculum_delay,
        g_conn_w_dna, g_cam_keys, g_cam_vals, g_cam_valid, g_cam_tick,
    )
    for i in range(n_births):
        child_dna = mutate_dna(g_b_genomes[i, :g_b_g_count[i]])
        for j in range(MAX_ORGANISMS):
            if not g_alive[j]:
                spawn_organism(j, find_birth_pos(g_b_pos[i]), child_dna, float(g_b_energy[i])); break
    global_time += 1
    g_read_log[0] = 0
    if (tick+1) % 1000 == 0:
        pop = int(g_alive[:MAX_ORGANISMS].sum())
        e = float(g_energy[np.where(g_alive[:MAX_ORGANISMS])[0]].mean()) if pop > 0 else 0
        cam = int(g_cam_valid[:MAX_ORGANISMS].sum())
        print(f"  tick {tick+1}: pop={pop} E={e:.0f} CAM={cam} ({time.time()-t0:.1f}s)", flush=True)

pop = int(g_alive[:MAX_ORGANISMS].sum())
print(f"\nFinal: pop={pop}", flush=True)
if pop > 0:
    idx = np.where(g_alive[:MAX_ORGANISMS])[0]
    print(f"  Energy: mean={g_energy[idx].mean():.0f} total={g_energy[idx].sum():.0f}", flush=True)
    print(f"  Ages: mean={g_age[idx].mean():.0f} max={g_age[idx].max():.0f}", flush=True)
print(f"  CAM: {int(g_cam_valid[:MAX_ORGANISMS].sum())}", flush=True)
print(f"  Reads: {int(g_read_log[:1000].sum())}", flush=True)
