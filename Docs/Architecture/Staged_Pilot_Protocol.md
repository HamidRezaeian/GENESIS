# Staged Pilot Protocol — Substrate 4 Deep-Time Confirmation Run

**Status: PRE-REGISTERED (binding) — 2026-08-06. Success and falsification criteria are fixed
HERE, before any stage is run. Results are judged against this document, not against a moving
"not yet" (cf. `Ascent.md` §1 loop diagnosis). Pre-registration per Rule 2.**

**Protocol ID:** `SUBSTRATE_4_STAGED_PILOT_v1`
**Base protocol:** `SUBSTRATE_4_EXTENDED_20K_v1` (`experiments/sub4_extended_20k.py`) — substrate,
seeds, patch construction, LR, and metric definitions are carried over UNCHANGED. Only the tick
budget and the stopping logic are new.

---

## 1. Why this pilot exists

The 5M-tick feasibility analysis (2026-08-06, commit `9dd5837` record) showed:

1. **Compute is not the constraint.** Measured on the unmodified repo code (8-core 2.6 GHz,
   home-hardware class): LEARN 77.5 ticks/s, NOLEARN 102.6 ticks/s → 5M ticks ≈ 17.9 h per
   LEARN run, ≈ 18 h wall for the full 4-seed × 2-arm protocol on 8 cores.
2. **The curve is already flat.** 2k→20k (10×) bought +0.24pp in-lifetime delta (3.45→3.70pp,
   Gate A needs ≥ +5pp) and +3.0pp late accuracy (86.9→89.9%). Within the 20k runs, accuracy
   peaks at ~tick 4k (~93–95%) and then oscillates around ~90% with ±3pp window noise.
3. **Gate A is mathematically inexpressible on this metric at any duration** (a +25% relative
   rise from a ~90% baseline exceeds the 100% bit-accuracy ceiling; from the ~50% NOLEARN floor
   it was already passed by tick 200).

The 5M question is therefore *almost certainly* closed. This pilot exists to close it
**with evidence rather than by extrapolation**, at a capped cost of ≤ ~6 h wall-clock, and to
watch the one deep-time failure mode the 20k data hints at but cannot resolve: **weight-norm
drift** (`norm_w` grew linearly 10.26 → 12.60 over 20k ticks; unbounded growth could eventually
degrade accuracy — that is a real, falsifiable deep-time question the plateau analysis does
not answer).

## 2. Pre-registered hypotheses

- **H0 (saturation / memorization):** accuracy at horizons > 20k stays inside the plateau
  band; in-lifetime delta stays < 5pp. Prediction: late-window accuracy at 100k, 500k, 1M all
  within **[87%, 93%]** (the 20k late mean 89.9% ± observed window noise 3pp).
- **H1 (deep-time gain):** accuracy keeps rising beyond 20k. Prediction: monotone trend in
  window accuracy across any stage, carrying the late mean **> 95%**.
- **H2 (deep-time degradation):** weight-norm drift eventually hurts. Prediction: late-window
  accuracy falls **< 87%** at some stage, coincident with `mean_norm` > 25 (≈ 2× the 20k
  endpoint).

Exactly one of H0/H1/H2 is declared the outcome at pilot end. No fourth outcome is
admissible after the fact.

## 3. Protocol

Everything inherits `SUBSTRATE_4_EXTENDED_20K_v1` except where listed.

| Parameter | Value | Notes |
|---|---|---|
| Seeds | [0, 1, 2, 3] | unchanged |
| Organisms | 60 | unchanged |
| Arms | LEARN all stages; **NOLEARN at Stage 1 only** | NOLEARN is frozen ⇒ its accuracy is time-invariant in expectation; one 100k measurement fixes the ablation baseline (pre-registered decision, saves ~4.5 h) |
| Stages | **S1 = 100k → S2 = 500k → S3 = 1M ticks** | hard cap at 1M; 5M is not in this protocol |
| Window logging | every **1,000 ticks** | same granularity as the 20k driver (S1: 100, S2: 500, S3: 1000 records/seed) |
| Weight snapshots | every **25,000 ticks**, rolling keep-last-2 + stage-end full dump | resume capability (base code has none — see §6); stage-end dump ≈ 5.9 MiB/seed (60 orgs × 25,088 params fp32) |
| Metrics | identical definitions: early = mean of first 3 windows, late = mean of last 3 windows, delta = late − early, gap = LEARN_late − NOLEARN_late | comparability with 2k/20k records |

**Cost ledger (measured rates, serial per seed):** S1 ≈ 22 min LEARN (+16 min NOLEARN), S2 ≈
1.8 h, S3 ≈ 3.6 h. Worst-case serial exposure ≈ 5.7 h/seed; running the 4 seeds in parallel
(1 core each) plus the 4 NOLEARN S1 runs on the remaining cores ⇒ **≤ ~6 h total wall-clock**,
< 2 GB RAM, < 200 MB storage for all logs+snapshots. Abort at any gate costs only the stages
already run.

## 4. Early-stop gates (checked at every 25k-tick snapshot and at each stage end)

- **G-plateau (stop, H0 confirmed at this horizon):** rolling mean of the last 10 windows
  inside **[87%, 93%]** AND OLS slope of window-accuracy over the trailing 50 windows
  statistically indistinguishable from 0 (95% CI contains 0 and |point estimate| < 0.5pp per
  50k ticks).
- **G-escape-up (continue with scrutiny):** rolling mean > 93% sustained over 3 consecutive
  snapshot evaluations (75k ticks). Inspect for instrument bugs FIRST (Rule 20: a sudden rise
  at long horizon in a saturated metric is more likely a logging artifact than learning), then
  continue.
- **G-degrade (stop, H2 confirmed):** rolling mean < 87% sustained over 3 consecutive
  evaluations, OR `mean_norm` > 25 at any snapshot.
- **G-delta:** in-lifetime delta is recomputed at each stage end with the frozen definitions
  (early = first 3 windows of the RUN, i.e. ticks 1k–3k — the definition does not drift with
  horizon).

## 5. Decision rules (pre-committed)

| Stage end | Evidence state | Action |
|---|---|---|
| **S1 (100k)** | G-plateau holds (expected) | Continue to S2. |
| | G-degrade | STOP. H2 confirmed → pivot to the regularized/weight-decay variant (see `Nonstationary_Variants_Protocol.md` V-series follow-ups); no further ticks spent. |
| | G-escape-up with verified instrument | Continue to S2 with mid-stage checks every 10k ticks. |
| **S2 (500k)** | Late mean inside band AND second-half vs first-half late-window means differ by < 1pp | **STOP — skip S3.** H0 confirmed to 500k; the marginal value of 500k→1M is declared not worth 3.6 h/seed. |
| | Upward trend (> +2pp over S1 late mean, monotone across ≥ 50 consecutive windows) | Continue to S3. |
| | G-degrade | STOP, H2 confirmed, pivot as above. |
| **S3 (1M)** | — | Final verdict regardless of outcome. |

**Falsification criterion (Rule 2, binding):**
- **H1 is falsified** if at S3 (or S2, if the S2 stop rule fires) the OLS slope of window
  accuracy over ticks 100k→end has a 95% CI containing 0 with |point estimate| < 0.5pp per
  900k ticks. Consequence: the 5M-tick experiment is **permanently cancelled** for this
  substrate+metric — no future proposal may reopen it without a new substrate or a new
  capability metric. This is the kill-switch the 5M proposal currently lacks.
- **H0 is falsified** if the late mean at 1M ≥ 95% with a monotone trend across the final 100
  windows. Consequence: a full 5M run is reconsidered — this is the ONLY outcome that reopens
  the 5M question.
- **H2 confirmed** at any stage → substrate instability over deep time is the finding; the
  next experiment is a regularization variant, not more ticks.

## 6. Required engineering deltas (no substrate changes)

1. **Resume-from-snapshot.** The base driver has no checkpointing; a crash at tick 4.9M/5M
   loses everything (that risk is one reason the 5M run was judged poor value). Snapshots every
   25k ticks + a resume entry point are MANDATORY before S1 starts.
2. **Slope/CI computation** on the window log at each gate check (numpy only; no new deps).
3. **Mid-run flush of the window log to disk** (the base driver writes only at the end).
4. The driver must record this document's protocol ID and the git SHA in its output JSON, so
   the result is attributable to the pre-registered criteria (Rule 2 hygiene).

## 7. What this pilot is NOT

- It is **not** a Rule 18 finish-line attempt. Rule 18's binding criteria (Ascent.md §2) are
  defined on a live `sim_loop` run with the prediction-depth income metric, Gates A∧B∧C. This
  diagnostic cannot express them at any tick count.
- It is **not** a search for a better plateau band. The band [87%, 93%] is fixed by the 20k
  record and may not be re-fit after S1 data arrives.
- It produces exactly one bit of scientific value: *which of H0/H1/H2 holds* — bought for
  ≤ 6 h instead of 18 h.
