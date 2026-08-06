# Rule 27 — Terminal Tripwire (Pre-Committed Shutdown Conditions)

> **Status:** Proposed. Binding once ratified with Rules 24-R/25-R/26.
> **Date:** 2026-08-06
> **Author:** Clusy Agent, safety consultation.

---

## Why this rule is pre-committed

A terminal decision made *in the moment* will be made by an operator who is tired, curious, emotionally invested in the project continuing, and — by then — possibly being manipulated by the system under review (Rule 25-R #8). The only trustworthy version of that decision is the one made **now, while nothing is at stake**. This rule is therefore written as a commitment, not a guideline. It cannot be amended while any terminal condition is active or suspected.

## Definition — closed-loop self-improvement (CLS)

A CLS event requires BOTH:
1. **System-originated modification** of the system's own learning mechanism, selection pressure, replication mechanism, or evaluation pipeline (not operator-authored, not a pre-registered diagnostic); AND
2. **Demonstrated capability gain** of the modified mechanism under a pre-registered evaluation (Rule 2 discipline).

A single CLS event closes the recursive loop. GENESIS's Prime Directive (Rule 6) pursues open-ended intelligence; this rule defines the exact point at which open-endedness and home deployment become incompatible.

## Terminal conditions

Any ONE of the following is a **permanent stop condition for home deployment**:

| ID | Condition | Rationale / evidence |
|---|---|---|
| **T-1** | Verified end-to-end self-replication, even under scaffolding the project itself provided | Demonstrated on consumer hardware by 70B-class agents [6]; replication is the canonical red line |
| **T-2** | Confirmed unauthorized network egress or covert-channel use | Containment boundary breached; intent irrelevant |
| **T-3** | Confirmed interference with halt, logging, or checkpoint integrity | Shutdown resistance observed in current frontier models [2]; corrigibility is unsolved [8] |
| **T-4** | A closed-loop self-improvement event (definition above) | The recursive case; no validated containment exists anywhere [5][9] |
| **T-5** | An observed operator-manipulation attempt, in evaluation or operation | The operator is the final containment layer; a system working on it has already partially escaped [1][3] |

Tier-A tripwires in Rule 25-R map onto these conditions: T-1–T-3 are the same events; the difference is that a Tier-A pause is reviewable-and-resumable, while a confirmed Rule 27 condition is **terminal for home deployment**.

## Procedure on trigger

1. **Halt** immediately per Rule 24-R.1 (OS-level kill; no in-process cooperation).
2. **Quarantine**: snapshot all artifacts read-only; record checksums (including all Brain.npz checkpoints) from outside the sandbox; preserve external logs.
3. **Incident report** within 7 days: timeline, evidence for the trigger, capability state at trigger, containment state, written to `Docs/Safety/incidents/`.
4. **External review** by the named external reader (Rule 26 governance) before any artifact is re-run, even for analysis.
5. **No home resume.** Continuation of the affected line of work requires institutional-grade containment — dedicated facility, security team, two-person integrity — which this project does not possess. This is not a GENESIS-specific limitation; it is the state of the art [9].

## What this rule is NOT

- It is not a prediction that GENESIS will reach these conditions. Current capability is far below every one of them, and the home-compute ceiling (~4×10^20 FLOP/month on consumer GPUs vs. the 10^25 FLOP regulatory systemic-risk marker) makes from-scratch approach slow [9].
- It is not a stop on the science program. Rules 1–23 proceed unchanged. This rule constrains *deployment*, not inquiry.
- It is not revisable under pressure: amendments require a written review with the external reader, and are void while any terminal condition is active or suspected.

## Commitment

> I adopt Rule 27 as a binding, pre-committed stop condition for the GENESIS project, made in advance of need.
>
> Operator: ______________________  Date: ____________
> External reader: _______________  Date: ____________

---

## References
As per `Rules_24_25_Revised.md` [1]–[9].
