"""Exp 34 — WITHIN-LIFETIME REMAP, held-out sandbox probe (Ascent.md §4 step 2, Rules 9<->6/14).

The decisive, survival-DECOUPLED test of Rule-6 in-lifetime LEARNING. Every prior "does it learn?"
result was confounded by the survival economy: making reading harder pushes the colony to the refuge
floor (pop=12), so a learner's re-tracking can't be separated from the economy collapsing. This probe
removes the economy entirely and measures learning in isolation, on the REAL world_tick_numba kernel
(no reimplemented physics — the Live-Loop-Test-Gap rule):

  - A fixed cohort of REMAP-ancestor clones stands on a fixed contiguous text patch.
  - Energy is PINNED high every tick -> nobody dies, nobody reproduces (births zeroed) -> the cohort
    is frozen; only SYNAPTIC WEIGHTS (STDP) change. So any change in accuracy is IN-LIFETIME LEARNING,
    nothing else.
  - The remap phase alternates on the REMAP_PERIOD clock (identity <-> 2-bit swap). The kernel reads
    the phase from global_time, exactly as in the live loop.
  - Observation-only per-bit accuracy is computed from the read_log (type-1 solves + type-2 misses
    carry target byte + emission), split into: the 2 SWAPPED bits (SB0/SB1) vs the 6 UNCHANGED bits.

THE PRE-REGISTERED PREDICTION (from the kernel analysis): STDP3C's credit is OUTPUT-GATED — it can
only reinforce/suppress vocal neurons that ACTUALLY FIRED. In a swapped phase the echo diagonal makes
vocal-SB0 fire (now WRONG) and leaves vocal-SB1 SILENT (should fire). STDP3C can LTD-suppress the wrong
firing route, but to make SB1 fire it must potentiate a synapse onto a SILENT neuron — no post-spike,
no eligibility, so Hebbian-family STDP can never RECRUIT it. Prediction: the learner PRUNES wrong
pathways (swap-bit acc may rise above the echo floor by suppression) but cannot RECRUIT the new one
(swap-bit acc stays well below the unchanged-bit acc), while NOLEARN stays pinned at the echo floor
(~correct only when the swap happens to be a no-op for that byte). If the learner CANNOT recruit, the
missing substrate capability is localised: a true ERROR/teaching signal that reaches silent-but-wanted
neurons — the next SUBSTRATE change, not another economy lever.

Run:
  GENESIS_ECONOMY=books GENESIS_REMAP=1 GENESIS_STDP3C=1 GENESIS_STDP_DIV=32 python tests/remap_sandbox_probe.py
  GENESIS_ECONOMY=books GENESIS_REMAP=1 GENESIS_NOLEARN=1               python tests/remap_sandbox_probe.py
"""
import os, sys
os.environ.setdefault("GENESIS_ECONOMY", "books")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
import genesis_lab as gl
import neuromorphic_engine as ne

N_ORG    = int(os.environ.get("PROBE_N", "120"))
TICKS    = int(os.environ.get("PROBE_TICKS", "60000"))
PATCH    = int(os.environ.get("PROBE_PATCH", "2000"))     # contiguous text patch width
REPORT   = int(os.environ.get("PROBE_REPORT", "2000"))    # print cadence (global_time units)
SB0, SB1 = int(os.environ.get("GENESIS_REMAP_SB0", "0")), int(os.environ.get("GENESIS_REMAP_SB1", "1"))


def build_patch():
    """Lay a fixed contiguous text scroll and stand the cohort on it, one org per cell."""
    from books_of_genesis import inject_contiguous_library
    inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, gl.BOOK_CATEGORY, gl.BOOK_NAME, PATCH)
    start = gl.contiguous_library_start(gl.RAM_SIZE, PATCH)
    dna = gl.create_intelligent_ancestor(None)
    placed = 0
    p = start
    while placed < N_ORG and p < start + PATCH:
        if gl.g_org_grid[p] == -1:
            if gl.spawn_organism(placed, p, dna, initial_energy=gl.SEED_ENERGY):
                placed += 1
        p += 3   # space them out so they don't collide-block on the saccade
    return placed


def remap_target(nb, swapped):
    if not swapped:
        return nb & 0xFF
    b0 = (nb >> SB0) & 1
    b1 = (nb >> SB1) & 1
    nb2 = nb & ~((1 << SB0) | (1 << SB1))
    nb2 |= (b1 << SB0) | (b0 << SB1)
    return nb2 & 0xFF


def measure_window(swapped):
    """Drain read_log; for every logged read, compare emission bits to the remapped target bits.
    type1 (solve) => emission == remapped target on all 8 bits. type2 (miss) => explicit emission."""
    rl = gl.g_read_log
    sc = st = uc = ut = 0
    idx = 1
    n = int(rl[0])
    while idx < n:
        t = int(rl[idx])
        if t == 1:
            tgt = remap_target(int(rl[idx + 2]), swapped)
            emit = tgt  # a full solve matched every bit by definition
            idx += 3
        elif t == 2:
            tgt = remap_target(int(rl[idx + 2]), swapped)
            emit = int(rl[idx + 3])
            idx += 4
        elif t == 3:
            idx += 3; continue
        elif t == 4:
            idx += 3; continue
        elif t == 5:
            idx += 3; continue
        else:
            break
        for b in range(8):
            ok = ((emit >> b) & 1) == ((tgt >> b) & 1)
            if b == SB0 or b == SB1:
                st += 1; sc += 1 if ok else 0
            else:
                ut += 1; uc += 1 if ok else 0
    rl[0] = 1
    return sc, st, uc, ut


def main():
    mode = ("NOLEARN" if ne.NOLEARN else ("STDP3C" if ne.STDP3C else ("STDP3" if ne.STDP3 else "STDP")))
    print(f"[SANDBOX] mode={mode} REMAP={ne.REMAP} period={int(ne.REMAP_PERIOD)} states={int(ne.REMAP_STATES)} "
          f"swapbits=({SB0},{SB1}) DIV={float(ne.STDP_DIV):.0f} N={N_ORG} ticks={TICKS} patch={PATCH}")
    # JIT warmup on a throwaway single org handled by first real tick.
    placed = build_patch()
    print(f"[SANDBOX] placed {placed} clones on a {PATCH}-byte patch; energy pinned (no death/birth)")

    global_time = 0
    HI = float(gl.ATP_MAX) * 0.5
    dummy_births = None
    while global_time < TICKS:
        # PIN energy high every tick so nobody dies and the reproduce threshold is moot; we also zero
        # the birth buffer return so the cohort stays frozen (only weights move).
        gl.g_energy[gl.g_alive] = np.float32(HI)

        n_alive, n_births = gl.world_tick_numba(
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
            gl.g_global_sense_type, gl.g_global_sense_meta)

        # Ignore births entirely (frozen cohort): free any birth-buffer bodies were NOT allocated (the
        # kernel only fills b_* arrays; spawning happens in sim_loop which we don't call), so nothing to
        # undo. Organisms that saccaded off the patch wrap on the ring; re-pin positions is unnecessary
        # because the scroll is contiguous and long.

        period = int(ne.REMAP_PERIOD); states = int(ne.REMAP_STATES)
        swapped = (states > 1) and (((global_time // period) % states) != 0)

        if global_time % REPORT == 0 and global_time > 0:
            sc, st, uc, ut = measure_window(swapped)
            swap_acc = (100.0 * sc / st) if st else float("nan")
            unch_acc = (100.0 * uc / ut) if ut else float("nan")
            phase = "SWAP" if swapped else "idnt"
            print(f"  t={global_time:>6} phase={phase} | swapbit_acc={swap_acc:5.1f}% (n={st:4d}) "
                  f"| unchbit_acc={unch_acc:5.1f}% (n={ut:5d}) | alive={int(n_alive)}")

        global_time += 1


if __name__ == "__main__":
    main()
