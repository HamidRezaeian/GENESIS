---
trigger: always_on
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
