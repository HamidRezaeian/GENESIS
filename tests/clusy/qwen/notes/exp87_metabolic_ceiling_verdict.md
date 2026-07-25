# Exp 87 Verdict: The Metabolic Ceiling Nullifies Selection

## Final Numbers (3 seeds/arm, 30 000 ticks, contiguous 00_Graded scroll)

| Metric | Arm 0: STDP_TARGET=0 | Arm 1: STDP_TARGET=1 | Ancestor |
|--------|:--------------------:|:--------------------:|:--------:|
| Income quantum (CELL_STATES) | 256 | 256 | 256 |
| Pure-idle cost (measured) | 384 cycles/tick | 350 cycles/tick | **436** |
| Idle cost: start → end | 414 → **2387** | 385 → **1619** | 414 |
| n_neurons: start → end | 77 → **183** | 78 → **113** | 65 |
| correct/tick: peak → end | 129 → **2.6** | 129 → **3.4** | — |
| Refugium firing rate | **11.3%** | **9.9%** | — |
| Fraction of ticks net-positive | **0.000** | **0.000** | 0.000 |

## Diagnosis

```
H1 (Rule-7 efficiency — idle cost falls toward 256):  FALSIFIED ── idle cost ROSE in both arms (brains bloated)
H2 (adaptive PARAM drift):                            NEUTRAL ──── per-seed SD ≈ 0 → mutational bias, not tuning
H3 (STDP_TARGET raises comprehension):                FALSIFIED ── correct/tick collapsed in BOTH arms
Rule-14 (refugium < 5% of ticks):                     VIOLATED ─── ~10-11% → population on life support
```

## The Verdicts

| Question | Answer |
|----------|--------|
| Does letting structure evolve shrink brains toward the income budget? | **NO** (idle cost rose; n_neurons grew) |
| Is there an income gradient for selection to climb? | **NO** (fraction net-positive = 0.000 in every condition) |
| Do the PARAM constants tune adaptively once structure can evolve? | **NO** (drift is mutational bias, shared across seeds) |
| Does the STDP_TARGET recruitment lever rescue comprehension income? | **NO** (comprehension collapses in both arms) |
| Is the income mechanism rigged? | **NO** — it is already Rule-21-grounded; the ceiling is physical, not authored |

## Why — the dynamical metabolic ceiling

The seeded ancestor (65 neurons / 93 synapses) is **structurally bankrupt**: its pure-idle
metabolic rate (~436 cycles/tick, dominated by `n_count × CYCLES_PER_NEURON_UPDATE` plus one
`CYCLES_PER_SYNAPSE_READ` per synapse) already exceeds the maximum income quantum (256 cycles/tick
= one full correct prediction). The fraction of ticks with positive net income is **0.000 in every
condition**, including trivially-predictable content on which the ancestor predicts 250/250 correctly.

When idle cost exceeds the income quantum, the income gradient is **flat at zero**:

- Selection cannot favour cheaper brains — being cheaper confers no survival advantage when income
  is zero (the organism dies regardless).
- The refugium that prevents total extinction simultaneously removes the selective gradient, and its
  reproduction (`mutate_dna(crossover_dna(...))`) carries a mutational bias toward genome growth
  (duplication/crossover) → **bloat**, the opposite of Rule-7 efficiency.
- Useful traits (echo-prediction) are **lost** because they confer no survival advantage.

This sharpens the Exp 82-86 finding ("max income < cost") into a dynamical statement: **the ceiling
nullifies selection.** "Make the constants evolvable" (Rule 21.2) and "let structure evolve" are both
INSUFFICIENT while the ceiling binds.

## Catch-22 (= Rule 5 corollary)

Earning enough income to survive requires a brain complex enough to hold context and predict
compositionally (which the engine rewards via its DELAY/DIGESTION information-scaling), but such a
brain is too expensive to survive on the income it can earn: compositional cognition is unaffordable
while `n_neurons × depth × spike_cost > 256`.

## The Next Frontier (no rigged mechanics — Rule 7 / Rule 21)

Re-ground the **INCOME** side, not the cost side:

1. **Information-scaling of income (Free Energy Principle made literal):** income proportional to
   measured Shannon information gain (bits of surprise reduced) rather than a fixed 256 per single
   next-cell prediction. The engine's DELAY/DIGESTION machinery already gestures at this. Must be
   designed as MEASURED information gain, NOT a multiplier.
2. **Re-derive the income quantum** as a measured WORK quantity (design doc §10 / Rule-21 open
   question), exactly as cost was grounded in Rule 21.1.

Any such change must pass the Rule 21.4 tuning test. A dedicated Rule-21 review of (1)/(2) is the
recommended next step before any engine change.
