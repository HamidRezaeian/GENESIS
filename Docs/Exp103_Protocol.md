# Exp 103 — Reservoir + Readout Probe

## Pre-Registration

- **Date**: 2026-08-05
- **Protocol**: EXP103_RESERVOIR_READOUT_v1
- **Branch**: feature/reservoir-readout

## Hypothesis

Reservoir computing with online LMS readout enables time-improving learning
on a static text-reading task, solving the three structural problems that
falsified the SNN-on-RAM Hebbian substrate:

1. Silent-synapse barrier → Reservoir state = persistent memory
2. Self-silencing → Linear readout always active
3. Directionless reward → Supervised per-bit error gradient

## Arms

- **LEARNER**: GENESIS_RESERVOIR=1 (reservoir + LMS readout active)
- **NOLEARN**: GENESIS_RESERVOIR=0 (no reservoir, no readout learning)

## Setup (identical to Exp 100–102)

- Frozen cohort: 60 organisms, no reproduction, no death
- Static text patch: 500 bytes
- Economy: books
- Duration: 20,000 ticks

## Success Criteria (binding, pre-registered)

1. LEARNER delta (late − early) > +2pp
2. LEARNER late_acc > NOLEARN late_acc + 3pp
3. No monotonic decline (no catastrophic forgetting)

## Failure Criteria

- Null result → pivot to Option 1 (differentiable plasticity) or Option 3 (neuroevolution)
- Crash / instability → fix before continuing

## Binding Prediction

Readout keeps improving while error > 0 (NO self-silencing).
