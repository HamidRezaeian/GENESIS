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

## Rule 21 — Physical Grounding: No Game Mechanics

GENESIS is a physical substrate, not a tuned game.

All computational costs must be grounded in measured host work: CPU/GPU cycles, 
RAM traffic, storage I/O, wall-clock time, and where available joules. No virtual 
cost shortcuts, invented points, fixed difficulty multipliers, or designer-tuned 
exchange rates may control survival, reproduction, inheritance, ranking, or 
reseeding.

Every tunable threshold, rate, gain, radius, capacity, or time constant must be 
hardware-derived (H), evolvable/DNA-encoded (E), a mathematical invariant, an 
empirical model parameter with documented provenance, or an ISA opcode/marker 
with no tunable physics.

If a number works because the designer searched for it, it is illegal until it 
is derived, evolved, or deleted.