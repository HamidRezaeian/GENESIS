## 3.3 Neuromodulatory Gating Fails to Filter Noise (Exp-P2B-03)

### Motivation

Phase 2A (v25-v27) showed e-prop is fragile to 5% input noise. Previous 
attempts (sparse encoding, postsynaptic gating) failed. This experiment 
tested acetylcholine (ACh) analog gating: only "surprising" inputs 
create eligibility traces.

### Mechanism
dz_i = max(0, z_i - z_bar_i)
ach_gate_i = (dz_i > 0.5)
eligibility += f'(v_j) * ach_gate_i * z_i


Where z_bar_i is a running mean with tau=100 ticks.

### Pre-registration

- H1: ACh gate at 5% noise > 80% (vs baseline 66.8%)
- H2: ACh gate at 0% noise > 85% (no regression)
- Success = H1 AND H2

### Results

| Condition | Noise | Gate | Accuracy |
|-----------|-------|------|----------|
| no_gate_0 | 0% | OFF | 93.6% |
| ach_gate_0 | 0% | ON | 93.6% |
| no_gate_5 | 5% | OFF | 51.4% |
| ach_gate_5 | 5% | ON | 51.4% |
| ach_gate_10 | 10% | ON | 52.0% |

**H1 FAIL:** ACh gate at 5% noise = 51.4% (expected >80%)
**H2 PASS:** ACh gate at 0% noise = 93.6% (expected >85%)

### Root Cause Analysis

Mathematical analysis reveals why gating failed:

Signal neuron firing rate: ≈ 0.10 spikes/tick
Noise neuron firing rate: ≈ 0.05 spikes/tick
z_bar_signal ≈ 0.10 → dz_signal = 1 - 0.10 = 0.90
z_bar_noise ≈ 0.05 → dz_noise = 1 - 0.05 = 0.95
Both dz values exceed threshold (0.5), so:
ach_gate_signal = 1
ach_gate_noise = 1
Result: Noise spikes are MORE surprising than signal spikes!


### Interpretation

ACh-style surprise gating with running mean baseline cannot distinguish 
signal from Poisson noise in this regime. The fundamental issue is that 
lower firing rate inputs (noise) have lower baselines, making individual 
spikes MORE surprising.

### Biological Implications

Real acetylcholine systems likely use more sophisticated mechanisms:
- Phasic vs tonic ACh release
- Interaction with other neuromodulators (dopamine, norepinephrine)
- State-dependent gating (attention, arousal)
- Hierarchical surprise detection (multiple timescales)

A simple running-mean surprise signal is insufficient.

### Implications for Biologically-Plausible AGI

This null result suggests that solving noise robustness with local 
learning rules requires:
1. Multi-timescale surprise detection (not single tau)
2. Hierarchical gating (multiple neuromodulatory systems)
3. State-dependent mechanisms (attention, context)
4. Or fundamentally different architectures (predictive coding, active inference)

### Data Availability

Code: `experiments/phase2b/code/eprop_p2b03_neuromodulation.py`
Results: `experiments/phase2b/results/exp_p2b_03_neuromodulation_*.json`