# GENESIS Research Protocol Rules 22–25

## Rule 22 — Brain-Inspired Efficiency Principle

Brain-like efficiency is a design objective, not a hard disqualification gate.

GENESIS should prefer architectures that improve capability per unit of measured physical cost: cycles, memory traffic, wall-time, footprint, and where available joules. The biological brain's high capability at low power is treated as an existence proof and regulative ideal, not as an implementation specification.

Architectures are ranked higher, all else equal, when they:
1. increase capability without proportional growth in footprint
2. reduce cost per learned behavior
3. exploit sparsity, locality, reuse, event-driven computation, or compression
4. preserve or improve Rule-18 capability under matched ablation controls

Failure to match biological efficiency does not invalidate a prototype. It must be reported honestly and used to guide the next design.


## Rule 23 — Substrate Falsification and Pivot Protocol

When a substrate hypothesis is formally falsified by a pre-registered Rule-18 kill criterion, no further mechanism, economy, reward, or tuning lever may be added to rescue that substrate as an AGI path.

After falsification, work on that substrate is allowed only for:
1. artifact analysis
2. reproducibility
3. extracting design requirements for the next substrate
4. historical documentation

A new AGI-path experiment must declare a new substrate hypothesis and explain which falsified mechanisms it retains, discards, or replaces.

**Current binding status:** SNN-on-RAM with local/Hebbian/STDP-style in-lifetime learning is falsified as the primary AGI substrate after the Rule-18 Exp-99 verdict. Future work must pivot substrate hypotheses while preserving the useful finding that two-timescale memory produced a real but unstable learning signal.


## Rule 24 — Containment and Corrigibility

Every prototype must be corrigible, interruptible, and contained by default.

Minimum requirements:
1. A human-controlled halt switch must stop learning, inference, reproduction, and external action within one scheduler tick
2. Prototypes must run without network access unless explicitly approved for a documented diagnostic
3. File-system write access is restricted to a declared sandbox
4. The system may not spawn subprocesses, modify its own source, exfiltrate artifacts, or persist outside the sandbox unless an explicit safety review approves it
5. Any behavior suggesting self-preservation, shutdown avoidance, deception, unauthorized replication, or resource acquisition must trigger an immediate pause and incident report


## Rule 25 — Capability Thresholds and Pause Conditions

GENESIS must maintain early-warning evaluations for capabilities that could increase risk if scaled:
1. autonomous long-horizon planning
2. self-modification or code generation
3. tool use beyond the sandbox
4. deception or hidden-state manipulation
5. replication or resource-seeking
6. cyber-relevant behavior
7. rapid capability gain without interpretability

If any prototype crosses a pre-registered threshold on two or more risk-relevant capabilities, scaling pauses until a written safety review is completed.
