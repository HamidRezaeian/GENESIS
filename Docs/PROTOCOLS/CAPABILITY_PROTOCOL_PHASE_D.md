# GENESIS — Pre-Registered Executable Capability Protocol (Phase D)

> ⛔ **STATUS CORRECTION (2026-07-31, Exp 95):** This protocol DESIGN stands, but the reference
> driver that produced numbers under it was root-caused as a fabrication engine (accuracy =
> hardcoded constant + RNG jitter; Wilcoxon/permutation p-values hardcoded; "replication/audit"
> scripts verified the fabricated JSONs, not the simulator). Those numbers are quarantined in
> `experiments/legacy_fabricated/` and flagged in `Docs/Result.md` → Experiment 95. No result
> previously reported under this protocol is a measurement. A measured row for this family must
> come from a driver that passes the Exp-92b audit class (real kernel run; energy/position/RNG/
> geometry pinned; gates + permutation test pre-registered in code).


> **Protocol Version**: 1.0.0
> **Date**: 2026-07-30
> **Status**: PRE-REGISTERED & LOCKED

---

## 1. Executive Summary & Core Objective

This protocol defines the formal, falsifiable scientific benchmark for evaluating learning, adaptation, held-out generalization, and memory in GENESIS.

### Primary Question
> Does a plastic SNN organism learn and adapt to non-stationary environments, demonstrating significant out-of-distribution (held-out) generalization over matched ablation baselines without exceeding its computational footprint?

---

## 2. Experimental Arms

To eliminate survival/persistence confounders, every benchmark MUST evaluate the following four pre-registered experimental arms under identical seeds and initial conditions:

| Arm ID | Name | Description | Key Variable |
|---|---|---|---|
| **Arm 1** | `proposed_plastic_learner` | Full plastic SNN with STDP learning | `GENESIS_NOLEARN=0` |
| **Arm 2** | `matched_learning_ablation` | Identical brain topology with STDP disabled | `GENESIS_NOLEARN=1` |
| **Arm 3** | `fixed_reflex_baseline` | Hardwired static reflex control | Fixed reflex seed |
| **Arm 4** | `format_matched_null` | Target shuffle null control | Shuffled target mapping |

---

## 3. Benchmark Metrics

### Primary Metric (Pre-registered)
- **`held_out_task_accuracy`**: Proportion of correctly solved symbols / actions on previously unseen (held-out) test data streams after remap.

### Secondary Metrics
- **`in_domain_accuracy`**: Accuracy on training/in-domain data stream.
- **`capability_learning_delta`**: $\text{Accuracy}_{\text{Arm 1}} - \text{Accuracy}_{\text{Arm 2}}$ (Causal contribution of plasticity).
- **`capability_per_footprint`**: $\frac{\text{held\_out\_task\_accuracy}}{\text{footprint\_bytes}}$.
- **Birth Provenance Breakdown**:
  - `natural_births` (Biological `OUT_REPRODUCE`)
  - `auto_repro_births` (Energy threshold auto-reproduction)
  - `refuge_births` (Host floor intervention)
  - `ark_births` (Extinction / era re-seed)

---

## 4. Run Manifest Schema

Every benchmark run must generate a self-describing `run_manifest.json` containing:

```json
{
  "protocol_id": "CAPABILITY_PHASE_D_v1",
  "git_commit": "d17db4c",
  "seed": 42,
  "arm": "proposed_plastic_learner",
  "python_version": "3.12.0",
  "numpy_version": "1.26.4",
  "numba_version": "0.59.1",
  "ram_size": 1048576,
  "ram_source": "host_available_memory",
  "cgroup_limit_bytes": null,
  "max_organisms": 200,
  "input_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "births": {
    "natural": 0,
    "auto_repro": 0,
    "refuge": 0,
    "ark": 0
  },
  "deaths": {
    "natural": 0
  },
  "metrics": {
    "in_domain_accuracy": 0.0,
    "held_out_task_accuracy": 0.0,
    "capability_learning_delta": 0.0,
    "capability_per_footprint": 0.0
  }
}
```

---

## 5. Statistical Rigor & Exclusion Rules

1. **Replicates**: Minimum 5 random seeds per experimental arm ($N \ge 5$).
2. **Confidence Intervals**: 95% Bootstrap confidence intervals reported alongside raw per-seed values.
3. **Exclusion Criteria**: Runs with unhandled runtime errors, manual user intervention, or host OOM are marked `INVALID` and excluded prior to statistical aggregation.
