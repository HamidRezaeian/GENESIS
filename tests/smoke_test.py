"""
Bounded headless smoke test for the neuromorphic SNN engine.
Drives world_tick_numba directly (no websocket thread, no infinite loop) so we can
confirm the engine JIT-compiles and runs a few hundred ticks without crashing, and
watch the population/energy dynamics. Used as a before/after guard around edits.
"""
import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import numpy as np
import genesis_lab as gl


def run(n_ticks=200, seed_pop=300, food_rate=0.1):
    gl.seed_universe(seed_pop)
    print(f"Seeded {int(np.sum(gl.g_alive))} organisms. Compiling + running {n_ticks} ticks...")
    t0 = time.time()
    GLOBAL_CYCLE_POOL = 3000
    peak = 0
    extinctions = 0
    for t in range(n_ticks):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            # Mirror sim_loop: extinction triggers an Ark/fossil reseed rather than ending.
            extinctions += 1
            print(f"  tick {t}: EXTINCT #{extinctions} -> Ark reseed")
            gl.seed_universe(300, use_ark=True)
            continue
        peak = max(peak, alive)
        # Food respawn, exactly as sim_loop does it (pristine-memory access = 0x55 cells).
        whole = int(food_rate)
        for _ in range(whole):
            idx = random.randint(0, gl.RAM_SIZE - 1)
            if gl.g_ram[idx] == 0x00:
                gl.g_ram[idx] = 0x55
        if random.random() < (food_rate - whole):
            idx = random.randint(0, gl.RAM_SIZE - 1)
            if gl.g_ram[idx] == 0x00:
                gl.g_ram[idx] = 0x55
        steps = max(1, int(GLOBAL_CYCLE_POOL / max(1, alive)))
        n_alive, n_births = gl.world_tick_numba(
            gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
            gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
            gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
            gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
            gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
            gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
            gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
            gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max,
            gl.g_viscosity, gl.global_time, gl.g_org_lif_steps,  # per-org architecture-derived steps
            gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
            gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.g_read_log,
        )
        # process births exactly like sim_loop
        for i in range(n_births):
            child_dna = gl.mutate_dna(gl.g_b_genomes[i, :gl.g_b_g_count[i]])
            slot = -1
            for j in range(gl.MAX_ORGANISMS):
                if not gl.g_alive[j]:
                    slot = j; break
            if slot != -1:
                child_pos = gl.g_b_pos[i]
                offset = 1
                while gl.g_org_grid[child_pos] != -1 and offset < 100:
                    child_pos = (gl.g_b_pos[i] + offset) % gl.RAM_SIZE
                    offset += 1
                gl.spawn_organism(slot, child_pos, child_dna, initial_energy=gl.g_b_energy[i])
        gl.global_time += steps
        if t % 25 == 0:
            energies = gl.g_energy[gl.g_alive]
            avg_e = float(np.mean(energies)) if len(energies) else 0.0
            print(f"  tick {t:4d} | pop {n_alive:4d} | births {n_births:3d} | avg_energy {avg_e:11.1f} | neurons_used {int(np.sum(gl.g_neuron_map))}")
    dt = time.time() - t0
    final = int(np.sum(gl.g_alive))
    print(f"DONE in {dt:.1f}s | final pop {final} | peak pop {peak}")
    return final, peak


if __name__ == "__main__":
    run()
