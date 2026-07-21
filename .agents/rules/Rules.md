---
trigger: always_on
---

---

# GENESIS PROJECT — FUNDAMENTAL RESEARCH AND ENGINEERING RULES

## DOCUMENT STATUS

This document defines the non-negotiable scientific, physical, evolutionary, and engineering principles governing the GENESIS project.

These rules are organized conceptually into:

1. **Scientific principles** — how claims are evaluated.
2. **Substrate principles** — what the computational universe is allowed to do.
3. **Evolutionary principles** — how life and capability may emerge.
4. **Research hypotheses** — ideas that must remain falsifiable.
5. **Engineering principles** — how the project is built and documented.

A research hypothesis must never be silently treated as an established physical law.

---

# RULE 1: MANDATORY PROJECT CONTEXT AND DOCUMENT SYNCHRONISATION

At the exact start of any new session or task, before writing code or analyzing implementation logic, the agent MUST explicitly read the current project documentation:

* `Docs/ARD.md`
* `Docs/PRD.md`
* `Docs/Roadmap.md`
* `Docs/Article_Draft.md`
* `Docs/Result.md`

No implementation or architectural analysis may begin until the relevant project context has been loaded.

At the end of every task, especially when files are added, deleted, architectures change, experiments complete, or phases advance, the authoritative `Docs/` files MUST be updated to accurately reflect the current state of the codebase and research.

Obsolete architecture, deleted scripts, superseded policies, and historical approaches must never remain documented as current.

Historical information must be explicitly marked as historical rather than silently deleted when it is required for scientific provenance.

---

# RULE 4: MANDATORY SCIENTIFIC SKEPTICISM

The entire system architecture, codebase, physical model, evolutionary model, and theoretical assumptions MUST be treated with a highly critical and rigorous perspective.

The agent MUST NOT blindly agree with existing implementations or project assumptions.

It must actively search for:

* biological inaccuracies;
* physical inaccuracies;
* hidden top-down selection;
* arbitrary constants;
* unvalidated assumptions;
* performance bottlenecks;
* emergent failure modes;
* evolutionary loopholes;
* unintended fitness shortcuts;
* mechanisms that reward complexity without capability;
* mechanisms that reward replication rather than intelligence;
* and designs that make the simulation behave like a scripted game rather than an open-ended system.

Every important assumption should be treated as a hypothesis until supported by evidence.

A mechanism that appears to promote intelligence must not be assumed to do so merely because it was designed with that intention.

---

# RULE 5: THE PROTO-COGNITIVE ANCESTOR AND BOTTOM-UP EVOLUTION

The universe may be seeded with a **Proto-Cognitive Ancestor** rather than a completely inert or biologically meaningless blank slate.

The Proto-Cognitive Ancestor may contain minimal, general-purpose primitives necessary for autonomous biological-style existence, including:

* self-maintenance;
* basic homeostatic regulation;
* environmental sensing;
* energy acquisition;
* adaptive plasticity;
* replication;
* and basic damage or failure response.

However, the initial ancestor MUST NOT contain pre-engineered general intelligence.

The following must not be directly hardcoded as completed cognitive capabilities:

* general reasoning;
* domain-specific problem-solving strategies;
* prebuilt planning algorithms;
* prebuilt abstract reasoning;
* human knowledge;
* human language;
* predefined intelligence scores;
* or a hidden general-purpose solution to the environment.

The purpose of evolution is to transform a minimally viable proto-cognitive substrate into increasingly capable intelligence.

The physics engine MUST NOT contain arbitrary fitness functions or explicit intelligence rewards.

Selection must emerge from the interaction between organisms and the substrate.

If total extinction requires reseeding, reseeding MUST follow Rule 14:

* multiple genuinely distinct fossil lineages must be used;
* genetic recombination and fresh variation must be introduced;
* no single lineage may become a permanent "God genome";
* and the Ark must remain an emergency backstop rather than the normal rhythm of evolution.

Dead genetic material may remain in the memory substrate and may participate in horizontal genetic transfer where permitted by the substrate.

The project must maintain a clear distinction between:

```text
Permitted:
initial general-purpose life primitives

Forbidden:
pre-engineered general intelligence
```

Any uncertainty about this boundary must be explicitly documented as a research question rather than silently resolved through implementation.

---

# RULE 6: THE PRIME DIRECTIVE — OPEN-ENDED GENERAL INTELLIGENCE

The ultimate objective of GENESIS is to evolve an energy-efficient, open-ended cognitive system capable of genuine:

* in-lifetime learning;
* memory formation and maintenance;
* adaptation to novel conditions;
* generalization;
* reasoning;
* goal-directed behavior;
* and increasingly general intelligence.

The human brain is a major biological reference system and a source of architectural hypotheses.

However, the project MUST NOT assume that a literal structural copy of the human brain is the only path to AGI.

The target is therefore:

```text
functional and computational convergence toward general intelligence,
not mandatory structural identity with the human brain.
```

The project may draw inspiration from:

* sparse temporal activity;
* massive parallelism;
* local learning;
* neuromodulation;
* long-term memory;
* hierarchical organization;
* energy-efficient computation;
* and other biological principles.

These are hypotheses and design references unless experimentally validated.

No biological architecture is automatically correct merely because it exists in the human brain.

The approximate energy efficiency of the biological brain, commonly associated with the ~20-watt scale, is a reference point for computational efficiency rather than a literal electrical-power requirement imposed on the host machine.

The project must seek increasing capability without allowing computational cost to grow without bound as the only path to progress.

---

# RULE 7: EMERGENT COMPUTATIONAL EFFICIENCY

Computational efficiency MUST be selected through real substrate costs rather than a top-down intelligence or efficiency score.

If two lineages achieve comparable long-term survival and reproductive success under comparable conditions, the lineage achieving that outcome with lower real computational and memory cost demonstrates greater substrate efficiency.

Efficiency must emerge from the economy of the universe.

Every executed operation that consumes real computational resources must incur an honest cost according to the substrate model, including where applicable:

* computation;
* memory access;
* memory allocation;
* data movement;
* communication;
* neural state updates;
* synaptic transmission;
* plasticity updates;
* and other measurable operations.

It is forbidden to select organisms by an externally calculated "efficiency score" or "IQ-per-cycle" metric.

Observation-only metrics are permitted.

They MUST NOT directly determine:

* survival;
* death;
* reproduction;
* ranking;
* reseeding;
* or genetic inheritance.

If efficiency pressure is too weak, the remedy must be to correct the underlying substrate accounting or resource economy, not to introduce a new top-down score.

Costs must not punish mere existence when the real substrate cost is activity-dependent.

In particular, a sparse-in-time biological-style system must not be penalized simply for possessing inactive structures whose actual physical cost is negligible or appropriately accounted for elsewhere.

---

# RULE 8: EXPERIMENTAL PROVENANCE AND DIRECTORY INTEGRITY

The project must maintain a clean and organized directory structure.

Evolutionary outputs, checkpoints, milestones, and experiment artifacts must be stored in dedicated directories.

However, cleanup MUST NOT destroy scientific provenance.

Any script, configuration, checkpoint, or artifact required to reproduce a numbered experiment or result cited by:

* `Docs/Result.md`;
* `Docs/Article_Draft.md`;
* or another authoritative research document

must be preserved or archived.

Dead-end exploratory artifacts may be removed only when their historical value has been evaluated.

Preferred structure:

```text
Milestones/
    Experiment-001/
    Experiment-002/
    Experiment-003/

Archive/
    historical experiments
    superseded implementations
```

The root and source directories must not become repositories for temporary or obsolete files.

Cleanliness and reproducibility must both be preserved.

---

# RULE 9: THE AUTOTELIC IMPERATIVE

The final evolutionary environment MUST NOT depend on human-authored puzzles, explicit intelligence rewards, or a predefined sequence of challenges.

Temporary artificial tests may be used during development to validate substrate properties, provided they are clearly identified as diagnostic experiments and are not silently treated as the final evolutionary environment.

The final environment must not contain a human-defined:

```text
problem → solution → reward
```

pipeline as its fundamental evolutionary mechanism.

Instead, organisms must face consequences arising from the substrate itself, including where applicable:

* resource competition;
* environmental uncertainty;
* other organisms;
* entropy;
* spatial constraints;
* computational constraints;
* failure;
* persistence;
* and ecological interactions.

Capability probes are permitted for scientific observation.

They must never become hidden selection mechanisms.

The distinction is fundamental:

```text
Observation:
measure what an organism can do.

Selection:
determine what survives and reproduces.

These must remain separate.
```

---

# RULE 10: AVOID THE REPLICATION TRAP

The substrate must not permit simple, blind replication and spatial overwrite to become an unlimited path to evolutionary dominance.

If the only meaningful advantage is:

```text
execute faster
→ overwrite more space
→ replicate faster
```

the system is likely to evolve optimized replicators rather than increasingly capable cognitive organisms.

The substrate must therefore expose organisms to genuine constraints and interactions in which sensing, memory, adaptation, prediction, or other cognitive capabilities may provide real survival advantages.

However, the project MUST NOT assume that adding complexity automatically makes intelligence necessary.

The hypothesis must be empirically tested.

A representative validation should compare, under the same substrate:

```text
fast blind replicator
        VS
sensing/predictive organism
```

under conditions where the environment contains measurable, non-instantaneous change.

The result must determine whether the claimed intelligence advantage actually exists.

Environmental hazards must not normally be instantaneous, perfectly unpredictable total wipes that provide no physical opportunity for sensing, adaptation, or migration.

Hazards should, where physically justified, possess spatial or temporal gradients that permit organisms to encounter changing conditions and respond.

---

# RULE 11: BIOLOGICAL COMPUTATION AS A HYPOTHESIS, NOT A DOGMA

The project must not assume that modern ANN architectures are either sufficient or optimal for general intelligence.

Dense, synchronous, globally coordinated, brute-force computation must not be allowed to win solely through unlimited scaling if the substrate claims to model constrained computational resources.

However, weighted summation, matrix-like operations, or other mathematical primitives must not be rejected merely because modern ANNs use them.

The relevant question is computational organization.

The project should investigate whether intelligence can emerge through properties such as:

* temporal sparsity;
* local computation;
* asynchronous activity;
* event-driven processing;
* parallelism;
* modularity;
* local plasticity;
* hierarchical organization;
* and efficient communication.

The term **sparse** must be used precisely.

Unless explicitly stated otherwise, biological sparsity refers primarily to:

```text
low activity density over time
```

not necessarily:

```text
few structural connections.
```

A system with many potential connections but relatively few active events may still be temporally sparse.

No architecture should be selected or rejected solely because it resembles or differs from a modern ANN.

Architectures must ultimately compete under comparable physical constraints.

---

# RULE 12: ACADEMIC PUBLICATION AND SCIENTIFIC RECORD

`Docs/Article_Draft.md` is the authoritative academic article describing the GENESIS project.

It must be maintained to the standard expected of a serious peer-reviewed scientific publication.

The article must not be reduced to promotional summaries.

Where appropriate, it must contain:

* precise methodology;
* reproducible experimental conditions;
* quantitative measurements;
* cycle counts;
* memory usage;
* error rates;
* population dynamics;
* survival statistics;
* ablation results;
* limitations;
* negative results;
* and falsifying evidence.

The article must distinguish clearly between:

```text
established result
hypothesis
engineering assumption
historical implementation
and unresolved question.
```

When a rule or implementation changes, the current methodology must reflect the current policy.

Superseded approaches may remain in the historical record, but they must be explicitly identified as superseded.

---

# RULE 13: COMPUTATIONAL CONTENTION MUST BE SUBSTRATE-GROUNDED

The project must prevent unlimited brute-force scaling from becoming an unbounded path to dominance where such scaling contradicts the modeled substrate.

However, the system MUST NOT assume that dense code or dense memory is inherently slower.

In real computational systems, density may sometimes improve locality and performance.

Therefore, any density-dependent computational cost must arise from measurable substrate constraints such as:

* memory bandwidth contention;
* cache contention;
* shared execution-resource contention;
* communication bottlenecks;
* synchronization cost;
* or another explicitly modeled physical limitation.

A formula whose sole purpose is to make dense computation slower in order to force biological-style sparsity is not automatically a physical law.

If a contention model contains authored parameters or curves that cannot be derived from the substrate, those parameters must be:

1. scientifically justified;
2. experimentally validated;
3. explicitly identified as model assumptions;
4. or recorded as tracked technical debt.

The system must never hide a designer-imposed selection pressure behind the word "physics."

---

# RULE 14: RESILIENCE, DIVERSITY, AND EMERGENT ASCENSION

Capability must emerge from selection rather than from a top-down evolutionary ratchet.

Total population extinction should be rare where the substrate permits:

* standing genetic diversity;
* spatial refugia;
* ecological resilience;
* and self-sustaining resource dynamics.

The fossil or Elite Ark is an emergency backstop only.

It must not become the normal rhythm of the simulation.

If reseeding is required:

1. multiple genuinely distinct lineages must be selected;
2. no single lineage may dominate the fossil pool by policy;
3. genetic recombination must occur;
4. fresh variation must be introduced;
5. reseeding must not clone a single "God genome."

Short-term regression, drift, partial die-offs, and fitness-valley crossings are permitted and may be necessary for open-ended evolution.

"No regression" must therefore refer to long-run capability potential, not the prohibition of every short-term decline.

Capability measurements remain observation-only.

They must never directly determine who survives, dies, reproduces, or is reseeded.

The Ark must preserve diversity, not enforce a capability ratchet.

---

# RULE 15: SUBSTRATE-GROUNDED ABSTRACTION

The universe must not introduce arbitrary game mechanics that create free energy, free information, or free computational capability.

Abstract entities may exist in the simulation only when their behavior is reducible to measurable substrate operations, resources, constraints, or processes.

Every resource and environmental feature must ultimately correspond to something measurable in the substrate.

The simulation may model concepts such as:

* memory;
* execution capacity;
* bandwidth;
* latency;
* error;
* contention;
* persistence;
* storage;
* communication;
* and other computational resources.

However, the project must not pretend that an analogy is a literal physical identity.

For example:

```text
RAM is not literally geographical space.
CPU cycles are not literally thermodynamic energy.
Free memory is not literally biological food.
```

They may serve as modeled substrate resources only when their rules are explicitly defined and measurable.

The fundamental constraint is:

```text
No free energy.
No free information.
No free memory.
No free computation.
No free capability.
```

A resource must have a real cost, limitation, or conservation relationship within the modeled substrate.

The project should investigate whether heterogeneous substrate resources can naturally produce specialization, niche differentiation, cooperation, and trade.

Such heterogeneity must be grounded in genuine substrate differences where possible, such as:

* latency;
* bandwidth;
* error rate;
* execution availability;
* memory locality;
* or other measurable constraints.

Artificial resources must not be introduced merely to manufacture desired social behaviors.

---

# RULE 17: NO ARBITRARY SELECTION-RELEVANT CONSTANTS

The physics engine must not contain arbitrary, unexplained, silently tuned parameters that shape selection.

A numeric parameter must be classified as one of the following:

### (A) HARDWARE-DERIVED

A direct consequence of the modeled substrate.

Examples may include:

* bit width;
* byte width;
* address space;
* representable numeric ranges;
* measured hardware limits;
* or values directly derived from substrate structure.

### (B) DNA-ENCODED

A biological, adaptive, plasticity, or behavioral parameter that evolution is intended to optimize.

Examples may include:

* learning rates;
* thresholds;
* time constants;
* mutation rates;
* behavioral tendencies;
* and other evolvable biological parameters.

### (C) STRUCTURAL OR ENGINEERING BOUND

A declared resource allocation or capacity limit, such as:

* maximum population;
* allocated memory;
* experiment duration;
* array capacity;
* or other engineering constraints.

These must be explicitly disclosed as resource budgets and must not be misrepresented as fundamental physical laws.

### (D) MATHEMATICAL OR LOGICAL INVARIANT

A value required by the definition of an operation or mathematical structure rather than chosen as a selection pressure.

Examples include values arising directly from:

* Boolean logic;
* mathematical identity;
* indexing;
* sign;
* representation;
* or operation semantics.

### (E) EMPIRICAL MODEL PARAMETER

A parameter that cannot yet be derived from hardware or encoded in DNA but is necessary for an explicitly stated scientific model.

Such a parameter must:

* be documented;
* have a justification;
* be exposed for experimental analysis;
* never be silently tuned;
* and be recorded as tracked debt if the project intends to replace it with a more fundamental derivation.

A number is not automatically invalid merely because it is a number.

The actual prohibition is:

```text
unjustified
undocumented
silently tuned
selection-relevant parameters
```

Searching for a convenient value until evolution produces a desired result is not a valid substitute for physical derivation.

When a derived physical magnitude conflicts with performance on a harsh diagnostic experiment, the default physics must not be silently softened.

Any diagnostic softening must remain explicitly scoped to that experiment and must never become a hidden production selection mechanism.

---

# RULE 18: FALSIFIABLE FINISH LINE AND ANTI-DESIGN-LOOP DISCIPLINE

The project must maintain a pre-registered, quantitative definition of success and a falsifying kill criterion in:

```text
Docs/Ascent.md
```

before experiments intended to evaluate ascent are run.

The project must not continue indefinitely under a moving definition of success.

The finish line must define:

* measurable capability thresholds;
* required duration or persistence;
* reproducible evaluation conditions;
* and a clear criterion that constitutes success.

The kill criterion must define when the current substrate or strategy has been falsified sufficiently to require a fundamental change rather than another incremental mechanic.

A failed experiment must not automatically justify adding another mechanism.

Before adding a new economy, physics mechanic, or selection-relevant feature to improve capability, the load-bearing assumption behind the proposed change must first be tested in isolation whenever practical.

For an evolved learner, the central load-bearing assumption is:

```text
the organism can learn during its lifetime.
```

Therefore, an appropriate ablation must compare a system with plasticity enabled against an otherwise comparable system with the relevant learning mechanism disabled.

If lifetime learning is not demonstrated, repeatedly optimizing the survival economy around the organism is premature.

The correct sequence is:

```text
Validate the mind.
        ↓
Validate that learning affects behavior.
        ↓
Validate that capability generalizes.
        ↓
Only then modify the economy to select for increasingly capable minds.
```

A run that does not move the pre-registered finish-line metrics is a closed research branch unless new evidence justifies revising the scientific hypothesis itself.

The project must not enter an endless loop of:

```text
new mechanic
→ new failure
→ new mechanic
→ new failure
```

without a falsifiable objective.

All finish-line metrics remain observation-only and must never feed back into selection.

---

# OPEN RESEARCH QUESTIONS

The following are genuine research questions rather than silently resolved assumptions:

## 1. Proto-Cognitive Ancestor Boundary

What is the maximum amount of pre-engineered structure permitted at genesis before the system ceases to be a genuinely evolutionary intelligence experiment?

The current default is:

```text
general-purpose survival primitives:
permitted

pre-engineered general intelligence:
forbidden
```

This boundary must remain explicit and reviewable.

---

## 2. Human Brain Convergence

The human brain is a reference system, not a mandatory blueprint.

The project must determine experimentally which biological principles are:

* essential;
* useful;
* incidental;
* or replaceable.

Functional convergence is a valid success path even when structural convergence does not occur.

---

## 3. Substrate Heterogeneity

A substrate consisting only of one fungible computational currency and one homogeneous memory resource may limit the emergence of:

* specialization;
* trade;
* cooperation;
* niche differentiation;
* and ecological complexity.

Before introducing artificial resources, the project should determine whether naturally modeled heterogeneous computational resources can produce these effects.

---

## 4. Computational Contention

The project must determine whether computational contention can be derived from actual shared-substrate constraints rather than imposed as an authored density penalty.

---

# CORE PROJECT PRINCIPLE

GENESIS must not be designed as a machine that is told how to become intelligent.

It must be designed as a substrate in which:

```text
life can persist,
variation can accumulate,
learning can occur,
memory can matter,
prediction can provide real advantage,
cooperation can emerge,
failure has consequences,
and intelligence can become a genuine evolutionary solution.
```

The project's responsibility is not to guarantee intelligence.

Its responsibility is to create a scientifically defensible substrate in which intelligence, if it is a genuine solution to the constraints of the universe, has the opportunity to emerge.

The project must continuously distinguish:

```text
what was designed,
what was assumed,
what was measured,
what emerged,
and what was falsified.
```

Anything that cannot be distinguished between these categories is a threat to the scientific validity of the project.
