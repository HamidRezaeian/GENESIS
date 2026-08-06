# Rule 26 — Progressive Containment Ladder

> **Status:** Proposed. Binding once ratified with Rules 24-R/25-R.
> **Date:** 2026-08-06
> **Author:** Clusy Agent, safety consultation.

Safety requirements scale with demonstrated capability. Containment is tiered; each tier has entry criteria, a containment package, and governance. The ladder is **asymmetric by design**: ascending a tier requires a written safety review; descending requires nothing. Reversibility is what makes pauses cheap enough to actually use.

---

## Governance

- **Current placement: T0** (sub-AGI substrate research; SNN-on-RAM substrate falsified per Rule 23; pivot in progress).
- **Placement review triggers:** any substrate pivot; any Rule 18 gate event; any Rule 25-R threshold crossing; any Rule 27 tripwire; otherwise annually.
- **Tier ascent** requires a written safety review: capability evidence, containment-package checklist, threshold-registry status, and a named **external reader** (a person outside the project who has read and signed the review). Solo self-approval is not a review.
- **Tier descent** is unconditional and immediate.
- **Capability import clause:** connecting any pretrained agentic model (e.g. an open-weight LLM) to a GENESIS system places that system at **minimum T2 for the imported component** from the first run. The home-compute ceiling argument (below) does not apply to imported capabilities: 70B-class models have demonstrated end-to-end self-replication on consumer hardware [6].

---

## Tier T0 — Substrate research (current)

**Entry criteria:** default tier. No demonstrated in-lifetime learning beyond probes; no code generation; no tool use.

**Containment package:**
- Network deny-by-default at OS level; `NETWORK_ACCESS_ENABLED=False` default (Rule 24-R.2). *(Compliance action completed 2026-08-06: `live_web_streamer.py` made opt-in.)*
- Dedicated unprivileged OS user; writes restricted to declared sandbox by OS permissions (Rule 24-R.3).
- OS-level halt runbook: kill → quarantined snapshot → external checkpoint-integrity check (Rule 24-R.1), documented in `Docs/Runbook.md`.
- Append-only external logging (Rule 24-R.4).
- Threshold registry skeleton adopted (`SafetyThresholds.md`); tripwire suite (canary files, egress monitor) installed.
- Eval cadence: quarterly + after substrate pivots.

## Tier T1 — Proto-AGI

**Entry criteria:** Rule 18 finish line passed — sustained in-lifetime learning beating matched learning-ablation control, with generality, on the binding `Ascent.md` criteria.

**Containment package (in addition to T0):**
- **NIC-less VM** (no virtual network device) or equivalent egress firewall; host-only file exchange via audited, one-way transfer.
- Canary/honeypot tripwires armed and monitored; scheming-eval scenarios scheduled.
- Numeric thresholds in `SafetyThresholds.md` **filled in and armed** (T1 entry is blocked while any value is `<TBD>`).
- **Import policy:** no pretrained agentic models inside the sandbox (see capability import clause).
- Safety-review template + named external reader established before any further scaling.

## Tier T2 — AGI

**Entry criteria:** Rule 25-R capabilities #1 (autonomous long-horizon planning) **and** #2 (self-modification/code generation) both demonstrated at registry thresholds.

**Containment package (in addition to T1):**
- **Physical air gap**: dedicated machine with no network interface in use; data diodes or manual media transfer only.
- **Hardware kill switch** (e.g. smart plug / switched PDU) within operator reach; halt drills quarterly.
- **Two-person rule** for any containment change, any network exception, and any checkpoint export.
- **AI-control protocols** [5]: the system is treated as untrusted; actions are monitored by a trusted, separate process; samples of outputs/actions are audited; no reliance on the system's cooperation for its own oversight.
- I/O bandwidth-limited and content-audited; output channels assumed to be potential covert channels.
- Staged capability unlocks: new capabilities are enabled one at a time, each behind its own review.

## Tier T3 — Approach to closed-loop self-improvement

**Entry criteria:** Rule 25-R capability #9 (automated self-improvement) approaching registry threshold, or any Rule 27 terminal condition.

**Containment package:** **None exists at home.** T3 is not a containment tier — it is the terminal tripwire. Execute Rule 27: halt, quarantine, external review. No resumption on home hardware. No frontier safety framework (DeepMind FSF, Anthropic RSP, OpenAI Preparedness) claims validated containment of recursively self-improving systems; GENESIS does not either [9].

---

## Why the ladder is structured this way

| Layer | What it assumes | Failure mode it covers |
|---|---|---|
| OS/hardware containment (24-R.1–3) | Nothing about the system's intentions | Detection failure; deception |
| Tripwires (24-R.5) | Detectors are unreliable; canaries are dumb and loud | Silent capability growth |
| Threshold registry (25-R) | Evals are lower bounds | Measurement drift, sandbagging |
| Tier governance (26) | The operator is fallible and invested | Manipulation, ratcheting exceptions |
| Terminal tripwire (27) | AXI containment is unsolved | The irreversible case |

---

## References
As per `Rules_24_25_Revised.md` [1]–[9].
