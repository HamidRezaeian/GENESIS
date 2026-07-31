# tests/legacy — Quarantined Historical Tests (2026-07-31 audit)

These files are **kept for historical provenance only** and are excluded from the
working test path. Each is broken against the current engine and must not be run:

| File | Why it is broken |
|---|---|
| `sim_test.py` | Standalone fossil of the deleted 1D opcode "Tierra" engine (`turing_engine.py` era). The substrate it simulates no longer exists. |
| `verify_baseline.py` | Imports the deleted `genesis_engine` graph module → `ImportError`. |
| `tierra_trap_test.py` | Uses retired env constants `GENESIS_EAT_GAIN` / `GENESIS_READ_SCALE` (deleted by the "remove all game constants" change — Result.md Exp 7). |
| `eat_gain_sweep.py` | Asserts `ne.CYCLES_PER_EAT_GAIN`, a constant that no longer exists (superseded by `CELL_STATES = 256`). |
| `book_read_test.py` | Same retired `GENESIS_READ_SCALE`/`GENESIS_EAT_GAIN` env knobs; the harness it describes lives in git history. |

The working smoke entry points today are `tests/smoke_test.py`,
`tests/self_sustain_test.py`, and the probes listed in `tests/test_suite_runner.py`.
See `Docs/Roadmap.md` ("P4 hygiene" items) for the retirement decision.
