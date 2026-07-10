# GENESIS: Experimental Results & Analysis (Current Engine)

> **Status (2026-07-10):** This document was fully rewritten to describe **only the live
> genome-encoded Spiking Neural Network engine** (`neuromorphic_engine.py` +
> `genesis_lab.py`). All earlier "experiments" describing the deleted graph-physics and
> 1D-opcode ("Tierra") engines were removed — they measured systems that no longer exist,
> and several of their headline claims (e.g. a 97.9% *supervised* symbol-grounding result,
> a recurrent 16×16 `w_hh` matrix, poison ±5000 ATP) were never part of this engine.
>
> To keep the record honest (Rule 16): results below are **engine characterisation** —
> what the physics engine measurably *does*. Emergent cognition (language, reasoning,
> long-term problem solving) remains a **goal, not a demonstrated result.**

---

## 1. Method
The engine is characterised with `tests/smoke_test.py`, a headless harness that drives
`world_tick_numba` directly (no websocket, no infinite loop) and processes births exactly
as `sim_loop` does. Universe: `RAM_SIZE = 65536`, `MAX_ORGANISMS = 600`, global cycle pool
3000, food byte `0x55`. Runs on CPU via Numba `@njit` (numba 0.61.2, numpy 1.26.4).

---

## 🧪 Experiment 1 — Baseline Population Dynamics
**Objective:** Confirm the engine compiles, runs deep-time without crashing, and produces
non-trivial ecological dynamics from the Intelligent Ancestor (Rule 5).

**Setup:** Seed 60 intelligent ancestors; run 500 world-ticks (each world-tick runs
`3000 / population` LIF sub-steps — conservation of compute).

**Results (representative run):**
- **Throughput:** 500 world-ticks in ~0.65 s → **~773 world-ticks/s**, simulating the full
  population's LIF + STDP dynamics each tick.
- **Population:** grew from 60 and **oscillated (min 61, max 382, mean ≈ 208)** with **no
  extinction** across the run — early evidence of bounded, boom-and-bust dynamics rather
  than either runaway explosion or collapse.
- **Footprint:** ~6,800 neurons and ~1,960 synapses allocated from the global heap at
  steady state.

**Analysis:** The global cycle pool couples population to a fixed compute budget: as numbers
rise, per-capita LIF steps fall and average energy declines, throttling reproduction. This
is the intended thermodynamic negative feedback. *Caveat:* deep-time robustness across many
extinction/Ark cycles (millions of ticks) has not yet been measured on this engine.

---

## 🧪 Experiment 2 — Mechanism Verification
Each physical mechanism was verified to be live and correct (not dead code):

1. **Genome → SNN decode:** `count_genes`/`decode_genome` build a sparse network from
   `RECEPTOR_MARKER`/`NEURON_MARKER`/`GENE_MARKER` records; the fixed 15-input/14-output I/O
   layer plus variable hidden neurons are allocated from the global heap per organism.
2. **Evolvable receptor chemistry (Rule 17):** STDP rates, time-constants, thresholds and —
   as of this revision — **resting/reset potentials (`V_REST`/`V_RESET`)** are all DNA-encoded
   per receptor. Previously `V_REST`/`V_RESET` were dead genes hardcoded to 0; they are now
   read from the genome, so evolution can tune neuron excitability.
3. **Graded STDP:** raw receptor amplitudes (0–255) are scaled by `STDP_SCALE = 8`, so a
   single spike moves a weight by at most ~12% of its range instead of slamming it to the
   ±127 rail (fixes the previous bang-bang saturation).
4. **Computational viscosity (Rule 13):** stall probability is now driven by the organism's
   **synaptic density** (synapses/neuron), capped at 0.5 — penalising dense brains and
   rewarding sparse topologies, rather than the previous purely spatial crowding measure.
5. **Cosmic radiation:** bit-flips now target **allocated living genomes** (germline
   mutation) instead of the mostly-empty multi-MB arena, where ~99% of flips previously
   landed in vacuum.
6. **Lamarckian consolidation (Rule 6):** at reproduction, each synapse's inherited DNA
   weight is blended 50/50 with the weight the parent **learned via STDP**, so plasticity is
   partially heritable. Verified to run on every birth; the engine remained stable and
   showed richer boom-bust dynamics (pop 60 → peak ~505 → ~289 over 200 ticks) with it active.
7. **Elite Ark + fossil pool (Rules 5/14):** the longest-lived genome is checkpointed
   (`Brain/Brain.npz`); a pool of up to 12 distinct elite **fossils** is retained, and on
   total extinction the universe reseeds by **crossover (horizontal gene transfer) between
   two fossils** plus mutation — a more bottom-up recovery than cloning a single genome.
   Verified: fossils populate, crossover preserves the protected physics header, and reseed
   spawns a fresh population.

---

## 3. Open Questions (Not Yet Demonstrated)
Honest gaps between the engine's *capacity* and demonstrated *emergence*:
- **Learning efficacy:** STDP + Lamarckian memory are implemented, but we have not yet
  measured that they *improve survival on a task* over a non-learning control.
- **Communication/logic:** vocal cords, neighbour hearing and the Oracle channel exist, but
  no unsupervised language or logic-gate emergence has been measured on this engine.
- **Efficiency selection (Rule 7):** an efficiency metric (age ÷ neural footprint) is now
  surfaced to the dashboard, but selection *for* efficiency at equal capability is unproven.
- **Autotelic end-state (Rule 9):** food/oracle/curriculum are still human-supplied
  scaffolds; agent-generated survival problems are future work.

## 4. Conclusion
The current neuromorphic engine is a working, stable substrate: genome-encoded SNNs learn
in-lifetime, reproduce with heritable topology **and** partially-heritable learned weights,
and are held in bounded population dynamics by a thermodynamic compute budget. It provides
the physical preconditions for emergent cognition; demonstrating that cognition is the open
research programme in `Roadmap.md`.
