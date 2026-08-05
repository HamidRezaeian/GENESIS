"""NE founder-viability diagnostic (2026-08-05): WHY do σ=0.1-every-gene founders die?
Arms: A = plain ancestor; B = ancestor + jitter all genes; C = ancestor + jitter only on
genes the ancestor expresses (|founder|>0) + params. 12 orgs each, 600 ticks, same physics
as the NE arm. Prints per-50-tick: pop alive, mean energy, cumulative deaths, kernel births
(reproduce spam), ne bytes read, total correct-read events."""
import os, sys, random
import numpy as np

PROBE_SEED = 0
os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"
os.environ["GENESIS_RESUME"] = "0"
os.environ["GENESIS_AUTO_REPRO"] = "0"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_NOLEARN"] = "1"
os.environ["GENESIS_STDP3C"] = "0"
os.environ["GENESIS_STDP3"] = "0"
os.environ["GENESIS_CAM"] = "0"
os.environ["GENESIS_STRUCTURAL_PLASTICITY"] = "0"
os.environ["GENESIS_NEUROEVOLUTION"] = "1"
os.environ["GENESIS_NE_POP"] = "12"
os.environ["GENESIS_NE_REPRO_PERIOD"] = "100000"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import genesis_lab as gl
import neuromorphic_engine as ne
random.seed(0); np.random.seed(0); ne.seed_kernel_rng(0)


def run_arm(label, make_genome):
    # reset world
    for i in range(gl.MAX_ORGANISMS):
        if gl.g_alive[i]:
            gl.g_alive[i] = False
            gl.g_org_grid[gl.g_positions[i]] = -1
            gl.free_block(gl.g_org_n_ptr[i], gl.g_org_n_count[i], gl.g_neuron_map)
            gl.free_block(gl.g_org_s_ptr[i], gl.g_org_s_count[i], gl.g_synapse_map)
            gl.free_block(gl.g_org_g_ptr[i], gl.g_org_g_count[i], gl.g_genome_map)
    gl.g_ram[:] = 0; gl.g_org_grid[:] = -1; gl.g_ne_bytes[:] = 0
    gl.g_read_fuel[:] = np.float32(gl.CELL_STATES)
    gl._lay_library()
    rng = np.random.default_rng(0)
    founder = gl.ne_project_byte_genome(gl.create_intelligent_ancestor(None))
    placed = 0
    for slot in range(gl.MAX_ORGANISMS):
        if placed >= 12: break
        g = make_genome(founder, rng)
        if gl.ne_spawn_genome(slot, g):
            placed += 1
    print(f"\n=== ARM {label}: placed {placed} ===")
    deaths0 = 0
    births_tot = 0
    for t in range(600):
        alive_steps = gl.g_org_lif_steps[gl.g_alive]
        dyn = int(alive_steps.max()) if alive_steps.size else 1
        gl.ne_world_maintenance(t, dyn)
        pre = int(np.sum(gl.g_alive))
        n_alive, n_births = gl.world_tick_numba(
            gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
            gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
            gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight, gl.g_global_conn_elig, gl.g_global_conn_elig_t,
            gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
            gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
            gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
            gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
            gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
            gl.g_viscosity, t, gl.g_org_lif_steps,
            gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
            gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
            gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
            gl.CANVAS_LO, gl.CANVAS_HI, gl.g_org_reward, gl.g_org_elig,
            gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
            gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch,
            gl.g_ram_bank_access, gl.g_ram_bank_access_next, gl.g_curriculum_delay,
            gl.g_conn_w_dna, gl.g_conn_w_slow,
            gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick,
            gl.g_clear_count, gl.g_org_run, gl.g_lump_acc,
            gl.g_race_state, gl.g_race_attempt_q,
            gl.g_reservoir_state, gl.g_reservoir_src, gl.g_reservoir_dst, gl.g_reservoir_weight, gl.g_readout_w,
            gl.g_ne_bytes,
        )
        deaths0 += pre - int(n_alive)
        births_tot += int(n_births)
        if (t % 50) == 0 or t == 599:
            en = gl.g_energy[gl.g_alive]
            print(f"  t={t:>4} alive={int(n_alive):>2} deaths={deaths0:>2} births={births_tot:>3} "
                  f"E_mean={float(en.mean()) if en.size else 0.0:>9.0f} bytes={int(gl.g_ne_bytes.sum())}")
        if int(n_alive) == 0:
            print(f"  EXTINCT by t={t}")
            break


run_arm("A plain ancestor", lambda f, r: f.copy())
run_arm("B jitter ALL genes sigma=0.1", lambda f, r: gl.ne_mutate_gaussian(f, 0.1, r))
def _c(f, r):
    mask = (f != 0.0)
    out = f.copy()
    out[mask] += r.normal(0.0, 0.1, size=int(mask.sum())).astype(np.float32)
    return out
run_arm("C jitter expressed-only", _c)
print("DIAG_DONE")
