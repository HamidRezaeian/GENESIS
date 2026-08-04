# Exp 101: R-STDP Protocol

Pre-Registration Date: 2026-08-04
Protocol: EXP101_RSTDP_SURPRISE_REWARD_v1
Status: PRE-REGISTERED

## Hypothesis

R-STDP with surprise-based reward enables time-improving learning.

## Design

Arms: LEARNER_RSTDP vs NOLEARN
Cohort: 60 frozen organisms
Duration: 20,000 ticks
Metric: Delta = Late accuracy - Early accuracy

## Success Criteria

Delta > +2.0pp -> LEARNING_SIGNAL
|Delta| <= 2.0pp -> FLAT
Delta < -2.0pp -> DEGRADED

## Implementation

Flags:
- GENESIS_RSTDP=1
- GENESIS_RSTDP_SURPRISE=1
- GENESIS_RSTDP_EFFICIENCY=1

Reward: surprise * efficiency
Update: delta_w = lr * eligibility * reward

## Expected Outcomes

Best case: Delta > +10pp (R-STDP enables genuine learning)
Moderate: Delta ~ +2pp (R-STDP helps but insufficient)
Worst case: Delta <= 0 (R-STDP insufficient, pivot needed)

## Next Steps

1. Apply R-STDP patches to kernel
2. Run 5 seeds for each arm
3. Analyze results
4. Update Docs/Result.md
