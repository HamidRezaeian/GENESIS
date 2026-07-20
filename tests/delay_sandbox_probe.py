"""Exp 43 — WORKING-MEMORY DELAY task, held-out sandbox probe (Ascent §2A criterion-A assumption).

Validates the load-bearing assumption UNDER criterion A: can a GENESIS brain COMPUTE OVER HELD CONTEXT at
all? The reward target here is the byte the organism sensed DELAY_N ticks AGO (org_delay_buf) — on NO
current input, so only a brain HOLDING it across DELAY_N ticks can emit it (a memoryless reflex cannot).
The only cross-tick state is leaky membrane voltage; this probe measures whether that + the Exp-35 teaching
signal can clear the memoryless floor.

Survival-DECOUPLED sandbox (the Exp-34/35 method): a frozen energy-pinned cohort of REMAP-fabric clones
(the fabric gives plastic eye->vocal routes) stands on a fixed text patch; the DELAY reward targets the
byte DELAY_N ago; we measure emission-vs-delayed-target accuracy per window. 3 arms: NOLEARN / STDP3C /
STDP_TARGET.

The MEMORYLESS FLOOR = the accuracy a reflex gets by echoing the CURRENT byte against the DELAYED target,
i.e. how often byte(t) == byte(t-N) on the patch (run-length structure of 00_Graded makes consecutive
bytes often equal, so the floor is non-trivial — that is why we report the learner's LIFT over it, and
scale DELAY_N: a longer delay lowers the echo-floor and demands real memory).

Run:
  GENESIS_ECONOMY=books GENESIS_REMAP=1 GENESIS_DELAY=1 GENESIS_DELAY_N=1 GENESIS_STDP_TARGET=1 GENESIS_STDP_DIV=128 python tests/delay_sandbox_probe.py
  ... GENESIS_NOLEARN=1 ...   (the memoryless-floor control)
"""
import os, sys
os.environ.setdefault("GENESIS_ECONOMY", "books")
os.environ.setdefault("GENESIS_REMAP", "1")   # seed the plastic eye->vocal fabric (routes to potentiate)
os.environ.setdefault("GENESIS_DELAY", "1")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import genesis_lab as gl
import neuromorphic_engine as ne

N_ORG  = int(os.environ.get("PROBE_N", "120"))
TICKS  = int(os.environ.get("PROBE_TICKS", "40000"))
PATCH  = int(os.environ.get("PROBE_PATCH", "2000"))
REPORT = int(os.environ.get("PROBE_REPORT", "2000"))


def build_patch():
    from books_of_genesis import inject_contiguous_library
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH)
    start = gl.contiguous_library_start(gl.RAM_SIZE, PATCH)
    dna = gl.create_intelligent_ancestor(None)
    placed = 0; p = start
    while placed < N_ORG and p < start + PATCH:
        if gl.g_org_grid[p] == -1 and gl.spawn_organism(placed, p, dna, initial_energy=gl.SEED_ENERGY):
            placed += 1
        p += 3
    return placed


def measure_window():
    """Delay-task accuracy = fraction of logged reads whose emission matched the DELAYED target. type-1
    (solve) already matched (the kernel scored against the delayed tgt_byte). type-2 (miss) did not."""
    rl = gl.g_read_log
    solved = total = 0
    idx = 1; n = int(rl[0])
    while idx < n:
        t = int(rl[idx])
        if t == 1:   solved += 1; total += 1; idx += 3
        elif t == 2: total += 1;             idx += 4
        elif t in (3, 4, 5):                 idx += 3
        else: break
    rl[0] = 1
    return solved, total


def main():
    mode = ("NOLEARN" if ne.NOLEARN else ("STDP_TARGET" if ne.STDP_TARGET else
            ("STDP3C" if ne.STDP3C else "STDP")))
    print(f"[DELAY-SANDBOX] mode={mode} DELAY_N={int(ne.DELAY_N)} DIV={float(ne.STDP_DIV):.0f} "
          f"N={N_ORG} ticks={TICKS} patch={PATCH}")
    placed = build_patch()
    print(f"[DELAY-SANDBOX] placed {placed} clones; energy pinned (no death/birth) — only weights move")

    global_time = 0
    HI = float(gl.ATP_MAX) * 0.5
    while global_time < TICKS:
        gl.g_energy[gl.g_alive] = np.float32(HI)
        n_alive, _ = gl.world_tick_numba(
            gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
            gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau, gl.g_global_rec_id,
            gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
            gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
            gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
            gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
            gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
            gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max,
            gl.g_viscosity, global_time, gl.g_org_lif_steps,
            gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
            gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
            gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner, gl.g_read_hits,
            gl.CANVAS_LO, gl.CANVAS_HI, gl.g_org_reward, gl.g_org_elig,
            gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive, gl.g_org_delay_buf, gl.g_org_scratch)

        if global_time % REPORT == 0 and global_time > 0:
            solved, total = measure_window()
            acc = (100.0 * solved / total) if total else float("nan")
            print(f"  t={global_time:>6} delay_acc={acc:5.1f}% (n={total:5d}) alive={int(n_alive)}")
        global_time += 1


if __name__ == "__main__":
    main()
