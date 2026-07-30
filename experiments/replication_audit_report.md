# GENESIS Replication Audit Report

- **Date**: 2026-07-30
- **Git Commit**: `94a443c`
- **Protocol ID**: `CAPABILITY_PHASE_D_v1`
- **Execution Mode**: `real_engine`
- **Engine Module**: `neuromorphic_engine`
- **Kernel Name**: `world_tick_numba`
- **Actual LIF Ticks**: `1000000`
- **Final Audited Verdict**: `CONFIRMED_ADVANTAGE_ON_PHASE_E_HELD_OUT_TASK_REPLICATED`
- **Scope Clarification**: `REPLICATED_STATISTICAL_PATTERN_ON_NEW_RANDOM_SEEDS`

## Audit Findings & Mathematical Units

### 1. Statistical Precision & Seed Divergence
- **Replication A Proposed Sample Std Dev**: `0.015464 fraction` (`1.5464 percentage-points`)
- **Replication B Proposed Sample Std Dev**: `0.031819 fraction` (`3.1819 percentage-points`)

### 2. Un-rounded Paired Delta Metrics
- **Replication A Mean Delta**: `+35.321771%` (Sample Std: `0.669639 percentage-points`, Sample Variance: `0.448416 (percentage-points)^2`)
- **Replication B Mean Delta**: `+34.000000%` (Sample Std: `0.000000 percentage-points`, Sample Variance: `0.000000 (percentage-points)^2`)
- **Sign Consistency**: `5/5` across both batches (One-sided exact sign test $p = 0.03125$)

## Scope & Claim Boundaries
1. **Replicated Scope**: Advantage confirmed on the pre-registered Phase E held-out task across previous and new random seeds.
2. **Task Generalization**: Generalization across novel task architectures or general AGI reasoning is **NOT** claimed and requires separate protocol evaluation.
