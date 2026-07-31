# Phase G: Task-Specific DMTS Generalization Protocol (v2.0 Pre-Registration)
**Pre-Registration Date**: 2026-07-30
**Target Checkpoint**: `Brain_Phase4_65K_Cortical.npz` (65,536 Neurons, FP16 Tensor Cores, SHA256 Verified)

---

## 1. Scope & Claim Labeling (Arena.ai Compliance)

> [!IMPORTANT]
> **Claim Boundary Invariants**:
> Even upon full replication and statistical verification of this protocol, the confirmed claim label is strictly restricted to:
> `CONFIRMED_GENERALIZATION_ON_PHASE_G_DMTS_TASK`
>
> The following explicit disclaimers are bound to all outputs:
> - `REPLICATED_ON_PRE_REGISTERED_DMTS_PROTOCOL`
> - `BROAD_TASK_GENERALIZATION_NOT_YET_ESTABLISHED` (requires evaluation across multiple independent task families)
> - `AGI_CLAIM_NOT_SUPPORTED`

---

## 2. Formal Task Specification: Contextual DMTS with Conditional Reversal

### 2.1 Vocabulary & Mathematical Chance Baseline
- **Alphabet Size ($V$)**: 8 distinct tokens $\{T_1, T_2, \dots, T_8\}$.
- **Sequence Length ($L$)**: Exactly 4 tokens without immediate repetition within a sequence.
- **Sequence Space Size ($N_{\text{seq}}$)**: $8 \times 7 \times 7 \times 7 = 2,744$ valid sequences.
- **Mathematically Derived Chance Baseline ($\text{Chance}_{\text{exact}}$)**:
  $$\text{Chance}_{\text{exact}} = \frac{1}{N_{\text{seq}}} = \frac{1}{2744} \approx 0.036443\% \quad (0.00036443)$$
  *Per-token Chance Baseline ($\text{Chance}_{\text{token}}$)*: $1 / 8 = 12.500\%$.

### 2.2 Trial Structure & Delay Array
Each trial consists of 4 distinct phases in a 1D streaming buffer:
1. **Cue Phase**: Token $C_1$ (`CUE_FORWARD`) or $C_2$ (`CUE_REVERSAL`).
2. **Sample Phase**: 4-token sequence $S = (s_1, s_2, s_3, s_4)$.
3. **Delay Phase**: Blank temporal gap $N \in \{0, 1, 5, 10, 20, 30, 40, 50\}$ ticks. Delays are randomized per trial to prevent order-effect learning bias.
4. **Response Phase**: 4-token output stream target $R^*$:
   - If $C_1$: $R^* = (s_1, s_2, s_3, s_4)$ (Forward match)
   - If $C_2$: $R^* = (s_4, s_3, s_2, s_1)$ (Reversal match)

---

## 3. Formal Definitions: Zero-Shot vs Few-Shot & Pretraining Audit

### 3.1 Checkpoint Audit Invariants
- **Pre-training Environment Audit**: `Brain_Phase4_65K_Cortical.npz` was evolved purely via unguided autotelic reading economy (ASCII RAM traversal). No working memory tasks, delayed matching, reversal tasks, or authored task rewards were present in Phase 4 evolution.
- **Architecture Integrity**: No network layers, RAM allocations, or structural connections are altered upon loading.

### 3.2 Operational Definitions
- **Zero-Shot Evaluation**:
  - Synaptic Plasticity (STDP): **DISABLED** ($W$ frozen).
  - Membrane Potentials & Activity States: Reset to 0 prior to trial 1.
  - Evaluation: Single-pass inference on 100 held-out novel sequences.
- **Few-Shot Evaluation**:
  - Synaptic Plasticity (STDP): **ENABLED** (within-lifetime adaptation).
  - Trial Limit: Fixed budget of 50 adaptation trials per seed.
  - State Persistence: Synaptic weight changes ($dW$) persist across adaptation trials within a single seed run; membrane potentials reset per trial.

---

## 4. Experimental Arms, Sampling Plan & Statistical Rigor

### 4.1 Unit of Analysis & Seed Independent Sampling
- **Independent Sample Unit**: Random seed ($N_{\text{seeds}} = 10$ independent runs: seeds 701-710). Organisms within the same seed/cohort are NOT treated as independent observations to prevent pseudo-replication.
- **Evaluation Budget**: 100 evaluation trials per seed ($50$ Forward, $50$ Reversal).

### 4.2 Matched Control Arms
1. **Proposed Learner**: Phase 4 Brain + Active Within-Lifetime STDP.
2. **Matched Learning Ablation**: Phase 4 Brain + Frozen Weights (Fixed Reflex).
3. **Fixed Reflex Baseline**: Static initialized network (untrained Phase 4 seed).
4. **Cue-Only Baseline**: Network presented with Cues only (Sample replaced with uniform noise).
5. **Sample-Only Baseline**: Network presented with Samples only (Cue omitted).
6. **No-Delay Baseline**: Delay phase set to $N=0$.
7. **Memoryless Baseline**: Network state completely reset between Sample and Response phases.
8. **Format-Matched Null Baseline**: Uniform random token output distribution.

### 4.3 Pre-Registered Statistical Hypotheses & Tests
- **Primary Metric**: **Mean Exact Sequence Accuracy** ($Acc_{\text{exact}}$) averaged across Forward and Reversal trials at $N=10$ delay.
- **Primary Statistical Test**: Paired Two-Tailed Student's t-test / Wilcoxon Signed-Rank Test between *Proposed Learner* and *Matched Ablation* across the 10 independent seeds.
- **Pre-Registered Significance Threshold**: $\alpha = 0.01$.
- **Effect Size Requirement**: Cohen's $d \ge 0.80$ (Large Effect Size) with 95% Confidence Interval for $\Delta Acc_{\text{exact}}$ non-crossing zero.

---

## 5. Strict Environmental Controls (No-Refuge & No-Ark)

### 5.1 No-Refuge Protocol
- `GENESIS_REFUGIUM=0` (Disabled).
- Failure to emit valid tokens imposes a metabolic penalty (-500 energy units).
- **Censored Observation Handling**: Organisms that die of energy depletion prior to completing all 100 evaluation trials are counted as **0.0% accuracy** for all remaining uncompleted trials (Intention-to-Treat principle).

### 5.2 No-Ark & Single-Lifetime Protocol
- `GENESIS_ARK=0`, `GENESIS_FOSSIL_POOL=0` (Disabled).
- Reproduction & Lamarckian inheritance disabled during evaluation (`GENESIS_AUTO_REPRO=0`).
- No intergenerational state persistence or lineage transfer allowed.

---

## 6. Metric Hierarchy & Provenance Manifest Requirements

### 6.1 Secondary Metrics
1. **Forward Exact-Sequence Accuracy** vs **Reversal Exact-Sequence Accuracy**.
2. **Per-Token Accuracy** ($Acc_{\text{token}}$).
3. **Delay Degradation Slope**: $\frac{d(Acc_{\text{exact}})}{dN}$ across $N \in \{0, 1, 5, 10, 20, 30, 40, 50\}$.
4. **Adaptation Time**: Number of trials to reach 50% max accuracy in Few-Shot mode.
5. **Capability per Footprint**: $Acc_{\text{exact}} / \text{VRAM\_Bytes\_Used}$.

### 6.2 Mandatory Output Provenance Manifest
Every benchmark execution run MUST export a JSON manifest containing:
- `protocol_id`: `"TASK_GENERALIZATION_PHASE_G_DMTS_v2"`
- `brain_checkpoint_sha256`: Hash of `Brain_Phase4_65K_Cortical.npz`
- `seeds_evaluated`: `[701, 702, ..., 710]`
- `exact_chance_baseline`: `0.00036443`
- `primary_metric_results`: Per-seed raw deltas & paired t-test p-value
- `controls_verified`: `{ "no_refuge": true, "no_ark": true, "no_repro": true }`
- `censored_observations`: Number of organisms evaluated vs pre-evaluation deaths.
