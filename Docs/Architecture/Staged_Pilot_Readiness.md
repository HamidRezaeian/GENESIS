# Staged Pilot Readiness

**Date:** 2026-08-07 16:59 UTC
**Status:** Driver pending — NOT ready to launch

## Gate Claim
- Gate: A1 (from scratch, no priors, random init)
- rho pass bar: >= 0.25
- Slope CI: > 0
- Paired gap CI: > 0

## Protocol Stages

| Stage | Ticks   | Purpose       | Status         |
|-------|---------|---------------|----------------|
| S1    | 5,000   | Smoke test    | Driver pending |
| S2    | 20,000  | Confirmatory  | Driver pending |
| S3    | 100,000 | Extended      | Driver pending |

## Alignment with Paper_Outline_v3
- Gate A1/A2 split: Appendix A
- rho metric amendment: SUBSTRATE_4_LEARNING_CURVE_v1
- Pre-registration: Rule 2
- Physical accounting: Rule 21

## Blocker
The staged-pilot driver needs implementation:
- Resume-from-snapshot
- Gate slope/CI evaluation on rho
- Mid-run flush
- Protocol-ID + SHA attribution

## Launch Commands (when ready)

    python experiments/sub4_staged_pilot.py --stage S1 --seed 0 --ticks 5000
    python experiments/sub4_staged_pilot.py --stage S2 --seed 0 --ticks 20000
    python experiments/sub4_staged_pilot.py --aggregate --stage S1 --seeds 0 1 2 3

## Cost Estimate
- S1 (5k):   ~2 min
- S2 (20k):  ~10 min parallel / ~70 min serial
- S3 (100k): ~6 h
