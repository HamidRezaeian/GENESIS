# Session 10 — STDP_TARGET=1 Recruitment Lever: Verdict

**Date:** 2026-07-26  **Branch:** `session9-lumpsum`  **Author:** Clusy Agent
**Notebook:** "Session 10 — STDP_TARGET recruitment lever A/B" (cells: harness → analysis → trajectory → figure).
**Driver:** `tests/clusy/qwen/session9_lumpsum_reward/run_evolution.py` (Exp-87-based), run as two
**fresh OS processes** (STDP_TARGET is a compile-time env flag and numba caches the kernel per
process — the repo's own `exp_stdp_target_ab_driver.py` states a fresh process "is the only way").
**Figure:** `stdp_target_ab_trajectory.png` (2×2: frac_net_pos, correct/tick, n_neurons, idle_cost).

---

## Question

Session 9's lump-sum reward is correct but an honest null: under finite fuel (`DEPLETE=1`) income is
zero, and even with fuel lifted (`DEPLETE=0`) the longest sustained correct-byte run caps at **7 < K=8**,
so the K=8 lump sum never fires. The bottleneck is learning capacity, not reward granularity. The
untested recruitment lever (income-design §15 / Exp 87 H3) is `STDP_TARGET=1`: a local delta-rule
teaching signal — on a wrong vocal bit, nudge each *active* reading-eye→vocal synapse by
`err = target − output` — so the organism stops repeating mistakes "in the dark."

**Does turning the teaching signal on break the metabolic ceiling** (extend runs to K=8 and/or raise
the net-positive tick fraction)?

## Method

Two fresh processes, matched flags `GENESIS_DEPLETE=0` (finite-fuel cap lifted so income is possible),
`GENESIS_INCOME_FOOTPRINT=1`, `GENESIS_INCOME_LUMP_SUM=1`, `GENESIS_LUMPSUM_K=8`; `STDP_TARGET ∈ {0,1}`;
`N_SEEDS=3`, `N_TICKS=8000` (40 snapshots @ 200 ticks), `POP_SIZE=min(200, MAX_ORGANISMS)=164`.
Metrics: `frac_net_pos` (fraction of ticks the total living-population energy rose), `max_run`
(cumulative longest consecutive correct-byte run), `correct_per_tick` (comprehension, from read_log),
`n_neurons_mean`, `idle_cost_mean`.

## Results (mean ± std over 3 seeds; per-seed in parentheses)

| Metric (late window = last 1000 ticks) | STDP_TARGET=0 | STDP_TARGET=1 |
|---|---|---|
| **final max_run** (per seed) | **7, 7, 7** | **7, 7, 7** |
| **K=8 lump sum ever fired?** | **NO (0/3)** | **NO (0/3)** |
| frac_net_pos, late window | 0.168 ± 0.035 (0.21/0.14/0.15) | 0.392 ± 0.257 (0.10/0.48/0.59) |
| frac_net_pos, whole-run mean | 0.159 | **0.319 (2.0×)** |
| correct/tick, whole-run mean | 12.48 | 12.78 (≈ unchanged) |
| n_neurons (late) | ~49 | ~54 |
| idle_cost (late) | 261 / 370 / 231 | 374 / 264 / 368 |

Trajectory shape: the two arms **track together through ~tick 2000** (both ≈ 0.15–0.19 net-positive),
then **diverge** — STDP=1 climbs steadily to ≈ 0.45+ by tick 3800 and holds, while STDP=0 stays flat
≈ 0.16. Because refugium dynamics are identical in both arms (both pinned at `n_alive=30`), the widening
gap is not a refugium artifact.

## Findings

1. **The ceiling is NOT broken (rock-solid).** `max_run` caps at **exactly 7 in all 6 runs**, both arms.
   The K=8 lump sum never fires under STDP_TARGET=1 any more than under =0. The lump-sum mechanism
   (Session 9) remains starved: the substrate still cannot sustain 8 consecutive correct byte predictions.
2. **The teaching signal has a real but high-variance effect on viability (suggestive, n=3).** Whole-run
   net-positive tick fraction doubles (0.159 → 0.319) and the trajectory diverges cleanly after tick 2000.
   BUT seed-to-seed variance is large: 2/3 STDP=1 seeds gain strongly (late frac_net_pos 0.48, 0.59) while
   **seed 0 (0.10) falls below every STDP=0 seed**. Needs more seeds to confirm; reported honestly as
   directional, not settled.
3. **Teaching raises the energy fraction, NOT raw accuracy.** `correct_per_tick` whole-run mean is
   essentially unchanged (12.48 → 12.78). The delta-rule signal reshapes *which* ticks are net-positive
   (energy dynamics) more than it raises the average prediction rate.
4. **H1 (efficiency) — modest partial support.** Brains shrink 65 → ~50 neurons and idle cost 586 → ~260–370
   over the run, approaching but mostly staying **above** the 256 income quantum (one STDP=0 seed reached
   late idle 231 < 256). Structure drifts cheaper but not reliably under break-even.

## Verdict — honest null on the load-bearing question, with a genuine partial positive

`STDP_TARGET=1` does **not** break the metabolic ceiling: the longest correct run stays pinned at 7 < K=8
in every run, so the lump-sum reward never fires. It does produce a real, divergent improvement in the
population net-positive tick fraction (≈ 2× whole-run), confirming the *direction* of H3 but at high
seed-variance and without raising raw comprehension. The binding constraint is **sustained-run capacity**,
which a per-byte local teaching signal does not fix — it lifts the *rate* of correct bytes, not the
*longest streak* the lump sum rewards. This is a mechanism mismatch the result exposes cleanly: the
reward targets run LENGTH; the lever moves run RATE.

## #1 open question for Session 11 (the real lever)

**Why does `max_run` cap at EXACTLY 7 in all 6 runs, both arms?** A cap this clean across independent
seeds and both treatment arms smells **structural**, not statistical. Candidate causes to rule out first:
(a) an 8-byte periodicity in the `00_Graded.txt` scroll or the reading gate (every 8th byte excluded /
reset); (b) the `org_delay_buf` / scratch-ring depth (a 7-deep memory would cap predictable context at 7);
(c) the 8-bit byte boundary itself (run counted in bytes; an off-by-one at the byte frame). **If the cap
is structural, K=8 is impossible by construction and NO learning lever can fire the lump sum** — that would
redirect the whole income-granularity programme. Diagnose by dumping the per-tick correct/miss sequence for
one ancestor run and inspecting the period of the miss pattern, and by reading the delay-buf / reading-gate
depth constants.

## Secondary next steps

2. **Raise N_SEEDS** (≥ 6) on the STDP=1 arm to settle whether the frac_net_pos gain is robust or a
   2-of-3 fluke; report a proper effect size + interval.
3. **Generalize the DEPLETE cap to work-units** (income-design Phase 2) so a lump sum can be paid under
   finite fuel (Rule-15 conservation) — still blocked behind the run-length cap above.
4. **Try a longer-horizon teaching signal** (eligibility trace over the last K bytes) that targets
   *sustained* runs rather than per-byte accuracy, directly attacking the rate-vs-length mismatch.

## Regression / disclosure (Rule 17 / 21)

- `STDP_TARGET` defaults to `0`; with it off the teaching block is compile-time skipped (engine L1924
  `if STDP_TARGET and net != 0`), byte-identical to the committed baseline. The A/B is purely env-gated.
- **Bug fix disclosed:** the driver hardcoded `POP_SIZE=200`, but Session 9 made `MAX_ORGANISMS`
  substrate-derived (=164 on this 8 GiB host), so spawning founder #164 indexed out of bounds. Added
  `POP_SIZE = min(POP_SIZE, MAX_ORGANISMS)` after the imports (driver L157–160), with an inline comment.
  This is a Session-9 integration fix, not a behaviour change to the engine.
- All flags (`DEPLETE`, `INCOME_FOOTPRINT`, `INCOME_LUMP_SUM`, `LUMPSUM_K`, `STDP_TARGET`) are recorded
  in each output JSON header; results are reproducible from the notebook harness cell.
