#!/usr/bin/env python3
"""
Dynamic Compact RAM — invariant + size-agnosticism probe (Session 14)
=====================================================================

Proves, by EXECUTION, the two claims behind the dynamic compact RAM:

  1. The Numba kernel is SIZE-AGNOSTIC. After Session 14 replaced every
     in-kernel `RAM_SIZE` bounds-check with `len(ram_substrate)`, the kernel
     must run correctly on a substrate of ANY length — not just the 65536
     default. Tests A and B are DISCRIMINATING: on the old baked-65536 kernel
     they would raise IndexError / return wrong values; on the new kernel they
     pass.

  2. The compact-RAM module maintains the design invariant
         RAM_SIZE = book_bytes + organism_count,  zero empty space,
     across build / book-switch / birth-death / solve, with position remapping.
     Test C covers this, including a NEGATIVE test (a poked blank byte must be
     detected).

  3. End-to-end: the REAL world_tick_numba runs for several ticks on a compact
     universe (U << 65536) resized in the live genesis_lab state, without any
     bounds crash, and the durable runtime invariants still hold afterwards.
     Test D covers this.

Run:  cd <repo> && python3 tests/dynamic_compact_ram_probe.py
Exit: 0 iff every check passes.
"""
import sys, os, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np

results = []
def record(name, passed, detail=""):
    results.append((name, bool(passed), detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}" + (f"\n        {detail}" if detail else ""), flush=True)

t0 = time.time()
import neuromorphic_engine as E
import dynamic_compact_ram as D
print(f"engine + dynamic_compact_ram imported in {time.time()-t0:.1f}s "
      f"(hardware capacity RAM_SIZE={E.HARDWARE_CAPACITY if hasattr(E,'HARDWARE_CAPACITY') else E.RAM_SIZE})", flush=True)

N_INPUT, MAX_ORG = E.N_INPUT, E.MAX_ORGANISMS

# ===========================================================================
# TEST A — sense() is boundary-safe on a TINY substrate (discriminating)
# ===========================================================================
# On the OLD kernel, right_pos = pos+1 whenever pos < 65535, so sense(pos=U-1)
# would index org_grid[U] -> IndexError on a length-U array. The size-agnostic
# kernel clamps to len(ram_substrate)-1.
U = 20
ram = np.array([33 + (i % 94) for i in range(U)], dtype=np.uint8)
grid = np.full(U, -1, dtype=np.int32)
vc = np.zeros(MAX_ORG, dtype=np.int32)
vp = np.zeros(MAX_ORG, dtype=np.int32)
sb = np.zeros(N_INPUT, dtype=np.float32)
try:
    E.sense(U - 1, ram, grid, np.float32(1000.0), 0, vc, vp, sb)   # last cell
    last3 = float(sb[3])
    E.sense(0, ram, grid, np.float32(1000.0), 0, vc, vp, sb)       # first cell
    record("A: sense() boundary-safe on tiny substrate (len=%d)" % U, True,
           "no IndexError at pos=0 and pos=%d; sense_buf[3]=%.3f (byte/255)" % (U - 1, last3))
except Exception as e:
    record("A: sense() boundary-safe on tiny substrate", False, f"{type(e).__name__}: {e}")

# ===========================================================================
# TEST B — sense_affordance() honours len(ram_substrate) bounds
# ===========================================================================
try:
    in_bounds = float(E.sense_affordance(0, 0, 0, U - 1, ram, grid, np.zeros(MAX_ORG, np.float32), vc, np.float32(0)))
    oob_pos = float(E.sense_affordance(0, +5, 0, U - 1, ram, grid, np.zeros(MAX_ORG, np.float32), vc, np.float32(0)))
    oob_neg = float(E.sense_affordance(0, -100, 0, 0, ram, grid, np.zeros(MAX_ORG, np.float32), vc, np.float32(0)))
    ok = (oob_pos == 0.0) and (oob_neg == 0.0) and (in_bounds > 0.0)
    record("B: sense_affordance() out-of-bounds -> 0.0, in-bounds -> value", ok,
           f"in_bounds={in_bounds:.3f}  oob(+5)={oob_pos}  oob(-100)={oob_neg}")
except Exception as e:
    record("B: sense_affordance()", False, f"{type(e).__name__}: {e}")

# ===========================================================================
# TEST C — dynamic_compact_ram module invariants
# ===========================================================================
book_bytes = 50
org_ids = [0, 1, 2, 3, 4]

# C1: build + full allocation-time invariants
g_ram, g_grid, g_cc, pos = D.build_compact_universe(book_bytes, org_ids)
try:
    ev = D.assert_compact_invariants(g_ram, g_grid, pos, org_ids, book_bytes, fresh=True)
    record("C1: build_compact_universe satisfies all invariants", True,
           f"U={ev['U']} (=book {book_bytes} + orgs {len(org_ids)}), blanks={ev['blanks']}, "
           f"book_homes={ev['book_homes']}, org_region_occupied={ev['org_region_occupied']}")
except AssertionError as e:
    record("C1: build invariants", False, str(e))

# C2: the size law itself
record("C2: compact_size law = book + organisms",
       D.compact_size(book_bytes, len(org_ids)) == len(g_ram),
       f"compact_size={D.compact_size(book_bytes, len(org_ids))}  len(g_ram)={len(g_ram)}")

# C3: BOOK SWITCH -> resize + remap (different book size)
new_book = 80
g_ram2, g_grid2, g_cc2, pos2, remap = D.reallocate_compact(g_ram, g_grid, pos, org_ids, new_book)
try:
    ev2 = D.assert_compact_invariants(g_ram2, g_grid2, pos2, org_ids, new_book, fresh=True)
    moved = all(remap[o][1] == new_book + rank for rank, o in enumerate(org_ids))
    record("C3: book-switch resize+remap (book %d -> %d)" % (book_bytes, new_book), moved,
           f"U={ev2['U']} blanks={ev2['blanks']} every home remapped to new org-region={moved} "
           f"sample remap org0={remap[org_ids[0]]}")
except AssertionError as e:
    record("C3: book-switch", False, str(e))

# C4: DEATH shrinks RAM (fewer organisms)
survivors = org_ids[:3]
g_ram3, g_grid3, g_cc3, pos3, remap3 = D.reallocate_compact(g_ram2, g_grid2, pos2, survivors, new_book)
try:
    ev3 = D.assert_compact_invariants(g_ram3, g_grid3, pos3, survivors, new_book, fresh=True)
    record("C4: death shrinks RAM (orgs %d -> %d)" % (len(org_ids), len(survivors)),
           len(g_ram3) == new_book + len(survivors),
           f"U {ev2['U']} -> {ev3['U']} (expected {new_book + len(survivors)})")
except AssertionError as e:
    record("C4: death shrink", False, str(e))

# C5: SOLVE shrinks the book region (freed memory)
solved = [0, 1, 2]
g_ram4, g_grid4, g_cc4, pos4, new_bb, remap4 = D.shrink_on_solve(
    g_ram3, g_grid3, pos3, survivors, new_book, solved)
try:
    ev4 = D.assert_compact_invariants(g_ram4, g_grid4, pos4, survivors, new_bb, fresh=True)
    record("C5: solve shrinks book region (book %d -> %d)" % (new_book, new_bb),
           new_bb == new_book - len(solved) and len(g_ram4) == new_bb + len(survivors),
           f"book {new_book} -> {new_bb}, U -> {ev4['U']}")
except AssertionError as e:
    record("C5: solve shrink", False, str(e))

# C6: NEGATIVE test — a poked blank byte MUST be detected
g_bad = g_ram4.copy(); g_bad[0] = 0
detected = False
try:
    D.assert_compact_invariants(g_bad, g_grid4, pos4, survivors, new_bb, fresh=True)
except AssertionError:
    detected = True
record("C6: zero-empty-space violation is DETECTED", detected,
       "poked 0x00 -> AssertionError raised" if detected else "VIOLATION SLIPPED THROUGH")

# ===========================================================================
# TEST D — end-to-end: the REAL world_tick_numba on a compact substrate
# ===========================================================================
try:
    tD = time.time()
    import genesis_lab as lab
    print(f"        genesis_lab imported in {time.time()-tD:.1f}s (loop NOT auto-started)", flush=True)
    lab.seed_universe(1, use_ark=False)
    alive_ids = [i for i in range(MAX_ORG) if lab.g_alive[i]]
    if not alive_ids:
        record("D: end-to-end compact tick", False, "seed_universe produced no alive organisms")
    else:
        # top up energy so the (big-universe-tuned) organisms survive a few compact ticks
        for i in alive_ids:
            lab.g_energy[i] = np.float64(1.0e6)
        nb = 120
        ev = D.reallocate_lab_state(lab, alive_ids, nb)
        U_alloc = len(lab.g_ram)
        print(f"        compact universe allocated: U={U_alloc} (book {nb} + orgs {len(alive_ids)}); "
              f"running real kernel ticks...", flush=True)

        n_ticks = 3
        alive_per_tick = []
        for tk in range(n_ticks):
            lab.world_tick_numba(
                lab.g_ram, lab.g_org_grid, lab.g_positions, lab.g_alive, lab.g_energy, lab.g_age,
                lab.g_global_v, lab.g_global_ref, lab.g_global_t_last, lab.g_global_thresh, lab.g_global_tau, lab.g_global_rec_id,
                lab.g_global_conn_src, lab.g_global_conn_dst, lab.g_global_conn_weight, lab.g_global_conn_elig, lab.g_global_conn_elig_t,
                lab.g_neuron_map, lab.g_synapse_map, lab.g_genome_map,
                lab.g_org_n_ptr, lab.g_org_n_count, lab.g_org_s_ptr, lab.g_org_s_count,
                lab.g_global_genome, lab.g_org_g_ptr, lab.g_org_g_count,
                lab.o_rec_a_plus, lab.o_rec_a_minus, lab.o_rec_tau_p, lab.o_rec_tau_m, lab.o_rec_v_rest, lab.o_rec_v_reset, lab.o_rec_tau_def, lab.o_rec_spk_max, lab.o_rec_tau_e,
                lab.g_viscosity, lab.global_time, lab.g_org_lif_steps,
                lab.g_b_pos, lab.g_b_parent, lab.g_b_g_start, lab.g_b_g_count, lab.g_b_genomes, lab.g_b_energy,
                0, 0, lab.voice_buf, lab.vocal_cords, lab.vocal_prev, lab.action_now, lab.action_prev, lab.g_read_log,
                lab.g_read_fuel, lab.g_cell_owner, lab.g_read_hits, lab.CANVAS_LO, lab.CANVAS_HI, lab.g_org_reward, lab.g_org_elig,
                lab.g_global_sense_type, lab.g_global_sense_meta, lab.g_global_act_drive, lab.g_org_delay_buf, lab.g_org_stomach_fuel, lab.g_org_scratch,
                lab.g_ram_bank_access, lab.g_ram_bank_access_next, lab.g_curriculum_delay,
                lab.g_conn_w_dna,
                lab.g_cam_keys, lab.g_cam_vals, lab.g_cam_valid, lab.g_cam_tick,
                lab.g_clear_count,
            )
            lab.global_time += 1
            alive_per_tick.append(sum(1 for i in range(MAX_ORG) if lab.g_alive[i]))

        # durable runtime invariants after ticks (organisms roamed; population may differ)
        alive_now = [i for i in range(MAX_ORG) if lab.g_alive[i]]
        evD = D.assert_runtime_invariants(lab.g_ram, lab.g_org_grid, lab.g_positions, alive_now)
        len_unchanged = (len(lab.g_ram) == U_alloc)
        record("D: real world_tick_numba ran on compact substrate (U=%d, %d ticks)" % (U_alloc, n_ticks),
               len_unchanged and evD["blanks"] == 0,
               f"len(g_ram) stayed {len(lab.g_ram)} (==allocated {U_alloc}); blanks={evD['blanks']}; "
               f"alive/tick={alive_per_tick}; post-tick alive={len(alive_now)}; "
               f"kernel used len(ram_substrate)={len(lab.g_ram)} — no bounds crash")
except Exception as e:
    record("D: end-to-end compact tick", False,
           f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}")

# ===========================================================================
# VERDICT
# ===========================================================================
passed = sum(1 for _, p, _ in results if p)
total = len(results)
print("\n" + "=" * 64)
print(f"DYNAMIC COMPACT RAM PROBE: {passed}/{total} checks passed  ({time.time()-t0:.1f}s total)")
print("=" * 64)
for name, p, _ in results:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
sys.exit(0 if passed == total else 1)
