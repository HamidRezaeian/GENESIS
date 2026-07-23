"""Abstract Problem Solving & Deep Live Simulation Probe (Experiment 59 - Phase C).

Evaluates coevolutionary cognitive dynamics and abstract multi-step sequence reasoning
across all 9 integrated substrate mechanics (Grounded Digestion, STDP3C Plasticity,
Memory Depth N=2, Peer Prediction, Red-Queen Evader Defense, Evolvable Sensors/Actuators,
Niche Economy, Working Memory Latch Fabric, and RAM Scratchpad Register Memory).

Strictly adheres to Rule 9 & Rule 18:
- All metrics are Observation-Only.
- Zero hardcoded top-down fitness scores.
- Raw hardware thermodynamics (CELL_STATES = 256).
"""
import os
import sys
import time
import json
import numpy as np
import random

# Force environment configuration for full Phase C substrate
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_BOOK_NAME"] = "00_Ascent"
os.environ["GENESIS_BOOK_CATEGORY"] = "English"
os.environ["GENESIS_DIGESTION"] = "1"
os.environ["GENESIS_PEER"] = "1"
os.environ["GENESIS_REDQUEEN"] = "1"
os.environ["GENESIS_EVOSENSE"] = "1"
os.environ["GENESIS_EVOACT"] = "1"
os.environ["GENESIS_NICHE_ECON"] = "1"
os.environ["GENESIS_WMEM"] = "1"
os.environ["GENESIS_SCRATCH"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import genesis_lab as gl
import books_of_genesis as bog
import self_sustain_test as sst

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
TARGET = int(os.environ.get("GENESIS_BOOK_TARGET", "6000"))
CATEGORY = "English"
NAME = "00_Ascent"

def count_active_sensors():
    """Count total active evolved sensors across all living organisms."""
    total_sensors = 0
    orgs_with_sensors = 0
    alive_mask = gl.g_alive
    for org_id in np.where(alive_mask)[0]:
        n_ptr = gl.g_org_n_ptr[org_id]
        n_count = gl.g_org_n_count[org_id]
        c = 0
        for sn in range(gl.N_IO, n_count):
            if gl.g_global_sense_type[n_ptr + sn] > 0:
                c += 1
        if c > 0:
            orgs_with_sensors += 1
            total_sensors += c
    return orgs_with_sensors, total_sensors

def count_scratch_writes():
    """Count active non-zero values in RAM scratchpads across the colony."""
    alive_mask = gl.g_alive
    active_scratch = 0
    for org_id in np.where(alive_mask)[0]:
        if gl.g_org_scratch[org_id] > 0:
            active_scratch += 1
    return active_scratch

def drain_reads():
    """Drain read log entries and tally predictions and correct solves."""
    rl = gl.g_read_log
    idx = 1
    correct = attempt = predict = peer_events = 0
    while idx < rl[0] and idx + 2 < len(rl):
        t = rl[idx]
        if t == 1:
            correct += 1; idx += 3
        elif t == 3:
            predict += 1; idx += 3
        elif t == 2:
            attempt += 1; idx += 4
        elif t == 4:
            peer_events += 1; idx += 3
        else:
            idx += 1
    rl[0] = 1
    return correct, attempt, predict, peer_events

def lib_bytes():
    """Count printable ASCII curriculum bytes in RAM."""
    r = gl.g_ram
    return int(np.count_nonzero((r >= 32) & (r <= 126) & (r != 0x55)))

def run_abstract_probe(n_ticks=HORIZON):
    print("=" * 70)
    print(f"=== GENESIS PHASE C: EXPERIMENT 59 — ABSTRACT PROBLEM SOLVING PROBE ===")
    print(f"Horizon: {n_ticks} Ticks | Book: {CATEGORY}/{NAME} | Target: {TARGET}B")
    print("Substrate Mechanics: Digestion=1, STDP3C=1, WMEM=1, SCRATCH=1, EVOSENSE=1, EVOACT=1, PEER=1, REDQUEEN=1, NICHE=1")
    print("=" * 70)

    random.seed(42)
    np.random.seed(42)

    # Pre-stock curriculum library
    while lib_bytes() < TARGET:
        if bog.inject_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME) is None:
            break

    gl.seed_universe(300, initial_energy=gl.SEED_ENERGY)
    t0 = time.time()

    extinctions = 0
    refuge_events = 0
    peak_pop = 0
    peak_age_all_time = 0

    ep_corr = ep_att = ep_pred = ep_peer = 0
    EPOCH = 500

    print(f"{'Tick':>7} | {'Pop':>5} | {'Mean E':>8} | {'Correct':>8} | {'Predict':>8} | {'Sensors':>8} | {'Scratch':>8} | {'MaxAge':>7}")
    print("-" * 75)

    for t in range(n_ticks):
        alive_mask = gl.g_alive
        alive_count = int(np.sum(alive_mask))

        if alive_count == 0:
            extinctions += 1
            gl.seed_universe(300, use_ark=True)
            continue

        if alive_count < gl.FOSSIL_POOL_MAX and len(gl.fossil_pool) > 0:
            refuge_events += 1
            gl.seed_refuge(gl.FOSSIL_POOL_MAX - alive_count)

        peak_pop = max(peak_pop, alive_count)
        current_max_age = int(gl.g_age[alive_mask].max()) if alive_count > 0 else 0
        peak_age_all_time = max(peak_age_all_time, current_max_age)

        if lib_bytes() < TARGET:
            bog.regrow_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME)

        gl.g_read_log[0] = 1
        steps = int(gl.g_org_lif_steps[alive_mask].max()) if alive_count > 0 else 1

        _, n_births = gl.world_tick_numba(
            gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
            gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
            gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight, gl.g_global_conn_elig, gl.g_global_conn_elig_t,
            gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
            gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
            gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
            gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
            gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
            gl.g_viscosity, gl.global_time, gl.g_org_lif_steps,
            gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
            gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev, gl.action_now, gl.action_prev,
            gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
            0, 0,
            gl.g_org_reward, gl.g_org_elig,
            gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
            gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch,
            gl.g_ram_bank_access, gl.g_ram_bank_access_next
        )

        sst._process_births(n_births)
        gl.global_time += steps

        c, a, p, pr = drain_reads()
        ep_corr += c; ep_att += a; ep_pred += p; ep_peer += pr

        if (t + 1) % EPOCH == 0 or t == n_ticks - 1:
            energies = gl.g_energy[alive_mask]
            mE = float(np.mean(energies)) if len(energies) > 0 else 0.0
            orgs_with_s, total_s = count_active_sensors()
            scratch_active = count_scratch_writes()
            print(f"{t+1:>7} | {alive_count:>5} | {mE:>8.1f} | {ep_corr:>8} | {ep_pred:>8} | {total_s:>8} | {scratch_active:>8} | {current_max_age:>7}")
            ep_corr = ep_att = ep_pred = ep_peer = 0

    dt = time.time() - t0
    final_pop = int(np.sum(gl.g_alive))
    orgs_with_s, total_s = count_active_sensors()
    scratch_active = count_scratch_writes()

    results = {
        "experiment": "Exp 59 — Abstract Problem Solving & Deep Simulation Probe",
        "horizon_ticks": n_ticks,
        "wall_clock_sec": round(dt, 2),
        "ticks_per_sec": round(n_ticks / dt, 1),
        "final_population": final_pop,
        "peak_population": peak_pop,
        "mass_extinctions": extinctions,
        "refugium_triggers": refuge_events,
        "peak_organism_lifespan": peak_age_all_time,
        "active_sensor_orgs": f"{orgs_with_s}/{final_pop}",
        "total_active_sensors": total_s,
        "active_scratchpad_registers": scratch_active,
    }

    print("\n" + "=" * 70)
    print("=== QUANTITATIVE BENCHMARK RESULTS (EXP 59) ===")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:<32}: {v}")
    print("=" * 70)

    out_file = "exp59_abstract_probe_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {out_file}")

    return results

if __name__ == "__main__":
    run_abstract_probe()
