"""SCRATCH retention live probe: Rule-18 load-bearing assumption for Crit-A.

Does depth-2 SCRATCH addressing get selected in a LIVE books economy,
or does uniform reading income (no depth-band reward) cause selection
to prune the addressing circuit?

Runs 3 arms via real sim_loop:
  ARM-A (control):  GENESIS_NOLEARN=1
  ARM-B:            GENESIS_STDP_TARGET=1 GENESIS_DELAY=1 GENESIS_DELAY_N=2
  ARM-C:            GENESIS_STDP_TARGET=1 GENESIS_DELAY=1 GENESIS_DELAY_N=2 GENESIS_SCRATCH=1

All: GENESIS_ECONOMY=books GENESIS_BOOK_NAME=00_Graded GENESIS_ARK=0 (terminal)

Observation-only metrics (Rule 9/6):
  - pop/ext/refuge (survival)
  - Universe N (brain size: neurons + synapses)
  - Delay-2 solve rate (accuracy)
  - SCRATCH retention: count live recall sensors per org over time (mutation drift observable)
  - Addressing circuit retention: does slot-N->vocal-bit connection persist under selection
"""
import os
import sys
import json
import numpy as np
import random

# Must set env BEFORE importing genesis_lab (which reads them at module load)
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_BOOK_NAME"] = "00_Graded"
os.environ["GENESIS_ARK"] = "0"
os.environ["GENESIS_BOOK_CATEGORY"] = "English"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import genesis_lab as gl
import books_of_genesis as bog
import self_sustain_test as sst
from neuromorphic_engine import world_tick_numba

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
TARGET = int(os.environ.get("GENESIS_BOOK_TARGET", "6000"))
CATEGORY = os.environ.get("GENESIS_BOOK_CATEGORY", "English")
NAME = os.environ.get("GENESIS_BOOK_NAME", "00_Graded")

# Parse arm from env
ARM = os.environ.get("PROBE_ARM", "A")
NOLEARN = os.environ.get("GENESIS_NOLEARN", "0") == "1"
STDP_TARGET = os.environ.get("GENESIS_STDP_TARGET", "0") == "1"
DELAY = os.environ.get("GENESIS_DELAY", "0") == "1"
DELAY_N = int(os.environ.get("GENESIS_DELAY_N", "0"))
SCRATCH = os.environ.get("GENESIS_SCRATCH", "0") == "1"

# Determine NUMBA cache suffix for this arm
if NOLEARN:
    CACHE_SUFFIX = "_nolearn"
elif SCRATCH:
    CACHE_SUFFIX = "_delay_tgt_scratch"
elif DELAY and STDP_TARGET:
    CACHE_SUFFIX = "_delay_tgt"
else:
    CACHE_SUFFIX = ""

print(f"=== SCRATCH RETENTION LIVE PROBE ===")
print(f"ARM={ARM}  NOLEARN={NOLEARN}  STDP_TARGET={STDP_TARGET}  DELAY={DELAY}  DELAY_N={DELAY_N}  SCRATCH={SCRATCH}")
print(f"Cache suffix: {CACHE_SUFFIX}")
print(f"Horizon: {HORIZON}  Target library: {TARGET}B  Book: {CATEGORY}/{NAME}")

# --- Metrics helpers ---
def lib_bytes():
    r = gl.g_ram
    return int(np.count_nonzero((r >= 32) & (r <= 126) & (r != 0x55)))

def encounter_frac():
    alive = gl.g_alive
    n = int(np.sum(alive))
    if n == 0:
        return 0.0, 0
    pos = gl.g_positions[alive]
    b = gl.g_ram[pos]
    on_text = int(np.count_nonzero((b >= 32) & (b <= 126) & (b != 0x55)))
    return on_text / n, n

def drain_reads():
    rl = gl.g_read_log
    idx = 1
    correct = attempt = predict = 0
    while idx < rl[0] and idx + 2 < len(rl):
        t = rl[idx]
        if t == 1:
            correct += 1; idx += 3
        elif t == 3:
            predict += 1; idx += 3
        elif t == 2:
            attempt += 1; idx += 4
        else:
            idx += 1
    rl[0] = 1
    return correct, attempt, predict

def count_recall_sensors(org_id):
    """Count live recall sensors (sense_type==8) for a given organism."""
    if not SCRATCH:
        return 0
    n_ptr = gl.g_org_n_ptr[org_id]
    n_count = gl.g_org_n_count[org_id]
    count = 0
    for sn in range(gl.N_IO, n_count):
        if gl.g_global_sense_type[n_ptr + sn] == 8:
            count += 1
    return count

def count_recall_to_vocal_synapses(org_id):
    """Count synapses from recall sensors (hidden band, sense_type==8) to vocal bits."""
    if not SCRATCH:
        return 0
    n_ptr = gl.g_org_n_ptr[org_id]
    s_ptr = gl.g_org_s_ptr[org_id]
    s_count = gl.g_org_s_count[org_id]
    n_count = gl.g_org_n_count[org_id]
    count = 0
    vocal_start = gl.N_INPUT + 6
    vocal_end = gl.N_IO
    for c in range(s_count):
        src = gl.g_global_conn_src[s_ptr + c]
        dst = gl.g_global_conn_dst[s_ptr + c]
        if dst >= vocal_start and dst < vocal_end:
            if src >= gl.N_IO:
                # Check if source is a recall sensor
                if gl.g_global_sense_type[n_ptr + src] == 8:
                    count += 1
    return count

def get_brain_size(org_id):
    """Return (neurons, synapses) for an organism."""
    return gl.g_org_n_count[org_id], gl.g_org_s_count[org_id]

def get_delay2_accuracy():
    """Measure delay-2 solve accuracy: organisms that correctly predict slot-2 target.
    Scored when DELAY=1 and DELAY_N=2: the target is the byte 2 saccades ago.
    """
    if not DELAY or DELAY_N != 2:
        return 0.0, 0, 0
    # Count organisms that solved delay-2 (full correct prediction of slot-2 byte)
    # This is logged as read_log type 3 when org_char_val == target from delay ring
    # We'll track from the accumulated correct predictions on delay-2 targets
    # For now, use the prediction rate from read_log type 3 as proxy
    return 0.0, 0, 0  # Placeholder - will compute from read_log types

def seed_universe(pop, initial_energy):
    """Seed universe with intelligent ancestors."""
    gl.seed_universe(pop, initial_energy=initial_energy)

# --- Main ---
def main():
    random.seed(1234)
    np.random.seed(1234)

    # Pre-stock library (contiguous scroll)
    while lib_bytes() < TARGET:
        if bog.inject_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME) is None:
            print("[WARN] cannot inject; library empty")
            break
    density = lib_bytes() / gl.RAM_SIZE

    # Use intelligent ancestors (same as live test)
    seed_universe(300, initial_energy=gl.SEED_ENERGY)

    print(f"[cfg] ARM={ARM} NOLEARN={NOLEARN} STDP_TARGET={STDP_TARGET} DELAY={DELAY} DELAY_N={DELAY_N} SCRATCH={SCRATCH}")
    print(f"Library: {lib_bytes()}B density={density:.3f}")
    print(f"{'tick':>5} {'pop':>4} {'mean_E':>9} {'lib':>6} {'enc%':>6} {'corr/t':>7} {'att/t':>7} {'pred/t':>7} {'N_mean':>7} {'S_mean':>8} {'recall_median':>12} {'r2v_syn_median':>14} {'delay2_acc':>10}")

    EPOCH = 50
    prev_E = None
    ep_corr = ep_att = ep_pred = 0

    # Track metrics over time
    recall_counts_over_time = []
    r2v_synapse_counts_over_time = []
    brain_sizes_over_time = []

    for t in range(HORIZON):
        alive_mask = gl.g_alive
        alive_count = int(np.sum(alive_mask))
        if alive_count == 0:
            print(f"{t:>5}  EXTINCT")
            break

        # Restock library if needed
        if lib_bytes() < TARGET:
            bog.regrow_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME)

        gl.g_read_log[0] = 1
        steps = int(gl.g_org_lif_steps[alive_mask].max()) if alive_count > 0 else 1

        # Call world_tick_numba directly with full 62-argument signature
        _, n_births = gl.world_tick_numba(
            gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
            gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
            gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
            gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
            gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
            gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
            gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
            gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max,
            gl.g_viscosity, gl.global_time, gl.g_org_lif_steps,
            gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
            gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev, gl.action_now, gl.action_prev,
            gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
            0, 0,  # canvas_lo, canvas_hi (not used in books mode)
            gl.g_org_reward, gl.g_org_elig,
            gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
            gl.g_org_delay_buf, gl.g_org_scratch
        )
        sst._process_births(n_births)
        gl.global_time += steps

        c, a, p = drain_reads()
        ep_corr += c
        ep_att += a
        ep_pred += p

        if t % EPOCH == 0 or t == HORIZON - 1:
            ef, n = encounter_frac()
            energies = gl.g_energy[alive_mask]
            mE = float(np.mean(energies)) if len(energies) else 0.0
            dE = (mE - prev_E) / EPOCH if prev_E is not None else 0.0

            # Compute per-org metrics
            if n > 0:
                # Brain sizes
                neuron_counts = []
                synapse_counts = []
                recall_counts = []
                r2v_counts = []

                for org_id in np.where(alive_mask)[0]:
                    n_count, s_count = get_brain_size(org_id)
                    neuron_counts.append(n_count)
                    synapse_counts.append(s_count)

                    if SCRATCH:
                        recall_counts.append(count_recall_sensors(org_id))
                        r2v_counts.append(count_recall_to_vocal_synapses(org_id))

                N_mean = float(np.mean(neuron_counts)) if neuron_counts else 0
                S_mean = float(np.mean(synapse_counts)) if synapse_counts else 0
                recall_median = float(np.median(recall_counts)) if recall_counts else 0
                r2v_median = float(np.median(r2v_counts)) if r2v_counts else 0

                recall_counts_over_time.append(recall_median)
                r2v_synapse_counts_over_time.append(r2v_median)
                brain_sizes_over_time.append((N_mean, S_mean))
            else:
                N_mean = S_mean = recall_median = r2v_median = 0

            # Delay-2 accuracy proxy: fraction of predictions that are correct (type 3 / type 1+2+3)
            total_reads = ep_corr + ep_att + ep_pred
            delay2_acc = (ep_pred / total_reads * 100) if total_reads > 0 else 0.0

            print(f"{t:>5} {n:>4} {mE:>9.0f} {lib_bytes():>6} {ef*100:>5.1f} "
                  f"{ep_corr/EPOCH:>7.2f} {ep_att/EPOCH:>7.2f} {ep_pred/EPOCH:>7.2f} "
                  f"{N_mean:>7.1f} {S_mean:>8.1f} {recall_median:>12.1f} {r2v_median:>14.1f} {delay2_acc:>9.1f}%")

            prev_E = mE
            ep_corr = ep_att = ep_pred = 0

    # Final summary
    alive_mask = gl.g_alive
    final_pop = int(np.sum(alive_mask))

    summary = {
        "arm": ARM,
        "config": {
            "nolearn": NOLEARN,
            "stdp_target": STDP_TARGET,
            "delay": DELAY,
            "delay_n": DELAY_N,
            "scratch": SCRATCH
        },
        "horizon": HORIZON,
        "final_pop": final_pop,
        "extinct": final_pop == 0,
        "final_library_bytes": lib_bytes(),
        "mean_brain_neurons": brain_sizes_over_time[-1][0] if brain_sizes_over_time else 0,
        "mean_brain_synapses": brain_sizes_over_time[-1][1] if brain_sizes_over_time else 0,
        "recall_sensor_median_final": recall_counts_over_time[-1] if recall_counts_over_time else 0,
        "recall_to_vocal_synapse_median_final": r2v_synapse_counts_over_time[-1] if r2v_synapse_counts_over_time else 0,
        "recall_sensors_trend": recall_counts_over_time,
        "r2v_synapses_trend": r2v_synapse_counts_over_time,
        "brain_sizes_trend": brain_sizes_over_time,
    }

    # Write JSON summary
    out_path = f"scratch_retention_arm_{ARM}.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[summary] Written to {out_path}")
    print(json.dumps(summary, indent=2))

    sys.stdout.flush()

if __name__ == "__main__":
    main()