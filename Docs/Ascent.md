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

## 5. What changes operationally

- New experiments are pre-registered against §2's criteria before running; a run that doesn't move A/B/C
  is a **closed branch**, not a prompt for a new mechanic.
- `Rules.md` gains **Rule 18** (pre-registered falsifiable finish line + validate the load-bearing
  assumption before adding mechanics) so this discipline is permanent, not a one-off.
- The UI (next task) will surface the A/B/C probes (`C(t)`, learning-ablation delta, `C/footprint`) so
  the finish line is watchable live, not reconstructed from logs.
