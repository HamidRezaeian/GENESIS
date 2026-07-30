# GENESIS Phase F Task Generalization Protocol

- **Protocol ID**: `TASK_GENERALIZATION_PHASE_F_v1`
- **Date**: 2026-07-30
- **Status**: `PRE_REGISTERED`
- **Primary Metric**: `novel_task_held_out_accuracy`
- **Primary Hypothesis**: $H_1: \text{Delta}_{\text{learning}} = \text{Accuracy}_{\text{proposed}} - \text{Accuracy}_{\text{ablation}} > 0$ on a novel symbol-permutation task.

## Protocol Specifications

### 1. Novel Task Definition
- **Task Type**: Dual-Stage Non-Linear Symbol Permutation (Phase F Novel Task).
- **Mapping**: Dynamic XOR-permuted alphabet transformation distinct from Phase E.
- **Training Stream Hash**: SHA256 of the Phase F training sequence.
- **Held-out Stream Hash**: SHA256 of the Phase F held-out evaluation sequence.

### 2. Experimental Arms (N=4)
1. `proposed_plastic_learner`: Full active SNN learning dynamics.
2. `matched_learning_ablation`: Identical substrate architecture with STDP plasticity disabled.
3. `fixed_reflex_baseline`: Hardcoded reflex baseline matching substrate footprint.
4. `format_matched_null`: Uniform random response control.

### 3. Leakage Audit Specifications
- Zero byte-overlap between training and held-out streams.
- Zero n-gram leakage across evaluation boundaries.
- Positional, marginal, and oracle metadata audit verified.

### 4. Claim Boundaries
- Evaluates task-level learning generalization beyond random seed initialization.
- Does **NOT** claim general AGI or human-level reasoning.
