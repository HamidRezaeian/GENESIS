"""
GENESIS Experiment 68: Shortcut-Proof Compositionality Probe (v1 -> v3)
======================================================================

PURPOSE
-------
Close the "Bigram Shortcut" loophole from Exp 30. Arms K/L reported ~70%
"compositionality" but that is contaminated by (C1) a RANDOM table (no rule to learn),
(C2) accuracy conflating cue/noise/answer bytes (positional-structure prediction), and
(C3) the bigram shortcut (P(next|current) peaked on structured text).

DESIGN
------
* RULE: answer = (cue1 + cue2) mod 8  (Latin square / quasigroup)
        => P(answer|cue1)=P(answer|cue2)=P(answer|prev_noise)=uniform, so an order-1
           (bigram) predictor gets EXACTLY chance on the answer; only a model holding
           BOTH cues (working memory + composition) beats it.
* NULL: answer = uniform, independent of cues.  Identical format/marginals/structure.
* Stream layout (period 7): [cue1 n n cue2 n n answer].

VERSIONS (each fixes a confound discovered while running)
---------------------------------------------------------
v1  noise UNIFORM (maximally shortcut-proof). RESULT: colony collapses (refugium fires
    ~50% of ticks, pop~7-14) because the energy-poor uniform stream gives ~12.5% baseline
    reading income -> starvation. Delta=-5.3pp (n.s.) but INCONCLUSIVE (noise-dominated).
    FINDING: a fully shortcut-free curriculum is NON-VIABLE -- survival needs regularity.
v2  noise CONSTANT 'a' (survival scaffold). Colony healthy (pop=300). But the 4 trivially
    predictable noise bytes dilute the answer signal to ~1/7 of the metric -> Delta=+1.9pp
    on 1 seed, too diluted to read.
v3  THIS VERSION. Fixes dilution by measuring ANSWER-BYTE-SPECIFIC accuracy. Answers use a
    DISJOINT alphabet (uppercase A-H) from cues/noise (lowercase a-h); the engine's
    g_read_log stores the target byte per read [type, org, read_byte, target_byte] (stride
    4), so reads whose target_byte is uppercase are ANSWER predictions. We compare
    answer_acc(RULE) vs answer_acc(NULL) -- the clean compositionality signal with the
    bigram + structure + dilution confounds all controlled out. Constant-noise scaffold
    keeps the colony viable. chance on the answer byte = 1/8 = 12.5%.

INTERPRETATION
--------------
  answer_acc(RULE) >> answer_acc(NULL) (significant) => organisms use cue1+cue2 (REAL).
  answer_acc(RULE) ~= answer_acc(NULL)               => no compositionality; prior 70%
                                                        was a structure/bigram artifact.

Runs on the BOOKS economy with the proven Exp-30 formula:
DEPLETE + Homeostatic STDP (lambda=0.01) + CAM v2 (32 slots) + Refugium.
"""
import os
import sys
import json
import time
import random
import subprocess
import textwrap

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOOKS = os.path.join(REPO, "Books", "Diagnostic")
os.makedirs(BOOKS, exist_ok=True)

K = 8
CUES = list("abcdefgh")     # lowercase: cues + noise (ASCII 97-104)
ANSWERS = list("ABCDEFGH")  # uppercase: answer (ASCII 65-72) -- disjoint => identifiable
PERIOD = 7                   # [c1 n n c2 n n A]
ANS_LO, ANS_HI = 65, 72      # ASCII range that marks an ANSWER target byte


def make_stream(mode, seed, n_units=1400, noise_symbols=None):
    """Build the curriculum scroll.
    mode='RULE': answer=ANSWERS[(c1+c2)%K].  mode='NULL': answer=ANSWERS[random].
    noise_symbols: lowercase symbols for the 4 noise bytes; default ['a'] (constant
    survival scaffold)."""
    assert mode in ("RULE", "NULL")
    if noise_symbols is None:
        noise_symbols = ['a']
    rng = random.Random(seed)
    out = []
    pairs = set()
    for _ in range(n_units):
        c1 = rng.randrange(K)
        c2 = rng.randrange(K)
        ns = [noise_symbols[rng.randrange(len(noise_symbols))] for _ in range(4)]
        a = (c1 + c2) % K if mode == "RULE" else rng.randrange(K)
        out.extend([CUES[c1], ns[0], ns[1], CUES[c2], ns[2], ns[3], ANSWERS[a]])
        pairs.add((c1, c2))
    return "".join(out), len(pairs)


# Headless engine driver. Parses g_read_log with the CORRECT stride-4 format
# [type, org, read_byte, target_byte] and classifies each read as ANSWER (target byte
# uppercase A-H) vs CONTEXT (lowercase), tracking correct/incorrect per class.
DRIVER = textwrap.dedent(r'''
import sys, os, time, json, random
import numpy as np
SEED   = int(os.environ.get("SEED", "42"))
N_TICKS= int(os.environ.get("N_TICKS", "150000"))
SAMPLE = int(os.environ.get("SAMPLE_EVERY", "1000"))
OUT    = os.environ.get("OUTPUT_FILE", "/tmp/exp68.json")
ARM    = os.environ.get("ARM_LABEL", "RULE")
BOOK   = os.environ.get("BOOK_NAME", "SPv3_RULE")
ANS_LO = int(os.environ.get("ANS_LO", "65"))
ANS_HI = int(os.environ.get("ANS_HI", "72"))
CELL_STATES = np.float32(256.0)
os.environ.update(GENESIS_ECONOMY="books", GENESIS_DELAY="1", GENESIS_DELAY_N="3",
    GENESIS_BOOK_CATEGORY="Diagnostic", GENESIS_BOOK_NAME=BOOK,
    GENESIS_CAM="1", GENESIS_CAM_SLOTS="32",
    GENESIS_HOMEOSTATIC_LAMBDA="0.01", GENESIS_DEPLETE="1",
    GENESIS_CURRICULUM="0", GENESIS_STIGMERGY="0", GENESIS_CANVAS="0",
    GENESIS_NICHE_ECON="0", GENESIS_PEER_PREDICT="0", GENESIS_EVOSENSE="0",
    GENESIS_EVOACT="0", GENESIS_SCRATCH="0", GENESIS_WMEM="0", GENESIS_DIGESTION="0",
    GENESIS_REMAP="0", GENESIS_STDP3="0", GENESIS_STDP3C="0",
    GENESIS_STDP_TARGET="0", GENESIS_STDP_COSTONLY="0")
sys.path.insert(0, os.path.join(os.environ["REPO"], "src"))
import genesis_lab as gl
from books_of_genesis import inject_contiguous_library
gl.g_curriculum_delay = 3
random.seed(SEED); np.random.seed(SEED)
gl.seed_universe(300)
inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, "Diagnostic", BOOK, 6000)
M = {"arm": ARM, "book": BOOK, "seed": SEED, "cam_slots": 32, "deplete": True,
     "ticks": [], "population": [],
     "ans_correct": [], "ans_incorrect": [], "ctx_correct": [], "ctx_incorrect": [],
     "extinctions": 0, "refugium_triggers": 0}
pool = 3000; ext = 0; ref_count = 0; t0 = time.time()
print(f"[{ARM}] seed={SEED} ticks={N_TICKS} book={BOOK}", flush=True)
for t in range(N_TICKS):
    alive = int(np.sum(gl.g_alive))
    if   t < 50000:  ref_thresh = 30; phase = 0
    elif t < 100000: ref_thresh = 20; phase = 1
    elif t < 130000: ref_thresh = 10; phase = 2
    else:            ref_thresh = 5;  phase = 3
    if alive < ref_thresh:
        gl.g_read_fuel[:] = CELL_STATES; ref_count += 1
        if alive < max(ref_thresh // 3, 2):
            gl.seed_universe(50, use_ark=True); alive = int(np.sum(gl.g_alive))
    if alive == 0:
        ext += 1; gl.seed_universe(300, use_ark=True); alive = int(np.sum(gl.g_alive))
    if t > 0 and t % 5000 == 0:
        inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, "Diagnostic", BOOK, 6000)
    gl.g_read_log[0] = 1
    steps = max(1, int(pool / max(1, alive)))
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
        gl.g_conn_w_dna, gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick)
    for i in range(n_births):
        child = gl.mutate_dna(gl.g_b_genomes[i, :gl.g_b_g_count[i]]); slot = -1
        for j in range(gl.MAX_ORGANISMS):
            if not gl.g_alive[j]:
                slot = j; break
        if slot != -1:
            pos = gl.g_b_pos[i]; off = 0
            while gl.g_org_grid[pos] != -1 and off < 100:
                pos = (gl.g_b_pos[i] + off) % gl.RAM_SIZE; off += 1
            gl.spawn_organism(slot, pos, child, initial_energy=gl.g_b_energy[i])
    gl.global_time += steps
    if t % SAMPLE == 0:
        ac = ai = cc = ci = 0
        idx = 1
        n_log = int(gl.g_read_log[0])
        while idx + 2 < n_log and idx < 996:
            et = int(gl.g_read_log[idx])
            tb = int(gl.g_read_log[idx + 2])      # target byte (next_byte/pval) at idx+2
            is_ans = (ANS_LO <= tb <= ANS_HI)     # uppercase A-H => answer position
            if et == 1:                            # correct stationary read (stride 3)
                if is_ans: ac += 1
                else:      cc += 1
                idx += 3
            elif et == 2:                          # incorrect stationary read (stride 4)
                if is_ans: ai += 1
                else:      ci += 1
                idx += 4
            elif et == 3:                          # correct jump-predict (stride 3)
                if is_ans: ac += 1
                else:      cc += 1
                idx += 3
            else:                                  # types 4/5 (peer-predict, disabled)
                idx += 1
        M["ticks"].append(t); M["population"].append(alive)
        M["ans_correct"].append(ac); M["ans_incorrect"].append(ai)
        M["ctx_correct"].append(cc); M["ctx_incorrect"].append(ci)
        if t % (SAMPLE * 10) == 0:
            atot = ac + ai
            apct = ac / atot * 100 if atot > 0 else 0.0
            print(f"  [{ARM}] tick {t:7d}/{N_TICKS} P{phase+1} pop {alive:4d} "
                  f"ANS_acc {apct:5.1f}% ({ac}/{atot})  ctx({cc}/{cc+ci})", flush=True)
M["extinctions"] = ext; M["refugium_triggers"] = ref_count
M["wall_clock_sec"] = time.time() - t0
M["ticks_per_sec"] = N_TICKS / M["wall_clock_sec"]
with open(OUT, "w") as f:
    json.dump(M, f)
print(f"[{ARM}] DONE in {M['wall_clock_sec']:.1f}s ({M['ticks_per_sec']:.0f} t/s)", flush=True)
''')


def _ratio(num, den):
    num = np.array(num, float); den = np.array(den, float)
    tot = num + den
    return np.where(tot > 0, num / tot * 100, np.nan)


def steady_answer_acc(M, frac=0.25):
    """Steady-state ANSWER-BYTE accuracy (last `frac` of samples), %."""
    n = len(M["ticks"]); s = int(n * (1 - frac))
    r = _ratio(M["ans_correct"][s:], M["ans_incorrect"][s:])
    return float(np.nanmean(r))


def steady_context_acc(M, frac=0.25):
    n = len(M["ticks"]); s = int(n * (1 - frac))
    r = _ratio(M["ctx_correct"][s:], M["ctx_incorrect"][s:])
    return float(np.nanmean(r))


def steady_answer_reads(M, frac=0.25):
    n = len(M["ticks"]); s = int(n * (1 - frac))
    ac = np.array(M["ans_correct"][s:], float); ai = np.array(M["ans_incorrect"][s:], float)
    return float(np.nansum(ac + ai))


def run_one(mode, seed, n_ticks, sample_every, cache_dir, noise_symbols, book_tag):
    book = f"SP{book_tag}_{mode}"
    stream, npairs = make_stream(mode, seed, noise_symbols=noise_symbols)
    with open(os.path.join(BOOKS, book + ".txt"), "w") as f:
        f.write(stream)
    out_json = f"/tmp/exp68{book_tag}_{mode}_{seed}.json"
    drv = "/tmp/exp68_driver.py"
    with open(drv, "w") as f:
        f.write(DRIVER)
    env = os.environ.copy()
    env.update(SEED=str(seed), N_TICKS=str(n_ticks), SAMPLE_EVERY=str(sample_every),
               OUTPUT_FILE=out_json, ARM_LABEL=mode, BOOK_NAME=book, REPO=REPO,
               ANS_LO=str(ANS_LO), ANS_HI=str(ANS_HI),
               GENESIS_NOLEARN="0", GENESIS_DEPLETE="1", GENESIS_CAM_SLOTS="32",
               NUMBA_CACHE_DIR=cache_dir)
    t0 = time.time()
    subprocess.run([sys.executable, drv], env=env, timeout=5400, check=True)
    dt = time.time() - t0
    with open(out_json) as f:
        M = json.load(f)
    return M, dt


def main(n_ticks=150_000, sample_every=1000, seeds=(42, 123, 7, 2024, 999),
         noise_symbols=None, version="v3", out_path=None):
    cache = "/tmp/numba_cache_exp68"
    seeds = list(seeds)
    noise_symbols = ['a'] if noise_symbols is None else noise_symbols
    book_tag = version
    res = {"experiment": f"exp68_shortcut_proof_{version}", "K": K,
           "cues": CUES, "answers": ANSWERS, "period": PERIOD,
           "rule": "answer=ANSWERS[(cue1+cue2)%K]", "noise_symbols": noise_symbols,
           "metric": "answer-byte-specific accuracy (target byte uppercase A-H)",
           "seeds": seeds, "n_ticks": n_ticks, "runs": {"RULE": [], "NULL": []}}
    t_start = time.time()
    for mode in ("RULE", "NULL"):
        for sd in seeds:
            M, dt = run_one(mode, sd, n_ticks, sample_every, cache, noise_symbols, book_tag)
            ans = steady_answer_acc(M)
            ctx = steady_context_acc(M)
            ansN = steady_answer_reads(M)
            pop = float(np.mean(M["population"][int(len(M["population"]) * 0.75):]))
            res["runs"][mode].append({"seed": sd, "ans_acc": ans, "ctx_acc": ctx,
                                      "ans_reads": ansN, "pop": pop,
                                      "extinctions": M["extinctions"],
                                      "refugium": M["refugium_triggers"],
                                      "wall_sec": dt, "tps": M.get("ticks_per_sec", 0)})
            print(f"[exp68 {version}] {mode:4s} seed={sd:5d}  ANS_acc={ans:6.2f}%  "
                  f"ctx={ctx:5.1f}%  ans_reads={ansN:.0f}  pop={pop:5.0f}  ({dt:.0f}s)", flush=True)
    rule = np.array([r["ans_acc"] for r in res["runs"]["RULE"]])
    null = np.array([r["ans_acc"] for r in res["runs"]["NULL"]])
    delta = rule - null
    dz = float(delta.mean() / (delta.std(ddof=1) / np.sqrt(len(delta)))) if delta.std(ddof=1) > 0 else float("inf")
    res["summary"] = {
        "rule_ans_mean": float(rule.mean()), "rule_ans_std": float(rule.std(ddof=1)),
        "null_ans_mean": float(null.mean()), "null_ans_std": float(null.std(ddof=1)),
        "rule_ctx_mean": float(np.mean([r["ctx_acc"] for r in res["runs"]["RULE"]])),
        "null_ctx_mean": float(np.mean([r["ctx_acc"] for r in res["runs"]["NULL"]])),
        "rule_pop_mean": float(np.mean([r["pop"] for r in res["runs"]["RULE"]])),
        "null_pop_mean": float(np.mean([r["pop"] for r in res["runs"]["NULL"]])),
        "rule_ans_reads_mean": float(np.mean([r["ans_reads"] for r in res["runs"]["RULE"]])),
        "null_ans_reads_mean": float(np.mean([r["ans_reads"] for r in res["runs"]["NULL"]])),
        "delta_per_seed": [float(x) for x in delta],
        "delta_mean": float(delta.mean()), "delta_std": float(delta.std(ddof=1)),
        "delta_z": dz, "chance": 100.0 / K,
        "total_wall_sec": time.time() - t_start}
    if out_path is None:
        out_path = os.path.join(REPO, f"exp68_shortcut_proof_results_{version}.json")
    with open(out_path, "w") as f:
        json.dump(res, f, indent=2)
    print("\n" + "=" * 72)
    print(f"  EXP 68 ({version}) VERDICT — Shortcut-Proof Compositionality")
    print(f"  metric: ANSWER-BYTE accuracy (chance = {100/K:.1f}%)")
    print("=" * 72)
    print(f"  RULE  answer_acc = {rule.mean():6.2f}% +/- {rule.std(ddof=1):5.2f}  "
          f"(ctx~{res['summary']['rule_ctx_mean']:.0f}%, pop~{res['summary']['rule_pop_mean']:.0f}, "
          f"ans_reads~{res['summary']['rule_ans_reads_mean']:.0f})")
    print(f"  NULL  answer_acc = {null.mean():6.2f}% +/- {null.std(ddof=1):5.2f}  "
          f"(ctx~{res['summary']['null_ctx_mean']:.0f}%, pop~{res['summary']['null_pop_mean']:.0f})")
    print(f"  Delta = {delta.mean():+.2f} pp  (z={dz:.2f}, per-seed {[round(x,1) for x in delta]})")
    if dz >= 2.0 and delta.mean() > 0:
        print("  => SIGNIFICANT positive Delta: compositionality is REAL")
        print("     (organisms predict the answer from cue1+cue2; bigram/structure controlled out).")
    elif delta.mean() > 0:
        print("  => Positive but NOT significant: weak/inconclusive compositionality.")
    else:
        print("  => Delta <= 0: NO compositionality. Prior 70% was a structure/bigram artifact.")
    print("=" * 72)
    return res


if __name__ == "__main__":
    main()
