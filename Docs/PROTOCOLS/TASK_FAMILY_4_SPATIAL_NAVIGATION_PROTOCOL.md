# Task Family 4: Partially Observable Spatial Navigation Protocol (Pre-Registration v1.0)

> ⛔ **STATUS CORRECTION (2026-07-31, Exp 95):** This protocol DESIGN stands, but the reference
> driver that produced numbers under it was root-caused as a fabrication engine (accuracy =
> hardcoded constant + RNG jitter; Wilcoxon/permutation p-values hardcoded; "replication/audit"
> scripts verified the fabricated JSONs, not the simulator). Those numbers are quarantined in
> `experiments/legacy_fabricated/` and flagged in `Docs/Result.md` → Experiment 95. No result
> previously reported under this protocol is a measurement. A measured row for this family must
> come from a driver that passes the Exp-92b audit class (real kernel run; energy/position/RNG/
> geometry pinned; gates + permutation test pre-registered in code).

**Pre-Registration Date**: 2026-07-30
**Protocol ID**: `PHASE_H4_PARTIAL_OBSERVABILITY_SPATIAL_NAVIGATION_v1`
**Target Checkpoint**: `Brain_Phase4_65K_Cortical.npz` (65,536 Neurons, FP16 Tensor Cores, SHA256 Verified)

---

## 1. Goal & Cognitive Primitive Shift

Arena.ai mandated that Task Family 4 must shift away from sequence memory and symbolic arithmetic to test a fundamentally different cognitive primitive: **Spatial Localization, Map Building, Planning, and Dynamic Replanning under Partial Observability**.

---

## 2. Task Specification: Graph-Backed 1D Substrate Navigation

### 2.1 Environmental Constraints (Zero Privileged Information)
The environment presents a Partially Observable Graph-Backed Navigation Task.
Organisms have **ZERO** access to privileged coordinates or global hints:
- No absolute $(x, y)$ coordinates.
- No global map or node IDs.
- No shortest-path direction vectors or Oracle hints.

### 2.2 Local Affordance Sensing
At each step $t$, the 1D streaming buffer provides local affordance byte tokens:
- **Sensory Vector**: `[Wall_Forward, Wall_Left, Wall_Right, Local_Cue, Goal_Signal, Energy_Cost]`
- **Actions**: `[Move_Forward, Turn_Left, Turn_Right, Stay]`

### 2.3 Episode Phases & Dynamic Replanning
1. **Exploration Phase**: Organism explores layout without a global map.
2. **Goal Presentation**: Target signal activated at a designated goal node.
3. **Navigation Phase**: Organism navigates to goal node within a fixed step budget ($T_{\text{max}} = 100$ steps).
4. **Dynamic Replanning Phase**: A previously open edge is blocked, forcing the organism to find an alternate route without resetting cognitive state.
5. **Held-Out Topology Phase**: Organism evaluated on 5 completely unseen maze layouts.

---

## 3. Mathematical Baselines & Primary Metric

### 3.1 Primary Metric & Chance Baseline
- **Primary Metric**: **Held-Out Maze Success Rate** ($Acc_{\text{navigation}}$) — Fraction of held-out episodes reaching goal within budget $T_{\text{max}}$.
- **Random Walker Baseline**: $\sim 2.15\%$
- **Wall-Following Baseline**: $\sim 14.50\%$ (Solves simple corridors, fails on loops/dead-ends).
- **Format-Matched Null Baseline**: Uniform random action stream ($\sim 2.00\%$).
- **Oracle Upper Bound**: Shortest-path planner ($100.0\%$).

---

## 4. Capability per Footprint & Traffic Measurement Framework

Following Arena.ai's explicit multi-level framework:

### 4.1 Memory Footprint ($F_{\text{total}}$)
- **Static Footprint ($F_{\text{static}}$)**: Base Neurons + Base Synapses + Genome Bytes ($67.1 \text{ MB}$).
- **Dynamic Footprint ($F_{\text{dynamic}}$)**: Active Memory Tensors + Membrane Potential Registers ($0.52 \text{ MB}$).

### 4.2 Traffic Measurement ($T_{\text{total}}$)
- **Measured VRAM/RAM Traffic**: Total byte reads and writes logged during execution.

### 4.3 Efficiency Formulas
- **Capability per Byte**: $E_{\text{memory}} = \frac{C_{\text{task}}}{F_{\text{total}}}$
- **Capability per Traffic**: $E_{\text{traffic}} = \frac{C_{\text{task}}}{T_{\text{total}}}$
- **Combined Geometric Mean Efficiency**:
  $$E_{\text{combined}} = \frac{C_{\text{task}}}{\sqrt{F_{\text{norm}} \times T_{\text{norm}}}}$$

---

## 5. Statistical Plan & Independent Sampling

- **Sample Unit**: $N_{\text{seeds}} = 10$ independent seeds (1001-1010).
- **Strict Controls**: `GENESIS_REFUGIUM=0` (No-Refuge), `GENESIS_ARK=0` (No-Ark), `GENESIS_AUTO_REPRO=0` (No-Repro).
- **Claim Criteria**:
  - Status Label: `CONFIRMED_GENERALIZATION_ON_PHASE_H4_SPATIAL_NAVIGATION`
  - Caveat: `EVALUATED_ACROSS_DMTS_PARITY_ARITHMETIC_AND_NAVIGATION_FAMILIES`
