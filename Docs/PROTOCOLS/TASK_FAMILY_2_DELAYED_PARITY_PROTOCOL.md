# Task Family 2: Delayed Bit Parity Protocol (v2.0 Audit-Grade Pre-Registration)
**Pre-Registration Date**: 2026-07-30
**Target Checkpoint**: `Brain_Phase4_65K_Cortical.npz` (65,536 Neurons, FP16 Tensor Cores, SHA256 Verified)

---

## 1. Scope & Claim Labeling (Arena.ai Compliance)

> [!IMPORTANT]
> **Claim Boundary Invariants**:
> Following Arena.ai's evaluation framework, the status of cross-family generalization is strictly bounded to:
> - Status Label: `CROSS_FAMILY_GENERALIZATION_OBSERVED`
> - Replication Note: `REPLICATED_ON_DMTS_AND_DELAYED_PARITY_PROTOCOLS`
> - Disclaimers:
>   - `BROAD_TASK_GENERALIZATION_NOT_YET_ESTABLISHED` (requires evaluation across 3+ independent task families)
>   - `AGI_CLAIM_NOT_SUPPORTED`

---

## 2. Formal Task Definition: Delayed Bit Parity

### 2.1 Environmental Input Stream & Input Balancing
- **Input Phase**: A 6-bit binary sequence $B = (b_1, b_2, b_3, b_4, b_5, b_6)$ where $b_i \in \{0, 1\}$.
- **Input Balancing**: Streams are generated with exact 50/50 balance (50% even parity targets, 50% odd parity targets) to eliminate majority-class skew shortcuts.
- **Delay Phase**: A blank temporal gap $N \in \{0, 1, 5, 10, 20, 30\}$ ticks.
- **Response Phase**: Target output bit $P^* = \sum_{i=1}^6 b_i \pmod 2$.

### 2.2 Mathematical Chance Baseline
- **Output Alphabet**: $V = \{0, 1\}$.
- **Exact Chance Baseline ($\text{Chance}_{\text{parity}}$)**:
  $$\text{Chance}_{\text{parity}} = \frac{1}{2} = 50.000\% \quad (0.500000)$$

---

## 3. Fresh Process Isolation & Base Weight Audit

To eliminate task-order carryover and transfer confounds:
1. **Fresh Process Execution**: Parity evaluation is executed in a completely isolated Python process loading directly from `Brain_Phase4_65K_Cortical.npz`. No memory state, membrane potential, or STDP weight changes carry over from DMTS trials.
2. **Base Weight Hash Verification**: The SHA256 hash of the base synaptic weight matrix (`w_matrix`) is computed before and after evaluation to verify $0.0\%$ base weight drift.

---

## 4. Evaluation Modes (Zero-Shot vs Few-Shot vs Transfer)

The protocol evaluates 3 distinct execution modes:
1. **Pure Zero-Shot Parity**:
   - STDP: **DISABLED** ($W$ frozen).
   - State: Membrane potentials zeroed prior to each trial.
2. **Few-Shot Parity**:
   - STDP: **ENABLED** (within-lifetime adaptation across 50 trials per seed).
   - State: Synaptic updates ($dW$) persist across adaptation trials within a seed.
3. **Sequential Transfer Parity**:
   - Organisms exposed to 50 trials of DMTS first, followed immediately by 50 trials of Parity.

---

## 5. Statistical Rigor & Metric Specifications

### 5.1 Unit of Analysis & Independent Sampling
- **Sample Unit**: $N_{\text{seeds}} = 10$ independent seeds (801-810).
- **Evaluation Budget**: 100 trials per seed.

### 5.2 Pre-Registered Statistical Methods
- **Cohen's $d_z$ Definition**: Paired sample effect size calculated as:
  $$d_z = \frac{\text{Mean}(\Delta)}{\text{Std}(\Delta)}$$
- **Multi-Test Reporting**:
  1. Paired Two-Tailed Student's t-test
  2. Wilcoxon Signed-Rank Test
  3. Exact Paired Permutation Test
  4. 95% Confidence Interval for $\text{Mean}(\Delta)$

---

## 6. Output Provenance Manifest Requirements

Every run MUST export `task_family_2_parity_raw_results.json` containing:
- `protocol_id`: `"TASK_FAMILY_2_DELAYED_PARITY_v2"`
- `base_weight_sha256_before`: SHA256 string
- `base_weight_sha256_after`: SHA256 string
- `process_isolated`: `true`
- `stat_summary`: { `mean_delta`, `std_delta`, `ci_95_lower`, `ci_95_upper`, `cohens_d_z`, `t_stat`, `p_value_ttest`, `p_value_wilcoxon`, `p_value_permutation` }
- `mode_breakdown`: { `zero_shot_accuracy`, `few_shot_accuracy`, `transfer_accuracy` }
- `per_seed_raw_deltas`: List of 10 raw delta float values.
