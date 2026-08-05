"""
Exp 3 — OPTION 3 NEUROEVOLUTION FULL RUN
Protocol: EXP3_NEUROEVOLUTION_v1  (pre-registered 2026-08-05; design approved via PR #15,
Docs/Architecture/Option3_Neuroevolution_Design.md)

Population-level neuroevolution, NO in-lifetime learning:
  - Genome: flat float32 vector -> synaptic weights + plasticity params
    (engine: ne_body_layout / ne_encode_genome).
  - Fitness = survival time + bytes read correctly
    (survival = delta g_age accumulated by the kernel; bytes = g_ne_bytes kernel hooks).
  - Selection: tournament (size 3). Mutation: Gaussian noise (sigma 0.1 step) applied at the
    substrate's own copy-fidelity rate (per-gene p = 1/G = one expected fault per genome
    replication — the legacy mutate_dna derivation; applying sigma to all ~849 genes at once
    is MEASURED lethal in ~50 ticks, scratch/ne_diag.py arm B vs arm C, 2026-08-05).
    Crossover: uniform (per-gene 50% chance).
  - Task: evolving population of 200 organisms, 100,000 world-ticks, 4 seeds (0..3),
    reproduction every 10,000 ticks (top-50% fitness parents), death when energy <= 0
    (the kernel's own energy accounting, unmodified).
  - Flag: GENESIS_NEUROEVOLUTION (default OFF = byte-identical default path; the two fitness
    hooks are dead-code-eliminated when off and the default is regression-guarded by
    tests/engine_defaultpath_regression_test.py).

NO IN-LIFETIME LEARNING — physics composition (pinned BEFORE genesis_lab import):
  GENESIS_NOLEARN=1 (STDP deleted), GENESIS_CAM=0 (no associative recall input),
  GENESIS_STRUCTURAL_PLASTICITY=0 (no rewire/prune), so a phenotype equals its genome for its
  whole life: ALL adaptation is generational. Kernel OUT_REPRODUCE births are intentionally
  NOT adopted — the population is managed only by the generational tournament (the parent
  still pays the physical reproduce energy cost, so evolve-toward-reproduce wastes energy and
  is selected against; honest physics, no free lunch and no hidden refund).

Environment: books economy on the 00_Graded scroll (the standard survival scaffold), RAM 2 MB,
GENESIS_MAX_ORGANISMS=512, AUTO_REPRO=0, RESUME=0, LIVE_WEB=0, REMAP=0. Founders = the proven
book ancestor projected onto the flat genome + ONE sigma=0.1 Gaussian round on the loci the
ancestor EXPRESSES (its wired synapses + plasticity params, |founder| > 0) — a diverse GA
initial population ON the tested prior's body plan (design §4); jittering silent loci is
measured lethal (see mutation note above).

PRE-REGISTERED SUCCESS CRITERIA (binding — evaluated per seed, and the MECHANISM is CONFIRMED
only if ALL FOUR seeds pass ALL THREE):
  S1. Fitness delta: (mean fitness of the final generation window - mean of the first) /
      first > +10%.
  S2. Population diversity maintained: mean per-gene genome std of the final window >= 10%
      of the initial window (no premature convergence).
  S3. No monotonic decline: the 10 generational mean-fitness reports are NOT all pairwise
      non-increasing.
Failure: null fitness signal -> pivot to non-evolutionary. Premature convergence (S2 fail
with S1 pass) -> add diversity mechanisms. Both reported honestly.

Reports every 10k ticks: mean fitness (+ survival/bytes decomposition), diversity (genome
std), pop size, elites/offspring, extinction flag. Writes per-seed JSONs +
exp3_summary.json to experiments/exp3_neuroevolution_results/.
"""

import os
import sys
import json
import time
import random
import hashlib
import subprocess
import numpy as np

# ── Physics composition (BEFORE genesis_lab import; identical for every seed) ──
os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"
os.environ["GENESIS_RESUME"] = "0"
os.environ["GENESIS_AUTO_REPRO"] = "0"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_NEUROEVOLUTION"] = "1"
os.environ["GENESIS_NOLEARN"] = "1"                  # no in-lifetime weight learning
os.environ["GENESIS_STDP3C"] = "0"
os.environ["GENESIS_STDP3"] = "0"
os.environ["GENESIS_STDP_TARGET"] = "0"
os.environ["GENESIS_CAM"] = "0"                      # no in-lifetime associative recall
os.environ["GENESIS_STRUCTURAL_PLASTICITY"] = "0"    # no in-lifetime rewire/prune

_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_DIR, "..", "src"))

import genesis_lab as gl
import neuromorphic_engine as ne

# ── Pre-registered geometry (env-overridable for smoke runs; defaults are binding) ──
PROTOCOL = "EXP3_NEUROEVOLUTION_v1"
PRE_REG_DATE = "2026-08-05"
TICKS = int(os.environ.get("GENESIS_NE_TICKS", "100000"))
SEEDS = [int(s) for s in os.environ.get("GENESIS_NE_SEEDS", "0,1,2,3").split(",")]

# Pre-registered success thresholds (binding)
DELTA_MIN = 0.10          # S1: early->late fitness delta must exceed +10%
DIVERSITY_FLOOR = 0.10    # S2: final diversity >= 10% of initial

RESULTS_DIR = os.path.join(_DIR, "exp3_neuroevolution_results")


def _world_tick(global_time):
    """One world-tick through the REAL kernel (identical argument list to genesis_lab.sim_loop),
    with the book-economy upkeep mirrored (restock + fuel regrow). Kernel births are discarded
    by design (see module docstring)."""
    alive_steps = gl.g_org_lif_steps[gl.g_alive]
    dynamic_lif_steps = int(alive_steps.max()) if alive_steps.size else 1
    gl.ne_world_maintenance(global_time, dynamic_lif_steps)
    n_alive, n_births = gl.world_tick_numba(
        gl.g_ram, gl.g_org_grid, gl.g_positions, gl.g_alive, gl.g_energy, gl.g_age,
        gl.g_global_v, gl.g_global_ref, gl.g_global_t_last, gl.g_global_thresh, gl.g_global_tau,
        gl.g_global_rec_id,
        gl.g_global_conn_src, gl.g_global_conn_dst, gl.g_global_conn_weight,
        gl.g_global_conn_elig, gl.g_global_conn_elig_t,
        gl.g_neuron_map, gl.g_synapse_map, gl.g_genome_map,
        gl.g_org_n_ptr, gl.g_org_n_count, gl.g_org_s_ptr, gl.g_org_s_count,
        gl.g_global_genome, gl.g_org_g_ptr, gl.g_org_g_count,
        gl.o_rec_a_plus, gl.o_rec_a_minus, gl.o_rec_tau_p, gl.o_rec_tau_m,
        gl.o_rec_v_rest, gl.o_rec_v_reset, gl.o_rec_tau_def, gl.o_rec_spk_max, gl.o_rec_tau_e,
        gl.g_viscosity, global_time, gl.g_org_lif_steps,
        gl.g_b_pos, gl.g_b_parent, gl.g_b_g_start, gl.g_b_g_count, gl.g_b_genomes, gl.g_b_energy,
        gl.g_oracle_val, gl.g_oracle_target, gl.voice_buf, gl.vocal_cords, gl.vocal_prev,
        gl.action_now, gl.action_prev, gl.g_read_log, gl.g_read_fuel, gl.g_cell_owner,
        gl.g_read_hits, gl.CANVAS_LO, gl.CANVAS_HI, gl.g_org_reward, gl.g_org_elig,
        gl.g_global_sense_type, gl.g_global_sense_meta, gl.g_global_act_drive,
        gl.g_org_delay_buf, gl.g_org_stomach_fuel, gl.g_org_scratch,
        gl.g_ram_bank_access, gl.g_ram_bank_access_next, gl.g_curriculum_delay,
        gl.g_conn_w_dna, gl.g_conn_w_slow,
        gl.g_cam_keys, gl.g_cam_vals, gl.g_cam_valid, gl.g_cam_tick,
        gl.g_clear_count, gl.g_org_run, gl.g_lump_acc,
        gl.g_race_state, gl.g_race_attempt_q,
        gl.g_reservoir_state, gl.g_reservoir_src, gl.g_reservoir_dst, gl.g_reservoir_weight,
        gl.g_readout_w,
        gl.g_ne_bytes,
    )
    return n_alive


def _reset_world():
    """Return every shared world structure to a clean cold-start state (exact seed parity:
    seed k must not inherit any heap/RAM residue from seed k-1)."""
    for i in range(gl.MAX_ORGANISMS):
        if gl.g_alive[i]:
            gl.g_alive[i] = False
            gl.g_org_grid[gl.g_positions[i]] = -1
            gl.free_block(gl.g_org_n_ptr[i], gl.g_org_n_count[i], gl.g_neuron_map)
            gl.free_block(gl.g_org_s_ptr[i], gl.g_org_s_count[i], gl.g_synapse_map)
            gl.free_block(gl.g_org_g_ptr[i], gl.g_org_g_count[i], gl.g_genome_map)
    gl.g_ram[:] = 0
    gl.g_org_grid[:] = -1
    gl.g_energy[:] = 0.0
    gl.g_age[:] = 0
    gl.vocal_cords[:] = 0
    gl.vocal_prev[:] = 0
    gl.action_now[:] = -1
    gl.action_prev[:] = -1
    gl.g_read_log[:] = 0
    gl.g_read_log[0] = 1
    gl.g_read_fuel[:] = np.float32(gl.CELL_STATES)
    gl.g_cell_owner[:] = -1
    gl.g_read_hits[:] = 0
    gl.g_clear_count[:] = 0
    gl.g_org_run[:] = 0
    gl.g_lump_acc[:] = 0.0
    gl.g_org_elig[:] = 0.0
    gl.g_org_reward[:] = 1.0
    gl.g_cam_valid[:] = 0
    gl.g_cam_tick[:] = 0
    gl.g_global_v[:] = 0.0
    gl.g_global_ref[:] = 0
    gl.g_global_t_last[:] = -1
    gl.g_global_conn_weight[:] = 0.0
    gl.g_global_conn_elig[:] = 0.0
    gl.g_global_conn_elig_t[:] = 0
    gl.g_ne_bytes[:] = 0
    if gl.g_ne_genomes is not None:
        gl.g_ne_genomes[:] = 0.0


def run_seed(seed):
    t0 = time.time()
    _reset_world()
    # Multi-seed replication (Rule 3): pin ALL THREE RNG families for this seed — python
    # `random` (placement/scratch genes), numpy host draws, and the KERNEL's in-JIT RNG.
    random.seed(seed)
    np.random.seed(seed % (2 ** 32))
    ne.seed_kernel_rng(seed)
    rng = np.random.default_rng(seed)  # GA operators (tournament/crossover/mutation)

    # Fresh contiguous curriculum scroll for this seed, then the founder cohort.
    laid = gl._lay_library()
    placed, founder = gl.ne_seed_population(rng)
    founder_hash = hashlib.sha256(
        b"".join(sorted(bytes(gl.g_global_genome[gl.g_org_g_ptr[i]:
                                                gl.g_org_g_ptr[i] + gl.g_org_g_count[i]])
                        for i in range(gl.MAX_ORGANISMS) if gl.g_alive[i]))).hexdigest()[:16]
    age_mark = gl.ne_reset_generation()

    assert gl.NEUROEVOLUTION, "GENESIS_NEUROEVOLUTION must be 1 for Exp 3"
    assert placed >= 1, "founder placement failed"

    print(f"\n{'=' * 78}\nEXP3 FULL RUN — seed={seed}  pop={placed}/{gl.NE_POP}  "
          f"ticks={TICKS}  repro_every={gl.NE_REPRO_PERIOD}  genome_len={gl.NE_GENOME_LEN} "
          f"(slots={gl.NE_N_SYN_BASE}+{len(gl.NE_DUP_SLOTS)}dup, params={gl.NE_N_PARAM})\n"
          f"laid_scroll={laid}B  founder_genomes={founder_hash}\n{'=' * 78}")

    windows = []
    global_time = 0
    next_repro = gl.NE_REPRO_PERIOD
    while global_time < TICKS:
        _world_tick(global_time)
        global_time += 1
        if global_time >= next_repro:
            stats = gl.ne_evolve_step(rng, age_mark)
            stats["gen"] = len(windows)
            stats["tick_end"] = int(global_time)
            windows.append(stats)
            print(f"  [seed {seed}] t={global_time:>7,} gen={stats['gen']:>2} "
                  f"| pop={stats['pop']:>3} fit={stats['mean_fitness']:>11.1f} "
                  f"(surv={stats['mean_survival']:>9.1f} bytes={stats['mean_bytes']:>7.1f}) "
                  f"max={stats['max_fitness']:>11.1f} | div={stats['diversity']:.4f} "
                  f"| elites={stats['n_elites']} offspring={stats['n_offspring']} "
                  f"extinct={stats['extinct']}")
            age_mark = gl.ne_reset_generation()
            next_repro += gl.NE_REPRO_PERIOD

    # ── per-seed verdict against the pre-registered criteria ──
    early = windows[0]["mean_fitness"]
    late = windows[-1]["mean_fitness"]
    fit_delta = (late - early) / early if early > 0 else float("nan")
    div0 = windows[0]["diversity"]
    div1 = windows[-1]["diversity"]
    div_ratio = (div1 / div0) if div0 > 0 else float("nan")
    fits = [w["mean_fitness"] for w in windows]
    monotonic_decline = all(fits[i + 1] <= fits[i] for i in range(len(fits) - 1))
    s1 = bool(fit_delta > DELTA_MIN)
    s2 = bool(div_ratio == div_ratio and div_ratio >= DIVERSITY_FLOOR)  # nan-guard
    s3 = bool(not monotonic_decline)
    verdict = {
        "early_fitness": float(early),
        "late_fitness": float(late),
        "fitness_delta": float(fit_delta),
        "fitness_delta_pct": (100.0 * float(fit_delta)) if fit_delta == fit_delta else None,
        "diversity_initial": float(div0),
        "diversity_final": float(div1),
        "diversity_ratio": float(div_ratio),
        "monotonic_decline": bool(monotonic_decline),
        "S1_delta_gt_10pct": s1,
        "S2_diversity_maintained": s2,
        "S3_no_monotonic_decline": s3,
        "seed_confirmed": bool(s1 and s2 and s3),
    }
    print(f"  [seed {seed}] VERDICT  early={early:.1f} late={late:.1f} "
          f"delta={100.0 * fit_delta:+.2f}% (S1>{int(DELTA_MIN * 100)}%: {s1}) "
          f"div_ratio={div_ratio:.3f} (S2>={DIVERSITY_FLOOR}: {s2}) "
          f"monotonic_decline={monotonic_decline} (S3: {s3}) "
          f"-> seed_confirmed={s1 and s2 and s3}  ({time.time() - t0:.0f}s)")

    try:
        git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                 text=True, cwd=_DIR).stdout.strip()
    except Exception:
        git_sha = "unknown"
    return {
        "protocol": PROTOCOL,
        "pre_registered": PRE_REG_DATE,
        "seed": int(seed),
        "git_sha": git_sha,
        "geometry": {
            "pop": int(gl.NE_POP), "ticks": TICKS, "repro_period": int(gl.NE_REPRO_PERIOD),
            "tournament": int(gl.NE_TOURNAMENT), "sigma": float(gl.NE_SIGMA),
            "xover_p": float(gl.NE_XOVER_P), "elite_frac": float(gl.NE_ELITE_FRAC),
            "hidden": int(gl.NE_HIDDEN), "genome_len": int(gl.NE_GENOME_LEN),
            "n_slots": int(gl.NE_N_SYN_BASE), "n_dup_slots": len(gl.NE_DUP_SLOTS),
            "n_param": int(gl.NE_N_PARAM),
            "placement": int(placed), "founder_genome_hash": founder_hash,
        },
        "physics": {
            "NEUROEVOLUTION": bool(ne.NEUROEVOLUTION), "NOLEARN": bool(ne.NOLEARN),
            "CAM": bool(ne.CAM), "STRUCTURAL_PLASTICITY": bool(ne.STRUCTURAL_PLASTICITY),
            "DEPLETE": bool(ne.DEPLETE), "REMAP": bool(ne.REMAP),
            "ECONOMY": os.environ["GENESIS_ECONOMY"], "RAM_SIZE": int(ne.RAM_SIZE),
            "MAX_ORGANISMS": int(ne.MAX_ORGANISMS),
            "fitness": "survival_time(delta g_age) + bytes_read_correctly(g_ne_bytes)",
            "births": "kernel OUT_REPRODUCE births discarded; population managed by the "
                      "generational tournament only",
        },
        "windows": windows,
        "verdict": verdict,
    }


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"EXP3 — OPTION 3 NEUROEVOLUTION FULL RUN | protocol={PROTOCOL} "
          f"pre-registered={PRE_REG_DATE}")
    print(f"geometry: pop={gl.NE_POP} ticks={TICKS} repro_every={gl.NE_REPRO_PERIOD} "
          f"seeds={SEEDS} tournament={gl.NE_TOURNAMENT} sigma={gl.NE_SIGMA} "
          f"xover={gl.NE_XOVER_P} elite_frac={gl.NE_ELITE_FRAC}")
    print(f"criteria (binding): S1 delta>{DELTA_MIN:+.0%} AND S2 diversity_ratio>="
          f"{DIVERSITY_FLOOR} AND S3 no monotonic decline — ALL seeds must pass ALL three.")

    # JIT warmup on a throwaway founder (mirrors sim_loop's compile warmup) so the seed loop
    # never pays the compile cost 4 times.
    t_w = time.time()
    print("JIT warmup (world_tick_numba compile)...", flush=True)
    rng = np.random.default_rng(12345)
    placed, _f = gl.ne_seed_population(rng, n=1)
    assert placed == 1
    _world_tick(0)
    _reset_world()
    print(f"  compile+warmup done in {time.time() - t_w:.0f}s")

    results = []
    for seed in SEEDS:
        res = run_seed(seed)
        out = os.path.join(RESULTS_DIR, f"exp3_neuroevolution_s{seed}_{TICKS}t.json")
        with open(out, "w") as f:
            json.dump(res, f, indent=1)
        print(f"  wrote {os.path.relpath(out)}")
        results.append(res)

    # ── all-seeds verdict (binding) ──
    all_pass = all(r["verdict"]["seed_confirmed"] for r in results)
    print(f"\n{'=' * 78}\nEXP3 PER-SEED FITNESS TABLE (mean fitness per generation window)")
    hdr = "seed | " + " ".join(f"gen{i:>10d}" for i in range(len(results[0]["windows"])))
    print(hdr)
    for r in results:
        row = f"{r['seed']:>4} | " + " ".join(
            f"{w['mean_fitness']:>12.1f}" for w in r["windows"])
        print(row)
    print("\nseed |  early |   late |  delta% | div_ratio | decline? | CONFIRMED")
    for r in results:
        v = r["verdict"]
        d = v["fitness_delta_pct"]
        print(f"{r['seed']:>4} | {v['early_fitness']:>6.0f} | {v['late_fitness']:>6.0f} "
              f"| {d if d is not None else float('nan'):>+6.2f}% | {v['diversity_ratio']:>8.3f} "
              f"| {str(v['monotonic_decline']):>8} | {v['seed_confirmed']}")
    final = ("MECHANISM CONFIRMED" if all_pass
             else "MECHANISM NOT CONFIRMED — honest null/pivot per the registered failure clause")
    print(f"\nEXP3 FINAL VERDICT (binding, pre-registered): {final}")

    summary = {
        "protocol": PROTOCOL,
        "pre_registered": PRE_REG_DATE,
        "criteria": {
            "S1_fitness_delta_gt": DELTA_MIN,
            "S2_diversity_ratio_gte": DIVERSITY_FLOOR,
            "S3_no_monotonic_decline": True,
            "rule": "ALL seeds must pass ALL three",
        },
        "seeds": [{
            "seed": r["seed"],
            "early_fitness": r["verdict"]["early_fitness"],
            "late_fitness": r["verdict"]["late_fitness"],
            "fitness_delta_pct": r["verdict"]["fitness_delta_pct"],
            "diversity_ratio": r["verdict"]["diversity_ratio"],
            "monotonic_decline": r["verdict"]["monotonic_decline"],
            "confirmed": r["verdict"]["seed_confirmed"],
            "windows": r["windows"],
        } for r in results],
        "final_verdict": final,
    }
    out = os.path.join(RESULTS_DIR, "exp3_summary.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=1)
    print(f"wrote {os.path.relpath(out)}")
    return 0 if all_pass else 0  # exit 0 either way: a null is a valid experiment outcome


if __name__ == "__main__":
    sys.exit(main())
