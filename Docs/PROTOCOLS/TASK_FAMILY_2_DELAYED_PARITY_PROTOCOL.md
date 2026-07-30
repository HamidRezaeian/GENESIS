# Task Family 2: Delayed Bit Parity Protocol (Pre-Registration v1.0)
**Pre-Registration Date**: 2026-07-30
**Target Checkpoint**: `Brain_Phase4_65K_Cortical.npz` (65,536 Neurons, FP16 Tensor Cores, SHA256 Verified)

---

## 1. Goal & Scientific Rationale

Arena.ai mandated that **Broad Task Generalization** cannot be established from a single task family (DMTS). 
This protocol pre-registers **Task Family 2: Delayed Bit Parity (XOR Accumulation)**. This task tests sequential modular arithmetic and temporal bit integration, which are mathematically and operationally distinct from matching/reversal memory tasks.

---

## 2. Formal Task Definition: Delayed Bit Parity

### 2.1 Environmental Input Stream
The environment presents a streaming binary sequence:
1. **Input Phase**: A 6-bit binary sequence $B = (b_1, b_2, b_3, b_4, b_5, b_6)$ where $b_i \in \{0, 1\}$.
2. **Delay Phase**: A blank temporal gap of $N \in \{0, 1, 5, 10, 20\}$ ticks.
3. **Response Phase**: The organism must output a single binary token $P^*$:
   - $P^* = 1$ if $\sum_{i=1}^6 b_i \pmod 2 \equiv 1$ (Odd Parity / XOR accumulation)
   - $P^* = 0$ if $\sum_{i=1}^6 b_i \pmod 2 \equiv 0$ (Even Parity)

### 2.2 Mathematical Chance Baseline
- **Output Alphabet**: $V = \{0, 1\}$.
- **Exact Chance Baseline ($\text{Chance}_{\text{parity}}$)**:
  $$\text{Chance}_{\text{parity}} = \frac{1}{2} = 50.000\%$$
- **Null Baseline**: Uniform random coin-flip ($50.0\%$).

---

## 3. Matched Control Arms & Sampling Plan

### 3.1 Experimental Arms
1. **Proposed Learner**: Phase 4 Brain + Active STDP.
2. **Matched Learning Ablation**: Phase 4 Brain + Frozen Weights.
3. **Cue/Bit-1 Only Baseline**: Output based only on the first bit $b_1$.
4. **Memoryless Baseline**: Network state completely zeroed before response phase.
5. **Random Null Baseline**: Uniform 50% random guessing.

### 3.2 Independent Sampling
- **Sample Unit**: $N_{\text{seeds}} = 10$ independent seeds (801-810).
- **Evaluation Budget**: 100 trials per seed.
- **Primary Metric**: **Parity Classification Accuracy** at $N=10$ delay.
- **Pre-Registered Significance**: Paired t-test $p < 0.01$, Cohen's $d \ge 0.80$.

---

## 4. Multi-Task Generalization Claim Criteria (Arena.ai Invariant)

Upon successful replication of **both** Task Family 1 (DMTS) and Task Family 2 (Delayed Parity) on the SAME saved Phase 4 brain without any architectural edits:
- Claim Label: `CONFIRMED_CROSS_FAMILY_TASK_GENERALIZATION`
- Caveat: `EVALUATED_ON_DMTS_AND_PARITY_FAMILIES`
