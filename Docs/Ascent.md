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

## 4f. RESULT — Experiment 34: the within-lifetime remap test (§4 step 2). The learner CANNOT re-track: STDP prunes but cannot RECRUIT (2026-07-18).

§4 step 2 — the affirmative test of Rule-6 learning that *no experiment had ever built* — was built and run.
The doubt it targets (§3, 2nd disconfirming hypothesis): next-symbol prediction is well-served by a *fixed*
reflex, so Exp 33's "learning is load-bearing" could still be evolution-of-a-fixed-reflex on a task a reflex
also solves. The remap task removes that escape hatch by making the **correct answer change within one
lifetime**, on a wall-clock phase that is on **no sensory input** — so a fixed genome provably cannot
pre-encode it and only genuine in-lifetime plasticity can track it.

**Task (`GENESIS_REMAP`, default-OFF, compile-time gated, byte-identical when off).** In a "swapped" phase
the reading-reward target has two designated vocal bits **exchanged** (SB0↔SB1); in the identity phase the
target is the ordinary next byte. The other 6 bits echo normally, so survival is barely perturbed and the
*only* thing that must be *learned* is to re-route eye-bit SB0→vocal-bit SB1 (and vice-versa) when the phase
flips. The ancestor is seeded with the two **cross synapses** at **zero weight** (present but silent), so
credit-assigning STDP has a physical route to potentiate — its fairest possible shot. (A first design used a
full 8×8 eye→vocal fabric; under learning it cold-cliffed the colony — 56 corruptible routes slam the echo —
which is itself the first data point: *dense plastic input fabric + STDP = catastrophic drift*. The minimal
2-route form isolates the question cleanly.)

**Measurement — a survival-DECOUPLED held-out sandbox probe** (`tests/remap_sandbox_probe.py`, Rules 9↔6/14).
Every prior "does it learn?" result was confounded by the economy: making reading harder drives the colony to
the refuge floor (pop=12), so a learner's re-tracking cannot be separated from the economy collapsing. This
probe removes the economy entirely and drives the **real `world_tick_numba` kernel** (Live-Loop-Test-Gap rule):
a frozen cohort of 120 REMAP-ancestor clones stands on a fixed text patch, **energy pinned high every tick**
(nobody dies, nobody reproduces → only synaptic weights change), the remap phase alternates on the
`REMAP_PERIOD` clock, and observation-only **per-bit accuracy** is split into the 2 swapped bits vs the 6
unchanged bits.

| phase (steady, all 5 phase-cycles identical) | STDP3C (learner, DIV=32) | NOLEARN (ablation) |
|---|---|---|
| unchanged-bit accuracy (health check) | **~99 %** | **~99 %** |
| identity-phase swap-bit accuracy | ~87 % | ~87 % |
| **swapped-phase swap-bit accuracy** | **~40 % (flat, no trend)** | **~42 % (flat, no trend)** |

**The learner does NOT re-track the swap — it is statistically indistinguishable from the ablation** (~40 %
vs ~42 %; the learner is marginally *worse*, from weight noise). At fine resolution (250-tick windows across
a 3000-tick swapped phase) the swap-bit accuracy is **flat noise around 40 %** from the first window to the
last — no within-phase recovery curve, no cumulative improvement across 5 phase-cycles. 120 organisms × 3000
ticks of in-phase experience produce **zero** measurable learning of the new mapping, while the unchanged
bits stay at 99 % (proving the cohort is healthy and reading fine — *only* the bits that require learning fail).

**This is a decisive, pre-registered NEGATIVE, and it localises the substrate defect precisely — it does NOT
trigger the kill-criterion.** The mechanism is exactly the pre-registered prediction from the kernel analysis:
**STDP3C's credit is OUTPUT-GATED — it can only reinforce/suppress vocal neurons that ACTUALLY FIRED.** In a
swapped phase the echo diagonal makes vocal-SB0 fire (now *wrong*) and leaves vocal-SB1 **silent** (it *should*
fire). Hebbian-family STDP (even credit-assigned) updates a synapse only on a **post-synaptic spike**; a silent
neuron generates no eligibility, so there is **no gradient that can turn a silent-but-wanted neuron ON**. The
rule can *prune* a wrong active pathway (LTD on the firing wrong bit) but cannot *recruit* a new one. Exp 33's
"learning holds above ablation" is therefore real but **narrow**: STDP3C consolidates/prunes an *already-firing*
correct-ish reflex; it does **not** perform the credit-*construction* that in-lifetime learning of a genuinely
new input→output mapping requires. This is the difference between *tuning* a circuit and *building* one — and
building is what reasoning/abstraction (Rule 6) needs.

**The diagnosis is not "the substrate cannot learn" (kill-criterion) but "the learning RULE carries a reward
signal, not an ERROR signal."** A `was-I-right?` scalar/per-bit-credit reaches only neurons that fired; a
teaching signal must also reach neurons that *should have fired and did not* (the classic delta/backprop-style
term, or a biologically-plausible three-factor rule with a **target-driven dendritic/error current** that
depolarises the wanted-silent neuron so it spikes and becomes eligible). **The pre-registered next step is
therefore a SUBSTRATE change to the plasticity rule, not another economy lever:** inject, on a rewarded read, a
small **target current** into the vocal neurons the target byte says *should* be on (derived from the org's own
reading target — Rule 9 autotelic, constant-free), so a wanted-silent neuron fires and its afferents become
eligible for LTP. Then re-run this exact sandbox A/B: if swapped-phase accuracy now *climbs within a phase and
holds above NOLEARN*, the substrate can construct new mappings in-lifetime (criterion B affirmed on a
reflex-proof task, and the first real evidence the substrate can support reasoning). If it *still* cannot after
a correct error-signal rule, the kill-criterion is genuinely in play. `GENESIS_REMAP` and the sandbox probe are
kept as permanent instruments; the default engine is byte-identical (verified) and was re-checked — no regression.

---

## 4g. RESULT — Experiment 35: the error/teaching signal RECRUITS — the substrate CONSTRUCTS a new mapping in-lifetime (2026-07-18). The Exp-34 negative is repaired.

The Exp-34 diagnosis was precise: STDP (even credit-assigned) updates only on a post-synaptic spike, so it can
prune a wrong-firing route but cannot **recruit** a silent-but-wanted neuron. The pre-registered fix — a
teaching/**error** signal rather than a reward signal — was built and run against the *same* sandbox.

**The rule (`GENESIS_STDP_TARGET`, default-OFF, compile-time gated, byte-identical when off).** A local delta
rule on the reading-eye→vocal-bit synapses, applied in the reward block on a rewarded read: for each vocal bit
b, `err_b = target_b − output_b ∈ {+1, 0, −1}`; every synapse from an **active** eye input j onto vocal neuron b
is nudged `w += err_b · (CELL_STATES/8)/STDP_DIV`. `err_b = +1` (WANTED but the neuron was **silent**)
**potentiates** the silent neuron's active eye afferents **without** requiring a post-spike — the exact
recruitment gradient STDP3C lacks; `err_b = −1` (fired but unwanted) depresses; `err_b = 0` leaves them. This is
the local, biologically-plausible teaching current of predictive-coding / dendritic-error SNNs (a "should-fire"
signal to the apical dendrite), **not** backprop. Autotelic (target = the org's own read target, Rule 9) and
constant-free (reuses `STDP_DIV`, `CELL_STATES` — Rule 17); charged like an STDP update (activity-gated).

**Result — sandbox A/B (identical to Exp 34; `STDP_TARGET`, DIV=4):**

| rule | swapped-phase swap-bit accuracy | behaviour |
|---|---|---|
| NOLEARN (ablation) | ~41 % **flat** | fixed reflex, never re-tracks |
| STDP3C (Exp 34) | ~40 % **flat** | cannot recruit silent neurons |
| **STDP_TARGET (Exp 35)** | **56 % → ~99 % within ~2000 ticks, EVERY phase flip** | **constructs the new mapping in-lifetime** |

Each phase transition now shows the recovery curve that was **absent** in Exp 34: at a flip to SWAP the swap-bit
accuracy drops to ~56 % (old mapping wrong), then climbs 84 → 86 → 98 → 99 % and holds; at the flip back to
identity it drops to ~50 % and re-climbs to ~99 %; the re-learning **repeats every cycle and gets faster**
(later cycles rail in fewer windows). The unchanged bits hold 99 % throughout (the teaching signal touches only
the eye→vocal fabric it is supposed to). The NOLEARN control on the identical fabric stays flat ~41 %, proving
the recovery is real in-lifetime plasticity, not a measurement artefact.

**Interpretation — the first in-lifetime CONSTRUCTION of a new input→output mapping in the project's history.**
Exp 33 showed the substrate can *tune/prune* an already-firing reflex; Exp 34 showed credit-assigned STDP cannot
*build* a new pathway; Exp 35 shows that **with an error signal that reaches silent-but-wanted neurons, the
substrate CAN build one** — re-tracking a mapping whose correct answer changes within a lifetime, on a task a
fixed genome provably cannot pre-encode. This is the affirmative form of criterion B on a reflex-proof task and
the first concrete evidence the substrate can support the circuit-*construction* that reasoning/abstraction
(Rule 6) requires. The kill-criterion is **not** in play; the substrate is validated one level deeper than Exp 33
left it — it can *learn to compute a new function*, not only tune a fixed one.

**Honest scope + next step (pre-registered).** This is proven **in the isolated sandbox** (frozen, energy-pinned
cohort on the seeded cross-fabric) — it isolates the learning mechanism from the economy by construction. It is
**not yet** shown that (i) `STDP_TARGET` beats NOLEARN on the **live books economy** (survival + comprehension
over deep time, the Exp-33 setting), nor (ii) that the recruitment mechanism generalises beyond the seeded 2-bit
fabric to *evolved* topology. The next experiments are exactly those two, in order: (1) live-loop A/B
`STDP_TARGET` vs NOLEARN vs STDP3C on `00_Graded` (does the recruiting rule hold above ablation on the real
economy, and does it fix the Exp-33 residual drift?); (2) then the criterion-A push (make held capability RISE),
now on a rule that can *construct* rather than only tune. `GENESIS_STDP_TARGET` + `GENESIS_REMAP` +
`tests/remap_sandbox_probe.py` kept as permanent instruments; default engine byte-identical (re-verified: cache
`genesis_numba_books`, ancestor 31 synapses).

**UPDATE — the live-loop A/B was run the same day, and the step size is decisive (the Exp-31 lesson recurs).**
Live A/B on `00_Graded`, 120–150 k ticks each:

| arm | population | solve-rate `reads/(reads+miss)` | Universe N |
|---|---|---|---|
| NOLEARN | 600 | ~77 % | 26 173 |
| STDP3C (DIV=32) | 600 | ~52 % | 26 059 |
| **STDP_TARGET, DIV=4** (large step) | **40 (CLIFFS)** | ~95 % (survivors) | 1 649 (tiny) |
| **STDP_TARGET, DIV=32** (small step) | **600 (full, no shed)** | **~74 %** | 25 971 |

At the large step (DIV=4) the teaching signal is so strong it slams the eye→vocal fabric to a minimal hyper-echo
during the bootstrap — Rule-7 efficiency then selects the tiny brain and most founders starve (**the Exp-31
bang-bang cliff, now on the teaching-signal axis**; the energy-pinned sandbox hid it because nothing could die).
At the **small step (DIV=32)** the tension resolves: `STDP_TARGET` **sustains a full 600 colony with no shedding
and ~74 % comprehension** (vs NOLEARN's ~77 %, STDP3C's ~52 %) — i.e. it is now **economy-compatible AND still
recruits** (the DIV=32 sandbox re-tracks the swap 66 %→~97 % every flip). So the shippable setting is the small
step. This is the **first learning rule that both (a) constructs a genuinely new in-lifetime mapping (Exp 35
sandbox) and (b) survives the live economy at full population** — though on the *stationary* books task it does
not yet *beat* NOLEARN's comprehension (it roughly matches it, because next-symbol prediction rewards a fixed
echo the ablation already nails). The honest conclusion: the recruiting rule's *value* shows up where the task
requires **learning a new mapping** (the remap), not where a fixed reflex suffices — which is precisely why the
next step (criterion A) must put the colony on a task whose optimum *keeps moving*, so construction is
continuously required and the rule that can construct out-competes the one that cannot. `GENESIS_STDP_DIV=32` is
the operative step for `STDP_TARGET`; the DIV=4 cliff is retained as the bang-bang A/B extreme.

---

## 4h. RESULT — Experiment 42: criterion B is affirmed UNDER LIVE SELECTION on a reflex-proof task — the constructive learner sustains a full colony AND re-tracks a moving optimum a fixed reflex cannot (2026-07-18).

§4g ended on the exact next test: put the colony on a task whose optimum *keeps moving* (so construction is
continuously required) and A/B the recruiting rule against the reflex **on the live loop under selection** — the
one thing never shown (Exp 35 was survival-decoupled sandbox; the earlier live REMAP A/B used only NOLEARN/STDP3C,
both of which stay flat). Built the live per-bit telemetry (observation-only, gated on REMAP: the swap-bit vs
unchanged-bit accuracy split, mirroring the sandbox) and ran the 3-arm live A/B on `00_Graded` with the REMAP
2-bit swap alternating every `REMAP_PERIOD`=4000 ticks.

| arm | population (live, survival active) | **swapped-phase** swap-bit accuracy | unswapped-phase |
|---|---|---|---|
| NOLEARN (fixed reflex) | 598–600, ext=0 | **~24–29 %** (collapses when the optimum swaps) | ~78–80 % |
| STDP3C (DIV=32) | **12 (CLIFFS)** | 0 | 86 % (pre-cliff) |
| STDP_TARGET, DIV=32 | **12–33 (CLIFFS)** | ~73–100 % (but only a refuge-floor pod) | 96–100 % |
| **STDP_TARGET, DIV=128** (gentle step) | **595–600, ext=0, refuge=0** | **~55–70 %, and RISING (58→70)** | ~64–70 % |

**Criterion B is affirmed under live selection — the first time in the project.** At the economy-compatible step
(DIV=128), `STDP_TARGET` **sustains a full 600 colony** (ext=0, refuge=0) AND **re-tracks the moving optimum**: in
the swapped phases — which a fixed genome provably cannot pre-encode — its swap-bit accuracy holds **~55–70 %**
and *trends up over the run* (58→70), versus NOLEARN's **~24–29 %** (the reflex is correct only when the mapping
is unswapped and collapses when it flips). A clear, sustained ~2× margin across every phase flip, on the real
economy, under real selection. STDP3C ≈ NOLEARN/cliff, confirming the recruit-vs-prune distinction transfers from
the sandbox to live. The step size is decisive exactly as §4g predicted: DIV=32 cliffs the colony to the refuge
floor under the *moving* optimum (the surviving pod re-tracks — swap-bit ~73–100 % — but that is a selected
remnant, not a healthy colony), because the moving target's teaching + plasticity load is too heavy at that step;
DIV=128 (gentler, the Exp-31 bang-bang lesson recurring on the teaching-signal axis) is where the colony both
survives and learns.

**Honest reading of the trade.** NOLEARN's *unswapped* accuracy (~78–80 %) is actually higher than the learner's
(~64–70 %) — the reflex is optimised for the one fixed mapping, while the learner is a jack-of-both, constantly
re-adapting between phases and so never peaking on either. That is the correct, expected signature of in-lifetime
learning: it trades peak performance on a *fixed* task for the ability to handle a *changing* one — and only the
learner is above chance in the swapped phase. This is precisely what makes it load-bearing where a reflex is not.

**What this does and does NOT establish (pre-registered honesty).** It establishes criterion **B under live
selection on a reflex-proof task** — the substrate's construction-capable learner (Exp 35) is not merely a
sandbox artefact; it survives and out-comprehends the reflex on the live economy when the task genuinely requires
learning. It does **NOT** establish criterion **A** (a sustained ≥25 % monotone RISE in the compute-depth metric):
REMAP is a *re-tracking* (recover-to-plateau) task, so it affirms B, not A; the swap-bit rise (58→70) is
suggestive but within a re-tracking envelope, not the open-ended climb A demands. A remains open. **Next (targets
A):** couple this validated constructive learner to a task whose optimum keeps moving *and deepens* (the
compute-band frontier of `00_Ascent`, or the peer economy where a neighbour's grounded behaviour is the moving
target the learner must model) — now that we have, for the first time, a learning rule proven to construct new
mappings live under selection. `GENESIS_REMAP` live per-bit telemetry + `GENESIS_STDP_TARGET` kept as permanent
instruments; `GENESIS_STDP_DIV=128` is the operative live step for the moving-optimum task; default engine
byte-identical (re-verified).

---

## 4i. RESULT — Experiment 43: the working-memory DEPTH under criterion A — the substrate holds ~1 step of context, and deep memory is the real A-blocker (2026-07-18).

Before building the criterion-A economy, Rule 18 demands validating A's load-bearing assumption: **can a
GENESIS brain compute over HELD CONTEXT at all?** A's metric is compute-depth income (carry/arithmetic bands),
and Exp 33 measured the tell — the colony SITS in the arithmetic band earning `pred`≈0 (holds the hard region,
earns no compute income). Arithmetic (`a+b=c`) needs the brain to hold operands across cells while the eye
(current cell only) moves; the only cross-tick state is **leaky membrane voltage** (`global_v` persists,
decaying) — a weak working memory of unproven sufficiency. Built the minimal isolating test.

**Task (`GENESIS_DELAY`, default-OFF, compile-gated, byte-identical off).** The reading-reward target is the
byte the organism sensed **`DELAY_N` cells ago** along the passage it walked (`org_delay_buf`, a per-org shift
ring pushed on each saccade — *movement*-keyed, not tick-keyed), on **no current input**. A memoryless reflex
cannot emit it; only a brain HOLDING it across `DELAY_N` steps can. Measured in the survival-decoupled sandbox
(`tests/delay_sandbox_probe.py`, frozen energy-pinned cohort on repeat-free `01_Alphabet` so echo cannot fake
it), 3 arms. (A first tick-keyed ring was a confound — a stationary reader's ring degenerated to the constant
current byte, letting NOLEARN "solve" it at ~100 %; the movement-keyed fix makes the target a genuine past
distinct cell, and NOLEARN drops to its true memoryless floor ~6 %.)

| DELAY_N | NOLEARN (memoryless floor) | STDP_TARGET (DIV=128) |
|---|---|---|
| **1** (hold 1 cell) | **~6 % (flat)** | **~65–68 % (STABLE)** |
| 2 | ~7 % | transient ~70 % → collapses to ~2 % (UNSTABLE) |
| 3 | ~8–20 % | transient ~73 % → collapses to ~9 % (UNSTABLE) |

**The assumption is validated for DEPTH 1, and falsified for DEPTH ≥2 — and that is the crisp, load-bearing
finding.** At `DELAY_N=1` the constructive learner **stably holds one step of context** — ~65 % vs the ~6 %
memoryless floor, a clean ~10× lift sustained over 40 k ticks — using nothing but leaky membrane voltage + the
Exp-35 teaching signal. So the substrate DOES have real, learnable in-lifetime working memory. But at
`DELAY_N`≥2 it is **unstable**: the learner *transiently constructs* the deeper memory (spikes to ~70 %) but
**cannot hold it** (collapses to near-floor), because a single leaky membrane trace carries ~1 step reliably and
a 2-step hold needs a value latched across an intervening cell the leak has already overwritten.

**This directly explains the criterion-A wall and localises the substrate change.** Arithmetic/carry (A's
compute bands) require holding ≥2 values (both operands) across the operator and `=` cells — i.e. working
memory of depth ≥2, which the substrate does **not** stably support. That is *why* the colony sits in the
arithmetic band earning ~0 (Exp 33): not because it can't learn, but because the held-context depth the task
needs exceeds the ~1-step the leaky membrane provides. **Criterion A therefore does NOT need another economy
lever — it needs an architectural working-memory pathway:** a persistent, genome-wireable register/latch (a
recurrent self-excitatory loop that holds a value against the leak, or an addressable RAM scratchpad the
organism can write and read) that gives depth ≥2. This is the pre-registered next substrate change, and it is
exactly the kind of decisive, mechanism-level result the finish-line discipline exists to surface — not "tune
the market," but "the mind needs one more organ." `GENESIS_DELAY` + `tests/delay_sandbox_probe.py` kept as
permanent instruments (the working-memory-depth probe); default byte-identical (re-verified).

**RULE-17 FOLLOW-UP (2026-07-18): the tuned STDP step `DIV=128` was a magic number — now hardware-derived, and
the derived one is STRONGER.** The learning step used in Exp 42/43 (`a_plus/STDP_DIV`, with `STDP_DIV` a
hand-searched 4/32/128) was a Rule-17 violation. It is now DERIVED: the weight step is capped at ONE MICROSTATE
of the 256-state byte weight (`/(CELL_STATES/STDP_SCALE)`), so a full-scale DNA amplitude moves the weight ≤1 of
256 states/event — graded from the register's own numbers, no picked divisor. Re-validated: the derived default
makes the ordinary books economy HEALTHIER (reads climb 136→175, pop=600, vs the old bang-bang default decaying
to pop=423, Exp 30), and on the live REMAP moving-optimum it re-tracks the swap to **~90 %** (rising 59→94), even
BETTER than the old tuned step's ~70 % (§4h). This changed the default learning-on behaviour on purpose — it
fixes the net-negative bang-bang Exp 30/31 proved harmful, so keeping the old default would preserve a known bug.
`STDP_DIV` survives only as an explicit experiment-specific diagnostic softener for harsh moving-optimum probes
(where the bootstrap needs a gentler step than the physical quantum), never a physics default; `DELAY_BUF`→
`BITS_PER_BYTE`. The delay-sandbox WM-depth result (depth-1 holds, depth ≥2 unstable) is unchanged under the
derived step (it is in fact sharper: N=1 reaches ~87 %). Rule 17's constant list updated to record the retirement.

---

## 4j. RESULT — Experiment 44: the working-memory latch primitive works but a passive latch is insufficient — depth ≥2 needs GATED memory (2026-07-18).

§4i named the criterion-A substrate change: an architectural working-memory pathway. Built the minimal form,
`GENESIS_WMEM` (`MEMORY_MARKER = 198`): a genome-wireable **latch neuron** — non-leaky, non-resetting integrator
(holds accumulated voltage across ticks, emits on threshold without wiping the store). **The primitive works**
(real-kernel micro-test: latch holds/accumulates 127→254→…→889 while a leaky neuron stays 0). **But it does NOT
unlock depth-2:** delay-sandbox N=2 with STDP_TARGET, WITH vs WITHOUT the seeded `eye→latch→vocal` fabric = both
~30 %. Diagnosis (structural): the ungated fabric writes the latch every tick, so it is continuously overwritten
by the current byte and holds only *the current* value — depth-1 again. **Real depth-2 needs GATED write/read
control (decide WHEN to store, WHEN to read out), which STDP re-weighting a fixed fabric cannot invent.** So the
substrate change is not a passive latch but **ADDRESSABLE/GATED memory** — a write-enable + read-enable
(RAM-scratchpad direction: an organism that explicitly writes a value to a held cell and reads it back on a
separate control line). The latch is a necessary building block; the missing piece is the **control path** that
gates it. This is the pre-registered next substrate change for criterion A. `GENESIS_WMEM`/`MEMORY_MARKER` kept
as instruments (the held-state primitive); default byte-identical (re-verified).
- `Rules.md` gains **Rule 18** (pre-registered falsifiable finish line + validate the load-bearing
  assumption before adding mechanics) so this discipline is permanent, not a one-off.
- The UI (next task) will surface the A/B/C probes (`C(t)`, learning-ablation delta, `C/footprint`) so
  the finish line is watchable live, not reconstructed from logs.

## 4k. RESULT — Experiment 45: the write-gate primitive works but STDP cannot self-clock a fixed fabric — depth ≥2 needs an ACTION-DRIVEN scratchpad (2026-07-19).

§4j named the fix: gated memory (write-enable). Built the hardware primitive — a kernel WRITE-GATE (`GENESIS_WMEM`,
default-OFF, byte-identical off): a latch declares a gate-source neuron (gene slot byte → `global_sense_meta`);
in Phase-1 propagation the latch accepts afferent writes **only on ticks its gate fired last step**, else HOLDS.
Seeded a **2-stage gated shift register** per bit (`eye→L0→L1→vocal`, gated by a control neuron `G`, all routes
silent/STDP-tunable). Verified wired (16 latches `N_IO+5..+20`, gate meta = gate+1 on each; default ancestor 159
bytes unchanged).

**Decisive test (delay N=2): the gate does NOT unlock depth-2.** Gated WMEM + STDP_TARGET averaged ~40 % (noisy
30–49 %), **BELOW** the NOLEARN echo floor (~46 %, stable). The learner loses to a memoryless reflex.

**Diagnosis (sharper than §4j):** `G` fires from the eye bits → pulses on ~every saccade (fresh byte each tick) →
write-enable ~always ON → degenerates to the ungated Exp-44 case. And a shift register needs **clock-phase
separation** (write→shift→read on distinct ticks) that a single feed-forward LIF pass collapses. There is **no
store-cue in the task** telling the org "hold THIS one," and STDP re-weighting a static fabric cannot invent a
self-clock. **Across Exp 43–45 (consistent): a neural fabric + STDP is the wrong substrate for working memory.**
Held-state (44) and gating (45) are necessary building blocks; the missing piece is a **controllable clock/address
the organism drives with ACTIONS**. The substrate already exposes real addressable external memory — RAM cells +
CONSUME-writes + eye-reads (stigmergy). **Pre-registered next substrate change: a RAM SCRATCHPAD** — the org writes
a byte to a cell, saccades away, saccades back, reads it (memory via environment, existing primitives, no new
lever). `GENESIS_WMEM` + write-gate kept as instruments (reusable once an action-driven address/clock exists).

## 4l. RESULT — Experiment 46: external addressable RAM memory UNLOCKS depth-2 — the first depth ≥2 success (2026-07-19).

§4k concluded (across Exp 43–45) that a neural substrate cannot hold state and that working memory needs an
EXTERNAL, non-leaky, org-ADDRESSABLE store. Built it — `GENESIS_SCRATCH` (`SCRATCH_MARKER = 199`, default-OFF,
byte-identical off): recall-sensor neurons that read one BIT of one SLOT of the organism's own movement-keyed
byte-history ring (`org_delay_buf`, a real non-leaky external store; slot k = k saccades ago), addressed by
`(slot<<3)|bit` in `sense_meta`. Seeded 32 recall sensors (slots 0–3 × 8 bits), each **silent** → its vocal bit;
extended the Exp-35 teaching signal to teach recall→vocal routes too. To solve delay-N the learner must
**potentiate the slot-N recall→vocal route and keep slot-0 (echo trap) silent** — learnable ADDRESSING of external
memory. **POSITIVE (first depth ≥2 success in project history):** delay N=2 STDP_TARGET rises **51→68 %** monotone
(140 k ticks) vs NOLEARN flat **~49 %** (+19 pts); N=3 **70–84 %** vs ~49 % (+25–35 pts). Exactly where the neural
latch bought nothing (44/45 at/below floor), external addressable memory + the validated learner clears it at
depth 3. **Resolves the §4i criterion-A blocker: the substrate CAN compute over held context of depth ≥2 — memory
is an ADDRESS the organism reads, not a voltage it holds.** STDP_TARGET (Exp 35) also generalises to a second
source class (recall sensors) — it constructs a routing circuit, not just a copy. Permanent; default byte-identical
(ancestor 159 bytes). **Next (criterion A, LIVE): a live economy where holding depth-2 context PAYS (copy-at-a-
delay / two-operand grounded computation) so selection drives the addressing circuit and C(t) can be measured for
the ≥25 % sustained RISE — the still-unmet criterion A.**

---
## 4m. RESULT — Experiment 47: SCRATCH retention live probe — Rule-18 validation for Crit-A load-bearing assumption (2026-07-21).

§4l resolved the substrate's *capacity* for depth-2 working memory (external addressable RAM + STDP_TARGET learns to address it). The **load-bearing assumption for Crit-A** is that a **live economy will select for this capability** — that the addressing circuit (slot-N→vocal) will be potentiated and retained under real selection. This experiment tests that assumption directly on the live books economy.

**Design (observation-only, Rules 9↔6, no selection pressure added).** Three-arm A/B/C probe on `00_Graded`, Ark OFF, 1000 world-ticks:
- **ARM-A (control):** `GENESIS_NOLEARN=1` — no plasticity at all.
- **ARM-B:** `GENESIS_STDP_TARGET=1 GENESIS_DELAY=1 GENESIS_DELAY_N=2` — learner + delay ring, but NO SCRATCH recall sensors (the brain must solve delay-2 from leaky membrane only).
- **ARM-C:** `GENESIS_STDP_TARGET=1 GENESIS_DELAY=1 GENESIS_DELAY_N=2 GENESIS_SCRATCH=1` — full SCRATCH fabric seeded (32 recall sensors slots 0–3 × 8 bits, each silent→vocal bit, doubled; teaching signal extended to recall→vocal routes per §4l).

All arms use identical environment (books, contiguous scroll, same seed). Metrics per epoch: population, mean energy, brain size (neurons/synapses), recall sensor count per org, recall→vocal synapse count per org, delay-2 solve accuracy (proxy from read-log type-3 fraction).

**Key results (live, 1000 ticks):**

| metric | ARM-A (NOLEARN) | ARM-B (STDP_TARGET+DELAY) | ARM-C (full SCRATCH) |
|---|---|---|---|
| final population | 247 | 252 | 195 |
| mean energy | 43 411 | 40 099 | 33 451 |
| brain neurons | 44 | 44 | 76 |
| brain synapses | 31 | 31 | 95 |
| recall sensors (median) | 0 | 0 | **32.0 (stable)** |
| recall→vocal synapses (median) | 0 | 0 | **64.0 (stable)** |
| delay-2 accuracy (final) | 0.0 % | 0.3 % | 0.4 % |

**Critical findings:**

1. **SCRATCH fabric is RETAINED but NOT potentiated.** ARM-C maintains all 32 recall sensors and 64 recall→vocal synapses perfectly stable across 1000 ticks (no mutation drift). The seeded circuit survives neutrally.

2. **Addressing circuit is NOT strengthened.** The 64 recall→vocal synapses stay at exactly the seeded weight 128 (silent). The slot-2 route (the correct delay-2 answer) is **not potentiated above the echo-trap slot-0 route**. The learner does not discover the addressing solution under live selection.

3. **Delay-2 accuracy collapses to ~0.4 % in BOTH ARM-B and ARM-C.** The STDP_TARGET teaching signal is present but the uniform reading income (gain = `net_bits/8 × CELL_STATES`, no depth-band multiplier) pays the same per-byte regardless of prediction depth. The metabolic cost of the SCRATCH sensors (32 extra reads/tick) is not offset by any marginal reward, so selection has no pressure to solve depth-2.

4. **Energy economy confirms the mechanism.** ARM-C mean energy (33K) < ARM-B (40K) < ARM-A (43K). The SCRATCH overhead is a net metabolic tax with no compensating income.

**Rule-18 verdict: the load-bearing assumption is FALSE.** The substrate *can* do depth-2 (Exp 46 sandbox), but the live books economy **does not select for it** because the reward function is depth-agnostic. Uniform reading income + metabolic cost of addressing = the addressing circuit is neutral-to-negative and is not driven by selection.

**Implication for Crit-A:** The ≥25 % sustained C(t) rise **cannot be achieved by economy shaping alone** on the current books substrate. The addressing circuit needs a **depth-band reward** (e.g., gain multiplier for delay-N solves, or a peer-economy where depth-2 context predicts neighbour behaviour). This is a *mechanism* requirement, not a *market* requirement — the teaching signal (STDP_TARGET) already exists; the economy must *pay* for its use. Next step (pre-registered): implement a depth-rewarded live economy (e.g., grounded foraging with copy-at-a-delay income, or peer prediction where the target is a deterministic function of neighbour state requiring held context).

## 5. Strategic reframe (2026-07-18, user-directed): grounded cognition, NOT human-language tuition

A user challenge forced an honest re-examination of the whole curriculum premise: **is teaching the organisms
human language (the `Books/` ASCII curriculum, next-symbol prediction) the right path to a mind at all?** The
conclusion, consistent with the project's own Rule 9 and the Exp 33–34 findings, is **no — as the path to
cognition it is inverted**, and the direction is now fixed:

**The diagnosis (why `Books` cannot build a mind, only the appearance of one):**
1. **Symbol grounding is absent.** An organism reading ASCII and predicting the next byte binds those symbols to
   *nothing in its own survival world*. "2+2=4" is a byte pattern, not a quantity; it learns text statistics, not
   meaning. Exp 33/34 confirmed this concretely: next-symbol prediction is solved by a *fixed reflex* — literacy
   as pattern-echo, not comprehension.
2. **It violates the spirit of Rule 9 (Autotelic).** Human-authored text IS a human curriculum; Rule 9 requires
   the challenges (and any language) to *emerge from agent–agent survival*, not be spoon-fed.
3. **It anthropomorphises.** It assumes intelligence == human literacy. An alien mind coupled to RAM may build a
   wholly non-linguistic cognition; imposing English from birth is teaching a fish to climb before it can swim.

**The correct order (mirrors child development — meaning before words):**
1. **Grounding first.** Cognition must be grounded in the organism's *own* real world (energy, space, neighbour
   behaviour, survival prediction). A child understands the world, then attaches words to it.
2. **Language emerges from agent–agent interaction** (the `GENESIS_PEER` line) — a language of *their own*,
   grounded in their world, not human orthography.
3. **The human interface is a LATER translator layer.** Once grounded cognition exists, we either translate their
   emergent signals (decoding a whale-song) or teach human language as a *second* language mapped onto
   already-grounded concepts. This is how the user's eventual "ask it 2+2 / say hello" interface is reached —
   **not** by pre-memorising English from t=0.

**Consequence — the two jobs `Books` was conflating are split:**
- **Survival scaffold:** an energy source that merely keeps the colony alive so cognition has time to evolve. This
  is all `Books`/reading is now asked to be — a nutrient, not a teacher. It may later be *removed* entirely in
  favour of a grounded survival economy (food/space/peer). Reading-as-cognition is retired.
- **The mind path (the real work):** grounded survival cognition + emergent peer communication + **widened
  behavioural expression** (Exp 21's ceiling: "a mind cannot be modelled richer than it can *act*"). The
  expression axis is now being widened from both sides — **evolvable SENSORS (Exp 37, built)** and **evolvable
  ACTUATORS (Exp 38 / Phase B, next)** — because without the capacity to sense and act richly, neither grounding
  nor theory-of-mind peer prediction can deepen.

**User decision (recorded):** the goal is **genuine grounded AGI**, explicitly *not* a trained-network chatbot
that emits "4" by pattern-completion. This is the slow Darwinian road; a typeable "2+2=4" is far off and, if
reached, will be *real* rather than a statistical echo. Phase B (evolvable actuators) is therefore the correct
next build — not merely to de-magic fixed I/O, but because widening what an organism can *do* is the load-bearing
prerequisite for grounded cognition and for peer prediction to become worth ascending. `Books` stays temporarily
as the survival scaffold while the grounded/peer economy is built to replace it.
