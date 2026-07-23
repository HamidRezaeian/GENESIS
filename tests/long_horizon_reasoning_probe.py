"""Long-Horizon Reasoning Probe (Open Research Question 2).

Evaluates whether the evolved organisms can hold a context cue (using WMEM)
across a long spatial/temporal gap and use it to predict the correct test answer.

Strictly adheres to Rule 9 & Rule 18:
- All metrics are Observation-Only.
- Zero hardcoded top-down fitness scores.
"""
import os
import sys
import time
import json
import numpy as np
import random

# Force environment configuration for full Phase C substrate
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_BOOK_NAME"] = "DelayedMatch"
os.environ["GENESIS_BOOK_CATEGORY"] = "Diagnostic"
os.environ["GENESIS_DIGESTION"] = "1"
os.environ["GENESIS_PEER"] = "1"
os.environ["GENESIS_REDQUEEN"] = "1"
os.environ["GENESIS_EVOSENSE"] = "1"
os.environ["GENESIS_EVOACT"] = "1"
os.environ["GENESIS_NICHE_ECON"] = "1"
os.environ["GENESIS_WMEM"] = "1"
os.environ["GENESIS_SCRATCH"] = "1"
# Enable true contention from our previous implementation
os.environ["GENESIS_TRUE_CONTENTION"] = "1"
os.environ["GENESIS_STDP_TARGET"] = "1"
os.environ["GENESIS_STDP3"] = "1"
os.environ["GENESIS_STDP3C"] = "1"


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import genesis_lab as gl
import books_of_genesis as bog

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
TARGET = int(os.environ.get("GENESIS_BOOK_TARGET", "6000"))
CATEGORY = "Diagnostic"
NAME = "DelayedMatch"

def lib_bytes():
    """Count printable ASCII curriculum bytes in RAM."""
    r = gl.g_ram
    return int(np.count_nonzero((r >= 32) & (r <= 126) & (r != 0x55)))

def drain_test_reads():
    """Drain read log entries and calculate test accuracy."""
    rl = gl.g_read_log
    idx = 1
    
    attempts = 0
    correct = 0
    
    while idx < rl[0] and idx + 2 < len(rl):
        t = rl[idx]
        if t == 1:
            idx += 3 # Correct solve (not used directly, we parse attempt)
        elif t == 3:
            idx += 3 # Predict
        elif t == 2:
            # Attempted solve: [2, org_id, target_byte, vocal_byte]
            org = rl[idx+1]
            tgt = rl[idx+2]
            voc = rl[idx+3]
            idx += 4
            
            if tgt == 65 or tgt == 66: # 'A' or 'B'
                attempts += 1
                if tgt == voc:
                    correct += 1
        elif t == 4:
            idx += 3 # Peer event
        else:
            idx += 1
            
    # Reset log
    rl[0] = 1
    
    return attempts, correct

def run_probe(n_ticks=HORIZON):
    print("=" * 70)
    print(f"=== GENESIS — LONG-HORIZON REASONING PROBE ===")
    print(f"Horizon: {n_ticks} Ticks | Book: {CATEGORY}/{NAME}")
    print("=" * 70)

    random.seed(42)
    np.random.seed(42)

    # Pre-stock curriculum library
    while lib_bytes() < TARGET:
        if bog.inject_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME) is None:
            break

    gl.seed_universe(300, initial_energy=gl.SEED_ENERGY)
    t0 = time.time()

    total_attempts = 0
    total_correct = 0
    
    # Track trailing accuracy over the last 1000 ticks
    history_correct = []
    history_attempts = []

    print(f"{'Tick':>7} | {'Pop':>5} | {'Acc (Batch)':>11} | {'Acc (All)':>9} | {'Attempts':>8}")
    print("-" * 75)

    for t in range(n_ticks):
        alive_mask = gl.g_alive
        alive_count = int(np.sum(alive_mask))

        if alive_count == 0:
            gl.seed_universe(300, use_ark=True)
            continue

        if lib_bytes() < TARGET:
            bog.regrow_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME)

        gl.g_read_log[0] = 1

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

        attempts, correct = drain_test_reads()
        
        history_attempts.append(attempts)
        history_correct.append(correct)
        if len(history_attempts) > 1000:
            history_attempts.pop(0)
            history_correct.pop(0)
            
        total_attempts += attempts
        total_correct += correct

        if (t + 1) % 1000 == 0:
            batch_att = sum(history_attempts)
            batch_corr = sum(history_correct)
            batch_acc = (batch_corr / batch_att * 100) if batch_att > 0 else 0
            overall_acc = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
            print(f"{t+1:7} | {alive_count:5} | {batch_acc:10.1f}% | {overall_acc:8.1f}% | {total_attempts:8}")

    print("=" * 70)
    print(f"DONE in {time.time() - t0:.1f}s")
    final_acc = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
    print(f"Final Test Accuracy: {final_acc:.2f}% ({total_correct}/{total_attempts})")

if __name__ == "__main__":
    run_probe()
