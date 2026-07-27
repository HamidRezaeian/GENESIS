# Session 9 — Lump-Sum Multi-Byte Reward: Verdict

**Date:** 2026-07-26  **Branch:** `session9-lumpsum`  **Author:** Clusy Agent
**Driver:** `tests/clusy/qwen/session9_lumpsum_reward/run_evolution.py` (built on the Exp 87
metabolic-ceiling driver) + clean diagnostic `probe_lump.py`.
**Design basis:** `Docs/RULE21_INCOME_REFACTOR_DESIGN.md` §19 (the load-bearing "multi-byte
work-unit" change), Session-8 verdict (scenario 2 = measured work), `Docs/FixedRules.md` Rules 7/9/17/21.

---

## Question

Exp 87 measured a metabolic ceiling: pure-idle cost ≈ 436 cycles/tick > income quantum = 256,
fraction of net-positive ticks = **0.000** in every condition; selection is nullified. The income
design (§19) identified the root cause: the engine predicts **one byte per tick**, so per-tick
income ≈ per-prediction idle cost (break-even) for any brain size. The proposed fix: reward
**multi-byte work-units** with a lump sum on completion, so income per work-unit can exceed the
per-tick idle cost.

## What was implemented (feature-flagged, default OFF)

- `GENESIS_INCOME_LUMP_SUM` (default `0`) + `GENESIS_LUMPSUM_K` (default `8`), gated behind the
  existing `GENESIS_INCOME_FOOTPRINT`.
- A correct byte (`net > 0`) extends a per-organism run (`g_org_run`); a wrong byte resets it. On
  the K-th consecutive correct byte the organism is paid **one lump sum `K × FOOTPRINT_QUANTUM`**
  (898 = 642 measured compute + 256 RAM freed); the in-progress ticks pay nothing. This **replaces**
  the per-byte footprint path (not additive → no rigged multiplier, Rule 21.4). Expected income/tick
  is unchanged; only the *temporal structure* changes (a sustained-cognition credit-assignment test).
- New mutable per-organism arrays `g_org_run` (int32) / `g_lump_acc` (float32) are passed as kernel
  **parameters** (numba treats module-global arrays as read-only — same pattern Phase 4 used for
  `g_clear_count`). `world_tick_numba` signature grew 75 → 77 args; both `genesis_lab.py` call sites
  and the Exp-87-derived driver were updated (AST-verified 77 == 77).
- Death resets the in-progress run. Cell-clearing (Phase 4) still runs on `net > 0`, independent of
  the lump sum.

## Results (clean diagnostic, seed 20260725, 2000 ticks, refugium-floored so the bankrupt ancestor stays measurable)

| Condition | lump payments | max run | earning frac | run-length distribution |
|---|---|---|---|---|
| DEPLETE=1 (Exp-87 condition), K=2/4/8 | **0** | **0** | **0.0** | all observations at run=0 |
| DEPLETE=0, K=2 | 1569 | 7 | 0.067 | 0:4390, 1:3983, 2:3625, 3:3161, 4:2696, 5:2319, 6:2053, 7:1874 |
| DEPLETE=0, K=4 | 1531 | 7 | 0.067 | (same shape) |
| DEPLETE=0, K=8 | **0** | 7 (< K) | 0.067 | (same shape — no run ever reaches 8) |

## Findings

1. **The mechanism is correct and fires.** With finite fuel lifted (DEPLETE=0), organisms earn
   income, runs extend up to length 7, and the lump sum pays ~1500× over 2000 ticks for K=2 and K=4.
   The feature flag, kernel parameters, and run/reset/death logic all behave as designed.
2. **The ceiling is NOT broken.**
   - Under the Exp-87 finite-fuel condition (DEPLETE=1) organisms earn **nothing** (`earning_frac=0`,
     `run=0`): the per-cell fuel reservoir caps income at the regrow rate (DEPLETE_REGROW=256/tick),
     which is below idle cost. The lump sum cannot fire because no income means no runs.
   - Even with finite fuel lifted (DEPLETE=0), only **6.7%** of (organism, tick) pairs are
     net-positive, and **K=8 never fires** because the longest sustained correct run is **7 bytes**.
3. **The bottleneck is learning capacity, not reward granularity.** The ancestor cannot sustain 8
   consecutive correct next-byte predictions (max run = 7, and the run distribution falls off steeply
   with length). A lump sum on K-byte completion can only reward sustained cognition the substrate
   can actually produce. Per-tick income (898 × correct-rate) also only *barely* exceeds idle cost
   (~436–590), so most ticks stay net-negative.

## Verdict — honest null (income-design scenario 3 / prediction P4)

The lump-sum multi-byte reward is implemented correctly and is Rule-21-compliant (measured footprint,
no rigged multiplier, env-gated + disclosed, sweeping K is the tuning test). It does **not** break the
metabolic ceiling, because the binding constraints are (a) the finite fuel reservoir under DEPLETE and
(b) the substrate's inability to sustain long correct-prediction runs — not the granularity of the
reward. This is the design doc's explicitly-permitted honest negative.

## Next steps (to break the ceiling, in priority order)

1. **Raise the learning capacity** so runs reach K: enable `STDP_TARGET=1` (the Exp-87 recruitment
   lever) and/or a richer curriculum, then re-test whether K-runs (and thus lump sums) emerge. This is
   the real bottleneck the present result exposes.
2. **Generalize the DEPLETE cap to work-units** (income-design Phase 2): let a completed K-byte
   work-unit draw from the *aggregate* fuel of the K cells it internalizes, so a lump sum can be paid
   under finite fuel without minting (Rule 15 conservation). The current per-cell cap zeroes income
   before any run can form.
3. **Re-measure α vs β** (income-design Phase 0): is the measured footprint-per-work-unit ever > the
   measured brain-cost-per-work-unit for a *learnable* work-unit? If not even in principle, record the
   ceiling as a hard substrate limit.

## Regression guarantee

With `GENESIS_INCOME_LUMP_SUM=0` (default) the new kernel branch is compile-time skipped and the code
reduces to the exact pre-Session-8/9 per-byte path; `g_org_run`/`g_lump_acc` are allocated but never
read or written, so default behaviour is unchanged. (Verified by code inspection + AST arg-count match;
the flag-OFF path is byte-identical to the committed Exp-87 reward core.)
