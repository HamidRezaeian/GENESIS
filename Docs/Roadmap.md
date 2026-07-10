# GENESIS Roadmap

> **Status (2026-07-10):** The live system is the genome-encoded Spiking Neural Network
> engine (`neuromorphic_engine.py` + `genesis_lab.py`). The long phase history below has
> been condensed into an honest account of how the *architecture* evolved — several early
> engines (graph physics, the 1D opcode "Tierra" soup, the 2D grid) have been **deleted**
> and survive only as narrative in `Result.md` / `Article_Draft.md`. The forward roadmap is
> derived from the 2026-07-10 critical review.

---

## Part A — Architectural History (condensed, honest)

The project passed through four distinct substrates. Each was genuinely built and studied,
then superseded; the source files for the first three no longer exist in the repo.

1. **Graph Physics (deleted `genesis_engine.py` / `DynamicBrain`).** Nodes predicting
   neighbours' states to earn energy; demonstrated Darwinian selection, Red-Queen
   coevolution, catastrophe/overfitting tests and a supervised "language" experiment.
   *Superseded because* it was an abstract graph, not hardware, and the language result was
   supervised.
2. **1D Opcode Soup (deleted `turing_engine.py`, Tierra/Avida-style).** Self-replicating
   byte programs with opcodes (`OP_SPLIT`, `OP_ABSORB`, `CATALYZE`, `OP_SENSE_ZONE`…),
   cosmic radiation, thermodynamic zones, computational viscosity and a multiverse GA.
   Produced real emergent phenomena (extinction waves, junk-DNA shields, "vacuum
   parasites"). *Superseded because* it rewarded replication/copying, not cognition, and
   the multiverse GA was a top-down "God script" (Rule 5 violation).
3. **2D Grid SNN (deleted).** A 64×64 toroidal world with LIF neurons + STDP and an
   age-based Elite Ark. *Superseded because* the 2D grid was a "video-game" abstraction
   (Rule 15 violation).
4. **1D RAM Neuromorphic SNN (current).** The 2D grid was replaced by a literal 65536-byte
   RAM ring; organisms are genome-encoded sparse SNNs on a shared global heap, with
   DNA-encoded receptor proteins (evolvable STDP/thresholds), an Oracle uplink and a
   curriculum injector. This is the engine documented in `ARD.md`.

## Part B — Current State (Completed)
- ✅ 1D RAM substrate (65536 bytes), pointer-based movement, food = `0x55`.
- ✅ Sparse genome→SNN decoder (receptor / neuron / synapse markers) on a global heap.
- ✅ LIF + spike-triggered STDP; DNA-encoded receptor chemistry (now incl. V_REST/V_RESET).
- ✅ Thermodynamic economy (cycles), computational viscosity, global cycle pool.
- ✅ Elite Ark reseed on extinction (Rule 14) + `Brain.npz` checkpoint.
- ✅ WebSocket dashboard (:8085): RAM canvas, Brain Analyzer, Oracle terminal, curriculum.
- ✅ Crowding sensor + protected receptor header + live "screaming" telemetry (2026-07-10).

## Part C — Forward Roadmap (from the 2026-07-10 critical review)

### 🔴 P1 — Physics correctness
- [ ] **Fix cosmic radiation** so it targets *allocated* genomes (currently ~99% of
      bit-flips land in unused arena; phenotype is decoded once at spawn) — make entropy a
      real-time pressure, not just inheritance noise.
- [ ] **Graded STDP:** scale `A_PLUS/A_MINUS` (raw 0–255) into the actual weight range so a
      single spike can't slam a weight to the ±127 rail (fixes bimodal saturation).

### 🟠 P2 — Toward the Prime Directive (Rule 6)
- [ ] **Long-term memory that survives reproduction** — e.g. heritable consolidation of
      learned weights, or an explicit recurrent/working-memory pathway (no `w_hh` matrix
      exists today despite older docs).
- [ ] **Per-lineage efficiency metric** (Rule 7): CPU cycles + RAM footprint at equal
      capability, surfaced as the dashboard "IQ/efficiency" tile (currently unimplemented).

### 🟡 P3 — Toward the Autotelic Imperative (Rules 9/10)
- [ ] Reduce reliance on human-injected food/oracle/curriculum; let survival problems arise
      from agent–agent competition (predation, trade, defence).
- [ ] Re-examine the Elite-Ark reseed vs Rule 5 (top-down resurrection) — add dead-DNA
      fossils / horizontal gene transfer so recovery is bottom-up.
- [ ] Make viscosity reward genuine **parallelism/code-sparsity**, not just spatial
      crowding, so Rule 11/13 pressure is real rather than cosmetic.

### 🟢 P4 — Rule 17 constant sweep & hygiene
- [ ] Move remaining arbitrary constants (`CYCLES_PER_EAT_GAIN`, `ATP_MAX`, threshold
      offset `+128`, idle metabolism, `GLOBAL_CYCLE_POOL`, `initial_energy`) to
      hardware-derived values or DNA where defensible.
- [ ] Replace the stale `tests/` scripts (they import the deleted graph engine) with tests
      that drive the real SNN engine (see `tests/smoke_test.py`).
