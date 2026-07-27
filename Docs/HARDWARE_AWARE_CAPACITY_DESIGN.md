# Hardware-Aware Population Cap — Design (Session 14, 2026-07-26)

> Status: implemented + proven. Module: `src/auto_capacity.py`. Probe:
> `tests/auto_capacity_probe.py` (7/7 PASS). Engine integration:
> `src/neuromorphic_engine.py` (the `MAX_ORGANISMS` definition).

---

## 1. The requirement

The population ceiling should not be a fixed magic number. It should be **sized to
the machine it runs on, at run time**: a stronger machine (more RAM) automatically
gets a larger population; a smaller machine gets a smaller one. No manual tuning.

## 2. Why a cap still exists (and must)

A truly "unlimited" population is physically impossible. Every *potential* organism
reserves a fixed slice of the neuron / synapse / genome pools **up front** — the
pools are allocated at import as `UNIVERSE_MAX_* = MAX_ORGANISMS × …` in
`genesis_lab`, whether or not the slots are ever filled. So memory grows **linearly
with the cap**, not with the live population. The cap therefore has to fit the
available hardware, leaving headroom for the OS / Python / Numba JIT.

What this design changes is *where the cap comes from*: not a hand-picked constant,
but the measured memory of the host.

## 3. The memory model (measured, not guessed)

Capacity-reserved per potential organism, measured from the live `genesis_lab`
pools (and cross-checked by formula — they match exactly):

| pool            | per-element | elements / organism          | subtotal      |
|-----------------|-------------|------------------------------|---------------|
| neuron pool     | 37.0 B      | `N_IO+800` = 839 neurons     | 31,043 B      |
| synapse pool    | 21.0 B      | 839 × 4 = 3,356 synapses     | 70,476 B      |
| genome pool     | 2.0 B       | 839 × 4 × 2.5 = 8,390 bytes  | 16,780 B      |
| organism-index  | —           | 35 arrays sized MAX_ORGANISMS| 3,782 B       |
| **total**       |             |                              | **122,081 B ≈ 119.2 KB** |

A 20% safety margin (miscellaneous arrays + allocator overhead) gives the design
constant `BYTES_PER_ORGANISM ≈ 146,497 B ≈ 143 KB`.

## 4. The design (`src/auto_capacity.py`)

```
budget = available_memory × 0.60  −  1 GB reserve
cap    = clamp( budget // BYTES_PER_ORGANISM,  100,  1_000_000 )
```

* `detect_available_bytes()` — reads available RAM via `psutil` (fallback
  `/proc/meminfo`), and honours a cgroup memory limit (containerised hosts) by
  taking the min of the two.
* `DEFAULT_MEMORY_FRACTION = 0.60` — share of available RAM given to the sim.
* `DEFAULT_RESERVE_BYTES = 1 GB` — always kept back for OS / Python / Numba / JIT.
* `MIN_ORGANISMS = 100` — even a tiny machine runs a viable population.
* `MAX_ORGANISMS_CAP = 1_000_000` — beyond this the `O(MAX_ORGANISMS)` free-slot
  scan in `genesis_lab` (`for j in range(MAX_ORGANISMS)`) becomes a bottleneck.

### Precedence (`resolve_max_organisms`)
1. `GENESIS_MAX_ORGANISMS` env var, if set → **explicit user override wins**.
2. otherwise → `auto_population_cap()` (sized to the hardware).
3. if memory cannot be detected → fixed fallback `600` (the old default).

## 5. Engine integration

`neuromorphic_engine.py` (the single `MAX_ORGANISMS` definition):

```python
try:
    from auto_capacity import resolve_max_organisms as _resolve_max_orgs
    MAX_ORGANISMS = _resolve_max_orgs(fallback=600)
except Exception:
    MAX_ORGANISMS = int(os.environ.get("GENESIS_MAX_ORGANISMS", "600"))
```

Everything downstream derives from this one value automatically: `BIRTH_BUF_SZ`
(`//4`), `UNIVERSE_MAX_NEURONS/SYNAPSES/DNA`, and every pool in `genesis_lab`. The
`try/except` guarantees the engine still imports if `auto_capacity` is unavailable
(falls back to the old behaviour).

## 6. Proof (by execution)

`tests/auto_capacity_probe.py` — **7/7 PASS**:

* **AUTO** — no env var → cap equals `(avail×0.60 − 1GB)//143KB`, clamped
  (this 8 GB host → ≈23,600 organisms, ≈2.8 GB of pools reserved).
* **OVERRIDE** — `GENESIS_MAX_ORGANISMS=777` → 777.
* **UNSET** — `resolve_max_organisms()` falls back to the auto value.
* **SCALING** — simulated 8 GB → 25,435; 128 GB → 516,913 (proportional).
* **CLAMPS** — 0.1 GB → 100 (min); 1 PB → 1,000,000 (max); undetectable → None/600.

End-to-end: with the cap set to 2000, `genesis_lab` allocates a neuron pool of
exactly `2000×839 = 1,678,000` and a synapse pool of `6,712,000` — the pools track
the cap. The two pre-existing probes (`dynamic_compact_ram_probe`, `oscillation_
maxrun_probe`) pin `GENESIS_MAX_ORGANISMS=600` via `setdefault` so they stay fast
and machine-independent, and still pass (9/9 and signature-reproduced).

Run: `cd <repo> && python3 tests/auto_capacity_probe.py` (exit 0 iff all pass).

## 7. Rule 21 status

* `BYTES_PER_ORGANISM` is **hardware-derived** (class H): computed from the measured
  per-element pool sizes, not picked. The derivation is documented in §3 and in the
  module docstring.
* `_N_IO = 39` is mirrored from the engine (documented; kept in sync).
* The budget policy constants (0.60 fraction, 1 GB reserve, 100/1M clamps) are
  documented engineering policy, not game mechanics; each has a stated rationale.

## 8. Relationship to the Dynamic Compact RAM

The compact-RAM law is `RAM_SIZE = book_size + organism_count`. This cap bounds the
*ceiling* of `organism_count` (and therefore the maximum compact-universe size) to
what the hardware can back. The live `organism_count` still fluctuates with births
and deaths inside that ceiling, and the compact RAM still resizes to track it.

## 9. Files changed / added

* `src/auto_capacity.py` — **new**: memory detection + cap computation + resolver.
* `src/neuromorphic_engine.py` — `MAX_ORGANISMS` now resolved via `auto_capacity`.
* `tests/auto_capacity_probe.py` — **new**: 7-check execution proof.
* `tests/dynamic_compact_ram_probe.py`, `tests/oscillation_maxrun_probe.py` — pin
  `GENESIS_MAX_ORGANISMS=600` (setdefault) for speed/portability.
