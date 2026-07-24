# GENESIS FIXED RULES — Consolidated and Revised

> **Status:** Proposal. Supersedes `RULES.md` once ratified per `Q.md` voting protocol.
> **Date:** 2026-07-24
> **Author:** Clusy Agent, based on Exp 30–68 findings and `Docs/Ascent.md` (2026-07-16) kill criterion.
>
> **Convention:** [ R ] = substantially revised from original; [ N ] = new (fills a gap or adds
> post-Exp-68 accountability); [ U ] = unchanged in substance, wording may be modernised.
>
> Every change has a footnote at the end explaining the empirical evidence that motivated it.

---

## PREAMBLE

Same as `Q.md`: GENESIS must not be designed as a machine that is told how to become intelligent.
It must be designed as a substrate in which life can persist, variation can accumulate, learning can
occur, memory can matter, prediction can provide real advantage, cooperation can emerge, failure has
consequences, and intelligence can become a genuine evolutionary solution.

The project's ultimate responsibility is to the question, not to a specific substrate hypothesis.

---

## Category A — Scientific Principles

### Rule 1: Mandatory Project Context and Document Synchronisation [ U ]

At the exact start of any new session or task, before writing code or analysing implementation logic,
the agent MUST explicitly read the current project documentation (`Docs/ARD.md`, `Docs/PRD.md`,
`Docs/Roadmap.md`, `Docs/Article_Draft.md`, `Docs/Result.md`, `Docs/Ascent.md`).

No implementation or architectural analysis may begin until the relevant project context has been
loaded. At the end of every task, especially when files are added, deleted, architectures change,
experiments complete, or phases advance, the authoritative `Docs/` files MUST be updated.

**Observation (2026-07-24):** `Docs/Result.md` and `Docs/Roadmap.md` end at Exp 57 (2026-07-22).
Experiments 30, 68, and all intermediate work are not recorded. This violates Rule 1. → See
footnote [1].

---

### Rule 2: Hierarchical Falsification [ N ] — *fills gap after Rule 1*

Every experimental claim must have a **pre-registered falsification criterion** before the experiment
that tests it begins. The criterion must be:

- **Quantitative** (a numeric threshold, e.g., "chance level = 12.5%", "Δ > 0 with p < 0.05").
- **Binding** (if the criterion fails, the claim is abandoned or revised — never silently ignored).
- **Archived** in `Docs/Ascent.md` or the experiment's own header.

A claim with no falsification criterion is not a scientific hypothesis; it is a narrative.
Experiments without kill criteria are not experiments — they are demonstrations. [2]

---

### Rule 3: Reproducibility and Multi-Seed Discipline [ N ] — *fills gap after Rule 2*

A single-seed result (one random seed) is **preliminary** and must never be presented as a validated
finding. Every quantitative claim must be reproduced across **at least 5 independent seeds** and
reported with mean ± standard deviation. The delta (experimental − control) and its z-score (or
equivalent) must be computed.

This rule exists because of a direct empirical lesson: a single-seed Δ of +11 pp (Exp 68, seed 42)
suggested compositionality was real; the 8-seed replication produced Δ = −7 pp ± 17, z = −1.22,
demonstrating the single-seed result was noise-dominated. [3]

---

### Rule 4: Mandatory Scientific Skepticism [ U ]

The entire system architecture, codebase, physical model, evolutionary model, and theoretical
assumptions MUST be treated with a highly critical and rigorous perspective.

No result may be accepted as evidence of AGI-like capability unless it has been (a) replicated,
(b) tested against a control that removes known measurement shortcuts (see Rule 20), and (c)
evaluated by an independent falsification criterion (Rule 2).

---

## Category B — Substrate Principles

### Rule 5: The Proto-Cognitive Ancestor Boundary [ R ]

**Principle unchanged:** The initial ancestor MUST NOT contain pre-engineered general intelligence.
Pre-engineered cognitive modules (attention, planning, arithmetic) are forbidden. General-purpose
survival primitives (energy seeking, reproduction, prediction) are permitted.

**Revised clause:** Empirical model parameters discovered during diagnostic experiments (Exp 30,
Exp 34, Exp 68) — including `HOMEOSTATIC_LAMBDA`, `CAM_SLOTS`, `CAM_MATCH_THRESHOLD`,
`CAM_WRITE_THRESHOLD` — MUST be documented (Rule 17, Category E) rather than silently tuned. They
are engineering tools that keep the learning substrate viable, not cognitive modules. The boundary
between "permitted survival primitive" and "forbidden cognitive module" must be reviewed after every
falsification cycle. [4]

---

### Rule 6: The Prime Directive [ U ]

The system exists to evolve open-ended intelligence. Nothing in the design may permanently prevent
this outcome. No short-term fix that closes the path to open-endedness is permitted.

---

### Rule 7: Emergent Efficiency Over Authored Limits [ U ]

Efficiency must emerge from substrate physics, not be authored as a top-down penalty. If efficiency
pressure is too weak, the remedy must correct the underlying substrate accounting or resource
economy, not introduce a new top-down score.

---

### Rule 8: Experimental Provenance and Directory Integrity [ U ]

Clean, organised directory structure. Dead-end exploratory artifacts may be removed only when their
historical value has been evaluated. Any artifact needed to reproduce a numbered experiment or result
cited by `Docs/Result.md`, `Docs/Article_Draft.md`, or another authoritative research document must
be preserved or archived.

---

### Rule 9: The Autotelic Imperative [ U ]

**Unchanged principle:** The final evolutionary environment MUST NOT depend on human-authored puzzles
or a predefined sequence of challenges.

**Clarification (already in original):** Temporary artificial tests may be used during development to
validate substrate properties, provided they are clearly identified as diagnostic experiments and are
not silently treated as the final evolutionary environment.

Exp 68 is a diagnostic experiment under this clause. Its shortcut-proof curriculum is an artificial
test, not the final evolutionary environment. The Finding — no compositionality under controlled
conditions — is a **substrate characterisation**, not a definitive statement about the autotelic
regime. [5]

---

### Rule 10: Diagnostic Experiments and the Exclusion Clause [ N ] — *fills gap after Rule 9*

A diagnostic experiment may inject a controlled curriculum with known statistical properties, provided:

1. The curriculum is clearly artificial (uniform alphabet, controlled entropy, etc.) and the deviation
   from the autotelic ideal is stated in the experiment header.
2. The purpose is to test a specific substrate capacity — never to author a curriculum that secretly
   contains the answer.
3. **The Exclusion Clause:** Any capacity demonstrated only on a diagnostic curriculum that removes
   known shortcuts is **pending** — it must be replicated on the autotelic curriculum (or on a
   shortcut-uncontrolled variant) to be claimed as a genuine substrate property. Positive results from
   diagnostic experiments are necessary, not sufficient, for an "ascent" claim under Rule 6.

Exp 68's null result is not subject to the Exclusion Clause (it is negative), but the clause is
documented for future positive findings. [6]

---

## Category C — Evolutionary Principles

### Rule 11: Biological Computation as a Hypothesis, Not a Dogma [ U ]

The project must not assume that modern ANN architectures are either sufficient or optimal for general
intelligence. No architecture should be selected or rejected solely because it resembles or differs
from a modern ANN. Architectures must ultimately compete under comparable physical constraints.

---

### Rule 12: Academic Publication and Scientific Record [ U ]

`Docs/Article_Draft.md` is the authoritative academic article. It must be maintained to the standard
expected of a serious peer-reviewed scientific publication: precise methodology, reproducible
experimental conditions, quantitative measurements, and honest documentation of negative results.

---

### Rule 13: True Open-Endedness and Non-Terminating Criteria [ U ]

The evolutionary environment must be capable of producing genuinely novel behaviours indefinitely.
A fixed curriculum where every possible behaviour is enumerable suffices for characterisation but
not for an open-endedness claim.

---

### Rule 14: Stable Population Dynamics with Selective Pressure [ R ]

**Principle unchanged:** Total population extinction should be rare, and the Ark/refugium must remain
an emergency backstop rather than the normal rhythm of evolution.

**Revised clause:** Empirical observation (Exp 68) shows that on shortcut-free, maximally-entropic
curricula, the refugium fires **~40 %–75 % of all ticks** and the population hovers at **~20–24
organisms** — sustained entirely by artificial reseeding. This constitutes a **known violation** of
the "emergency backstop" ideal and is a **survivorship confound**: any accuracy measurement on such
a population is measured on a small, constantly-rescued remnant and may not reflect the substrate's
natural learning capacity.

**Obligation:** Every experiment that reports population size and refugium triggers must discuss
whether the refugium count exceeds 5 % of ticks. If it does, the population is on life support, and
the survivorship confound must be acknowledged in the experiment's interpretation. [7]

---

### Rule 15: Substrate Heterogeneity [ U ]

A substrate consisting only of one fungible computational currency and one homogeneous memory resource
may limit emergence. Before introducing artificial resources, the project must determine whether
naturally modelled heterogeneous computational resources can produce the desired effects.

---

### Rule 16: Death, Extinction, and the Ark as Bounded Resource [ N ] — *fills gap after Rule 15*

Extinction must be **possible** within an experiment window, and when it occurs it must be **final**
for the genomes lost: no ghost populations, no infinite saves. The Ark (fossil pool / refugium) must
be documented as a **bounded, energy-costly mechanism**, not an infinite checkpoint.

**Minimum disclosure for every run:** total extinctions, refugium trigger count, and Ark reseed count.
If the refugium fires more than once every 100 ticks averaged over the run, the run is in
"life-support regime" and all accuracy/capability metrics must be interpreted with the survivorship
confound explicitly acknowledged. [8]

---

### Rule 16a (formerly Rule 16 — "Existing Law Mapped to the Substrate"): Preserved as ARCHIVED

The original Rule 16 from `RULES.md` (which covered `GENESIS_STIGMERGY`, `GENESIS_SUPER_RENT`, and
smart-contract-like economy mechanics built on the existing substrate) is **archived** — those
mechanisms are no longer being developed and the original text is preserved in `RULES.md` for
provenance. The number 16 has been re-assigned to the broader evolutionary principle above. [9]

---

## Category D — Engineering and Accountability

### Rule 17: No Arbitrary Selection-Relevant Constants [ R ]

**Principle unchanged:** The physics engine must not contain arbitrary, unexplained, silently tuned
parameters that shape selection.

**Revised clause:** All env-gated parameters discovered during diagnostic experiments (Exp 30, Exp 34,
Exp 68) MUST be listed in the table below, classified by provenance, and updated whenever a new
experiment changes a default.

#### Parameter Disclosure Table (Exp 30–68 Relevant)

| Parameter | Default | Provenance (Rule 17 class) | Discovered in | Justification |
|-----------|---------|---------------------------|---------------|---------------|
| `HOMEOSTATIC_LAMBDA` | 0.01 | (E) Empirical Model Parameter | Exp 30 Arm C/D | Restoring force toward DNA-birth weight that prevents STDP drift while preserving local adaptation. λ=0.01 gives a drift-ceiling of ~10 % over a lifetime at typical STDP rates. |
| `CAM` | 1 (on) | (E) Empirical | Exp 30 Arm F | Compositional Memory substrate — associative key-value store. Default ON after Exp 30 showed frozen STDP (Arm C) beats learned STDP (Arm A). The CAM provides working memory the leaky membrane cannot. |
| `CAM_SLOTS` | 32 | (C) Structural Engineering Bound | Exp 30 Arm J/ K | 32 slots proven sufficient to store all 16 cue→answer mappings (4 × 4 compositionality, Arm K). For 8 × 8 compositionality (64 pairs) 32 slots are insufficient — the colony partially memorises ≈32 pairs and gets chance on the rest. This is an acknowledged capacity limit. |
| `CAM_MATCH_THRESHOLD` | 6 | (E) Empirical | Original engine | Number of input bits that must match a CAM key to trigger a read. Derived from hardware-like bit width reasoning. |
| `CAM_WRITE_THRESHOLD` | 3 | (E) Empirical | Exp 30 v2 (CAM v2) | Associative match strength required to trigger a CAM write. Write occurs on CORRECT PREDICTION only (reward-gated). |
| `STDP_COSTONLY` | 0 (off) | (B) DNA-Encoded / (E) Empirical | Exp 30 Arm C | When 1, STDP's energy cost is charged but the weight update is zeroed. Used for the control that isolates weight drift (Arm C). |
| `STRUCTURAL_PLASTICITY` | 1 (on) | (E) Empirical | Exp 30 Arm N | Growth (rewire weak synapses) and pruning. Enabled by default. `SP_MAX_GROWTH=2`, `SP_CULL_THRESHOLD=15`. |
| `DEPLETE` | 1 (on) | (E) Empirical | Exp 24 / Exp 30 Arm G | When 1, reading draws from finite per-cell fuel (CELL_STATES = 256.0) rather than unlimited income. Necessary for selective pressure (learn or die). |

All parameters are env-gated (`GENESIS_<NAME>=<value>`) and inspectable at runtime. No parameter may
be silently hard-coded without a written justification (this rule) and a corresponding env var. [10]

---

### Rule 18: The Falsifiable Finish Line [ R ]

**Principle unchanged:** The search must terminate on a pre-registered quantitative criterion, not
drift indefinitely.

**Revised clause:** The binding finish line is `Docs/Ascent.md` §2, requiring ALL THREE of:
- **A:** `C(t)` monotone up ≥25 % over 5 M ticks (prediction-depth metric).
- **B:** STDP-ablation control shows learning is load-bearing.
- **C:** Efficiency (capability per brain footprint) non-decreasing.

**Data point recorded (Exp 68, 2026-07-24):** Controlled Latin-square compositionality test on
shortcut-proof uniform curriculum. 8 seeds × 80 k ticks. RULE (answer = (c1+c2) mod 8) vs NULL
(answer = random). **Δ = −7 pp ± 17, z = −1.22 (n.s.).** Conclusion: the current substrate does NOT
support systematic compositionality under shortcut-proof conditions. Prior 70 % compositionality
(Arm K/ L) was a measurement artifact (structure + bigram shortcut).

This does NOT trigger Ascent.md's kill criterion (which concerns criterion B — learning
load-bearing — which Exp 30 confirmed as positive: STDP matters). But it informs the evaluation:
with no compositionality, criterion A (capability rise over 5 M ticks) appears unreachable on the
current substrate without a substrate-level change. [11]

---

### Rule 19: CAM Parameter Provenance and Environmental Gating [ N ]

All CAM-related parameters MUST be:
1. **Env-gated** (read from `os.environ` at startup, default 32 for slots).
2. **Documented** in the Rule 17 parameter table (above) with their provenance class.
3. **Referenced** in the experiment header that first validated their value (Exp 30 Arm J for 32 slots).

Rationale: CAM is the substrate's primary working-memory mechanism. Its capacity (`CAM_SLOTS`) is a
hard bound on how many distinct cue→answer associations a single organism can store. Every
experiment that relies on CAM must record `CAM_SLOTS` in its configuration. Changing the default
requires a dedicated ablation experiment (analogous to Exp 30 Arm F → Arm J). [12]

---

### Rule 20: Shortcut Accountability [ N ]

When a positive cognitive claim is made (e.g., "organisms exhibit compositionality", "organisms
perform multi-step reasoning"), the **burden of proof** is on the claimant to:

1. **Identify** the statistical shortcuts the organisms COULD be exploiting (bigram skew, positional
   structure, non-uniform marginals, echo reflex, etc.).
2. **Control** for each identified shortcut by running a NULL condition — identical format, structure,
   and marginals — where the claimed dependency is replaced with a random (independent) relationship.
3. **Replicate** across ≥5 seeds (Rule 3).
4. **Report** the delta (claim − control) with the same standards as any experimental result.

If Δ ≤ 0 (or not significant), the claim is **not supported** and must not be presented as a positive
finding. If Δ > 0 and significant, the claim survives the shortcut accountability check but the
burden of proof shifts to the next level (see Rule 10: diagnostic → autotelic).

**Exp 68 serves as the procedural precedent:** the prior 70 % compositionality survived the Bigram
Shortcut check (Steps 1–2) only to fail the replication check (Step 3). Future positive claims must
clear all four steps before acceptance. [13]

---

## Footnotes

[1] **Rule 1 gap.** `Docs/Result.md` last experiment: Exp 57 (2026-07-22). `Docs/Roadmap.md` last
experiment: Exp 57. Exp 30 (STDP ablation, six arms), Exp 34 (REMAP), Exp 59–67 (probes), and
Exp 68 (shortcut-proof compositionality) are all absent. Updating these documents is a pending task.

[2] **Rule 2 motivation.** The Exp 30–68 arc: Exp 30 Arm K reported 70 % compositionality without a
pre-registered falsification criterion for what would disprove compositionality. When we later built
Exp 68 with a quantitative Δ test (z < 2.0 → null), the result was null. Had Rule 2 existed before
Arm K, the 70 % would have been flagged as preliminary until the control (RULE vs NULL) was run.

[3] **Rule 3 motivation (direct empirical).** Exp 68 single-seed (seed 42, 40 k ticks, overall mode):
RULE=63 %, NULL=52 %, Δ=+11 pp → looked like compositionality. 8-seed replication (80 k ticks):
Δ=−7 pp, z=−1.22 → null. The single seed was a fluke. This rule prevents future wasted effort on
single-seed hints.

[4] **Rule 5 revision motivation.** The engine code contains `HOMEOSTATIC_LAMBDA=0.01`,
`CAM_SLOTS=32`, `CAM_MATCH_THRESHOLD=6`, `CAM_WRITE_THRESHOLD=3` — all discovered experimentally
(Exp 30, original engine) and now deployed as defaults. These are not cognitive modules (they don't
implement reasoning or planning) but they ARE engineered parameters that shape selection. Per
Rule 17, they belong in Category E (Empirical Model Parameter) and must be documented.

[5] **Rule 9 clarification.** Exp 68's curriculum (uniform 8-symbol alphabet, Latin-square rule) is
a temporary artificial test under the original Rule 9's exception clause. Its negative result
therefore does NOT constitute an Ascent.md kill-criterion-level failure — it characterises the
substrate under a specific artificial condition.

[6] **Rule 10 (new) rationale.** The Exclusion Clause closes a loophole: a positive compositionality
result on a diagnostic curriculum (e.g., Arm K's 16-pair random lookup) should not be automatically
generalised to the autotelic environment. The clause exists to prevent false positives — the very
phenomenon that motivated Exp 68.

[7] **Rule 14 revision motivation.** Exp 68 triggered the refugium 30 k–60 k times in 80 k ticks,
across all 8 seeds. Population stabilised at 20–24 organisms (initial 300). The colony is on life
support — the refugium has become the normal rhythm, not an emergency backstop. This must be
disclosed as a survivorship confound.

[8] **Rule 16 (new) rationale.** Exp 68 logged zero extinctions because the refugium prevented them.
Zero extinctions in a run where the refugium fires 50 % of ticks is misleading — the mechnism
masks non-viability. Rule 16 requires the raw refugium count to be reported so the reader can
assess whether "zero extinctions" reflects genuine viability or life support.

[9] **Rule 16a rationale.** Original Rule 16 (stigmergy/super-rent economy) is no longer under
active development (the `Docs/Roadmap.md` strategic pivot identifies this). It is preserved as
archived text in `RULES.md` but the number is re-used for the more fundamental evolutionary
principle. All archived text is clearly marked as historical.

[10] **Rule 17 revision motivation.** Before Exp 30, parameters like `CAM_SLOTS=8` (original default)
were silently baked into the engine. Exp 30 Arm J demonstrated that 32 slots are necessary and
sufficient for 4 × 4 compositionality. These parameters must now be documented with their provenance
and justification, and changed only via dedicated ablation experiments.

[11] **Rule 18 revision motivation.** Ascent.md (2026-07-16) fixed the finish line but did not
predict Exp 68's result. The null compositionality finding directly informs the evaluation of
criterion A: if the substrate cannot learn compositionality under controlled conditions, it is
unlikely to produce a monotone 25 % rise in prediction-depth over 5 M ticks. This is a checkpoint,
not a trigger of the kill criterion (which concerns criterion B — load-bearing learning — confirmed
positive in Exp 30).

[12] **Rule 19 rationale (post-Exp 30).** The chat history mentions "Rule 19: CAM slots env-gated,
default 32" as a planned addition that was never committed. This rule formalises that requirement
and extends it to all CAM parameters. CAM is load-bearing for any claim of working memory —
unilateral changes to its capacity would invalidate cross-experiment comparisons.

[13] **Rule 20 rationale (post-Exp 68).** The prior 70 % compositionality (Arm K) was accepted as a
positive result for ~24 hours before Exp 68's controlled test revealed it as an artifact. Rule 20
ensures that future positive claims are challenged at the moment they are made, not weeks later when
a dedicated falsification experiment is built. The burden of proof is on the positive claim.

---

## Appendix: Exp 68 Condensed Technical Synopsis

| Property | Value |
|----------|-------|
| Numbered as | Exp 68 |
| Date | 2026-07-24 |
| Claim tested | "Organisms use cue1 + cue2 to predict the compositional answer" |
| Previous evidence | Arm K: ~70 % on 4 × 4 random table (single seed, contaminated by structure + bigram) |
| Controlled condition | RULE: answer = (c1 + c2) mod 8 (Latin square). NULL: answer random, identical format. |
| Curriculum | Uniform 8-symbol alphabet. Constant-noise scaffold `['a']`. Period-7 stream `[c1 n n c2 n n A]`. |
| Metric | Overall next-byte accuracy (upper bound: chance=12.5 %, trivially-solvable noise=62.5 %). |
| Seeds | 8 (42, 123, 7, 2024, 999, 314, 2718, 1618) |
| Runs | 16 (8 × 2) at 80 k ticks/run |
| RULE accuracy | 63.0 % ± 9.4 |
| NULL accuracy | 70.2 % ± 9.6 |
| Δ (RULE − NULL) | −7.2 pp ± 16.6 |
| z-score | −1.22 (p > 0.2, NOT significant) |
| Refugium | 30 k–60 k triggers/80 k ticks (∼40–75 % of ticks, life-support regime) |
| Population | Stable at 20–24 organisms (initial 300; non-viable without constant reseeding) |
| Verdict | **No compositionality detected.** The prior 70 % was a structure + bigram artifact. |
| Deposited | `src/exp68_shortcut_proof_compositionality_probe.py`, `exp68_shortcut_proof_results_overall.json`, `exp68_verdict.png` |
| Commit | `93c0ec5` on `main` |
