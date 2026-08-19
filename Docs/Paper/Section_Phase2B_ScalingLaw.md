## 3.4 Metabolic Scaling Law: Null Result (Exp-P2B-04)

### Motivation

Phase 2A found a metabolic phase transition at ~75% blocking for 50-neuron 
networks. This experiment tested whether this threshold scales with network 
size, establishing a power law relationship:

threshold = a * (n_neurons)^b


### Experimental Design

**Network sizes:** 50, 100, 200, 400 (geometric progression)
**Task:** Temporal XOR (noise=0%)
**Conditions:** 0%, 25%, 50%, 75%, 90% blocking
**Budget:** Fixed at 500 updates for all sizes

### Pre-registration

- H1: Power law scaling (R² > 0.9)
- H2: 400-neuron threshold > 50-neuron + 10pp
- Success = H1 AND H2

### Results

| Size | 0% Block | Phase Transition |
|------|----------|------------------|
| 50 | 88.4% | 82.8% |
| 100 | 94.1% | 88.7% |
| 200 | 90.0% | 83.4% |
| 400 | 77.8% | 83.3% |

**Power law fit:**
- Model: threshold = 86.94 * (n_neurons)^(-0.01)
- R² = 0.026
- Scaling exponent: b = -0.01

**H1 FAIL:** R² = 0.026 (expected >0.9)
**H2 FAIL:** 400 - 50 = +0.6pp (expected >10pp)

### Key Findings

**Finding 1: No clear scaling relationship**
Phase transition thresholds are remarkably stable across network sizes 
(82.8% to 88.7%), with no clear power law relationship. This suggests 
that metabolic tolerance is a property of the learning rule (e-prop), 
not network size.

**Finding 2: Underfitting in large networks**
400-neuron networks achieved only 77.8% accuracy (vs 88.4% for 50 neurons) 
with the same 500-update budget. This reveals a confound: fixed update 
budgets lead to severe underfitting in larger networks.

**Finding 3: Phase transition shifted from Phase 2A**
Phase 2A found transition at ~75%, but this experiment finds ~83%. The 
difference may be due to different network initialization or random seeds.

### Interpretation

These results suggest that:

1. **Metabolic tolerance is size-independent:** The phase transition 
   threshold appears to be an intrinsic property of e-prop, not a 
   function of network scale.

2. **Proportional budgets are necessary:** To fairly compare across 
   sizes, update budgets should scale with network size (e.g., 
   budget = k * n_neurons).

3. **Simple tasks don't benefit from scale:** XOR is a simple task 
   that doesn't require large networks. More complex tasks might 
   show different scaling behavior.

### Biological Implications

Biological brains scale across many orders of magnitude (mouse: 70M neurons, 
human: 86B neurons). Our results suggest that:

- Metabolic constraints may be similar across species (when normalized)
- Larger brains may not have higher metabolic tolerance per neuron
- The phase transition may be a universal property of local learning rules

### Limitations

- Fixed budget confound: Should have used proportional budgets
- Simple task: XOR may not reveal scaling in complex tasks
- Small scale: 400 neurons is tiny compared to biological systems
- No recurrent connections in scaling analysis

### Future Work

1. **Proportional budgets:** Repeat with budget ∝ n_neurons
2. **Complex tasks:** Test on pattern recognition, sequence learning
3. **Hierarchical scaling:** Test multi-layer architectures
4. **Hardware validation:** Implement on neuromorphic chips

### Data Availability

Code: `experiments/phase2b/code/eprop_p2b04_scaling_law.py`
Results: `experiments/phase2b/results/exp_p2b_04_scaling_law_*.json`
