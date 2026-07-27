#!/usr/bin/env python3
"""
Session 15 — headless A/B runner: ONE arm ( Dale + WM + SCRATCH + STDP_TARGET ).
================================================================================

Runs the GENESIS book economy on Books/English/00_Graded.txt for a fixed number of
ticks and measures the two Ascent-relevant signals:

  * max_run    = peak per-organism consecutive-correct-prediction run length
                 (max over organisms and over time of engine global g_org_run; the
                 Session-9 work-unit counter, capped/reset at LUMPSUM_K). The 00_Graded
                 ramp is run-length 10->5->3->2->1; the symptom is max_run stuck at 1
                 (echo reflex) despite ~92% per-read solve-rate.
  * solve_rate = reads / (reads + miss) drained from g_read_log (Ascent Exp 30 metric).

ENCOUNTER FIX: the default RAM is 2^21 cells with a 6000-byte library, so randomly
seeded organisms starve before finding the text (reads=0). We therefore use the
Session-14 DYNAMIC COMPACT RAM (dynamic_compact_ram.reallocate_lab_state) to shrink the
universe to U = book_bytes + n_alive, placing every organism's home cell directly
adjacent to the book scroll -> guaranteed high encounter, exactly the regime the
oscillation probe's falsifiable next step targets.

All compile-time gates are read at engine IMPORT, so each arm runs in its own fresh
interpreter; the orchestrating notebook cell spawns this once per arm with the right env.
Output: a single line  RESULT_JSON:<json>  on stdout.
"""
import os, sys, json, time, random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np

SEED   = int(os.environ.get("AB_SEED", "12345"))
random.seed(SEED)
np.random.seed(SEED)

import genesis_lab as lab          # gates read here, at import
import neuromorphic_engine as E
import dynamic_compact_ram as D

# ---- config ----
N_TICKS      = int(os.environ.get("AB_N_TICKS", "12000"))
POP          = int(os.environ.get("AB_POP", "120"))
SAMPLE_EVERY = int(os.environ.get("AB_SAMPLE_EVERY", "5"))
ENERGY_FLOOR = float(os.environ.get("AB_ENERGY_FLOOR", "0"))   # 0=off; else clamp alive energy up to this floor each tick (survival scaffold, identical across arms)
BOOK_REPEAT  = int(os.environ.get("AB_BOOK_REPEAT", "16"))   # tile the 231-B ramp into a longer scroll
ARM          = os.environ.get("AB_ARM", "unknown")

assert lab.GENESIS_ECONOMY == "books", \
    "AB runner needs the book economy; set GENESIS_ECONOMY=books (got %r)" % lab.GENESIS_ECONOMY
lab.g_curriculum = False           # single 00_Graded scroll

# ---- load the real 00_Graded ramp and tile it into a non-blank scroll ----
# AB_BOOK_MODE selects the scroll content:
#   "full" -> the whole 231-B graded ramp (run-length 10->5->3->2->1), tiled.
#   "run1" -> ONLY the run-length-1 tail (the non-repeating ABCDEFGHIJ... section), tiled.
#             This is the ramp level the echo reflex CANNOT solve (predicting the current byte is
#             always wrong when the next byte is its successor), so any correct run there requires
#             memory + learning -- the discriminating test of the Session-15 hypothesis.
BOOK_MODE = os.environ.get("AB_BOOK_MODE", "full")
book_path = os.path.join(os.path.dirname(__file__), "..", "Books", "English", "00_Graded.txt")
raw = open(book_path, "rb").read()
glyphs = np.frombuffer(raw, dtype=np.uint8)
glyphs = glyphs[(glyphs >= 32) & (glyphs <= 126)]      # printable, non-blank only
assert glyphs.size > 0, "no printable bytes in 00_Graded.txt"
if BOOK_MODE == "run1":
    # maximal trailing run-length-1 stretch: walk backwards while consecutive bytes differ
    j = int(glyphs.size) - 1
    while j - 1 >= 0 and glyphs[j] != glyphs[j - 1]:
        j -= 1
    run1 = glyphs[j:]
    assert run1.size >= 2, "no run-length-1 tail found in 00_Graded.txt"
    base = run1
else:
    base = glyphs
book_fill = np.tile(base, BOOK_REPEAT).astype(np.uint8)
book_bytes = int(book_fill.size)

# ---- seed founder population, then COMPACT the universe around the book ----
lab.seed_universe(POP, use_ark=False)
alive_ids = [i for i in range(E.MAX_ORGANISMS) if lab.g_alive[i]]
ev = D.reallocate_lab_state(lab, alive_ids, book_bytes, new_book_fill=book_fill)
U = len(lab.g_ram)

# ---- the exact 79-arg kernel call (mirrors genesis_lab sim_loop warmup) ----
def tick():
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
        0, 0, lab.voice_buf, lab.vocal_cords, lab.vocal_prev, lab.action_now, lab.action_prev,
        lab.g_read_log, lab.g_read_fuel, lab.g_cell_owner, lab.g_read_hits, lab.CANVAS_LO, lab.CANVAS_HI, lab.g_org_reward, lab.g_org_elig,
        lab.g_global_sense_type, lab.g_global_sense_meta, lab.g_global_act_drive, lab.g_org_delay_buf, lab.g_org_stomach_fuel, lab.g_org_scratch,
        lab.g_ram_bank_access, lab.g_ram_bank_access_next, lab.g_curriculum_delay,
        lab.g_conn_w_dna,
        lab.g_cam_keys, lab.g_cam_vals, lab.g_cam_valid, lab.g_cam_tick,
        lab.g_clear_count,
        lab.g_org_run, lab.g_lump_acc,
        lab.g_race_state, lab.g_race_attempt_q,
    )
    lab.global_time += 1

# ---- drain the FULL read_log (no 20-event dashboard cap) -> (reads, miss) ----
# Also track per organism the longest streak of CONSECUTIVE correct reads (type 1),
# reset on a miss (type 2). UNCAPPED run length: unlike engine g_org_run it is NOT
# reset at LUMPSUM_K, so it reports the true longest correct-prediction run sustained.
_streak = {}            # org -> current consecutive-correct streak
_max_streak = [0]       # mutable holder for the global peak
def drain():
    L = lab.g_read_log
    idx = 1
    reads = miss = 0
    n = int(L[0])
    while idx < n:
        t = int(L[idx])
        if t == 1:
            reads += 1
            o = int(L[idx + 1])
            s_now = _streak.get(o, 0) + 1
            _streak[o] = s_now
            if s_now > _max_streak[0]:
                _max_streak[0] = s_now
            idx += 3
        elif t == 2:
            miss += 1
            _streak[int(L[idx + 1])] = 0
            idx += 4
        elif t in (3, 4, 5): idx += 3
        else: break
    L[0] = 1
    return reads, miss

# ---- run ----
tot_reads = tot_miss = 0
max_run = 0
max_run_timeline = []
solve_timeline = []
alive_timeline = []
t0 = time.time()
for tk in range(N_TICKS):
    tick()
    if ENERGY_FLOOR > 0:
        al = lab.g_alive
        en = lab.g_energy
        for _i in range(len(al)):
            if al[_i] and en[_i] < ENERGY_FLOOR:
                en[_i] = ENERGY_FLOOR
    r, m = drain()
    tot_reads += r
    tot_miss  += m
    if tk % SAMPLE_EVERY == 0:
        alive = lab.g_alive
        nal = int(alive.sum())
        mr = int(lab.g_org_run[alive].max()) if nal else 0
        if mr > max_run:
            max_run = mr
        sr = tot_reads / (tot_reads + tot_miss) if (tot_reads + tot_miss) else 0.0
        max_run_timeline.append((tk, int(max_run)))
        solve_timeline.append((tk, round(sr, 4)))
        alive_timeline.append((tk, nal))
        if tk % (SAMPLE_EVERY * 40) == 0:
            print(f"[{ARM}] tick {tk}/{N_TICKS} alive={nal} max_run={max_run} "
                  f"reads={tot_reads} miss={tot_miss} solve={sr:.3f} ({time.time()-t0:.1f}s)",
                  flush=True)

alive = lab.g_alive
nal = int(alive.sum())
final_mr = int(lab.g_org_run[alive].max()) if nal else 0
max_run = max(max_run, final_mr)
solve_rate = tot_reads / (tot_reads + tot_miss) if (tot_reads + tot_miss) else 0.0

result = {
    "arm": ARM,
    "seed": SEED,
    "n_ticks": N_TICKS,
    "pop": POP,
    "book_mode": BOOK_MODE,
    "run1_base_len": int(base.size) if BOOK_MODE=="run1" else int(glyphs.size),
    "book_bytes": book_bytes,
    "U": int(U),
    "env": {k: os.environ.get(k) for k in
            ["GENESIS_DALE", "GENESIS_WMEM", "GENESIS_SCRATCH",
             "GENESIS_STDP_TARGET", "GENESIS_NOLEARN", "GENESIS_ECONOMY",
             "GENESIS_BOOK_CATEGORY", "GENESIS_BOOK_NAME"]},
    "max_run": int(max_run),
    "max_streak_uncapped": int(_max_streak[0]),
    "total_reads": int(tot_reads),
    "total_miss": int(tot_miss),
    "solve_rate": round(float(solve_rate), 4),
    "final_alive": nal,
    "wall_seconds": round(time.time() - t0, 1),
    "max_run_timeline": max_run_timeline,
    "solve_timeline": solve_timeline,
    "alive_timeline": alive_timeline,
}
print("RESULT_JSON:" + json.dumps(result))
