# GENESIS Digital Universe

**Tagline:** Intelligence from Thermodynamics.

GENESIS is a research substrate for evolving biological-style **spiking neural networks
(SNNs)** inside a literal 1-D RAM universe, where **energy is execution cycles**, **space is
memory addresses**, and survival requires wiring a genome-encoded brain into an efficient
survival circuit under Darwinian selection. The long-term goal (the *Prime Directive*,
Rule 6) is genuine in-lifetime learning, reasoning and long-term memory at biological
(~20 W) efficiency — studied with falsifiable, pre-registered criteria rather than
declared victories.

> **Honesty note (Rule 16).** GENESIS is **not** a demonstrated AGI. It is a laboratory for
> testing whether learning, memory and selection can be made *load-bearing* on a physical
> compute substrate. All capability claims live in `Docs/Result.md` (including the many
> **negative** results), and the binding finish line is pre-registered in
> `Docs/Architecture/Ascent.md` (Rule 18).

## Architecture at a glance

```
src/
  neuromorphic_engine.py   # Numba-JIT SNN kernel: LIF + STDP, genome decoder, world_tick
  genesis_lab.py           # Universe orchestration: pools, reproduction, Ark, WS server
  books_of_genesis.py      # Curriculum scroll injector (graded bootstrap → ascent ramp)
  compile_fingerprint.py   # Rule-21.8 numba cache-key fingerprint of all baked env flags
  capacity_resolver.py     # Hardware-aware RAM sizing (cgroup/psutil/fallback)
  auto_capacity.py         # Hardware-aware population cap
  brain_io.py              # Self-describing, fingerprinted, monotonic Brain.npz checkpoint
  physical_cost_model.py   # Measured host cost per primitive (Rule 21.1)
  live_web_streamer.py     # Optional live-text scaffold (Wikipedia/news), background-fed
public/                    # Observation deck (canvas RAM map, brain analyzer, KPIs)
tests/                     # Executable probes/tests (see test_suite_runner.py)
  legacy/                  # Quarantined historical tests (broken, kept for provenance)
experiments/               # Benchmark drivers + raw JSON results
Docs/                      # PRD / ARD / Roadmap / Result / Ascent / Rules (binding specs)
```

- **Physics:** 1 cycle per honest primitive (measured on the host — Rule 21.1), memory is
  laid out as flat global pools (`UNIVERSE_MAX_NEURONS/SYNAPSES/DNA`), reading pays
  `CELL_STATES = 2^8 = 256` per resolved cell, death at `energy ≤ 0`.
- **Cognition instruments:** STDP variants (3/3C/TARGET), CAM associative memory,
  WRITE-gated latches (WMEM), external scratchpad registers, evolvable sensors/actuators
  (self-grown I/O), Dale E/I neuron types, remap/delay tasks — all behind compile-time,
  env-gated, cache-fingerprinted flags.
- **Controls culture:** every cognitive claim needs a matched learning-ablation control
  (Rule 18-B), a shortcut/null control (Rule 20), multi-seed replication (Rule 3).

## Install

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
# or pinned, known-good stack:
.venv/bin/pip install "numba==0.61.2" "numpy==2.1.2" websockets psutil pytest
```

## Run

```bash
# Headless smoke (JIT-compiles the kernel the first time, then ticks)
python tests/smoke_test.py

# Live observation deck at ws://localhost:8085 (open public/index.html)
python src/genesis_lab.py

# Headless lab run
GENESIS_HEADLESS=1 python src/genesis_lab.py
```

## Test

```bash
pytest -m "not slow"          # fast suite (subprocess-wrapped script tests)
pytest -m slow                # kernel-driving probes (JIT compile, minutes)
```

## The Rules

Development is governed by binding rules in `.agents/rules/` and
`Docs/Architecture/FixedRules.md` — notably: **Rule 5** (no top-down God-scripts),
**Rule 9** (no wired-in fitness), **Rule 15/21** (physics must be real hardware, no game
mechanics), **Rule 16** (documentation must reflect the true state of the code),
**Rule 18** (pre-registered falsifiable finish line), **Rule 20** (shortcut accountability).

## State of the search (2026-07)

The load-bearing programme is *learning-first* (Ascent.md §4): in-lifetime STDP was shown
net-negative (Exp 30), then repaired through neuromodulated, credit-assigning and
error/teaching-signal plasticity (Exp 31–35, 42), memory-depth limits were mapped
(Exp 43–46), and the current binding constraint is the **metabolic ceiling** — brains
complex enough to hold context cost more cycles/tick than the income quantum pays
(Exp 78–91, sessions 9–15). Escaping that ceiling without violating Rule 21 is the open
frontier — see `Docs/Roadmap.md`.
