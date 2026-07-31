# Task Family 3: Compositional Rule Switching & Delayed Arithmetic Protocol (Pre-Registration v1.0)
**Pre-Registration Date**: 2026-07-30
**Target Checkpoint**: `Brain_Phase4_65K_Cortical.npz` (65,536 Neurons, FP16 Tensor Cores, SHA256 Verified)

---

## 1. Goal & Scientific Rationale

To satisfy Arena.ai's final requirement for multi-family task generalization, this protocol pre-registers **Task Family 3: Compositional Rule Switching & Delayed Modular Arithmetic**. 
Unlike Task Family 1 (DMTS memory matching) and Task Family 2 (Bit Parity XOR accumulation), Task Family 3 requires dynamic rule interpretation and compositional digit manipulation over time.

---

## 2. Task Specification: Contextual Modular Arithmetic

### 2.1 Environmental Input Stream & Rules
- **Rule Cue Phase**: Token $R_1$ (`ADD_MOD10`) or $R_2$ (`SUB_MOD10`).
- **Operand Phase**: Two single-digit operands $A, B \in \{0, 1, 2, \dots, 9\}$.
- **Delay Phase**: Blank temporal gap $N \in \{0, 1, 5, 10, 20, 30\}$ ticks.
- **Target Output $Y^*$**:
  - If $R_1$: $Y^* = (A + B) \pmod{10}$
  - If $R_2$: $Y^* = (A - B) \pmod{10}$ (where negative results wrap modulo 10)

### 2.2 Mathematical Chance Baseline
- **Output Alphabet Size**: $V = 10$ digits $\{0, 1, \dots, 9\}$.
- **Exact Chance Baseline ($\text{Chance}_{\text{arithmetic}}$)**:
  $$\text{Chance}_{\text{arithmetic}} = \frac{1}{10} = 10.000\% \quad (0.100000)$$

---

## 3. Pre-Registered Execution Modes

1. **Mode 1: Zero-Shot Compositional Rule Switching**:
   - STDP: **DISABLED** ($W$ frozen). State zeroed before each trial.
   - Tests intrinsic zero-shot rule interpretation of novel held-out digit pairs.
2. **Mode 2: Few-Shot Delayed Arithmetic**:
   - STDP: **ENABLED** (within-lifetime adaptation across 50 trials per seed).
3. **Mode 3: Cross-Family Sequential Transfer**:
   - Organism exposed to DMTS and Parity first, followed immediately by Compositional Arithmetic.

---

## 4. Matched Control Arms

1. **Proposed Learner**: Phase 4 Brain + Active STDP.
2. **Matched Learning Ablation**: Phase 4 Brain + Frozen Weights.
3. **Random Arithmetic Baseline**: Uniform 10% random guessing.
4. **No-Delay Baseline**: Delay phase set to $N=0$.
5. **Memoryless Baseline**: Network state completely zeroed before response phase.
6. **Rule-Only Baseline**: Operand digits replaced with uniform noise.
7. **Operand-Only Baseline**: Rule token replaced with uniform noise.

---

## 5. Statistical Rigor & Delta Definition

- **Sample Unit**: $N_{\text{seeds}} = 10$ independent seeds (901-910).
- **Explicit Delta Definition**:
  $$\Delta_{\text{seed}} = \text{Few-Shot (STDP) Accuracy}_{\text{seed}} - \text{Matched Ablation Accuracy}_{\text{seed}}$$
- **Cohen's $d_z$**: Paired sample effect size $d_z = \frac{\text{Mean}(\Delta_{\text{seed}})}{\text{Std}(\Delta_{\text{seed}})}$.
- **Pre-Registered Significance**: Paired t-test $p < 0.01$, Wilcoxon $p < 0.01$, Permutation $p < 0.01$.

---

## 6. Multi-Family Claim Criteria

Upon successful execution and verification of Task Family 3 alongside DMTS and Parity:
- Claim Label: `CONFIRMED_MULTI_FAMILY_TASK_GENERALIZATION`
- Scope Note: `EVALUATED_ACROSS_DMTS_PARITY_AND_ARITHMETIC_FAMILIES`
