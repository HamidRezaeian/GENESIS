# Gate A Reconciliation: Old Metric vs Corrected Metric

**Date:** 2026-08-07 16:59 UTC
**Status:** Binding

## The Problem

The original Gate A used accuracy delta:

- Old metric: d = late_accuracy - early_accuracy >= +5.00 pp
- Result: all substrates failed (only +2-4 pp observed)

Accuracy is a coarse, saturated measure that masks real learning.

## The Correction

Amended metric (commit e4c4db7) uses rho (error-space reduction):

- Corrected metric: rho = (E0 - E1) / E0 >= 0.25
- Result: sub4-20k passes  (rho = 26.8 %, CI [23.4, 30.1])

## Gate A1 / A2 Split (Paper_Outline_v3 Appendix A)

| Gate | Priors  | Init                | Bar                          |
|------|---------|---------------------|------------------------------|
| A1   | None    | Random / ancestor   | rho >= 0.25  OR  d >= +5 pp |
| A2   | Allowed | Evolved/meta/pretrain| Same bars; ablation same priors |

## Current Status

| Artifact                    | Verdict                            | Gate | rho           |
|-----------------------------|------------------------------------|------|---------------|
| sub4-20k                    | SCREEN PASS (confirmatory pending) | A1   | 26.8 [23.4,30.1] |
| sub4-2k                     | REAL_BUT_NEGLIGIBLE (F2)          | A1   | ~20 %         |
| sub4-novel                  | REAL_BUT_NEGLIGIBLE (F2)          | A1   | rho_B ~ 6 %   |
| sub3, sub5, sub4-nonstat    | STATIC_ONLY (F3)                  | A1   | < 25 %        |
| exp103b                     | STATIC_ONLY (F3)                  | A1   | < 25 %        |
| exp103                      | NULL + F4 audit flag              | A1   | N/A           |

## D8 Confirmatory Status
- Status: pending execution (seeds 100-107)
- Gate: A1
- Pass criteria: T (slope CI > 0) + M (rho >= 0.25) + B (paired gap CI > 0)

## Rule Compliance
- Rule 2, 16, 17
