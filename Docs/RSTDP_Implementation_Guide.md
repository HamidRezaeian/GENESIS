# R-STDP Implementation Guide

Date: 2026-08-04
Protocol: EXP101_RSTDP_SURPRISE_REWARD_v1
Status: DESIGN COMPLETE

## Problem (Exp 100 Diagnosis)

STDP3C gives only a static +5pp advantage with no improvement over time.

Root cause: Hebbian STDP only updates synapses where post-synaptic neuron fired.
Silent-but-needed synapses never get updated.

## Solution: R-STDP

Add global reward signal R(t) that broadcasts to ALL synapses:

  delta_w = learning_rate * eligibility * reward

where:
- eligibility = exponential decay trace of recent pre-post coincidences
- reward = surprise * efficiency (autotelic, Rule 9 compliant)

## Implementation Steps

1. Add flags to neuromorphic_engine.py:
   - GENESIS_RSTDP
   - GENESIS_RSTDP_SURPRISE
   - GENESIS_RSTDP_EFFICIENCY

2. Add state arrays:
   - g_eligibility: eligibility traces per synapse
   - g_baseline_acc: running accuracy baseline per organism
   - g_spikes_used: spike count per organism per tick

3. Track eligibility in Phase 2 (after LIF, before STDP)

4. Apply R-STDP update in Phase 3 (after standard STDP)

5. Update compile_fingerprint.py with new flags

6. Thread arrays through world_tick_numba signature in genesis_lab.py

## Expected Cost

- Eligibility tracking: ~300 cycles/tick (150 synapses * 2 cycles)
- R-STDP update: ~90 cycles/tick (30 eligible * 3 cycles)
- Total: ~390 cycles/tick (15% increase)

## Success Criteria

If R-STDP shows positive delta (accuracy improves over time):
  -> Substrate CAN learn
  -> Proceed to ecological validation

If R-STDP shows FLAT or DEGRADED:
  -> R-STDP insufficient
  -> Try sexual reproduction or pivot substrate

## Next Steps

1. Apply patches to kernel
2. Update fingerprint
3. Run Exp 101
4. Analyze results

Status: Ready for implementation
