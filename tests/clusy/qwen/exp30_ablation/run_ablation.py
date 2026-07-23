"""
Exp 30: STDP Learning Ablation — Driver.

Runs two arms (STDP ON vs OFF) in separate subprocesses (required by Numba
compile-time flags). Writes structured JSON metrics to arm_A.json and arm_B.json.

Usage:
    export GENESIS_NOLEARN=0   # Arm A: STDP ON
    python run_ablation.py

    export GENESIS_NOLEARN=1   # Arm B: STDP OFF
    python run_ablation.py

Configuration via environment:
    SEED=42                    # Random seed
    N_TICKS=200000             # Run duration
    SAMPLE_EVERY=1000          # Metrics sample interval
    BOOK_TARGET_BYTES=6000     # Curriculum size
"""
import subprocess, os, json, time, textwrap, sys

REPO = "/home/user/repos/GENESIS"
DRIVER = "/tmp/exp30_driver.py"
N_TICKS = 200_000
SAMPLE_EVERY = 1_000
SEED = 42
BOOK_TARGET_BYTES = 6000

driver_code = textwrap.dedent(r'''
import sys, os, time, json, random
import numpy as np

SEED         = int(os.environ.get("SEED", "42"))
N_TICKS      = int(os.environ.get("N_TICKS", "200000"))
SAMPLE_EVERY = int(os.environ.get("SAMPLE_EVERY", "1000"))
OUTPUT_FILE  = os.environ.get("OUTPUT_FILE", "/home/user/exp30_arm.json")
NOLEARN      = os.environ.get("GENESIS_NOLEARN", "0")
ARM_LABEL    = "B_STDP_OFF" if NOLEARN == "1" else "A_STDP_ON"
BOOK_BYTES   = int(os.environ.get("BOOK_TARGET_BYTES", "6000"))

os.environ["GENESIS_ECONOMY"]       = "books"
os.environ["GENESIS_DELAY"]         = "1"
os.environ["GENESIS_DELAY_N"]       = "3"
os.environ["GENESIS_CURRICULUM"]    = "0"
os.environ["GENESIS_BOOK_CATEGORY"] = "Diagnostic"
os.environ["GENESIS_BOOK_NAME"]     = "GradedMemory"
os.environ["GENESIS_STIGMERGY"]     = "0"
os.environ["GENESIS_CANVAS"]        = "0"
os.environ["GENESIS_NICHE_ECON"]    = "0"
os.environ["GENESIS_PEER_PREDICT"]  = "0"
os.environ["GENESIS_DEPLETE"]       = "0"
os.environ["GENESIS_EVOSENSE"]      = "0"
os.environ["GENESIS_EVOACT"]        = "0"
os.environ["GENESIS_SCRATCH"]       = "0"
os.environ["GENESIS_WMEM"]          = "0"
os.environ["GENESIS_DIGESTION"]     = "0"
os.environ["GENESIS_REMAP"]         = "0"
os.environ["GENESIS_STDP3"]         = "0"
os.environ["GENESIS_STDP3C"]        = "0"
os.environ["GENESIS_STDP_TARGET"]   = "0"
os.environ["GENESIS_STDP_COSTONLY"] = "0"
sys.path.insert(0, "/home/user/repos/GENESIS/src")
import genesis_lab as gl
from books_of_genesis import inject_contiguous_library

gl.g_curriculum_delay = 3
random.seed(SEED)
np.random.seed(SEED)

gl.seed_universe(300)
inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, "Diagnostic", "GradedMemory", BOOK_BYTES)

M = {"arm": ARM_LABEL, "nolearn": NOLEARN == "1", "seed": SEED,
     "n_ticks": N_TICKS, "sample_every": SAMPLE_EVERY,
     "ticks": [], "population": [], "mean_energy": [], "total_energy": [],
     "correct_reads": [], "incorrect_reads": [], "extinctions": 0}

CYCLE_POOL = 3000
extinctions = 0
t0 = time.time()

print(f"[Exp30 {ARM_LABEL}] seed={SEED} ticks={N_TICKS}", flush=True)

for t in range(N_TICKS):
    alive = int(np.sum(gl.g_alive))
    if alive == 0:
        extinctions += 1
        gl.seed_universe(300, use_ark=True)
        alive = int(np.sum(gl.g_alive))
    if t > 0 and t % 10000 == 0:
        inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, "Diagnostic", "GradedMemory", BOOK_BYTES)
    
    gl.g_read_log[0] = 1
    steps = max(1, int(CYCLE_POOL / max(1, alive)))
    n_alive, n_births = gl.world_tick_numba(
        gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
        gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh,
        gl.g_global_tau, gl.g_global_rec_id,
        gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
        gl.g_global_conn_elig, gl.g_global_conn_elig_t,
        gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
        gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
        gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
        gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
        gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
        gl.g_viscosity, gl.global_time, gl.g_org_lif_steps,
        gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
        gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
        gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
        0, 0, gl.g_org_reward, gl.g_org_elig,
        gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
        gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch,
        gl.g_ram_bank_access, gl.g_ram_bank_access_next, gl.g_curriculum_delay,
    )
    for i in range(n_births):
        child = gl.mutate_dna(gl.g_b_genomes[i, :gl.g_b_g_count[i]])
        slot, pos = -1, gl.g_b_pos[i]
        for j in range(gl.MAX_ORGANISMS):
            if not gl.g_alive[j]: slot = j; break
        if slot != -1:
            off = 0
            while gl.g_org_grid[pos] != -1 and off < 100:
                pos = (gl.g_b_pos[i] + off) % gl.RAM_SIZE; off += 1
            gl.spawn_organism(slot, pos, child, initial_energy=gl.g_b_energy[i])
    gl.global_time += steps
    
    if t % SAMPLE_EVERY == 0:
        cr = ir = 0; idx = 1
        while idx < int(gl.g_read_log[0]) and idx < 996:
            et = int(gl.g_read_log[idx])
            if et == 1: cr += 1; idx += 3
            elif et == 2: ir += 1; idx += 4
            else: idx += 1
        eng = gl.g_energy[gl.g_alive]
        M["ticks"].append(t); M["population"].append(alive)
        M["mean_energy"].append(float(np.mean(eng)) if len(eng) else 0.0)
        M["correct_reads"].append(cr); M["incorrect_reads"].append(ir)
        if t % (SAMPLE_EVERY * 20) == 0:
            print(f"  [{ARM_LABEL}] tick {t:7d}/{N_TICKS} pop {alive:4d} acc {cr/(cr+ir)*100:.1f}% ({cr}/{cr+ir}) E {float(np.mean(eng)):.0f}", flush=True)
    # end if t % SAMPLE_EVERY
# end for t

M["extinctions"] = extinctions
M["wall_clock_sec"] = time.time() - t0
M["ticks_per_sec"] = N_TICKS / M["wall_clock_sec"]
with open(OUTPUT_FILE, "w") as f: json.dump(M, f)
print(f"[{ARM_LABEL}] DONE -> {OUTPUT_FILE}")
''')

with open(DRIVER, "w") as f:
    f.write(driver_code)

for label, nolearn, outfile in [
    ("A_STDP_ON", "0", "results/arm_A.json"),
    ("B_STDP_OFF", "1", "results/arm_B.json"),
]:
    env = os.environ.copy()
    env.update(GENESIS_NOLEARN=nolearn, SEED=str(SEED), N_TICKS=str(N_TICKS),
               SAMPLE_EVERY=str(SAMPLE_EVERY), OUTPUT_FILE=outfile,
               BOOK_TARGET_BYTES=str(BOOK_TARGET_BYTES),
               NUMBA_CACHE_DIR=f"/tmp/numba_cache_{label}")
    print(f"\nLaunching {label} (NOLEARN={nolearn})...")
    subprocess.run([sys.executable, DRIVER], env=env, timeout=5400)
