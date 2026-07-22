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