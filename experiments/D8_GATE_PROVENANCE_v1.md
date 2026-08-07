# D8 Gate Provenance Declaration

**Run ID:** D8_CONFIRMATORY
**Date:** 2026-08-07 16:59 UTC
**Gate Claim:** A1 (from scratch, no priors)

## Evidence

### Initialization Source
File: `experiments/sub4_small_transformer.py`

The agent initialization is purely random:

    weights = (rng.randn(...) - 0.5) * 0.1

RNG stream: `seed * 100 + org_id`

### No Priors Present
- No pretrained weights
- No meta-trained readout initialization
- No evolved ancestor structure
- No world-model priors

### NOLEARN Ablation
- Constructed identically (same init, same RNG stream)
- Only difference: READOUT_LR = 0.0 (update gate disabled)
- Receives same initialization as LEARN arm

## Verdict
This run claims **Gate A1** per Paper_Outline_v3 Appendix A.

## Rule Compliance
- Rule 17: Provenance declared before execution
- Rule 2:  Pre-registered, no post-hoc changes
