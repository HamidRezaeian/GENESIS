# Phase 2B: Hierarchical SNN Extends Metabolic Tolerance

## Overview

Building on Phase 2A's finding of a metabolic phase transition at ~75% 
blocking rate, we investigated whether hierarchical architectures can 
extend this threshold. Our results show that **both depth and size 
contribute to metabolic tolerance**, with depth providing an additional 
benefit beyond size alone.

## Experimental Design

**Task:** Temporal XOR (noise=0%)
**Architectures tested:**
- 2-layer [50]: 50 hidden neurons (Phase 2A baseline)
- 2-layer [150]: 150 hidden neurons (size control)
- 3-layer [100,50]: 150 hidden neurons (depth test)

**Conditions:** 0%, 75%, 90% metabolic blocking
**Evaluation:** 5 seeds × 500 trials per condition

## Results

| Architecture | Neurons | 0% Block | 75% Block | 90% Block |
|--------------|---------|----------|-----------|-----------|
| 2-layer [50] | 50 | 86.5% | 69.2% | 55.4% |
| 2-layer [150] | 150 | 93.9% | 86.8% | 75.6% |
| 3-layer [100,50] | 150 | 97.1% | 97.2% | 83.9% |

### Key Findings

**Finding 1: Size helps (H2 PASS)**
2-layer [150] outperforms 2-layer [50] by 17.7pp at 75% block.
Interpretation: Redundancy allows the system to absorb lost updates.

**Finding 2: Depth helps beyond size (H1 PASS)**
3-layer [100,50] outperforms 2-layer [150] by 10.3pp at 75% block,
despite having the same number of neurons (150).
Interpretation: Hierarchical processing provides an additional benefit.

**Finding 3: Phase transition eliminated**
The 3-layer architecture shows NO phase transition up to 90% block.
At 75% block, accuracy remains at 97.2% (vs 69.2% for 2-layer [50]).

## Biological Interpretation

The cerebral cortex is organized in 6 layers. Our results suggest this 
hierarchical organization may serve as a **metabolic adaptation**:

1. **Load distribution:** Each layer handles a portion of the learning, 
   reducing metabolic demand per layer.

2. **Independent eligibility traces:** Layers can maintain separate 
   eligibility traces, preventing interference.

3. **Graceful degradation:** If one layer's updates are blocked, other 
   layers can compensate.

## Implications for Biologically-Plausible AGI

These results provide a **design principle** for AGI architectures:

> "Hierarchical processing is not just computationally advantageous; 
> it is metabolically necessary for learning under energy constraints."

This suggests that future biologically-plausible AGI systems should:
1. Use deep architectures (≥3 layers)
2. Distribute learning across layers
3. Implement layer-specific metabolic budgets

## Limitations

- Small network (150 neurons) — scaling behavior unknown
- Single task (Temporal XOR) — generalization untested
- Fixed learning rate — adaptive rates may change results
- No noise — real-world robustness not addressed

## Data Availability

Code: `experiments/phase2b/code/eprop_p2b01b_depth_vs_size.py`
Results: `experiments/phase2b/results/exp_p2b_01b_depth_vs_size_*.json`