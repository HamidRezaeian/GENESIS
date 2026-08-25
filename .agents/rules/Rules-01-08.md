---
trigger: always_on
---

# GENESIS Agent Rules — 1–8

These rules are binding. Distinguish what was designed, assumed, measured, emerged, and falsified.

## Rule 1: Context and documentation sync
Before implementation or architectural analysis, read the relevant current documents in `Docs/` and `Docs/Architecture/` (`Docs/ARD.md`, `Docs/PRD.md`, `Docs/Roadmap.md`, `Docs/Paper/Article_Draft.md`, `Docs/Result.md`, `Docs/Architecture/Ascent.md`, `Docs/Architecture/FixedRules.md`, `Docs/Architecture/DYNAMIC_COMPACT_RAM_DESIGN.md`, `Docs/Architecture/HARDWARE_AWARE_CAPACITY_DESIGN.md`, `Docs/Architecture/RULE21_2_ENGINE_REFACTOR_DESIGN.md`, and `Docs/Architecture/RULE21_INCOME_REFACTOR_DESIGN.md`). After changes or experiments, update authoritative documentation; mark superseded material as historical rather than presenting it as current.

## Rule 2: Pre-register falsification
Before each experiment, archive a quantitative, binding falsification criterion in `Docs/Architecture/Ascent.md` or the experiment header. A failed criterion invalidates or revises the claim; it must never be ignored after observing results.

## Rule 3: Reproduce across seeds
Treat single-seed findings as preliminary. Validate quantitative claims with at least five independent seeds and report mean, standard deviation, experimental-control delta, and z-score or an equivalent statistic.

## Rule 4: Mandatory skepticism
Actively test biological and physical assumptions, arbitrary constants, bottlenecks, shortcuts, hidden top-down selection, evolutionary loopholes, and scripted-game mechanics. Accept cognitive claims only after replication, shortcut-removing controls, and a pre-registered test.

## Rule 5: Proto-cognitive ancestor boundary
The ancestor may contain minimal general survival primitives: sensing, energy acquisition, homeostasis, plasticity, replication, and failure response. It must not contain authored reasoning, planning, domain solutions, human knowledge/language, target computation, or general intelligence. Diagnostic oracle code is not organism capability. Review and document any ambiguous primitive.

## Rule 6 — Prime Directive

GENESIS pursues open-ended intelligence progressing from AGI toward AXI: genuine in-lifetime learning, memory, adaptation, generalization, reasoning, and goal-directed behavior across novel situations.

The long-horizon deployment target is execution on commodity home-computer hardware: a single consumer workstation-class CPU/GPU with a reasonable memory footprint.

This hardware target is a design objective and reporting envelope, not an early-research disqualification criterion. Research prototypes may exceed the target only when explicitly labelled as diagnostic or substrate-comparison runs, with measured cost, memory, and wall-time reported under Rule 21.

A claim of AGI/AXI progress is invalid unless it passes the Rule 18 capability, learning-ablation, generality, and efficiency gates.

## Rule 7: Emergent efficiency
Selection must arise from honest substrate resource accounting, never an authored IQ/efficiency score. Charge actual computation, memory, traffic, communication, neural activity, and plasticity costs where applicable. Observation metrics must not control survival, reproduction, inheritance, ranking, or reseeding. Repair weak pressure through physical accounting/economy, not penalties by fiat.

## Rule 8: Provenance and directory integrity
Keep the repository clean without destroying reproducibility. Preserve/archive every artifact needed for cited experiments and negative results. Agent experiments belong under `tests/clusy/qwen/<experiment_name>/` with drivers, analysis, `results/`, `figures/`, a verdict in `tests/clusy/qwen/notes/`, and a README entry. Drivers must discover the repository root from `__file__` and add `<root>/src` to `sys.path`.