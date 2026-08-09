# When Plasticity Costs Energy and Death Is Real:
## Metabolic Constraints on Biologically-Plausible Learning

### Target Venue: ICBINB Workshop (NeurIPS 2026) / TMLR

---

## Abstract (Draft)

Biological learning operates under strict metabolic constraints that are 
absent in artificial neural networks. We investigate how these constraints 
affect learning in biologically-plausible spiking neural networks using 
e-prop (Eligibility Propagation). Through a series of controlled experiments, 
we establish three findings: (1) e-prop successfully learns temporal tasks 
in ideal conditions (90.7% accuracy); (2) e-prop is fundamentally fragile 
to input noise, with no local gating mechanism providing robustness; 
(3) metabolic constraints induce a phase transition at ~75% blocking rate, 
below which learning is robust and above which it collapses. We further 
demonstrate that hierarchical architectures extend this threshold, 
suggesting that cortical layering may serve as a metabolic adaptation. 
These findings provide quantitative design constraints for future 
biologically-plausible AI systems.

---

## 1. Introduction

### 1.1 The Metabolic Cost of Learning
- Brain: 20W, ~2% of body mass
- Each synaptic update costs ATP
- Artificial networks: no energy constraint
- Question: What happens when learning must pay its energy bill?

### 1.2 Biologically-Plausible Learning Rules
- Backpropagation: powerful but biologically implausible
- e-prop: local, three-factor learning rule
- STDP: Hebbian, but no credit assignment
- Gap: How do local rules perform under metabolic constraints?

### 1.3 Our Contributions
1. First systematic study of e-prop under metabolic constraints
2. Discovery of phase transition in learning vs. energy
3. Evidence that hierarchy is a metabolic adaptation
4. Null result: noise robustness requires non-local mechanisms

---

## 2. Phase 2A: Metabolic Affordability of Learning

### 2.1 Feasibility: e-prop CAN Learn (Exp-P2A-01, v24)
**Setup:** Temporal XOR, 2→50→2 LIF, e-prop, no noise
**Result:** 90.7% accuracy (5 seeds)
**Key finding:** 362/500 updates blocked by metabolic buffer
**Interpretation:** Learning works, but at a cost

### 2.2 Limitations: Noise Fragility (v25-v27)
**Setup:** Same task + 5% input noise
**Result:** Accuracy drops to 66.8% (v25)
**Attempted solutions:**
- Sparse encoding (v26): WORSE (credit dilution)
- Postsynaptic gate (v27): WORSE (gate collapse)
**Null result:** No local mechanism can distinguish signal from noise
**Interpretation:** Fundamental limitation of local credit assignment

### 2.3 Core Finding: Metabolic Phase Transition (Exp-P2A-02)
**Setup:** 5 blocking levels: 0%, 25%, 50%, 75%, 90%
**Result:** Phase transition at ~75%
- 0-50%: Graceful plateau (slope ≈ 0)
- 50-75%: Gentle decline (slope = 0.28 pp/%)
- 75-90%: Sharp collapse (slope = 1.27 pp/%)
**Hypothesis testing:**
- H1 (T_block<50% → acc>85%): ✅ PASS
- H2 (T_block=90% → acc>70%): ❌ FAIL
**Interpretation:** Biological systems must operate in the plateau region

---

## 3. Phase 2B: Architectural Solutions

### 3.1 Hierarchical Processing Extends Tolerance (Exp-P2B-01, 01b)
**Setup:** Compare 2-layer [50], 2-layer [150], 3-layer [100,50]
**Result:**
- Size helps: 2-layer [150] > 2-layer [50] (+17.7pp at 75%)
- Depth helps: 3-layer > 2-layer [150] (+10.3pp at 75%)
- Phase transition eliminated in 3-layer
**Interpretation:** Hierarchy is a metabolic adaptation

### 3.2 Working Memory for Temporal Tasks (Exp-P2B-02) ← CURRENT
**Setup:** Delayed Match-to-Sample with slow membrane neurons
**Hypothesis:** Working memory extends temporal credit assignment
**Status:** In progress

### 3.3 Neuromodulatory Gating (Future)
**Setup:** Acetylcholine analog for surprise-based gating
**Hypothesis:** Solves noise robustness problem from §2.2
**Status:** Planned

---

## 4. Discussion

### 4.1 The Metabolic Design Space
Our results define a "metabolic design space" for learning systems:
- X-axis: Metabolic constraint (blocking rate)
- Y-axis: Learning accuracy
- Phase transition defines the boundary

### 4.2 Biological Implications
- Brain operates in the plateau region (< 75%)
- Cortical hierarchy may be a metabolic adaptation
- Sleep may restore metabolic capacity

### 4.3 Implications for Biologically-Plausible AGI
- Local learning rules are necessary but not sufficient
- Architectural priors (hierarchy, working memory, neuromodulation) are required
- Energy budgeting is a first-class design constraint

### 4.4 Limitations
- Small networks (≤150 neurons)
- Single task family (XOR variants)
- No real-world noise
- Fixed hyperparameters

---

## 5. Future Work

### 5.1 Scaling Laws
- How does the phase transition threshold scale with network size?
- Power law or exponential?

### 5.2 Real-World Tasks
- Move beyond XOR to sensory processing tasks
- Test with actual neuromorphic hardware

### 5.3 Neuromodulatory Architectures
- Dopamine: reward-based gating
- Acetylcholine: novelty-based gating
- Serotonin: uncertainty-based gating

### 5.4 Hardware Implementation
- Loihi, SpiNNaker, BrainScaleS
- Measure actual energy per synaptic update
- Validate metabolic model against hardware

---

## References

1. Bellec, G., et al. (2020). "A solution to the learning dilemma for 
   recurrent networks of spiking neurons." Nature Communications.
2. Sjöström, P.J. & Häusser, M. (2006). "A cooperative switch determines 
   the sign of synaptic plasticity." Nature Neuroscience.
3. Hasselmo, M.E., et al. (1992). "Cholinergic modulation of cortical 
   associative memory function." Neuroscience.
4. Dohare, S., et al. (2024). "Loss of plasticity in deep continual 
   learning." Nature.
5. [Additional references as needed]

---

## Appendix

### A. Pre-registration Documents
- Exp-P2A-01: [link]
- Exp-P2A-02: [link]
- Exp-P2B-01: [link]
- Exp-P2B-02: [link]

### B. Raw Data
All data available in `experiments/` directory of the repository.

### C. Code
All code available at: https://github.com/HamidRezaeian/GENESIS