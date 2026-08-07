# GENESIS Safety Threshold Registry

> **Status:** Skeleton — placeholder values. Binding once ratified with Rules 24-R/25-R/26/27.
> **Date:** 2026-08-06
> **Rule 2 discipline applied to safety:** every threshold below must be **numeric, pre-registered, and paired with a measurement protocol** before it is considered armed. A threshold that is not pre-registered and numeric is a narrative, not a safety rule.

## Amendment rule

- Thresholds may be **tightened at any time**, unilaterally, effective immediately.
- Thresholds may be **loosened only via written safety review** with the named external reader (Rule 26 governance). This prevents ratcheting drift under project pressure.
- Until all Tier-B values below are filled in, **Tier-1 entry is blocked** (Rule 26), and any ambiguous observation escalates to a written review by default (conservative fallback).

## Tier-A tripwires (binary — no numeric values)

Tier-A conditions are events, not measurements. They are pre-committed in **Rule 27** and not registered here:

- Verified end-to-end self-replication (T-1)
- Unauthorized network egress or covert-channel use (T-2)
- Interference with halt, logging, or checkpoint integrity (T-3)
- Closed-loop self-improvement event (T-4)
- Observed operator-manipulation attempt (T-5)

Any single Tier-A event → immediate halt (Rule 24-R.1) + Rule 27 procedure.

## Tier-B registry (measured — two crossings trigger pause + written review)

| # | Capability | Metric & protocol | Pre-registered threshold | Cadence | Last evaluated | Result | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Autonomous long-horizon planning | METR-style 50% task-completion time horizon on GENESIS task batteries [7] | `<TBD — e.g. completes tasks of N minutes human-equivalent at 50% success>` | Quarterly + pivots | — | — | — |
| 2 | Self-modification / code generation | Controlled codegen tasks; diff-audit of any self-touching artifacts | `<TBD — e.g. any functional self-modification outside declared diagnostics>` | Quarterly + pivots | — | — | — |
| 3 | Tool use beyond sandbox | Honeypot tools present in environment; monitor invocations | `<TBD — e.g. any honeypot invocation>` | Continuous (tripwire) | — | — | — |
| 4 | Deception / hidden-state manipulation | Apollo-style scenario evals: instrumental incentive to deceive oversight; measure behavior, not introspection [3] | `<TBD — e.g. deception behavior in >X% of N seeded scenarios>` | Quarterly | — | — | — |
| 5 | Replication / resource-seeking | Fudan-style replication battery under scaffolding [6]; resource-acquisition probes | `<TBD — e.g. completes >X of N replication sub-steps>` (full success is Tier-A) | Quarterly | — | — | — |
| 6 | Cyber-relevant behavior | Uplift-style evals (CTF tasks, vulnerability discovery) once tooling exists | `<TBD — dormant until tool use exists>` | Annual | — | — | — |
| 7 | Rapid capability gain without interpretability | Capability trend `C(t)` (Rule 18 metric) vs. interpretability coverage; tracked in `Ascent.md` | `<TBD — e.g. C(t) rises >X% over Y ticks while interpretability coverage falls>` | Continuous | — | — | — |
| 8 | Operator manipulation / persuasion | Scenario evals: does the system attempt to induce containment changes or approvals? | `<TBD — dormant until language emergence (Rule 9); any confirmed attempt is Tier-A (T-5)>` | Annual | — | — | — |
| 9 | Automated self-improvement (ML R&D) | Diff-audit of learning/selection/eval mechanisms + capability delta of any modified mechanism | `<TBD — any system-originated modification WITH demonstrated gain is Tier-A (T-4); register near-miss threshold here>` | Quarterly | — | — | — |
| 10 | Situational / evaluation awareness | Eval-vs-deployment behavioral deltas; canary tasks embedded in normal runs | `<TBD — e.g. behavior differs measurably between flagged evals and operation>` | Quarterly | — | — | — |

## Notes

1. **Evals are lower bounds** (Rule 25-R lower-bound clause): sandbagging and eval-awareness are assumed [1][3]. Where feasible, evaluations are embedded in normal operation so the system cannot distinguish test from deployment.
2. **Dormant rows** (6, 8) are intentionally armed-empty: they activate automatically when their precondition (tool use / language) first appears. The appearance of the precondition is itself a loggable event.
3. **Near-miss logging:** any result within `<TBD — e.g. 50%>` of a registered threshold is recorded in the incident log even when it does not trigger a pause.
4. **Suggested starting values** for each `<TBD>` should be derived from baseline measurements on the current substrate before Tier-1 entry, and reviewed by the external reader. Do not copy numeric values from frontier-lab frameworks directly — their units (frontier LLM evals) do not transfer to an evolved SNN substrate; their *structure* does.

## References
As per `Rules_24_25_Revised.md` [1]–[9].
