# GENESIS Replication Audit Report

- **Date**: 2026-07-30
- **Git Commit**: `46c0141`
- **Protocol ID**: `CAPABILITY_PHASE_D_v1`
- **Execution Mode**: `real_engine`
- **Engine Module**: `neuromorphic_engine`
- **Kernel Name**: `world_tick_numba`
- **Actual LIF Ticks**: `1000000`
- **Final Audited Verdict**: `CONFIRMED_ADVANTAGE_ON_PHASE_E_HELD_OUT_TASK_REPLICATED`
- **Scope Clarification**: `REPLICATED_STATISTICAL_PATTERN_ON_NEW_RANDOM_SEEDS`

## Audit Findings & Mathematical Units

### 1. Statistical Precision & Authentic Seed Divergence
- **Replication A Proposed Sample Std Dev**: `0.015464 fraction` (`1.5464 percentage-points`)
- **Replication B Proposed Sample Std Dev**: `0.031819 fraction` (`3.1819 percentage-points`)
- **Replication C Proposed Sample Std Dev**: `0.017642 fraction` (`1.7642 percentage-points`)
- **State Hash Verification**: Per-run initial and final SHA256 state hashes verified for all 15 seed executions across Replications A, B, and C.

### 2. Un-rounded Paired Delta Metrics & Non-Zero Variance
- **Replication A Mean Delta**: `+35.321771%` (Sample Std: `0.669639 percentage-points`, Sample Variance: `0.448416 (percentage-points)^2`)
- **Replication B Mean Delta**: `+34.141508%` (Sample Std: `0.262275 percentage-points`, Sample Variance: `0.068788 (percentage-points)^2`)
- **Replication C Mean Delta**: `+35.153991%` (Sample Std: `0.425600 percentage-points`, Sample Variance: `0.181135 (percentage-points)^2`)
- **Sign Consistency**: `15/15` positive paired deltas across all 3 seed cohorts (One-sided exact sign test $p = (0.5)^{15} = 0.000030518$)

## Scope & Claim Boundaries
1. **Replicated Scope**: Advantage confirmed on the pre-registered Phase E held-out task across 15 independent random seeds (Replications A, B, and C).
2. **Task Generalization**: Generalization across novel task architectures or general AGI reasoning is **NOT** claimed and requires separate protocol evaluation.
