# D8 Confirmatory Run — Pre-Registration

**Date:** 2026-08-07 16:59 UTC
**Status:** Pre-registered, pending execution

## Run Specification
- Run ID: D8_CONFIRMATORY
- Driver: experiments/sub4_extended_20k.py (byte-copy, 3-line diff)
- Modification: ONLY seed list + output path changed
- Seeds: 100-107 (8 seeds)
- Arms: LEARN + NOLEARN (matched ablation, READOUT_LR=0.0)
- Gate claim: A1
- Ticks per arm: 20,000
- Total ticks: 320,000

## Pass Criteria (Frozen)

| Verdict | Criterion                              | Threshold |
|---------|----------------------------------------|-----------|
| T       | Slope of learning curve, 95% CI lower  | > 0       |
| M       | rho = (E0-E1)/E0                       | >= 0.25   |
| B       | Paired LEARN-NOLEARN gap, 95% CI lower | > 0       |
| PASS    | All three T+M+B                        | —         |

## Output
- Directory: sub4_results/d8_confirmatory/
- Summary:   experiments/CONFIRMATORY_D8_SUMMARY_v1.md

## Physical Accounting
- Wall-clock + tick count
- RAPL gap recorded where unavailable
- Rule 21 compliance

## Halt Conditions
- Any seed anomaly > 3 sigma from cohort mean
- Monitor Tier-A alert
- Import error or crash

## Rule Compliance
- Rule 2, 3, 8, 16, 17, 21
