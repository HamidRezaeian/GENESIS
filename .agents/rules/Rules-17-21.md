---
trigger: always_on
---

# GENESIS Agent Rules — 17–21

## Rule 17: No arbitrary selection-relevant constants
Classify every relevant value as hardware-derived (H), evolvable/DNA-encoded (E), structural engineering bound, mathematical invariant, empirical model parameter, or ISA opcode (O). Document derivation, provenance, default, and experiment. Never silently tune. Experimental softening must remain scoped and must not replace physical defaults.

## Rule 18: Falsifiable finish line
Use the binding `Docs/Architecture/Ascent.md` finish line: **A** capability `C(t)` rises at least 25% in monotone trend for at least 5M ticks without baseline regression; **B** learning beats a matched learning-ablation control; **C** `C/footprint` is non-decreasing. Metrics are observation-only. Validate each load-bearing assumption in isolation before adding mechanics. If corrected, task-matched learning cannot beat ablation, change the substrate hypothesis rather than adding economy levers.

## Rule 19: Memory capacity and dynamic RAM
Record all CAM configuration in every dependent experiment; CAM parameters must be env-gated and H/E-grounded, and capacity changes require ablation. Dynamic compact RAM follows `live_size = book_bytes + alive_organisms`, contains no blank cells, reallocates only between kernel ticks, and remaps positions on book/population changes. Kernel bounds use runtime array length. Solved content may shrink the universe only through audited compaction. ISA markers carry identity, not tunable physics.

## Rule 20: Shortcut accountability
For every positive cognitive claim: identify possible shortcuts (echo, bigrams, position, skewed marginals, authored/oracle logic), run format- and marginal-matched NULL controls, replicate under Rule 3, and report claim-control delta. A non-positive or insignificant delta does not support the claim. Oracle probes and theoretical key counts are diagnostics, never organism capability; the substrate must learn the capability without hand-set solution weights.

## Rule 21: Physical Grounding and Brain-Inspired Efficiency—no game mechanics
GENESIS is a physical substrate, not a tuned game.

All computational costs must be measured in actual hardware cycles (no virtual 
shortcuts). The system must strive for **brain-like computational efficiency**: 
achieving high intelligence with minimal energy consumption, inspired by 
biological neural systems.

Biological reference: Human brains achieve complex cognition (reasoning, 
generalization, adaptation) with approximately 20W power consumption. This 
demonstrates that powerful intelligence does not require massive energy budgets.

Design principle: Efficiency is not just measurement — it is a core objective. 
Architectures should be evaluated on **capability per unit of computational cost**, 
not just raw capability.

1. **Costs:** charge measured host work—CPU/GPU cycles, RAM traffic, storage I/O, time, and where available joules—not invented points.
2. **Parameters:** every tunable threshold, rate, gain, radius, capacity, or time constant must be H-derived or E-encoded. Otherwise derive, evolve, or delete it.
3. **ISA:** markers/opcodes are allowed only as documented identifiers without tunable physics.
4. **Tuning test:** if a number works because a designer searched for it, it is illegal. Defaults follow physical derivation; diagnostic overrides stay explicit.
5. **Income:** reward must be grounded in measured work/resources actually freed, not a fixed “difficulty” multiplier. Freeing is paid once and only after genuine internalization; if measured benefit does not exceed measured cost, report the null rather than tuning exchange rates.
6. **Capacity:** population limits derive at runtime from measured available/cgroup memory and measured bytes per organism, with documented engineering reserves/clamps and explicit user override. Dynamic live RAM remains compact within that hardware ceiling.
7. **Evolvable constants:** per-organism parameters are genome records decoded at spawn and mutated through inheritance. Default/flag-off behavior must remain regression-tested; adaptive benefit requires multi-seed selected-vs-neutral evidence, not mere mutational drift.
8. **Numba discipline:** kernel state uses preallocated typed arrays/scalars; avoid unsupported Python objects. Clear/bump JIT caches after kernel edits and run kernel-changing A/B arms in separate seeded processes.

### Binding empirical constraints
- Learning must include credit/error reaching silent-but-wanted outputs; reward-gated Hebbian STDP alone can prune but cannot recruit.
- Small, physically derived update steps are required; bang-bang plasticity is destructive.
- Deep working memory uses addressable external/CAM-like storage and learned routing, not only leaky voltage or passive latches.
- Fixed per-byte income and immediate clearing do not solve the metabolic ceiling; real clearing must preserve learnable structure, and complex work requires measured multi-byte work-unit accounting.
- Compact RAM and hardware-aware capacity changes require executable invariant probes, not assertion-only validation.
