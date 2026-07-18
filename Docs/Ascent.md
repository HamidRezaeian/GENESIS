# Ascent — The Pre-Registered Finish Line and Strategy Review

**Status: strategic pivot (2026-07-16). This document closes the 29-experiment "design loop" by
committing, in advance, to (a) what "ascent" quantitatively MEANS, (b) the falsifiable finish line that
ends the search, and (c) an adversarial review of whether the strategy pursued so far can ever reach the
goal. It is binding: experiments are now judged against the criteria fixed HERE, not against a moving
"not yet."**

Read this with `Rules.md` (esp. Rules 6, 9, 14, 17) and `Result.md` (the Exp 1–29 record).

---

## 1. Why this document exists (the loop diagnosis)

Experiments 13–29 form a single pattern: **build a lever → hit a new wall → build the next lever → hit
the next wall.** DEPLETE → STIGMERGY → SUPER-RENT → PERSIST → LEASE → CANVAS … the engine accumulated
mechanics while the goal ("does capability RISE over deep time?") stayed exactly as far away. Two
structural causes, both process failures rather than engine failures:

1. **"Ascent" was only ever defined NEGATIVELY.** Every experiment asked "did it ascend?" and answered
   "no, because X." There was never a *pre-registered, quantitative* threshold whose crossing would mean
   "done." Without a finish line, every result is a "not yet," and the loop cannot terminate by
   construction.

2. **The search optimised the ECONOMY, not the MIND.** All 29 experiments reshaped the energy economy
   (what pays, how scarce, who owns what). None validated the project's *load-bearing assumption*: that a
   GENESIS organism's brain **learns within its lifetime** — that STDP + Lamarckian inheritance actually
   improve survival over a non-learning control. `Result.md`'s own Open Questions admits this was never
   measured. If in-lifetime learning does not work, **no economy can produce ascent**, because there is
   no learning engine for selection to amplify — we would be tuning the incentive structure of a system
   that cannot get smarter regardless.

The goal (`Rules.md` Rule 6) is **AGI: genuine in-lifetime learning, reasoning, and long-term memory, at
~20 W biological efficiency** — a real mind, not a survivable "weed." That reframes the whole search:
**the primary variable is learning capability, and the economy is only the pressure that selects for it.**
We have spent 29 experiments on the pressure and zero on verifying the thing being pressured.

---

## 2. The pre-registered definition of ASCENT (binding)

Ascent is **a sustained, non-regressing rise in modelled capability over deep time, achieved emergently
(never wired into selection, Rules 9/14).** It is declared **only** when ALL THREE of the following
observation-only criteria hold simultaneously on a single live `sim_loop` run, each measured by a probe
that never feeds back into who lives/dies/reproduces:

- **A. Capability rises (primary).** A capability metric `C(t)` shows a **monotone-in-trend increase of
  ≥ 25 % from its post-bootstrap baseline, sustained over ≥ 5 M ticks without regressing below the
  baseline.** `C(t)` is the **prediction-depth** metric: the fraction of reading/authoring income earned
  from cells that require *computation over context* (the carry/arithmetic frontier bands of `00_Ascent`,
  or authored must-compute content), NOT from bootstrap/echo cells. Rationale: this is the closest
  observable to "the brain got better at a hard cognitive task," and it cannot be farmed by a reflex.

- **B. Learning is load-bearing (mechanistic).** A **learning-ablation control** (same genomes, STDP
  disabled → `a_plus = a_minus = 0`) must **survive worse or comprehend worse** than the learning-enabled
  run by a clear margin. If ablating learning changes nothing, capability is genetic-only and "ascent" is
  just evolution of fixed reflexes — not the in-lifetime learning Rule 6 requires.

- **C. Efficiency holds or improves (Rule 6/7).** Universe N (total neurons/synapses) per unit of
  capability `C(t)` must **not balloon** — capability must rise without a proportional brain-size
  explosion, i.e. the colony gets smarter *per byte/cycle*, honouring the 20 W paradigm. Measured as
  `C(t) / footprint`, must be non-decreasing over the same window.

**Finish line:** the first live run where A ∧ B ∧ C hold is the demonstration of ascent, and the
economy-shaping search STOPS — the remaining work becomes scaling and characterisation, not new levers.

**Kill criterion (equally binding, prevents an infinite search):** if, after the **learning-first
programme (§4)** is complete, criterion **B still fails** — i.e. in-lifetime learning is shown to be
non-load-bearing and cannot be made load-bearing on this substrate — then the current SNN-on-RAM
substrate is **falsified as an AGI substrate** and the project must change substrate hypotheses, not add
another economy lever. This is the escape hatch the loop never had.

---

## 3. Adversarial review of the strategy so far

Steel-manning the critique that "this whole approach cannot reach AGI":

- **Verdict on the economy search (13–29): correct in DIRECTION, premature in ORDER.** Scarcity /
  division-of-labour / stigmergy are genuinely the right *pressures* for open-ended selection (Rule 9).
  But applying pressure to a mind whose learning is unvalidated is optimising the loss function of an
  untrained network — you can shape incentives forever and see only "sustains, never ascends," because
  the substrate has no validated capacity to convert pressure into skill. **The order was inverted:
  validate learning FIRST, then shape the economy that rewards it.**

- **The strongest disconfirming hypothesis (must be tested, not assumed away):** *GENESIS organisms do
  not learn in-lifetime at all — they are fixed reflexes whose genome is tuned by evolution, and STDP is
  cosmetic.* Evidence consistent with this: the colony always converges to a monoculture reflex (Exp 22:
  eat/fwd), capability never rises, and no experiment has ever shown STDP mattering. If true, every
  "ascent" attempt was doomed a priori. **Criterion B is designed to kill or confirm exactly this.**

- **Second disconfirming hypothesis:** *the reward is on the wrong thing.* Reading pays for
  next-symbol prediction, which a fixed Markov reflex approximates well — so there is no gradient toward
  a *general* learner, only toward a better lookup. A real test of learning needs a task where the
  optimal policy CHANGES within a lifetime (so a fixed genome cannot pre-encode it and only in-lifetime
  plasticity wins). This is the affirmative form of the redirect and belongs in §4.

- **What survives the review:** the SNN-on-literal-RAM substrate, the thermodynamic honesty (Rule 17),
  the emergent-only discipline (Rules 5/9), the refugium/hall-of-fame deep-time machinery, and the
  bounded-reading carrying capacity (Exp 24). These are keepers. What does NOT survive is the *habit of
  adding an economy mechanic every time a run fails to ascend.*

---

## 4. The learning-first programme (replaces "Exp 30 = another economy lever")

Ordered so each step gates the next; every metric observation-only (Rules 9/14):

1. **Learning-ablation baseline (the decisive first test).** Run the current best economy twice —
   STDP ON vs STDP OFF (`a_plus=a_minus=0`), identical seeds/genomes. Measure survival, reads, and
   prediction-depth `C(t)`. **If OFF ≈ ON → learning is not load-bearing → criterion B fails now → do NOT
   build more economy; pivot to making learning matter (step 2).** This is one flag and one A/B; it is
   the highest-information experiment available and should have been Exp 1.

2. **A within-lifetime task only a LEARNER can solve.** If step 1 shows learning is weak, introduce a
   task whose correct response *changes during a single lifetime* (e.g. the reading reward periodically
   remaps which emission is "correct" for a symbol, on a timescale shorter than a generation but longer
   than a spike). A fixed genome cannot pre-encode this; only in-lifetime STDP can track it. This is the
   affirmative test of Rule 6's "genuine learning," and the first economy change that targets the MIND
   rather than the market.

3. **Only after B holds:** re-introduce the scarcity/division-of-labour pressure (the Exp 24–29 line) on
   top of a *validated learner*, and measure for the full A ∧ B ∧ C finish line.

---

## 4b. RESULT — Experiment 30: the learning-ablation test (2026-07-16). Criterion B FAILS: STDP is net-NEGATIVE.

The step-1 test was built (`GENESIS_NOLEARN`, compile-time deletion of STDP Phase 3 — no in-lifetime
weight change and no plasticity energy cost, so every synapse keeps its DNA-decoded weight for life;
byte-identical default when off) and run as a live A/B on the default books economy, learning ON vs OFF,
to equilibrium.

| metric (equilibrium) | STDP **ON** (current default) | STDP **OFF** (ablated) |
|---|---|---|
| population | 596 → **423** (steady decay) | **599** (flat) |
| brain size `Universe N` | 25 834 → **17 441** (−34 %, sheds) | 25 790 (−2 %, flat) |
| reading solve-rate `reads/(reads+miss)` | **~23 %** | **~51 %** |
| reads / 5 s window | ~60 | **~148** |

**The result is not "learning is weak" — it is that learning is actively HARMFUL.** Ablating plasticity
makes the colony *more* stable, keeps the brain *larger*, and *doubles* reading comprehension. This is a
stronger and more surprising failure of criterion B than "OFF ≈ ON": in-lifetime STDP, as currently
implemented, degrades the very capability it was meant to build. The long-observed "sustains but decays"
pattern (brain sheds, prediction dies — Result Exp 12 and after) is now causally attributed: **it is
STDP driving the decode-good genetic weights toward noise**, not an economic abundance problem. Every
economy lever built on top of a net-negative learning rule was pushing against a mechanism that was
actively eroding capability.

**Interpretation — the substrate is NOT yet falsified; the learning RULE is.** Criterion B's kill-clause
falsifies the substrate only if learning *cannot be made* load-bearing. Exp 30 shows the *current* rule
is anti-load-bearing, which admits three repairable causes that must be diagnosed before any verdict:
1. **Wrong-sign / wrong-target plasticity:** the STDP rule (potentiate on post-spike, depress on
   pre-spike, DNA-encoded `a_plus/a_minus`) may be driving weights toward noise rather than toward the
   task, corrupting an already-good evolved reflex. (Most likely — the brain *shedding* under learning
   is the signature of destructive weight drift.)
2. **Metabolic overhead:** the per-update STDP energy cost taxes a learner with no offsetting benefit,
   so Rule-7 efficiency selection grinds the plastic brain down.
3. **Task/plasticity mismatch:** next-symbol prediction is well-served by a *fixed* good reflex, so
   there is no gradient rewarding a *changing* weight — plasticity only adds variance.

**Revised next step (a DIAGNOSIS, not a new economy lever — Rule 18):** determine which cause dominates
— e.g. run OFF-vs-ON on a task whose answer *changes within a lifetime* (step 2 above; only there can a
correct learner beat a fixed reflex), and separately isolate the STDP energy cost from the weight-update
effect. Only if a *corrected, sign-correct, task-matched* plasticity rule still cannot beat ablation is
the SNN-on-RAM substrate falsified. Until then the operative conclusion is narrower and actionable:
**the current STDP rule is net-negative and must be fixed or removed before any further capability work;
the default engine should be treated as "reflex-evolution only" until a learning rule is shown to help.**

---

## 4c. DIAGNOSIS — Experiment 31: WHY STDP is net-negative (2026-07-16). Three causes; the ROOT is no supervision.

Two orthogonal diagnostic ablations were built (`GENESIS_STDP_COSTONLY` = keep the plasticity energy
cost but freeze the weight; `GENESIS_STDP_DIV` = scale every STDP step down, testing whether *truly
graded* small steps help) and run against the ON / NOLEARN baselines. First, a code read settled the
cheapest hypothesis: **the STDP sign is CORRECT** — pre-before-post potentiates (LTP), post-before-pre
depresses (LTD); it is Hebbian, not anti-Hebbian. So "wrong sign" is ruled out. The live A/B then
separated the rest:

| mode | population | brain `N` | solve-rate | reading |
|---|---|---|---|---|
| **NOLEARN** (no plasticity) | 599 flat | 25.8k flat | **~51 %** | best — fixed reflex |
| **ON** (full STDP, current) | 596 → **423** | −34 % (sheds) | ~23 % | collapse + degradation |
| **DIV=32** (truly graded, small steps) | 599 flat | ~25k flat | ~5 % → **3 %** | collapse FIXED, but reading slowly dies |
| **COSTONLY** (energy kept, weight frozen) | cold-cliff → 12 | — | — | raw STDP energy cost kills bootstrap |

**Three real causes, now separated:**
1. **Bang-bang step size (fixed).** The current step could move a weight up to ~32 of the 255-wide range
   in ONE event (~12 %), despite a "graded" comment — so a good decoded weight was slammed to the rail in
   a few spikes. This caused the brain-shedding and population collapse: DIV=32 (small steps) FIXES it —
   population and `N` go flat, no more shedding.
2. **Metabolic overhead (real, secondary).** COSTONLY (the energy tax alone, no weight change) cold-cliffs
   the bootstrap — the raw per-update STDP cost, unamortised by any benefit, can starve founders.
3. **ROOT CAUSE — no supervision (the decisive finding).** Even the *corrected* graded rule (DIV=32) still
   makes reading **slowly die** (solve-rate 23 %→5 %→3 %). Plain STDP is **unsupervised**: it reinforces
   *any* temporal coincidence with no reward/error signal, so it has no way to know a prediction was
   *correct*. It therefore drifts the decode-good genetic weights toward task-irrelevant input
   correlations — constructive-looking, actually destructive. Fixing the step size stops the *catastrophe*
   but not the *slow rot*, because the rule is optimising the wrong thing (coincidence, not correctness).

**Verdict — the substrate is NOT falsified; the LEARNING RULE is diagnosed and fixable in a specific
direction.** Pure two-factor Hebbian STDP cannot be load-bearing here because the task needs *correct*
prediction and STDP is blind to correctness. The indicated fix is **three-factor / neuromodulated
plasticity**: gate (multiply) the weight update by a success signal — the organism's own reading-reward
energy — so a coincidence is reinforced **only when it coincided with getting the prediction right**
(dopamine-style eligibility × reward). This is (a) more biologically faithful (Rule 6/11 — real synapses
are neuromodulated, not pure Hebbian), (b) Rule-9 autotelic (the reward is the economy's own reading
income, not a human-supplied error label), and (c) the first lever in the whole project that targets the
MIND (how it learns) rather than the market (what it's paid for). Small steps (a DNA-derived divisor) and
amortised cost come along for free. `GENESIS_STDP_COSTONLY`/`GENESIS_STDP_DIV` kept as permanent
diagnostic instruments (default = current behaviour). **Next: build three-factor neuromodulated STDP and
A/B it against NOLEARN — if it BEATS ablation, criterion B is finally satisfiable and the mind, not the
economy, is the thing that ascends.**

---

## 4d. RESULT — Experiment 32: three-factor STDP (first form) beats ablation EARLY, then still drifts (2026-07-16).

Three-factor neuromodulated plasticity was built (`GENESIS_STDP3`): the weight update is scaled by a
per-organism neuromodulator = that organism's own normalised reading reward last tick (one-tick
eligibility delay), so plasticity is damped toward zero when the organism is *not* comprehending and runs
at full gain when it is. Combined with the Exp-31 small-step fix (`GENESIS_STDP_DIV=32`), this is the
"corrected rule." Live A/B vs the NOLEARN baseline (solve ~51 % flat):

| phase | population | brain `N` | solve-rate |
|---|---|---|---|
| STDP3+DIV32, **early** | 599 | 26 267 | **~78 %** (best in the whole project) |
| STDP3+DIV32, **steady** | 599 → 251 | 26 267 → 10 611 (sheds) | 78 % → **~29 %** |

**Partial success — and a precise next diagnosis.** For the first time a learning rule pushed
comprehension *above* the no-learning baseline (78 % vs 51 %), proving **constructive learning IS possible
on this substrate** — the kill-criterion stays un-triggered, the substrate is alive. But it does not hold:
the colony still decays to a lower plateau. Root cause of the residual drift: the neuromodulator only
**gates the timing** of plasticity (learn when comprehending, not when idle) — it does not fix the
**direction / credit assignment**. When reading *is* paying, full-gain STDP is back on and still blindly
reinforces *every* coincident synapse, including those that did not cause the correct output. A reward
*magnitude* is not an error *signal*: the third factor must carry **which synapses deserve credit for the
correct prediction**, not merely *that* a reward occurred. This is the classic SNN credit-assignment
problem, and it is the specific, well-posed next target — not another economy lever and not a blind STDP
tweak. `GENESIS_STDP3` kept as an instrument. **Next: a credit-assigning third factor (e.g. reward-modulated
eligibility that potentiates only synapses onto neurons whose spikes drove the *correct* vocal bits, and
depresses those onto wrong bits) — a true reward-modulated STDP, then A/B vs NOLEARN for a rule that
*holds* above ablation.**

---

## 4e. RESULT — Experiment 33: credit-assigning three-factor STDP HOLDS above ablation (2026-07-17). Criterion B is met for the first time.

The Exp-32 residual was a credit-assignment failure: the neuromodulator `stdp_mod` is a single per-org
scalar, so while reading pays it scales EVERY coincident synapse equally — including those that drove the
WRONG vocal bits. A reward *magnitude* gated the *timing* of plasticity but never its *direction*, so the
decode-good weights still drifted (the slow rot Exp 31 isolated). The fix (`GENESIS_STDP3C`, default-OFF,
superset of STDP3): a **per-vocal-bit signed eligibility trace**. Reading reward already scores each of the
8 vocal bits separately against the target byte (`correct_bits` / `wrong_bits`); that per-bit verdict is
stored as `org_elig[org, 0..7]` (+1 correct, −1 wrong, 0 silent, one-tick delay) and multiplies each Phase-3
update whose destination is a vocal-bit neuron. LTP then consolidates ONLY synapses that drove a correct
bit; LTD reverses onto wrong-bit drivers; motor/hidden destinations keep the scalar `stdp_mod` (Exp-32
behaviour). Autotelic (the credit sign derives from reading's own per-bit correctness, never a human label —
Rule 9), constant-free (a pure per-bit ratio — Rule 17), compile-time gated (default byte-identical, verified),
and composes with `STDP_DIV=32` (small steps). STDP3C implies STDP3 (same dopamine × eligibility gain).

Live A/B on the default books economy (`00_Graded`), STDP3C vs the NOLEARN control, both to 400 000 LIF-ticks,
identical environment:

| metric | NOLEARN (ablation baseline) | STDP3C (credit-assigning) |
|---|---|---|
| population | 599–600 flat | 597–599 flat |
| brain size `Universe N` | ~25 900 flat | ~26 050 flat (no shedding) |
| solve-rate `reads/(reads+miss)`, early | ~54 % | **~72 %** |
| solve-rate, steady (~350 k ticks) | **~51 %** | **~60 %** |

**Criterion B (learning is load-bearing) is SATISFIED — and, unlike every prior rule, it HOLDS.** STDP3C
stays *above* the ablation baseline across the whole 400 k-tick run (steady 60 % vs 51 %), with **no brain
shedding** (`N` flat ~26 050 vs Exp-32's 26 267 → 10 611 collapse) and **no population decay** (599 flat vs
Exp-32's 599 → 251). Directional credit assignment fixed the slow rot that scalar reward-gating (Exp 32)
could not: giving the third factor *which synapses deserve credit* — not merely *that* reward occurred —
is what makes in-lifetime learning net-POSITIVE and stable on this substrate. This is the first learning
rule in the project's history that measurably and durably beats not-learning; the kill-criterion stays
un-triggered and the SNN-on-RAM substrate is now positively validated as a learner, not merely un-falsified.

Residual: a mild early-to-steady drift remains (72 % → 60 %), so credit assignment is *sufficient to hold
above ablation* but not yet *monotone-rising* — capability criterion A (a sustained ≥25 % RISE in
prediction-depth) is still not met. Note also the frontier probe: the colony sits ~93 % off-scroll in the
arithmetic band but `pred` stays ~0, i.e. it holds the hard region without yet earning compute-depth income.
Two instrument notes: (i) eligibility is written only in the stationary-read scoring block, so a jump-predict
tick uses a one-tick-stale credit vector (bounded harmless — the reward-gate zeroes plasticity when reading
pays nothing); (ii) `GENESIS_STDP3C` kept as a permanent instrument (default = current behaviour).
**Next (targets criterion A, not a new economy lever): make the held capability RISE — e.g. couple the
credit trace to the prediction-DEPTH frontier (pay/への consolidate compute-band predictions more), or the
within-lifetime remap task of §4 step 2 (a task whose correct answer changes mid-life, where only a credit-
assigning learner can track it) — then A/B for the full A ∧ B ∧ C finish line.**

---

- New experiments are pre-registered against §2's criteria before running; a run that doesn't move A/B/C
  is a **closed branch**, not a prompt for a new mechanic.
- `Rules.md` gains **Rule 18** (pre-registered falsifiable finish line + validate the load-bearing
  assumption before adding mechanics) so this discipline is permanent, not a one-off.
- The UI (next task) will surface the A/B/C probes (`C(t)`, learning-ablation delta, `C/footprint`) so
  the finish line is watchable live, not reconstructed from logs.
