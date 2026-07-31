# Energy Accounting Basis (Rule 21.1) — What Is Measured, What Is Estimated

> Status: binding nomenclature, added 2026-07-31 (Session 15) implementing deep-review
> P1‑6 / P1‑7 / P1‑8. Every energy number quoted anywhere in this project (papers, logs,
> telemetry, Result.md) must state its basis class from the table below.

## 1. The four basis classes

| Class | What it means | Members today |
|---|---|---|
| **MEASURED** | Timed on the actual host in a tight `@njit` loop (`physical_cost_model.engine_primitive_cycles`), native cost including the loop bookkeeping the engine itself pays. | All engine-side `CYCLES_PER_*` metabolic charges (synapse_read, move, eat, eat_idle, byte_copy, neuron_update, stdp_update, write, cam_*, scratch_*, sense/act, etc.) — wired at engine import. |
| **FORCED-BY-DESIGN** | Algebraically fixed by the substrate definition, not tuned. | `CELL_STATES = 2^8 = 256` (uint8 cells), `BASE_ENERGY = 4096 = 16 × 256` (BMR = 16 ticks of one base read), food energy `128 = FOOD_DENSITY` (0x55 = 25% concentration). |
| **NOMINAL-HOST** | Reporting-layer constants that depend on the machine; cycle/joule reports should be recomputed on the reference host. | clock `3.0 GHz` (seconds→cycles for the *human-facing report* layer only), `joules_per_flop ≈ 10 pJ` (order-of-magnitude; **RAPL gap** — a power-monitor measurement is outstanding). |
| **POLICY (env-gated, justified-or-flagged)** | Evolution-facing knobs exposed as `GENESIS_*` env vars, recorded in the compile fingerprint so results are reproducible. | `AUTO_REPRO_THRESH = 200000.0` cycles — currently **flagged as underived** (deep review P1‑8); classify as Rule-17 "free parameter requiring an experiment", not a physical constant. |

## 2. Charging vs reporting: two layers, don't conflate them

- **Charging (in-simulation).** The kernel subtracts MEASURED native cycles per primitive
  (`CYCLES_PER_*` in `neuromorphic_engine.py`, from `engine_primitive_cycles()`). This is the
  physically honest cost layer: the substrate pays what the host pays to run it (Rule 21.1).
- **Reporting (out-of-simulation).** `PhysicalCostModel.costs[]` and `summary_table()` present
  human-facing units: seconds (measured), cycles = seconds × NOMINAL 3.0 GHz, joules = flops ×
  NOMINAL 10 pJ. These carry **NOMINAL-HOST** uncertainty and must never be quoted as
  "measured energy". Until a RAPL/power measurement lands, report joules as order-of-magnitude
  only (see `rapl_energy_monitor.py`).

## 3. Why `CELL_STATES = 256` is not an "exchange rate" (deep review P1‑7)

The income quantum is not a tunable payout: a cell **is** a uint8, so correctly resolving a
cell yields **exactly one byte of information = log2(256) = 8 bits**; pricing that at
256 cycles still charges ~1 cycle per 0.031 bits *below* the measured cost of the read
primitives that produced it — i.e. income < cost by construction, which is precisely the
recorded income-barrier result (Exp 5: net-negative base reading). There is no free
multiplier here. Two consequences:

1. **An honest sensitivity sweep over the quantum is only meaningful jointly with the
   substrate's byte-width** (cell encode width, ring addressing, food density `0x55`, and
   `CYCLES_PER_*` all move together). "CELL_STATES=128 vs 512" under uint8 storage is not a
   comparison of exchange rates but of *different substrates*.
2. The pre-registered sensitivity question that IS well-posed on this substrate: **how does
   colony-level outcome vary with the ratio** `income quantum / measured read cost`, swept via
   `CYCLES_PER_SYNAPSE_READ` and `CYCLES_PER_MOVE` scale factors at fixed 256-quantum?
   The Reward Auditor protocol (`Docs/PROTOCOLS/`, Exp 42 lineage) defines the A/B arms;
   results must be filed in `Docs/Result.md` with basis class MEASURED.

## 4. `AUTO_REPRO_THRESH` (P1‑8)

- Class: **POLICY**, env-gated (`GENESIS_AUTO_REPRO_THRESH`), dunder-default 200000.0,
  recorded in the compile fingerprint (both engine and lab read it).
- Current status: **underived**. It gates `AUTO_REPRO` (population-spawning when energy is
  comfortable). A derivation must come from an experiment (e.g. threshold × ATP-scale sweep
  with extinction/birth-provenance telemetry), its result filed in Result.md.
- Until then, treat AUTO_REPRO=1 runs as **life-support-assisted** for capability claims
  (they are already labelled via the `births.auto_repro` provenance counter in telemetry
  schema v2).

## 5. Exposure in telemetry (schema v2, 2026-07-31)

The WebSocket `state` payload carries `"energy_basis"` — a one-line string naming the basis
classes above, so any captured manifest states what its numbers mean. The dashboard shows
cycles (measured native) unchanged; it does not display joules/seconds reporting units.
