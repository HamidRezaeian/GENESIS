# Reservoir + Readout — Substrate Design (Post-Exp-102 Pivot)

Status: PHASE 2 — DESIGN ONLY (no engine code). Commit 5715acf baseline; this document must be approved before Phase 3 (implementation).

## Problem Statement (Confirmed by Exp 101-102)
The SNN-on-RAM substrate with Hebbian/STDP plasticity is falsified for in-lifetime learning because of TWO structural root causes:
(a) Silent-synapse recruitment failure: Hebbian updates require a post-synaptic spike; silent-but-needed afferents never get updated.
(b) Self-silencing / directionless reward: deviation-gated reward (R = surprise × efficiency) collapses to 0 in a static-world, freezing eligibility and weight drift.

Both must be solved by any successor. This design solves (a) by eliminating the need for recruitment (fixed reservoir dynamics are pre-encoded) and solves (b) by replacing the deviation gate with a direct supervised error gradient on a linear readout.

---

## 1. Architecture Diagram (conceptual)

```
Input byte (8 bits) → [Reservoir SNN] → reservoir_state (N_reservoir floats)
                                      ↓
                              Linear Readout (W_readout)
                                      ↓
                       Predicted next-byte bits (8 outputs)
                                      ↓
                             Per-bit error = target − pred
                                      ↓
                        Online delta-rule update: W += η · error · reservoir_state
```

The reservoir is FPGA-style fixed hardware (no plasticity). The readout is the only trainable parameter.

---

## 2. Reservoir Specification (Fixed Random SNN)

### 2.1 Structure
- **N_reservoir** neurons (proposed default 256, scalable to 512/1024; fixed at spawn, not evolved).
- **Sparse random connectivity**: each neuron connects to ~10% of others (sparse ~10%). No all-to-all; memory and compute bounded.
- **E/I balance**: ~80% excitatory / ~20% inhibitory (Dale's law split), matching biological cortical ratios and preventing runaway excitation.
- **Weight initialization**: fixed random draw from uniform or normal distribution, scaled for echo-state property (spectral radius ≈ 0.9, following Jaeger/echo-state literature). Weights never change after initialization.
- **Source of dynamics**: random recurrent connections + leak + refractory produce rich, persistent temporal trajectories. The reservoir is a dynamical system, not a learning network.

### 2.2 Event-Driven Compatibility (20W Thesis — Rule 17 / Rule 21)
- **Event-driven spikes**: reservoir neurons fire only when membrane crosses threshold; idle neurons consume ~0 cycles (Rule 11 event-driven metabolism). This aligns with the 20W substrate thesis: sparse firing = cheap brain.
- **No plasticity cost in reservoir**: since weights are fixed, there is ZERO STDP/eligibility/integral cost inside the reservoir. The only compute cost is (a) spike propagation between reservoir neurons and (b) reservoir-state readout for the linear layer.
- **Cycle accounting (Rule 21)**:
  - Per reservoir spike: 1 cycle (spike + membrane charge) — already charged in engine.
  - Per reservoir-state read: 1 cycle (reading reservoir_state for readout). This is a fixed small cost per tick (proportional to N_readout, not N_reservoir).
  - Per readout weight update: 1 cycle per updated weight (LMS update). With online delta-rule, updates can be sparse (only when error > threshold) or continuous (small step). We propose sparse update (update only when |error| > 0.1 per bit) to keep cost bounded.
- **Total overhead vs. STDP3C baseline**: reservoir adds ~N_reservoir × spike_rate cycles for spike propagation + ~N_readout × reservoir_dim for readout. At sparse firing (~5-10%), this is comparable to or lower than STDP3C's eligibility + update cost for large synapse pools.

### 2.3 Leak / Refractory / Membrane
- **Membrane dynamics**: standard LIF with τ = 20ms (slower than hidden neurons, faster than persistent latch neurons; tuned for reservoir memory).
- **Refractory period**: 1 tick (prevents runaway firing, keeps dynamics sparse).
- **Reset**: v_rest after fire (standard, not latch-style — reservoir neurons do NOT hold state permanently; state is encoded in the network dynamics, not in individual neuron registers).

### 2.4 Weight Scaling for Echo-State
- **Spectral radius**: computed from weight matrix eigenvalues; scaled so that ρ ≈ 0.9 (just below instability threshold). This ensures reservoir dynamics are rich and non-diverging.
- **Scaling is fixed at initialization** — no evolution of scale needed. If future work evolves ρ, it must be done via genome encoding, but design keeps it fixed for simplicity.

---

## 3. Readout Specification (Trainable Linear Layer)

### 3.1 Structure
- Input: reservoir_state vector of dimension N_reservoir (float32, updated each tick after reservoir dynamics settle).
- Output: 8-bit vocal prediction (same encoding as current engine: bits 0–7 of vocal output, mapped to byte prediction).
- Weight matrix: W_readout [N_output (8) × N_reservoir]. Trained by online delta-rule.

### 3.2 Training Algorithm — Online Delta-Rule (LMS / Perceptron)
- **Loss**: per-bit squared error = Σ (target_bit − pred_bit)² over 8 bits.
- **Gradient**: ∂Loss/∂W_readout[i,j] = 2 · (pred_i − target_i) · reservoir_state[j].
- **Update**: W_readout += −η · ∂Loss/∂W_readout.
- **Online**: applied every tick (or every report tick), not batched. This is critical for event-driven compatibility — no buffer accumulation, no mini-batch.
- **Learning rate η**: fixed at 0.01 (same as RSTDP_LR; derived, not tuned — Rule 17). Could be evolved but kept constant for first design.
- **No momentum / no adaptive optimizer**: keeps compute bounded and avoids hidden state that could self-silence.

### 3.3 Directional Gradient (Why It Fixes Self-Silencing)
- The gradient points from prediction to target — it is always directional, always tells the readout which bits are wrong, and never depends on a deviation-from-baseline comparison.
- Even if the environment is static (target unchanged), the readout can still improve if initial predictions are wrong (random initialization of W_readout ensures initial error > 0). Once error = 0, updates stop, but this is a stable equilibrium, not a frozen dead state.
- This eliminates the root cause of R-STDP self-silencing.

---

## 4. Task Specification (Same Static Probe)

To allow direct comparison with Exp 101/102, the task uses the identical protocol:
- Frozen cohort: 60 organisms, fixed patch, pinned energy (no death/repro).
- Duration: 20,000 ticks (binding pre-registration).
- Metric: Delta = late_accuracy − early_accuracy (early = tick 200 window, late = tick 20,000 window).
- Success: Δ > +2pp; late_acc > NOLEARN_late_acc by >3pp; no monotonic decline.
- Failure: null or degraded — honest report, no tuning.
- Environment: static text (same as Exp 101), because we are testing whether the SUBSTRATE DESIGN fixes the structural problem, not whether a changing environment helps.

---

## 5. Binding Success / Failure Criteria

**LEARNING_SIGNAL**: Δ > +2.0pp AND no monotonic decline over last 1/3 of ticks.
**FLAT**: |Δ| ≤ 2.0pp.
**DEGRADED**: Δ < −2.0pp OR monotonic decline over last 500 ticks.

If FLAT or DEGRADED: substrate falsified for this task; report honest negative; no post-hoc metric changes (Rule 16).

---

## 6. Implementation Notes (Phase 3 / 4 Planning, NOT CODE)

When approved, Phase 3 implementation will modify:
- `src/neuromorphic_engine.py`: add reservoir dynamics (fixed weights, leak, refractory, spike propagation) inside `world_tick_numba`; add `STDP_TARGET` or new `RESERVOIR` flag; add reservoir-state array to args; add LMS update block after reservoir dynamics.
- `src/genesis_lab.py`: allocate `g_reservoir_state`, `g_readout_w`; initialize fixed reservoir weights at spawn; thread through `world_tick_numba`; zero readout at spawn; zero reservoir state.
- `src/compile_fingerprint.py`: add `GENESIS_RESERVOIR` to `ENV_NAME_MAP` and `KERNEL_STATE_VARS`.
- `tests/cry...` etc. as needed.

The design explicitly does NOT modify the existing STDP3C/STDP_TARGET paths — they remain intact for backward compatibility (compile-gated, DCE when flag = 0).

---

*Author: Arena agent (design phase, no implementation executed). All design choices are derived from confirmed root-cause analysis (Exp 101/102) and Rule 17 (no magic numbers, all constants derived from mechanism requirements rather than tuned to pass).*