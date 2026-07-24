"""
GENESIS Experiment 69: Phased Curriculum — Decouple Survival from Compositionality Test
=======================================================================================

PURPOSE
-------
Exp 68 showed that shortcut-proof curricula are NON-VIABLE: the colony collapses (pop~21,
refugium ~50% ticks) because reading income depends on statistical regularity. This creates
a catch-22: removing shortcuts is necessary to test compositionality, but doing so starves
the colony.

SOLUTION: Phased curriculum.
- 86% of bytes are a SURVIVAL STREAM: long runs of constant 'a' → ~100% prediction accuracy
  → enough reading income to sustain a healthy colony (pop ~100-300).
- 14% of bytes are SHORTCUT-PROOF COMPOSITIONALITY PROBES: [c1 a a c2 a a A] Latin-square
  items (same as Exp 68 v3). Only answer-byte-specific accuracy is the compositionality
  metric.
- This DECOUPLES survival from the test: the colony thrives on the survival stream while
  probe accuracy measures genuine compositionality without shortcut confounds.

DESIGN
------
* Stream repeats a 50-byte segment: 43 survival bytes + 7 probe bytes.
  - Survival: 43 × 'a' (constant, perfectly predictable → ~100% accuracy → energy income)
  - Probe (7 bytes): [c1 'a' 'a' c2 'a' 'a' ANSWER]
    - c1, c2 ∈ {a..h} (lowercase, uniform random)
    - 'a' constant noise (predictable, same as survival bytes)
    - ANSWER uppercase A-H:
      * RULE: answer = (idx(c1) + idx(c2)) % 8  (Latin square / quasigroup)
      * NULL: answer = random uniform

* ANSWER-BYTE-SPECIFIC accuracy (same as Exp 68 v3):
  - Reads whose target_byte ∈ {A..H} (65-72) → answer reads
  - All other reads → context/survival reads
  - This isolates compositionality from the survival-stream noise.
  - Chance on answer byte = 1/8 = 12.5%.

* Clean Δ = answer_acc(RULE) − answer_acc(NULL) with high statistical power because the
  colony is healthy and produces enough answer reads for measurement.

HYPOTHESIS
----------
- If compositionality is real: answer_acc(RULE) >> answer_acc(NULL) (significant Δ > 0).
- If Δ ≈ 0: no compositionality — the prior ~70% (Exp 30 K/L) was a measurement artifact.
- Secondary: population should be healthy (pop > 100, refugium < 5% ticks), confirming
  the phased design solves the survival problem.

RUNS
----
5 seeds × 2 conditions (RULE, NULL) = 10 runs, 80k ticks/run.
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

# ── Constants ──────────────────────────────────────────────────────────────────────
K = 8                                              # alphabet size
CUES = list("abcdefgh")                            # lowercase cues + noise (ASCII 97-104)
ANSWERS = list("ABCDEFGH")                         # uppercase answer (ASCII 65-72)
NOISE = 'a'                                        # constant noise byte (predictable)
PERIOD = 7                                         # probe period: [c1 a a c2 a a A]
SURVIVAL_RUN_LEN = 43                              # bytes of survival padding per segment
SEGMENT_LEN = SURVIVAL_RUN_LEN + PERIOD            # 50 bytes per segment
N_PROBES = 120                                     # 120 probes × 50 = 6000 bytes
BOOK_TARGET = N_PROBES * SEGMENT_LEN               # exactly 6000 bytes

# ASCII ranges for answer-byte classification
ANS_LO, ANS_HI = 65, 72                            # uppercase A-H marks answer target

DEFAULT_SEEDS = (42, 123, 7, 2024, 999)


def make_stream(mode, seed, n_probes=N_PROBES, survival_run_len=SURVIVAL_RUN_LEN):
    """
    Generate a phased curriculum stream.

    Layout (repeated 50-byte segment):
      [43 × 'a' (survival)] [c1 'a' 'a' c2 'a' 'a' ANSWER (7-byte probe)]

    Returns (stream_string, n_answer_positions).
    """
    rng = random.Random(seed)
    parts = []
    for _ in range(n_probes):
        # ── Survival padding: 43 bytes of 'a' (perfectly predictable) ──
        parts.append(NOISE * survival_run_len)

        # ── Probe: c1 a a c2 a a A ──
        c1 = rng.randrange(K)
        c2 = rng.randrange(K)
        if mode == "RULE":
            a_idx = (c1 + c2) % K
        else:
            a_idx = rng.randrange(K)

        parts.append(CUES[c1])
        parts.append(NOISE)
        parts.append(NOISE)
        parts.append(CUES[c2])
        parts.append(NOISE)
        parts.append(NOISE)
        parts.append(ANSWERS[a_idx])

    stream = "".join(parts)
    return stream


# ── DRIVER (runs INSIDE the headless Python process, injected as a heredoc string) ──

DRIVER = textwrap.dedent("""\
import sys, os, time, random, json, numpy as np

SEED = int(os.environ["EXP_SEED"])
MODE = os.environ["EXP_MODE"]
OUTFILE = os.environ["EXP_OUTFILE"]
N_TICKS = int(os.environ["EXP_NTICKS"])
SAMPLE = int(os.environ["EXP_SAMPLE"])
ANS_LO = int(os.environ["ANS_LO"])
ANS_HI = int(os.environ["ANS_HI"])
BOOK_NAME = os.environ["EXP_BOOK"]

os.environ.update(
    GENESIS_ECONOMY="books",
    GENESIS_CAM="1",
    GENESIS_CAM_KEY_BITS="8",
    GENESIS_CAM_SLOTS="32",
    GENESIS_HOMEOSTATIC_LAMBDA="0.01",
    GENESIS_DEPLETE="1",
    GENESIS_REMAP="0",
    GENESIS_NOLEARN="0",
    GENESIS_BOOK_CATEGORY="Diagnostic",
    GENESIS_BOOK_NAME=BOOK_NAME,
    GENESIS_BOOK_TARGET_BYTES="6000",
)

sys.path.insert(0, "/home/user/repos/GENESIS/src")
import genesis_lab as gl
from books_of_genesis import inject_contiguous_library

random.seed(SEED)
np.random.seed(SEED)
gl.seed_universe(300)
inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, "Diagnostic", BOOK_NAME, 6000)

N = N_TICKS
POOL = 3000
SAMP = SAMPLE

M = {
    "ticks": [],
    "population": [],
    "ans_correct": [],
    "ans_incorrect": [],
    "ctx_correct": [],
    "ctx_incorrect": [],
    "extinctions": 0,
    "refugium_triggers": 0,
}

ref_count = 0
ext = 0

for t in range(N):
    alive = int(np.sum(gl.g_alive))

    # ── Phased refugium ──
    ref_thresh = 30 if t < 50000 else 20
    if alive < ref_thresh:
        gl.g_read_fuel[:] = np.float32(256.0)
        ref_count += 1
        if alive < max(ref_thresh // 3, 2):
            gl.seed_universe(50, use_ark=True)
    if alive == 0:
        ext += 1
        gl.seed_universe(300, use_ark=True)

    # ── Periodic book restock ──
    if t > 0 and t % 5000 == 0:
        inject_contiguous_library(gl.g_ram, gl.RAM_SIZE, "Diagnostic", BOOK_NAME, 6000)

    # ── World tick ──
    gl.g_read_log[0] = 1
    steps = max(1, int(POOL / max(1, alive)))
    gl.world_tick_numba(
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
        gl.g_conn_w_dna, gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick
    )

    # ── Process births ──
    for i in range(gl.g_b_genomes.shape[0]):
        child = gl.mutate_dna(gl.g_b_genomes[i, :gl.g_b_g_count[i]])
        slot = -1
        for j in range(gl.MAX_ORGANISMS):
            if not gl.g_alive[j]:
                slot = j
                break
        if slot != -1:
            pos = gl.g_b_pos[i]
            off = 0
            while gl.g_org_grid[pos] != -1 and off < 100:
                pos = (gl.g_b_pos[i] + off) % gl.RAM_SIZE
                off += 1
            gl.spawn_organism(slot, pos, child, initial_energy=gl.g_b_energy[i])

    gl.global_time += steps

    # ── Sample metrics ──
    if t % SAMP == 0:
        ac = ai = cc = ci = 0
        idx = 1
        n_log = int(gl.g_read_log[0])
        while idx + 2 < n_log and idx < 996:
            et = int(gl.g_read_log[idx])
            tb = int(gl.g_read_log[idx + 2])  # target byte
            is_ans = (ANS_LO <= tb <= ANS_HI)
            if et == 1:       # correct stationary read
                if is_ans:
                    ac += 1
                else:
                    cc += 1
                idx += 3
            elif et == 2:     # incorrect stationary read
                if is_ans:
                    ai += 1
                else:
                    ci += 1
                idx += 4
            elif et == 3:     # correct jump-predict
                if is_ans:
                    ac += 1
                else:
                    cc += 1
                idx += 3
            else:
                idx += 1

        M["ticks"].append(t)
        M["population"].append(alive)
        M["ans_correct"].append(ac)
        M["ans_incorrect"].append(ai)
        M["ctx_correct"].append(cc)
        M["ctx_incorrect"].append(ci)

        if t % (SAMP * 10) == 0:
            atot = ac + ai
            apct = ac / atot * 100 if atot > 0 else 0.0
            ctot = cc + ci
            cpct = cc / ctot * 100 if ctot > 0 else 0.0
            print(f"  [{MODE}] tick {t:7d}/{N_TICKS} pop {alive:4d} "
                  f"ANS_acc {apct:5.1f}% ({ac}/{atot})  CTX_acc {cpct:5.1f}% ({cc}/{ctot})",
                  flush=True)

M["extinctions"] = ext
M["refugium_triggers"] = ref_count
M["wall_clock_sec"] = time.time() - t0_internal
M["ticks_per_sec"] = N_TICKS / M["wall_clock_sec"] if M["wall_clock_sec"] > 0 else 0

with open(OUTFILE, "w") as f:
    json.dump(M, f)

print(f"[{MODE}] DONE in {M['wall_clock_sec']:.1f}s ({M['ticks_per_sec']:.0f} t/s)", flush=True)
""")

# The driver needs t0_internal defined. Patch it into the DRIVER string.
DRIVER_PATCHED = DRIVER.replace(
    't0_internal',
    't0_internal'
)
# Actually, we must add t0_internal before the loop. Let me rewrite slightly.
DRIVER = DRIVER.replace("import sys, os, time, random, json, numpy as np",
                        "import sys, os, time, random, json, numpy as np\nt0_internal = time.time()")


# ── Metrics helpers ────────────────────────────────────────────────────────────────

def _ratio(num, den):
    num = np.array(num, float)
    den = np.array(den, float)
    tot = num + den
    return np.where(tot > 0, num / tot * 100, np.nan)


def steady_metric(arr_correct, arr_incorrect, frac=0.25):
    """Steady-state accuracy (last `frac` of samples), %."""
    n = len(arr_correct)
    s = int(n * (1 - frac))
    r = _ratio(arr_correct[s:], arr_incorrect[s:])
    return float(np.nanmean(r))


def steady_metric_total(arr_correct, arr_incorrect, frac=0.25):
    """Total count of (correct+incorrect) in steady-state window."""
    n = len(arr_correct)
    s = int(n * (1 - frac))
    return float(np.nansum(np.array(arr_correct[s:], float) + np.array(arr_incorrect[s:], float)))


# ── Run one condition × seed ──────────────────────────────────────────────────────

def run_one(mode, seed, n_ticks=80000, sample_every=1000, cache_dir="/tmp/numba_cache_exp69"):
    """Run one (mode, seed) pair. Returns metrics dict."""
    # Generate book
    stream = make_stream(mode, seed)
    book_name = f"PHASED_{mode}_{seed}"
    book_path = os.path.join(BOOKS, book_name + ".txt")
    with open(book_path, "w") as f:
        f.write(stream)

    out_json = f"/tmp/exp69_{mode}_{seed}.json"
    drv_path = "/tmp/exp69_driver.py"
    with open(drv_path, "w") as f:
        f.write(DRIVER)

    env = os.environ.copy()
    env.update(
        EXP_SEED=str(seed),
        EXP_MODE=mode,
        EXP_OUTFILE=out_json,
        EXP_NTICKS=str(n_ticks),
        EXP_SAMPLE=str(sample_every),
        EXP_BOOK=book_name,
        ANS_LO=str(ANS_LO),
        ANS_HI=str(ANS_HI),
        GENESIS_NOLEARN="0",
        GENESIS_DEPLETE="1",
        GENESIS_CAM="1",
        GENESIS_CAM_SLOTS="32",
        GENESIS_CAM_KEY_BITS="8",
        NUMBA_CACHE_DIR=cache_dir,
    )

    t0 = time.time()
    subprocess.run([sys.executable, drv_path], env=env, timeout=7200, check=True)
    dt = time.time() - t0

    with open(out_json) as f:
        M = json.load(f)

    # Steady-state metrics (last 25%)
    ans_acc = steady_metric(M["ans_correct"], M["ans_incorrect"])
    ctx_acc = steady_metric(M["ctx_correct"], M["ctx_incorrect"])
    ans_reads = steady_metric_total(M["ans_correct"], M["ans_incorrect"])
    ctx_reads = steady_metric_total(M["ctx_correct"], M["ctx_incorrect"])
    pop = float(np.mean(M["population"][int(len(M["population"]) * 0.75):]))
    refugium_frac = M["refugium_triggers"] / (n_ticks / sample_every) if n_ticks > 0 else 0

    return {
        "seed": seed,
        "ans_acc": ans_acc,
        "ctx_acc": ctx_acc,
        "ans_reads": ans_reads,
        "ctx_reads": ctx_reads,
        "pop": pop,
        "extinctions": M["extinctions"],
        "refugium_triggers": M["refugium_triggers"],
        "refugium_frac": refugium_frac,
        "wall_sec": dt,
        "tps": M.get("ticks_per_sec", 0),
        "raw": M,  # full time-series for plotting
    }


# ── Main orchestrator ─────────────────────────────────────────────────────────────

def main(
    n_ticks=80000,
    sample_every=1000,
    seeds=DEFAULT_SEEDS,
    out_path=None,
):
    """Run the phased curriculum experiment.

    Parameters
    ----------
    n_ticks : int
        Number of world ticks per run (default 80k).
    sample_every : int
        Sample interval for metrics.
    seeds : tuple
        Random seeds.
    out_path : str or None
        Output JSON path.
    """
    seeds = list(seeds)
    res = {
        "experiment": "exp69_phased_curriculum",
        "K": K,
        "cues": CUES,
        "answers": ANSWERS,
        "noise_byte": NOISE,
        "survival_run_len": SURVIVAL_RUN_LEN,
        "probe_period": PERIOD,
        "segment_len": SEGMENT_LEN,
        "n_probes": N_PROBES,
        "rule": "RULE: answer=ANSWERS[(cue1+cue2)%K]  NULL: random",
        "metric": "answer-byte-specific accuracy (target byte uppercase A-H, chance=12.5%)",
        "seeds": seeds,
        "n_ticks": n_ticks,
        "runs": {"RULE": [], "NULL": []},
    }

    t_start = time.time()
    for mode in ("RULE", "NULL"):
        print(f"\n{'='*60}")
        print(f"  EXP 69 — MODE={mode}  ({len(seeds)} seeds × {n_ticks} ticks)")
        print(f"{'='*60}")
        for sd in seeds:
            print(f"  Starting seed {sd}...", flush=True)
            r = run_one(mode, sd, n_ticks, sample_every)
            res["runs"][mode].append({
                "seed": r["seed"],
                "ans_acc": r["ans_acc"],
                "ctx_acc": r["ctx_acc"],
                "ans_reads": r["ans_reads"],
                "ctx_reads": r["ctx_reads"],
                "pop": r["pop"],
                "extinctions": r["extinctions"],
                "refugium_triggers": r["refugium_triggers"],
                "refugium_frac": r["refugium_frac"],
                "wall_sec": r["wall_sec"],
                "tps": r["tps"],
            })
            print(f"  [{mode}] seed={sd:5d}  ANS_acc={r['ans_acc']:6.2f}%  "
                  f"CTX_acc={r['ctx_acc']:5.1f}%  ans_reads={r['ans_reads']:.0f}  "
                  f"pop={r['pop']:5.0f}  refug={r['refugium_frac']:.3f}  ({r['wall_sec']:.0f}s)",
                  flush=True)

    # ── Aggregate ──
    rule_ans = np.array([r["ans_acc"] for r in res["runs"]["RULE"]])
    null_ans = np.array([r["ans_acc"] for r in res["runs"]["NULL"]])
    delta = rule_ans - null_ans
    dz = float(delta.mean() / (delta.std(ddof=1) / np.sqrt(len(delta)))) if delta.std(ddof=1) > 0 else float("inf")
    chance = 100.0 / K

    res["summary"] = {
        "rule_ans_mean": float(rule_ans.mean()),
        "rule_ans_std": float(rule_ans.std(ddof=1)),
        "null_ans_mean": float(null_ans.mean()),
        "null_ans_std": float(null_ans.std(ddof=1)),
        "rule_ctx_mean": float(np.mean([r["ctx_acc"] for r in res["runs"]["RULE"]])),
        "null_ctx_mean": float(np.mean([r["ctx_acc"] for r in res["runs"]["NULL"]])),
        "rule_pop_mean": float(np.mean([r["pop"] for r in res["runs"]["RULE"]])),
        "null_pop_mean": float(np.mean([r["pop"] for r in res["runs"]["NULL"]])),
        "rule_ans_reads_mean": float(np.mean([r["ans_reads"] for r in res["runs"]["RULE"]])),
        "null_ans_reads_mean": float(np.mean([r["ans_reads"] for r in res["runs"]["NULL"]])),
        "rule_refugium_frac_mean": float(np.mean([r["refugium_frac"] for r in res["runs"]["RULE"]])),
        "null_refugium_frac_mean": float(np.mean([r["refugium_frac"] for r in res["runs"]["NULL"]])),
        "delta_per_seed": [float(x) for x in delta],
        "delta_mean": float(delta.mean()),
        "delta_std": float(delta.std(ddof=1)),
        "delta_z": dz,
        "chance": chance,
        "total_wall_sec": time.time() - t_start,
    }

    if out_path is None:
        out_path = os.path.join(REPO, "exp69_phased_curriculum_results.json")
    with open(out_path, "w") as f:
        json.dump(res, f, indent=2)

    # ── Print verdict ──
    print("\n" + "=" * 72)
    print("  EXP 69 VERDICT — Phased Curriculum: Decoupled Survival + Compositionality Probe")
    print(f"  metric: ANSWER-BYTE accuracy (chance = {chance:.1f}%)")
    print("=" * 72)
    print(f"  RULE  answer_acc = {rule_ans.mean():6.2f}% +/- {rule_ans.std(ddof=1):5.2f}  "
          f"(ctx~{res['summary']['rule_ctx_mean']:.0f}%, pop~{res['summary']['rule_pop_mean']:.0f}, "
          f"ans_reads~{res['summary']['rule_ans_reads_mean']:.0f})")
    print(f"  NULL  answer_acc = {null_ans.mean():6.2f}% +/- {null_ans.std(ddof=1):5.2f}  "
          f"(ctx~{res['summary']['null_ctx_mean']:.0f}%, pop~{res['summary']['null_pop_mean']:.0f})")
    print(f"  Delta = {delta.mean():+.2f} pp  (z={dz:.2f}, per-seed {[round(x,1) for x in delta]})")

    # Population viability check
    rule_pop = res['summary']['rule_pop_mean']
    null_pop = res['summary']['null_pop_mean']
    rule_rf = res['summary']['rule_refugium_frac_mean']
    null_rf = res['summary']['null_refugium_frac_mean']
    print(f"\n  POPULATION VIABILITY:")
    print(f"    RULE: pop~{rule_pop:.0f}, refugium~{rule_rf*100:.1f}% of samples")
    print(f"    NULL: pop~{null_pop:.0f}, refugium~{null_rf*100:.1f}% of samples")

    if rule_pop > 80 and null_pop > 80 and rule_rf < 0.1 and null_rf < 0.1:
        print("  => ✅ Phased curriculum SUCCEEDS: colony viable, refugium rare.")
        print("     The catch-22 is resolved — survival is decoupled from the probe.")
    else:
        print("  => ⚠️ Phased curriculum PARTIALLY works. Colony may still struggle.")

    if dz >= 2.0 and delta.mean() > 0:
        print(f"\n  => ✅ SIGNIFICANT positive Delta (z={dz:.2f}): compositionality is REAL.")
        print("     Organisms predict the answer from cue1+cue2 under shortcut-proof conditions.")
    elif delta.mean() > 0:
        print(f"\n  => ⏳ Positive but NOT significant (z={dz:.2f}): weak/inconclusive.")
    else:
        print(f"\n  => ❌ Delta <= 0: NO compositionality detected.")
        print("     Even with a viable colony, organisms do NOT learn the Latin-square rule.")
        print("     This strengthens Exp 68: compositionality is absent on this substrate.")

    print("=" * 72)
    return res


if __name__ == "__main__":
    main()
