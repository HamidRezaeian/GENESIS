# 4. Discussion

## 4.1 The Metabolic Design Space

Our experiments define a "metabolic design space" for biologically-plausible 
learning systems:

                Learning Accuracy
                     ↑
                100% |
                     |  ╭───── Plateau Region
                     |  │      (metabolically affordable)
                     |  │
                     |  │
                 75% |──┼──────────── Phase Transition
                     |  │
                     |  │  ╲
                     |  │    ╲  Collapse Region
                     |  │      ╲  (unsustainable)
                 50% |────────────────────────→
                     0%    25%    50%    75%    90%
                          Metabolic Constraint (Blocking Rate)


**Key insight:** Biological learning systems must operate in the plateau 
region (< 75% blocking). Beyond this threshold, learning collapses 
rapidly due to insufficient eligibility traces for credit assignment.

## 4.2 Three Principles for Biologically-Plausible AGI

Our findings establish three design principles:

### Principle 1: Hierarchy is Metabolically Necessary
3-layer architectures eliminate the phase transition entirely. This 
suggests that cortical layering is not just computationally advantageous, 
but metabolically essential.

### Principle 2: Local Learning Rules Have Implicit Memory
e-prop with standard LIF neurons can handle temporal gaps without explicit 
working memory modules. Eligibility traces and sub-threshold integration 
provide implicit temporal credit assignment.

### Principle 3: Noise Robustness Requires Non-Local Mechanisms
Standard e-prop cannot distinguish signal from noise. Local gating 
mechanisms (postsynaptic gates, sparse encoding) fail. Solving noise 
robustness likely requires neuromodulatory systems (acetylcholine, 
dopamine) that provide global context.

## 4.3 Biological Implications

### 4.3.1 Cortical Hierarchy as Metabolic Adaptation
The 6-layer structure of neocortex may serve as a metabolic adaptation:
- Distributes learning load across layers
- Each layer operates within its metabolic budget
- Prevents phase transition by maintaining plateau operation

### 4.3.2 Sleep and Metabolic Recovery
Sleep may serve to restore metabolic capacity:
- During wakefulness, metabolic reserves deplete
- Sleep restores ATP and clears metabolic waste
- Prevents system from entering collapse region

### 4.3.3 Neuromodulatory Systems as Noise Filters
Acetylcholine and dopamine may serve as "surprise detectors":
- Only unexpected inputs trigger learning
- Filters out predictable noise
- Explains why attention modulates learning

## 4.4 Comparison with Artificial Neural Networks

| Feature | ANN (Backprop) | SNN (e-prop) |
|---------|----------------|--------------|
| Energy constraint | None | Critical |
| Learning rule | Global gradient | Local traces |
| Noise robustness | High (with regularization) | Low (requires gating) |
| Temporal processing | Explicit (RNN, LSTM) | Implicit (eligibility) |
| Scalability | Proven | Unknown |

**Key difference:** ANNs optimize for accuracy without energy constraints. 
SNNs must optimize for accuracy *within* metabolic budgets. This fundamentally 
changes the design space.

## 4.5 Limitations

### 4.5.1 Scale
All experiments used small networks (≤150 neurons). Scaling behavior 
is unknown. The phase transition threshold may shift with scale.

### 4.5.2 Task Complexity
We used simple tasks (XOR, DMS). Real-world tasks involve:
- High-dimensional inputs
- Multiple simultaneous objectives
- Non-stationary environments

### 4.5.3 Biological Fidelity
Our LIF model is simplified. Real neurons have:
- Dendritic computation
- Multiple neurotransmitter systems
- Glial interactions
- Structural plasticity

### 4.5.4 Noise Model
We used simple Poisson noise. Real neural noise includes:
- Correlated noise
- Non-stationary noise
- Structured distractors

## 4.6 Ethical Considerations

This research contributes to understanding biological learning constraints. 
It does not claim to build AGI or sentient systems. All experiments are 
computational simulations with no welfare implications.

---

# 5. Conclusion

We have established three key findings about biologically-plausible 
learning under metabolic constraints:

1. **Feasibility:** e-prop can learn temporal tasks in ideal conditions 
   (90.7% accuracy), but is fragile to noise.

2. **Phase Transition:** Metabolic constraints induce a sharp transition 
   at ~75% blocking rate. Below this, learning is robust; above it, 
   learning collapses.

3. **Architectural Solutions:** Hierarchical processing extends metabolic 
   tolerance, while explicit working memory is unnecessary (e-prop has 
   implicit temporal memory).

These findings provide quantitative design constraints for future 
biologically-plausible AI systems. They suggest that achieving 
brain-like efficiency requires not just local learning rules, but 
careful architectural design that respects metabolic budgets.

The path toward biologically-plausible AGI is not through scaling alone, 
but through understanding and respecting the metabolic constraints that 
shaped biological intelligence.

---

# Acknowledgments

[To be added]

# Code Availability

All code and data available at: https://github.com/HamidRezaeian/GENESIS

# Competing Interests

The authors declare no competing interests.