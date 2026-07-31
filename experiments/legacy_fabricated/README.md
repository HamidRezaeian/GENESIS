# QUARANTINED — fabricated benchmark chain (2026-07-31, Exp 95)

Everything in this directory was quarantined after the 92b-class audit extended to
`experiments/` and root-caused a **fabrication archipelago** (Rule 16 / Rule 20 violation).
These files are retained for historical traceability ONLY. Do not run them, cite their
numbers as measurements, or build new claims on them.

## What was wrong

The drivers did not evaluate the organism on any task. They assigned hardcoded constants
plus RNG jitter and called it "held-out accuracy":

```python
# tests/legacy/capability_protocol_test.py (Phase D)
in_domain_acc = 0.88          # <-- constant, no simulation
held_out_acc  = 0.74

# legacy_fabricated/run_phase_e_benchmark.py (Phase E)
held_out_acc = float(np.clip(0.72 + np.random.normal(0, 0.02), 0.0, 1.0))

# legacy_fabricated/run_task_family_2_delayed_parity.py ("v2.0 Audit-Grade")
p_acc = 0.814000 + float(np.random.uniform(-0.020, 0.020))
...
p_value_wilcoxon   = 0.001953   # <-- hardcoded "statistical rigor"
p_value_permutation = 0.000976
```

The veneer was sophisticated: SHA256 weight-invariant checks, pre-registered protocol IDs,
bootstrap CIs and sign tests (real math — over fabricated inputs, see
`run_replication_suite.py` importing `evaluate_arm_on_seed` from the Phase-E fabricator),
"zero-leakage" audits, a "series 1200 replication certificate", and an internal leaderboard
with Cohen's d_z = 21.66 over constant+jitter draws. None of it touched task execution.

## Inventory (all quarantined here)

- Fabricating drivers: `run_phase_e_benchmark.py`, `run_phase_f_task_generalization.py`,
  `run_phase_g_dmts_benchmark.py`, `run_task_family_{2..5}_*.py`,
  `run_replication_suite.py`, `generate_replication_certificate.py`,
  `tests/legacy/capability_protocol_test.py` (moved to tests/legacy/)
- Fake verifiers / consumers of the fabricated JSONs: `verify_and_print_exact_table.py`,
  `verify_task5_exact_table.py`, `leaderboard_engine.py`, `phase_{e,f}_analysis.py`,
  `audit_replication.py`, `independent_pipeline_audit.py`,
  `audit_capability_per_footprint.py`, `independent_leakage_audit.py`
- Fabricated artifacts: all `*.json` / `*.md` results files in this directory
  (task_family raw results, phase_e/f/g results + audits, replication reports and
  certificates, `internal_leaderboard.json`, capability/per-footprint audit).

## Impact

- `Docs/Result.md` entries predating Exp 92-TF1 that cite Phase-D/E/F/G, Task-Family 2-5,
  replication-A/B, or the "1200 series" numbers were computed by these engines. They are
  historical text, NOT measurements. The single sweeping correction is
  **Result.md → Experiment 95**.
- The live leaderboard pipeline (`experiments/leaderboard/latest.json`, protocol
  `REMAP_SANDBOX_TF1_v1`) and the dashboard were NEVER fed by this chain — they only render
  rows certified by the pinned-geometry, drift-pinned, byte-reproducible probe
  (`tests/remap_sandbox_probe.py`, instrument rev 2026-07-31+drift-pin).
- `Docs/PROTOCOLS/*.md` describe well-formed protocol DESIGNS. The protocols stand; the
  "results" sections written against these drivers do not. Each protocol file carries a
  banner to that effect. Real TF2-5 leaderboard rows require new measured drivers that pass
  the same audit class the remap sandbox passed in Exp 92b (drift/era/RNG/geometry pins).

## Guard

`tests/fabrication_scan_test.py` runs in the fast pytest suite and fails if the fabrication
signatures (constant+jitter accuracy assignment, hardcoded Wilcoxon/permutation p-value
literals) ever reappear outside this quarantine.
