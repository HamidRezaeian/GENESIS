# Internal Leaderboard Framework Specification (v1.0)
**Framework Identifier**: `GENESIS_LEADERBOARD_FRAMEWORK_v1`
**Repository Scope**: GENESIS Autonomous Cortical Benchmark Engine

---

## 1. Architectural Philosophy

The Internal Leaderboard is an **immutable, version-controlled, artifact-linked tracking engine**.
It explicitly separates performance visualization from formal scientific certification.

### Immutable Invariants
- **No Entry Without Artifacts**: Every entry MUST link to a SHA256-verified `raw_results.json`, `protocol.md`, `analysis.py`, and `leakage_audit.json`.
- **No Accuracy-Only Rankings**: Rankings are partitioned into 5 independent views to prevent rank inflation.

---

## 2. Five Independent Ranking Views

1. **View A — Raw Capability**: Ordered by held-out accuracy / primary task success rate.
2. **View B — Learning Advantage**: Ordered by paired delta $\Delta = \text{FewShot} - \text{Ablation}$ and Cohen's $d_z$.
3. **View C — Hardware Efficiency**: Ordered by Capability per Memory MB ($E_{\text{memory}}$) and Capability per Traffic MB ($E_{\text{traffic}}$).
4. **View D — Reproducibility**: Ordered by number of verified independent seed replications and exact permutation test $p$-values.
5. **View E — Scientific Scope**: Partitioned by task complexity level (Single-Task, Cross-Family, Multi-Family, Causal).

---

## 3. Status Lifecycle

- `UNVERIFIED`: Entry registered, audit pending.
- `PIPELINE_VALIDATED`: Artifacts present, mathematical verification passed.
- `AUDITED`: Leakage audit, process isolation, and base weight SHA256 verified.
- `REPLICATED_NEW_SEEDS`: Tested on 10 independent seeds (Series 1200).
- `CERTIFIED`: Formally issued a Level 1, 2, or 3 Replication Certificate.
