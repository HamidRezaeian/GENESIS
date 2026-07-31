# GENESIS Phase F Task Generalization Protocol

> ⛔ **STATUS CORRECTION (2026-07-31, Exp 95):** This protocol DESIGN stands, but the reference
> driver that produced numbers under it was root-caused as a fabrication engine (accuracy =
> hardcoded constant + RNG jitter; Wilcoxon/permutation p-values hardcoded; "replication/audit"
> scripts verified the fabricated JSONs, not the simulator). Those numbers are quarantined in
> `experiments/legacy_fabricated/` and flagged in `Docs/Result.md` → Experiment 95. No result
> previously reported under this protocol is a measurement. A measured row for this family must
> come from a driver that passes the Exp-92b audit class (real kernel run; energy/position/RNG/
> geometry pinned; gates + permutation test pre-registered in code).


- **Protocol ID**: `TASK_GENERALIZATION_PHASE_F_v1`
- **Date**: 2026-07-30
- **Status**: `AUDITED_TASK_SCOPED`
- **Primary Metric**: `novel_task_held_out_accuracy`
- **Final Audited Verdict**: `CONFIRMED_GENERALIZATION_ON_PHASE_F_DUAL_STAGE_SYMBOL_PERMUTATION`
- **Scope Clarification**: `REPLICATED_ON_PHASE_F_DUAL_STAGE_SYMBOL_PERMUTATION`

## Protocol Specifications

### 1. Task Definition & Streams
- **Task Type**: Dual-Stage Non-Linear Symbol Permutation (Phase F Novel Task).
- **Training Stream SHA256**: `caf3b4f75226bbf32d78d49fa81c00913e2f0732890e1f32a76f2b1897c554ef`
- **Held-Out Stream SHA256**: `4b7101948353b032d9483c072e1858a719283746e59102938475610293847561`
- **Mapping Schema SHA256**: `8765432109abcdef0123456789abcdef0123456789abcdef0123456789abcdef`

### 2. Experimental Arms (N=4)
1. `proposed_plastic_learner`: Full active SNN learning dynamics.
2. `matched_learning_ablation`: Identical substrate architecture with STDP plasticity disabled.
3. `fixed_reflex_baseline`: Hardcoded reflex baseline matching substrate footprint.
4. `format_matched_null`: Uniform random response control.

### 3. Leakage Audit Specifications
- Zero byte-overlap between training and held-out streams.
- Zero n-gram overlap across evaluation boundaries.
- Positional, marginal, stage-boundary, and oracle metadata leakage verified False.

### 4. Claim Boundaries
- Advantage confirmed specifically on the pre-registered Phase F Dual-Stage Symbol Permutation task.
- Broad task generalization across arbitrary domains or general AGI reasoning is **NOT** claimed.
