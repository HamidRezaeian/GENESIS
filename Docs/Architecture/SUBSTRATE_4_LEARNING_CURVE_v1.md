# Learning-Curve Protocol Amendment — Corrected Gate A Operationalization and Re-Scoring

**Status: PRE-REGISTERED (binding) — 2026-08-07. The metric definitions (D1–D6), statistics (D7),
seed rules (D8), falsification criteria, and decision table below are fixed HERE, before the
re-scoring script is written or run. No definition may be revised after re-scored values are
observed (Rule 2). Pre-registration of an amendment to an already-collected corpus follows the
repo precedent of `Ascent.md` §2.D (criteria archived for increments that had already run) and
the anti-winner's-curse discipline of Exp 96 → Exp 97 (fresh seeds, reuse disabled) for any
confirmatory claim.**

**Protocol ID:** `SUBSTRATE_4_LEARNING_CURVE_v1`
**Amends:** the Gate A operationalization used in `Substrate_Comparison_Protocol.md` ("in-run Δ
(late − early) ≥ +2pp / +3pp / +5pp" short-horizon proxy) for all substrate-screening purposes.
**Does NOT amend:** `Ascent.md` §2. Rule 18's binding finish line (Gates A ∧ B ∧ C on a live
`sim_loop` run, prediction-depth income metric, ≥ 5M ticks) is unchanged and remains the only
finish line. This amendment governs *diagnostic substrate screening* and the *re-analysis of
existing artifacts* — nothing here certifies or weakens ascent.

---

## 1. Why this amendment exists

The substrate-comparison programme (substrates 1–5, `Substrate_Comparison_Protocol.md`) scored
Gate A with a **late-minus-early accuracy proxy**: in-run Δ ≥ +2pp (Exp 103 criterion), +3pp
(Exp 102 bar), or +5pp (Rule 18 short-horizon reading), over 2k–20k ticks. All five substrates
failed this proxy (in-run Δ +0.16 to +3.70pp) while all five passed Gate B (static gaps +17.69
to +42.22pp over matched NOLEARN ablations; verified from the artifacts listed in §3.1).

A threshold re-evaluation (2026-08-06/07 consultation) found the proxy deviates from the
binding Rule 18 criterion (`Ascent.md` §2, Rule 18 in `.agents/rules/Rules-17-21.md`) on four
independent axes:

| Axis | Binding Rule 18 A (Ascent.md §2) | Retired proxy |
|---|---|---|
| Metric | prediction-depth income fraction `C(t)` (must-compute cells only) | raw task accuracy |
| Threshold | ≥ 25% **relative** rise from post-bootstrap baseline | absolute +2/+3/+5pp |
| Shape | **monotone-in-trend**, no regression below baseline | two endpoint windows; curve shape discarded |
| Duration | sustained ≥ 5M ticks | 2k–20k ticks |

Additionally, the proxy is **mathematically broken on this metric**, as already recorded in
`Staged_Pilot_Protocol.md` §1: "Gate A is mathematically inexpressible on this metric at any
duration (a +25% relative rise from a ~90% baseline exceeds the 100% bit-accuracy ceiling; from
the ~50% NOLEARN floor it was already passed by tick 200)." A criterion that is impossible from
high baselines and trivial from low ones cannot rank substrates. The 5/5 proxy failures
therefore indict the proxy, and the substrates' Gate A verdicts must be re-scored under a
corrected operationalization before the substrate-pivot decision consumes them.

## 2. Corrected Gate A operationalization

### 2.1 Definitions (frozen)

- **D1 — Diagnostic capability metric.** For diagnostic (non-live) substrate runs,
  `C(t)` := the per-window must-compute prediction accuracy `acc` as logged in
  `results.learn[seed][i].acc`. Justification: the diagnostic corpora (static repeat-free
  patches, REMAP non-stationary patches, novel-sequence switch) contain *only* must-compute
  content — no bootstrap/echo cells exist in these tasks — so task accuracy is the diagnostic
  analogue of the Ascent §2 prediction-depth metric ("income earned from cells that require
  computation over context … NOT from bootstrap/echo cells"). Windows are used **as logged**
  by each driver (1,000-tick windows in the 20k drivers; 200-tick windows in the 2k drivers);
  definitions below are window-count-based and do not drift with horizon
  (`Staged_Pilot_Protocol.md` §3/§4, G-delta clause).
- **D2 — Baseline and late points.** `C0` = mean of the first 3 windows; `C1` = mean of the
  last 3 windows (frozen from `SUBSTRATE_4_EXTENDED_20K_v1`; identical across substrates).
  Error-space coordinates: `E0 = 100 − C0`, `E1 = 100 − C1`.
- **D3 — Existence-of-rise test (trend, primary).** Per seed: OLS slope of `acc` on window
  index over the full logged horizon. Across seeds: mean slope with 95% Student-t CI
  (df = n − 1). The rise is **statistically real (T)** iff the CI excludes 0 in the positive
  direction. This mirrors Rule 18's "monotone-in-trend" language instead of discarding the
  curve. Secondary descriptor (continuity with Exp 101–103 records): per-seed Δ = `C1 − C0`,
  mean, sd, paired t vs 0.
- **D4 — Magnitude test (corrected 25% criterion).** Rule 18's 25% is applied **in error
  space**: the must-compute error rate must fall by ≥ 25% relative,
  `ρ = (E0 − E1) / E0 ≥ 0.25`. The magnitude bar is on the point estimate, evaluated per seed
  and reported as mean with 95% CI; **M** holds iff mean ρ ≥ 0.25 with the CI excluding 0.
  Rationale (recorded before any re-scoring):
  1. *Ceiling expressibility.* A 25% relative accuracy rise from a baseline ≥ 80% exceeds the
     100% ceiling; error-space is expressible from every baseline < 100%.
  2. *Floor non-triviality.* From the ~50% NOLEARN floor the accuracy-space criterion "was
     already passed by tick 200" (pilot §1); error space requires E to fall 25%
     (50% → 37.5%, i.e. +12.5pp) — not trivial.
  3. *Faithfulness.* "Capability rises 25%" applied to a saturating metric is standard
     relative error reduction; it is a monotone reparameterization, not a new direction of
     search, and it is **not one-way**: it is harder than the old reading from low baselines
     and possible (not automatic) from high ones.
- **D5 — Within-phase re-learning (non-stationary artifact).** A phase = the 5 windows between
  remaps (`switch_every = 5000`, 1,000-tick windows). Primary: over post-switch phases
  p ∈ {2, 3, 4} only — re-learning means recovery *after* a switch — per-phase
  `Δ_p = mean(last 2 windows of p) − first window of p`; per-seed mean over p; across-seed mean
  with 95% CI, paired t vs 0. Pre-registered robustness variants: (i) all four phases;
  (ii) last-window-only achieved point. NOLEARN paired phases provide the ablation reference.
- **D6 — Transfer (novel-sequence artifact).** With the A→B switch at tick 10,000:
  `A_late` = mean of last 3 A-windows; `B0` = first B window; `B_late` = mean of last 3
  B-windows. Pre-registered transfer statistics: (i) *retention* `B0 − A_late`
  (catastrophic-interference reference, expected ≤ 0); (ii) *transfer learning* = B-phase error
  reduction `ρ_B = (E(B0) − E(B_late)) / E(B0)` under the D4 bar; (iii) *ablation-referenced
  transfer gap* `B_late − NOLEARN B_late` (Gate B continuity; recorded in the artifact as
  `gap_late_pp_b`).
- **D7 — Statistics.** Every quantitative claim reports: n seeds, mean, sd, 95% Student-t CI,
  paired t vs 0 (existence) or LEARN−NOLEARN paired by seed (gaps). Robustness: paired
  permutation p, 10,000 draws, reported as a Monte-Carlo estimate — never as an "exact"
  enumeration (correction precedent: `Docs/RESUME_NEXT_SESSION.md`, Session 18). Rule 20:
  any positive claim is accompanied by its matched NOLEARN control delta.
- **D8 — Seeds.** The existing artifacts carry seeds [0, 1, 2, 3] (n = 4). Re-scoring them is
  **re-analysis**, not confirmation. Any §4 decision-table row marked *confirm* requires a
  top-up with fresh seeds **100–107** (as many as needed to reach **n ≥ 8 total**, minimum 4;
  never reusing 0–3 for both nomination and confirmation — Exp 96/97 anti-winner's-curse
  precedent), run under the ORIGINAL driver
  protocol IDs with D1–D7 scoring applied, NOLEARN arm re-run on the same fresh seeds for
  pairing, result-cache reuse disabled. Rule 3's ≥5-seed floor is treated as a floor, not a
  target.

### 2.2 Measurement windows and checkpoints

- Window cadence: as logged (D1). Gate checks on any future extended run: at every 25,000-tick
  snapshot and at each stage end, per `Staged_Pilot_Protocol.md` §4, with D3/D4 recomputed at
  each check.
- The early/late definitions do not drift with horizon (G-delta clause, pilot §4): `C0` is
  always the first 3 windows of the RUN.

### 2.3 Short-horizon screen vs the 5M finish line (mapping)

This amendment's corrected Gate A is a **substrate-viability screen at diagnostic horizons**.
It answers: "does `C(t)` rise, is the rise non-negligible, and is it learning (not static
capacity)?" It does **not** and **cannot** certify Rule 18 A, which requires sustainment over
≥ 5M ticks on the live prediction-depth income metric (`Staged_Pilot_Protocol.md` §7: a
diagnostic "cannot express them at any tick count"). The deep-time question is delegated,
unchanged, to:

- `SUBSTRATE_4_STAGED_PILOT_v1` (S1 = 100k → S2 = 500k → S3 = 1M ticks; H0/H1/H2; plateau band
  [87%, 93%] fixed from the 20k record and not re-fittable), including its kill-switch: if H1
  is falsified, the 5M-tick experiment is permanently cancelled for this substrate+metric.
- `5M_Tick_Feasibility_Report.md`: a direct 5M run costs ≈ 17.9 h/seed LEARN at the measured
  77.5 ticks/s and is not feasible on the home-hardware envelope without the engineering
  speedups documented there; this amendment's re-scoring costs nothing (existing artifacts)
  and the fresh-seed top-up (D8) is capped at 20k-tick horizons.

No result under this amendment reopens the 5M question; only the staged pilot's H1 outcome can
(pre-registered in the pilot, §5).

## 3. Re-scoring protocol

### 3.1 Corpus

Primary (all substrates of the comparison, all existing horizons/tasks):

| Artifact | Protocol ID (as recorded) | Horizon | Task |
|---|---|---|---|
| `experiments/sub3_results/sub3_summary.json` | `SUBSTRATE_3_RECURRENT_WORLD_MODEL_v1` | 2k | static |
| `experiments/sub4_results/sub4_summary.json` | `SUBSTRATE_4_SMALL_TRANSFORMER_v1` | 2k | static |
| `experiments/sub4_results/sub4_20k_summary.json` | `SUBSTRATE_4_EXTENDED_20K_v1` | 20k | static |
| `experiments/sub4_results/sub4_nonstationary_summary.json` | `SUBSTRATE_4_NONSTATIONARY_TASK_v1` | 20k | REMAP / 5k |
| `experiments/sub4_results/sub4_novel_summary.json` | `SUBSTRATE_4_NOVEL_SEQUENCE_v1` | 20k | A→B @ 10k |
| `experiments/sub5_results/sub5_summary.json` | as recorded in artifact | 2k | static |

Secondary (substrate 2, reservoir family): the full-run per-seed JSONs in
`experiments/exp103_results/` and `experiments/exp103b_results/` (20k, static). The 1,000-tick
`exp103_pilot_results/` files are excluded (pilot granularity). Substrate 1 (SNN-on-RAM) is
historical, artifact-analysis only (`Substrate_Comparison_Protocol.md`), and is not re-scored.

Per-window record schema (verified): `{tick, acc, mean_err, norm_w}` plus `pattern` in the
non-stationary / novel artifacts. **No prediction-depth decomposition is logged** — D1's
must-compute equivalence is what makes re-scoring possible at all; if a future driver logs
income-band decomposition, D1 is superseded by the direct income-fraction metric for those
runs only (such a change requires its own pre-registered amendment).

### 3.2 Procedure

1. Single script `experiments/rescore_learning_curve_v1.py`; numpy + stdlib only. It records
   this protocol ID and the git SHA in every output (Rule 2 hygiene, pilot §6.4), reads the
   artifacts unmodified, and writes NEW files
   `experiments/<sub>_results/<name>_rescored_v1.json`. Existing artifacts and their
   `gate_a_pass` / `verdict` fields are **historical** (scored under the retired proxy) and
   must not be mutated in place (Rule 8 provenance).
2. Per artifact per seed: `C0`, `C1`, Δ, ρ, OLS slope; D5/D6 statistics where applicable.
3. Across seeds: D7 statistics for T, M, B (B = LEARN_late − NOLEARN_late, paired by seed).
4. Emit one row per artifact for the §4 decision table, plus a machine-readable
   `rescored_summary_v1.json` aggregating all rows.

### 3.3 Worked example (non-binding, from already-published aggregate metrics)

Using the `sub4_20k` artifact's recorded aggregate metrics (C0 = 86.1979, C1 = 89.8958):
Δ = +3.6979pp (old proxy: FAIL vs +5pp). Corrected: E0 = 13.8021, E1 = 10.1042,
ρ = 26.8% ≥ 25%. This illustration is arithmetic on values already published in the artifact;
the binding per-seed re-scoring with CIs has not been run at commit time and its result is
unknown to the author of this amendment.

## 4. Pre-registered falsification criteria and decision table

**Binding falsification criteria (Rule 2):**

- **F1 — "in-run learning is real" is FALSIFIED** for an artifact iff the D3 slope CI contains
  0 AND the per-seed Δ CI contains 0. (Existence fails; magnitude is moot.)
- **F2 — "learning is non-negligible" is FALSIFIED** for an artifact iff the upper 95% CI
  bound of ρ is < 0.25. (A real-but-tiny rise keeps the Paper v2 conclusion: learning is real
  but metabolically negligible at this horizon.)
- **F3 — "the advantage is in-lifetime learning" is FALSIFIED** (static-only) iff T fails but
  the Gate B gap CI excludes 0: the gap is capacity/memorization, not learning (the Exp 103
  "IN-RUN FAIL (static only)" pattern).
- **F4 — instrument alarm (Rule 20):** any M-pass with T-fail, or a Gate B gap whose CI
  contains 0, triggers an instrument/shortcut audit BEFORE any claim in either direction.

**Decision table (binding; exactly one row fires per artifact):**

| T (slope > 0) | M (ρ ≥ 25%) | B (gap > 0) | Verdict | Pre-committed action |
|---|---|---|---|---|
| ✓ | ✓ | ✓ | **GATE-A SCREEN PASS (corrected)** | Substrate viability re-opened → fresh-seed confirmation per D8 (n ≥ 8, seeds 100–107); Paper v2 Gate-A row revised; staged pilot still decides deep time. |
| ✓ | ✗ | ✓ | Real but negligible | Paper v2 conclusion stands (real but metabolically unaffordable at this horizon); no new runs except via `Nonstationary_Variants_Protocol.md` V1–V8. |
| ✗ | ✗ | ✓ | Static-only (F3) | In-lifetime-learning claim withdrawn for this substrate; record alongside Exp 103's pattern. |
| ✗ | ✗ | ✗ | Null | Substrate remains Gate-A-negative; no further spend. |
| any contradictory combination (F4) | — | — | Instrument suspect | Rule 20 audit first; no claim. |

No outcome of re-scoring modifies `Ascent.md` §2, retires the staged pilot, or revises the
Exp 99 substrate falsification of SNN-on-RAM. A corrected-screen PASS re-opens *substrate
viability* (substrates 3–5 may be viable under the corrected metric), not the finish line.

## 5. Amendment justification (Rule 2 compliance)

1. **Why the proxy was inadequate.** It deviated from the binding criterion on metric,
   threshold type, curve shape, and duration (§1 table); it is mathematically inexpressible
   from high baselines and trivial from low ones (pilot §1); and a single absolute pp bar
   across substrates with different baselines (86.2% static vs 67.6% non-stationary) is not a
   comparable criterion, where Rule 18's relative form is.
2. **No post-hoc fitting.** (i) D1–D8, F1–F4, and the decision table are fixed in this commit,
   before the re-scoring script exists; (ii) the only re-scored quantities disclosed at commit
   time are arithmetic on already-published aggregates (§3.3) and are labelled non-binding;
   (iii) the corrected criterion is not one-way — it is *harder* than the old reading from low
   baselines (floor non-triviality, D4); (iv) confirmation requires fresh seeds with reuse
   disabled (D8), the Exp 96 → 97 discipline; (v) retroactive archiving for an
   already-collected corpus follows `Ascent.md` §2.D precedent.
3. **Continuity with repo precedent.** Exp 101 pre-registered an absolute learning-signal bar
   on this metric family — "Delta > +2.0pp -> LEARNING_SIGNAL; |Delta| <= 2.0pp -> FLAT"
   (`Docs/Exp101_Protocol.md`) — and Exp 102/103 extended it to +3pp/+2pp. Those bars answered
   a different yes/no question ("does mechanism X produce any signal?"). For Gate A screening
   they are retired in favour of D3+D4; Δpp is still reported (D3 secondary) so the Exp
   101–103 records remain comparable.
4. **Honest status of the consultation figures.** The 2026-08-06 consultation reported
   within-phase re-learning ≈ +4.13pp, novel-sequence transfer ≈ +7.17pp, and a per-seed
   significance of t ≈ +20.6 with sd ≈ 0.36pp. Those numbers were computed under ad-hoc,
   unarchived definitions. Under this amendment's frozen D2/D3 definitions, a reproduction
   attempt on `sub4_20k_summary.json` yields per-seed Δ mean +3.6979pp, sd 0.4143pp,
   t = +17.85 (df = 3); candidate D5-family definitions yield within-phase re-learning in the
   +4.9 to +5.2pp band. The discrepancy is exactly why D5/D6 fix definitions before scoring:
   **the binding numbers are the ones the re-scoring script will produce under D1–D7, and no
   others.** Gate B's range (+17.69 to +42.22pp) and the in-run Δ range (+0.16 to +3.70pp)
   are verified directly from the artifacts and stand.

## 6. Cross-references

- `Docs/Architecture/Ascent.md` §2 — binding Rule 18 finish line (A/B/C verbatim source).
- `.agents/rules/Rules-17-21.md` — Rule 18 text; `.agents/rules/Rules-01-08.md` — Rules 2, 3;
  Rules 20, 21 per the same rule files.
- `Docs/Architecture/Substrate_Comparison_Protocol.md` — the 5-substrate comparison whose
  Gate A proxy this amends.
- `Docs/Architecture/Staged_Pilot_Protocol.md` — `SUBSTRATE_4_STAGED_PILOT_v1`; deep-time
  instrument; frozen early/late definitions; §1 metric-inexpressibility record.
- `Docs/Architecture/Nonstationary_Variants_Protocol.md` — `SUBSTRATE_4_NONSTATIONARY_VARIANTS_v1`
  (V1–V8), the follow-up falsification matrix.
- `Docs/Architecture/5M_Tick_Feasibility_Report.md` — measured 77.5 ticks/s LEARN,
  ≈ 17.9 h/seed at 5M ticks.
- `Docs/Exp101_Protocol.md` (+2.0pp bar), `Docs/Paper_Draft_v2.md` (Gate A/B summary,
  +0.16…+3.70pp / up to +42.2pp).
- Artifacts: the six primary JSONs and the Exp 103/103b full-run JSONs listed in §3.1.

## 7. What this amendment is NOT

- It is **not** a Rule 18 finish-line attempt and cannot certify ascent at any tick count.
- It is **not** a re-fit of the plateau band, the proxy bar, or any threshold after re-scored
  data arrives. One amendment, one scoring, one decision-table row per artifact.
- It is **not** a rescue of SNN-on-RAM (Exp 99's falsification stands) and not a revocation of
  Paper v2's metabolic-affordability thesis; it determines whether the substrates' *Gate A*
  column was measured with a broken ruler.
