# Final Pivot Decision

**Date:** 2026-08-05
**Status:** BINDING DECISION — pending path approval. Design-doc-only next step; no implementation, no PR, no merge until explicitly approved.
**Supersedes:** `Docs/Decision/Pivot_Decision.md` (interim; recommended Option 3 neuroevolution — that option has now been executed and falsified by Exp 3; see §1.5).
**Evidence base:** `experiments/exp101_*`, `experiments/exp101_option_b_results/exp102_*`, `experiments/exp103_results/`, `experiments/exp103b_results/`, `experiments/exp3_neuroevolution_results/`.

---

## 1. Experiment Summary and Verdicts

Five pre-registered mechanisms were tested against in-lifetime learning on the
SNN-on-RAM substrate. The mechanism changed every time; the outcome did not.

| Exp | Protocol | Mechanism | Binding result | Verdict |
|---|---|---|---|---|
| 101 | `EXP101_RSTDP_SURPRISE_REWARD_v1` (pre-reg 2026-08-04) | R-STDP, reward = surprise × efficiency | reward = 0, eligible = 0, weight drift = 0 at every diagnostic checkpoint through 2000t (`exp101_option_b_learner_s0_2000t_diag.json`) | **NULL — self-silencing** |
| 102 | `EXP102_STDP_TARGET_STATIC_PROBE_v1` (pre-reg 2026-08-04) | STDP_TARGET: direct per-bit directional error, no reward gate | learner Δ (late−early) = **−11.1pp** mean vs NOLEARN **−11.3pp** (bar: learner Δ > +2pp AND > NOLEARN + 3pp) | **NULL** |
| 103 | `EXP103_RESERVOIR_READOUT_v1` (pre-reg 2026-08-05) | Shared fixed reservoir + online LMS readout | late gap vs NOLEARN **+10.35pp** (criterion 2 PASS) but in-run Δ **+0.06pp** (criterion 1 FAIL, bar +2pp) | **STATIC ONLY** — `RESERVOIR_HELPS_STATICALLY_BUT_INRUN_LEARNING_WEAK` |
| 103b | `EXP103B_PER_ORG_RESERVOIR_v1` (pre-reg 2026-08-05) | Per-organism reservoir + per-organism readout over non-stationary input | late gap vs NOLEARN **+21.31pp** (larger static advantage) but in-run Δ **−0.02pp** (flat/negative) | **NULL_OR_DEGRADED** — static only |
| 3 | `EXP3_NEUROEVOLUTION_v1` (pre-reg 2026-08-05) | Cross-generation evolution of fixed weights (abandons in-lifetime updates) | fitness Δ **−30.8% / −29.3% / −29.4%** (s0/s2/s3), s1 undefined (extinct at gen 0); extinction cycles in all 4 seeds; 0/4 seeds confirmed | **NULL — extinction cycles; `MECHANISM NOT CONFIRMED`** |

### 1.1 Exp 101 — R-STDP: self-silencing

Hypothesis: three-factor R-STDP with reward = surprise × efficiency enables
time-improving learning. Measured diagnostic (binding): the reward signal
collapses to exactly zero in the static world, eligibility count is zero, and
mean absolute weight drift is zero at every one of ten checkpoints through
tick 2000. Not weak — *identically* zero. Every deviation-from-baseline
reward structure is now falsified at mechanism resolution.

### 1.2 Exp 102 — STDP_TARGET: null

The last Hebbian-class candidate with a directional per-bit error signal that
does not depend on a deviation gate. Per-seed learner Δ (late−early, 20000t):
**−16.7, −4.0, −15.4, −8.3pp** (seeds 0–3). Matched NOLEARN: **−12.7, −4.1,
−14.9, −13.4pp**. Both arms decline together — the decline is environmental
drift, and the mechanism provides no separable advantage (mean paired gap
≈ +0.2pp against a pre-registered bar of +3pp). Hebbian-class plasticity on
this substrate is closed at every locus tested (cf. Exp 96–98 tuning/gating
closures, Result.md).

### 1.3 Exp 103 — shared reservoir: static only

The reservoir + supervised readout architecture works *statically*: learner
late accuracy 78.08% vs NOLEARN 67.73%, a **+10.35pp** baked-in advantage
(criterion 2 PASS, no monotonic decline — criterion 3 PASS). But the binding
in-run criterion failed: Δ late−early = **+0.06pp** against the +2pp bar.
Diagnosis (recorded in `Per_Organism_Reservoir_Design.md` §0): one shared
input stream → the readout saturates at the best linear predictor of that
stream within the first window and stops improving.

### 1.4 Exp 103b — per-organism reservoir: static only, larger margin

The registered fix for 103's saturation (per-organism readouts over
non-stationary, saccade-driven input — error predicted to stay > 0 and keep
adapting). Result: the static advantage *doubled* (**+21.31pp**, late 78.66%
vs 57.35%) while in-run learning stayed flat-to-negative (**−0.02pp**).
The non-stationarity hypothesis failed: even a continuously-refreshed input
stream produces no measurable in-run improvement. Verdict recorded:
`NULL_OR_DEGRADED`.

### 1.5 Exp 3 — neuroevolution: extinction cycles

The interim `Pivot_Decision.md` recommendation (Option 3) — replace
in-lifetime learning with cross-generation evolution of fixed weights — was
executed as registered. 100k ticks × 4 seeds, pre-registered criteria S1
(fitness delta > +0.1), S2 (diversity ratio ≥ 0.1), S3 (no monotonic
decline), ALL seeds × ALL criteria required. Result: fitness Δ **−30.78%**
(s0), undefined (s1, population extinct at generation 0), **−29.35%** (s2),
**−29.39%** (s3). Extinction cycles in every seed: s0 went extinct for **7
consecutive generations** (gens 2–8) before a late recolonization burst; s2
and s3 extinct at gens 2–3; s1 extinct at gens 0 and 4–5. 0/4 seeds
confirmed. Final verdict recorded: *"MECHANISM NOT CONFIRMED — honest
null/pivot per the registered failure clause."* The last option compatible
with the existing physics and evolution machinery is closed.

---

## 2. Binding Conclusion

**SNN-on-RAM is falsified as a substrate for in-lifetime learning.**

This is now established across five mechanism classes, not one: reward-modulated
Hebbian (101), direct-error Hebbian (102), fixed-reservoir + supervised
readout at shared (103) and per-organism (103b) granularity, and
cross-generation evolution of fixed weights (3). Per Rule 18's escape clause —
*"if corrected, task-matched learning cannot beat ablation, change the
substrate hypothesis rather than adding economy levers"* — the correct move is
a substrate-hypothesis change, not a sixth mechanism on the same physics.

Two qualifications keep the conclusion precise and honest:

1. **The falsification is specific to in-lifetime adaptation.** Exp 103/103b
   prove the substrate can *hold* a learned representation (+10.35pp / +21.31pp
   static advantage, no monotonic decline). It is a memory-capable substrate
   that cannot *acquire* capability during life.
2. **The missing ingredient in every null is credit assignment**, in two
   confirmed forms: the silent-synapse recruitment barrier (credit never
   reaches needed-but-silent weights) and reward/eligibility collapse
   (directionless or zero signals). Both are structural properties of local,
   spike-gated update rules — not of any one tuning.

---

## 3. The Two Remaining Paths

### PATH A — Option 1: Differentiable Plasticity

Replace Hebbian/reservoir learning with gradient-based credit assignment.

**Architecture.**
- Requires an **autograd-compatible substrate** (JAX or PyTorch backend). The
  current event-driven numba kernel cannot host gradient flow; a new backend
  is mandatory, not optional.
- Candidate gradient mechanisms, in decreasing physical fidelity, increasing
  implementation speed:
  1. **Surrogate-gradient SNN** (BPTT with surrogate derivatives) — keeps
     spiking physics; most faithful to the original vision; highest cost.
  2. **Rate-coded reference backend** — fastest decisive YES/NO on whether
     gradient-based in-lifetime learning beats ablation on this task family;
     risks becoming the product.
  3. **Local gradient approximations** (e-prop / feedback alignment /
     predictive-coding-style local rules) — the Rule-21-plausible middle
     ground for a later physically-grounded port back toward event-driven
     hardware.
- **Rule 21 accounting designed in from day one:** charge measured host work
  (FLOPs, memory traffic, wall time) for forward *and* backward passes;
  no invented points. **Rule 17 provenance table** for every new constant —
  learning rate, optimizer state, window sizes must be H-derived, E-encoded
  (genome-inherited, mutated through inheritance), or deleted. No tuned
  constants. The optimizer zoo is a tuning magnet and is out of scope.
- Parity/determinism harness must be rebuilt for the new backend before any
  measured row (Session-18 instrument-inheritance rule applies).

**Risks.**
1. Major architecture change — certified determinism, cost accounting, and
   the replication harness all require re-certification.
2. Backprop's non-local weight transport is physically suspect under the
   20W / event-driven thesis (candidate 1 and 3 mitigate; candidate 2
   concedes it). The "port back to physics" step may fail, leaving a
   conventional NN project wearing a GENESIS badge.
3. Rule 21 accounting risk: user-flagged. Mitigated by measured-cost charging
   and the Rule 17 provenance table, but this is the path's top review item.
4. May re-confirm the *task* rather than the substrate as the blocker — in
   which case the money buys a decisive answer, not a product.

**Potential.** Gradient descent is the one credit-assignment mechanism with
no silent-synapse barrier (dense gradient reaches every weight) and no
self-silencing (directional error independent of any baseline). It is the
only remaining path that preserves the founding in-lifetime-learning vision,
and it directly optimizes the exact metric the falsifying probes measured.

**Timeline (sessions).** 1 design doc → 2–3 prototype backend + both-passes
cost accounting + parity harness → 1 pre-registered feasibility probe →
binding verdict in **~5–7 sessions**. No tuning axis (Rule 17): one probe,
pass or kill.

### PATH B — Different Substrate, or Acceptance

SNN-on-RAM may be fundamentally unsuitable; leave the physics.

**Options.**
- **B1 — Simpler rule-based systems.** Honest engineered behavior (reflex /
  symbolic rules), dropping the learning claim entirely. Fast, but abandons
  the vision without answering the founding question.
- **B2 — A different neural substrate wholesale** (e.g., hyperdimensional/VSA
  computing, predictive-coding networks with genuinely local learning,
  CAM-augmented learned routing per Rule 21's binding working-memory
  constraint). Restarts the design → pre-register → falsify loop from zero,
  with unknown duration and no evidence the next substrate fares better.
- **B3 — Acceptance.** Re-scope GENESIS as a physically-grounded evolutionary-
  persistence substrate with **no in-lifetime-learning claim**. Publish the
  five pre-registered nulls as the result; downgrade the Rule-18-A/B finish
  line; correct README/ARD claims. Requires no new machinery and converts the
  nulls into an auditable negative result — which this repository's Rule 20 /
  REVIEW_PACK culture already treats as a first-class outcome.

**Risks.**
1. B1/B2 pivot away from the original SNN vision; B2's timeline is unbounded
   and its priors are no better than the last one's were.
2. B3 is an honest acknowledgment of substrate limits at real
   reputational/vision cost — but it is a terminus, not a failure state.
3. Choosing B first leaves the strongest known credit-assignment method
   forever untested on this problem — the five nulls falsify Hebbian /
   reservoir / evolution on this substrate, **not** gradient learning.

**Timeline.** B3: **1–2 sessions** (acceptance doc + claim downgrades).
B1/B2: unknown, ≥ one full design cycle each before the first measured row.

---

## 4. Recommendation

**PATH A — staged, gated, and pre-committed to PATH B3 on failure.**

Reasoning:

1. **Only one hypothesis class remains that targets the founding goal.** Every
   non-gradient mechanism — including the mechanism-independent fallback of
   cross-generation evolution — has now been pre-registered, executed, and
   falsified on this substrate. Differentiable plasticity is the sole untested
   path still aimed at in-lifetime learning.
2. **The failure mode points at it.** All five nulls share one root cause:
   credit assignment (silent-synapse barrier + signal collapse). Exp 103/103b
   additionally prove the task family is learnable to ~78–79% by an
   error-driven method and the substrate can *retain* structure — what fails
   is *in-run acquisition*. Gradient descent is the strongest existing
   instrument for that precise question, and a Rule-18-B-decisive one.
3. **The cost is bounded by discipline.** One pre-registered probe, one
   matched ablation, fresh seeds, no tuning axis (Rule 17), measured-cost
   accounting (Rule 21). If it fails, **PATH B3 executes immediately with no
   further experiments** — this sentence is the kill criterion, registered in
   advance.
4. **PATH B remains fully available.** B3's cost (1–2 sessions) does not grow
   after the PATH A probe; taking the probe first forfeits nothing except the
   small bounded cost of the probe itself, and skipping it leaves the
   project's central question permanently open.

If PATH A is rejected on architecture-risk grounds, the recommended fallback
is **B3 (acceptance + honest re-scoping)**, not B1/B2: no further
substrate-hopping without a pre-registered reason to expect a different
outcome.

---

## 5. Next Steps (design doc only — pending approval)

No engine code, no experiments, no PR, no merge until explicitly approved. On
approval of PATH A:

1. **Author `Docs/Architecture/Option1_Differentiable_Plasticity_Design.md`**
   (design only): backend selection (JAX vs PyTorch), gradient mechanism
   choice (§3 candidates), both-passes Rule-21 measured-cost model, Rule-17
   provenance table for every new constant, parity/determinism harness plan,
   and the migration boundary (isolated module; certified engine paths
   untouched).
2. **Pre-register the feasibility probe** (Exp 2xx protocol doc) before any
   implementation: gradient-learner arm vs matched no-learn ablation, fresh
   seeds, binding pass/fail metrics, and the explicit PATH-B3 trigger as the
   registered failure clause.
3. Only then: implement the prototype behind the isolated boundary; run the
   probe; publish the result either way per Rule 20.
4. On probe failure: execute PATH B3 —
   `Docs/Decision/Substrate_Limits_Acceptance.md`, README/ARD claim
   corrections, Rule-18-A/B finish-line downgrade, and the five-null evidence
   trail preserved as the published negative result.

---

*Recorded 2026-08-05 on branch `arena/019fd211-genesis`. This document states
a decision and a gated plan; it authorizes no code. Awaiting explicit path
approval.*
