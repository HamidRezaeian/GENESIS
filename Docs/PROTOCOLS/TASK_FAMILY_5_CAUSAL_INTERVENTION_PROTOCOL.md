# Task Family 5: Causal Intervention & Effect Prediction Protocol (Pre-Registration v1.0)
**Pre-Registration Date**: 2026-07-30
**Protocol ID**: `PHASE_5_CAUSAL_INTERVENTION_AND_EFFECT_PREDICTION_V1`
**Target Checkpoint**: `Brain_Phase4_65K_Cortical.npz` (65,536 Neurons, FP16 Tensor Cores, SHA256 Verified)

---

## 1. Goal & Cognitive Primitive Shift

Arena.ai mandated that Task Family 5 must evaluate a fundamental cognitive primitive: **Disambiguating Observational Correlation $P(Y|X)$ from Active Causal Intervention $P(Y|\text{do}(X))$**.

---

## 2. Environment & Causal Graph Specification

### 2.1 Causal DAG Topology
The environment simulates a Directed Acyclic Graph (DAG) over discrete variables $\{X, Y, Z, W\}$:
$$X \to Y, \quad X \to Z, \quad Y \to W, \quad Z \to W$$

### 2.2 Zero Privileged Information
Organisms have **ZERO** access to privileged causal hints:
- No variable names or node IDs.
- No direct causal edge vectors.
- No Oracle target predictions.

---

## 3. Five Protocol Execution Stages

1. **Stage 1 — Passive Observation**: Organism observes correlated variable streams without intervention.
2. **Stage 2 — Active Intervention**: Organism applies active intervention actions: $\text{do}(X=0)$ or $\text{do}(X=1)$.
3. **Stage 3 — Held-Out Intervention**: Intervention applied to novel held-out variable combinations.
4. **Stage 4 — Held-Out Graph Topology**: Evaluated on 5 completely unseen DAG structures.
5. **Stage 5 — Confounding Challenge**: Spurious observational correlations are broken during active intervention. The organism MUST predict true causal outcomes rather than repeating surface correlations.

---

## 4. Primary Metric & Experimental Control Arms

### 4.1 Primary Metric
- **Primary Metric**: **Held-Out Interventional Effect Prediction Accuracy** — Fraction of correct outcome predictions following active $\text{do}(\cdot)$ interventions on held-out DAG topologies.

### 4.2 Matched Control Arms
1. **Arm 1: Proposed Zero-Shot**: Base Checkpoint, STDP Frozen, State Zeroed.
2. **Arm 2: Proposed Few-Shot**: Base Checkpoint, STDP Active over 20 adaptation trials.
3. **Arm 3: Matched Learning Ablation**: Fixed weights, frozen plasticity.
4. **Arm 4: Observational-Only Control**: Organism receives passive observation only (no active intervention).
5. **Arm 5: Correlation-Only Baseline**: Predicts purely based on training correlations (Fails on Confounding Challenge).
6. **Arm 6: Shuffled-Intervention Null**: Interventions shuffled while preserving marginal distributions.
7. **Arm 7: Oracle Upper Bound**: True Causal Graph Planner ($100.0\%$).

---

## 5. Statistical Plan & Provenance Manifest Requirements

- **Sample Unit**: $N_{\text{seeds}} = 10$ independent seeds (1101-1110).
- **Multi-Test Significance**: Paired Permutation Test $p < 0.01$, Wilcoxon $p < 0.01$, Cohen's $d_z \ge 0.80$.
- **Strict Controls**: `GENESIS_REFUGIUM=0`, `GENESIS_ARK=0`, `GENESIS_AUTO_REPRO=0`.
- **Claim Boundary Invariant**:
  - Status Label: `CONFIRMED_GENERALIZATION_ON_PHASE_5_CAUSAL_INTERVENTION`
  - Caveats:
    - `REPLICATED_ON_HELD_OUT_INTERVENTIONAL_TASKS`
    - `CORRELATION_ONLY_BASELINE_BEATEN`
    - `BROAD_TASK_GENERALIZATION_NOT_YET_ESTABLISHED`
    - `AGI_CLAIM_NOT_SUPPORTED`
