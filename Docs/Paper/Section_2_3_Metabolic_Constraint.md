# 2.3 Metabolic Constraint: Phase Transition in Learning

## Overview

We investigated how metabolic constraints affect learning performance in 
biologically-plausible spiking neural networks using e-prop (Eligibility 
Propagation). Our central finding is a **phase transition** at approximately 
75% blocking rate, below which learning remains robust and above which it 
collapses.

## Experimental Design

**Task:** Temporal XOR (input A at t=3, input B at t=6, target at t=9)

**Architecture:** 2 input neurons → 50 LIF hidden neurons → 2 output neurons

**Learning rule:** e-prop with eligibility traces (τ_e = 15 ticks)

**Metabolic constraint:** Update budget limiting the number of synaptic 
weight updates per episode. Five conditions tested:
- Unconstrained: 500 updates allowed (0% blocked)
- Light: 375 updates (25% blocked)  
- Moderate: 250 updates (50% blocked)
- Heavy: 125 updates (75% blocked)
- Extreme: 50 updates (90% blocked)

**Evaluation:** 5 seeds × 500 trials per condition, noise-free environment.

## Results

| Condition | Block Rate | Accuracy (mean ± std) | Updates Used | Updates Blocked |
|-----------|------------|----------------------|--------------|-----------------|
| Unconstrained | 0% | 88.4% ± 6.2% | 500 | 0 |
| Light | 25% | 87.0% ± 7.8% | 375 | 125 |
| Moderate | 50% | 86.9% ± 8.0% | 250 | 250 |
| Heavy | 75% | 79.9% ± 13.2% | 125 | 375 |
| Extreme | 90% | 60.8% ± 10.1% | 50 | 450 |

### Phase Transition Analysis

The accuracy-block rate curve reveals three distinct regimes:

**Regime 1: Graceful Plateau (0-50% block)**
- Accuracy remains stable: 88.4% → 86.9%
- Slope: ≈ 0 pp/% block
- Interpretation: System has sufficient redundancy to absorb 
  moderate metabolic constraints without performance loss.

**Regime 2: Gentle Decline (50-75% block)**
- Accuracy drops gradually: 86.9% → 79.9%
- Slope: 0.28 pp/% block
- Interpretation: Redundancy exhausted, system begins to degrade 
  gracefully as fewer updates are available.

**Regime 3: Sharp Collapse (75-90% block)**
- Accuracy drops rapidly: 79.9% → 60.8%
- Slope: 1.27 pp/% block (4.5× steeper than Regime 2)
- Interpretation: System crosses a critical threshold below which 
  eligibility traces cannot accumulate sufficiently for credit assignment.

## Hypothesis Testing

**Pre-registered hypotheses:**
- H1: T_block < 50% → accuracy > 85% ✅ **PASS** (min: 87.0%)
- H2: T_block = 90% → accuracy > 70% ❌ **FAIL** (actual: 60.8%)

**Interpretation:** H1 confirms that moderate metabolic constraints are 
affordable. H2 failure reveals the existence of a critical threshold — 
extreme constraints fundamentally break the learning mechanism.

## Biological Interpretation

The phase transition at ~75% blocking rate suggests that biological 
learning systems must operate within the plateau region. This is 
consistent with:

1. **ATP reserves:** Neurons maintain ~2-second ATP reserves, suggesting 
   they operate with substantial metabolic headroom.

2. **Synaptic pruning:** The brain prunes ~50% of synapses during 
   development, potentially optimizing for the plateau region.

3. **Sleep and metabolic recovery:** Sleep may serve to restore metabolic 
   capacity, preventing the system from entering the collapse regime.

## Implications for Biologically-Plausible AGI

Any AGI architecture based on local learning rules (e-prop, STDP, etc.) 
must either:

1. **Operate within the plateau:** Accept metabolic limits and design 
   within them. This requires accurate energy budgeting.

2. **Extend the plateau:** Implement architectural priors that increase 
   metabolic tolerance:
   - Working memory to bridge temporal gaps
   - Neuromodulatory gating to prioritize important updates
   - Hierarchical processing to distribute metabolic load

This finding provides a **quantitative design constraint** for future 
biologically-plausible AI systems.

## Limitations

- Single task (Temporal XOR) — generalization to complex tasks unknown
- Small network (50 neurons) — scaling behavior untested
- Noise-free environment — real-world robustness not addressed (see §2.2)
- Fixed learning rate — adaptive rates may shift the threshold

## Data Availability

All code and results: `experiments/phase2a/code/eprop_p2a02_metabolic_pareto.py`
Raw data: `experiments/phase2a/results/exp_p2a_02_metabolic_pareto_*.json`