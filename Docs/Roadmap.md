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
- ✅ Living-genome cosmic radiation, graded STDP, synaptic-density viscosity, Lamarckian
     weight consolidation, fossil-pool crossover (HGT) reseed (2026-07-10).
- ✅ **Honest raw-cycle metabolism** — neuron update = 1 cycle, activity-gated STDP-update
     cost; removes the arbitrary `0.1` idle discount so Rule 7 efficiency is selected
     *emergently* (Result.md Exp 3); `sense()` hoisted out of the sub-step loop → ~3× faster
     simulator (2026-07-10).
- ✅ **Ark fossil-capture freeze fixed** (2026-07-10): `max_ark_age` was a persistent all-time
     record set once before the loop, so after the first golden era no organism could beat it
     and the fossil pool froze onto one lineage; now reset per era so each era contributes its
     champion — the root cause of the Exp 4 clockwork-collapse loop.
- ✅ **Ark-reseed crash fixed** (2026-07-11): `mutate_dna` duplication branch called
     `random.randint(8, l-1)` with no `l > 8` guard (its sibling insert/delete branches have it),
     so a genome of length exactly 8 — the floor the deletion branch shrinks to — raised
     `ValueError: empty range in randrange(8, 8)` the moment an Ark reseed recombined a short
     fossil (observed live at LIF Time ≈ 3.79M). Added the `l > 8` guard; proven by
     `tests/mutate_crash_test.py` (20,000 calls on lengths 8–12, zero crashes).

## Part C — Forward Roadmap (from the 2026-07-10 critical review)

### 🔴 P0 — Wire the book-reading economy into the LIVE sim (2026-07-11)
**Wiring DONE + verified; sustain BLOCKED on navigation (2026-07-11 pass 2).** `genesis_lab.py`
now has a full `GENESIS_ECONOMY=books` path: it pre-stocks + restocks a contiguous-passage library
(`inject_passage`, `BOOK_TARGET_BYTES`), pays reading (`READ_SCALE=64`) with food at subsistence
(`EAT_GAIN=16`), and seeds a modest 20k buffer — all gated so the default `food` path is byte-for-byte
unchanged (zero regression). Verified headless with `tests/live_book_economy_test.py` (Ark OFF, no
0x55 food). RESULT: reading works and income scales with library density (correct_reads 16→275 across
3k→24k standing bytes) — but **no config self-sustains**; every cohort dies at ~42–56 ticks on the
seed buffer. ROOT CAUSE (proven, not guessed): `seed_universe` spawns organisms only on empty (`0x00`)
cells, i.e. **born in the gaps *between* passages, off the text**; with no text-seeking sense they
rarely reach a page, so read rate is ~20× lower than the 90%-flood control (645 reads at 61% coverage
vs ~18,000 at flood). A uniform flood sustains but is the video-game shortcut. **Therefore the real
next lever is a TEXT-SEEKING SENSE** (mirror the food-scan: printable-symbol density ahead/behind →
inputs; passages CLUSTER so — unlike uniform food — they yield a real ±16 gradient to climb) so a
sparse, navigable library can feed minds. Until then default stays `food`. Files: `inject_passage`
(books_of_genesis), book params + injection in `genesis_lab.py`, `tests/live_book_economy_test.py`.

**▶ UPDATE (2026-07-11 pass 3 — M1, largely addressed; see Result Exp 6).** The live books path was
first found *dead-on-arrival* — a `dynamic_lif_steps` use-before-assignment crashed `sim_loop` on
tick 1 in books mode (fixed). Then the predicted text-seeking lever was built: (1) the seek-scan now
targets **printable symbols** in books mode (`SEEK_TEXT`), reusing the ancestor's food-seek wiring;
(2) `seed_universe` **spawns readers in the library** (empty cells with text in ±`FOOD_SCAN_RADIUS`).
Encounter `0.00→0.38`, reads `0.3→55/tick`. The remaining burn wall was closed by making compute
**architecture-derived** — per-organism LIF steps = the organism's synapse-graph depth (retires the
`GLOBAL_CYCLE_POOL/alive` pool + its death-spiral). Efficiency now selects emergently (mean depth
8→2). Cohorts live ~700–1000 world-ticks on reading income. **Still open (P0 residual):** cohorts
*spatially leak* — offspring + restocked passages drift from readers — shrinking to a ~23-org pod.
Next: spatial co-location (restock near population / offspring born in library) + reclaimed-compute
read value. Diagnostic: `tests/_m1_econ_probe.py`.


The 2026-07-11 breakthrough — **life by reading** (organisms sustain purely on energy from
solving book-symbols; 95%+ echo accuracy, food off) — lives **only in the test harness**
(`tests/book_read_test.py`). The live `genesis_lab.py` still runs the **old 0x55-food economy**
and therefore still exhibits the Exp 4 clockwork collapse: the 2026-07-11 run pinned Pop at
300/600 with a MASS EXTINCTION every ~6,000 ticks continuously past 1.8M cycles — weeds that
don't even self-sustain, exactly the loop we diagnosed. **The mind-making economy is proven but
unplugged.** To wire it in: (a) seed the reading eye + echo reflex into the *live* ancestor
(already in `create_intelligent_ancestor`; confirm it is active in the live path); (b) make the
live world inject the Books curriculum as the primary energy source with `READ_SCALE` high and
`EAT_GAIN` at bare subsistence (or off); (c) the density sweep showed sustenance needs ~60% text
with *no seeking* — so either flood text or first give organisms a **text-seeking sense**
(reuse the food-seek pattern) so sparse books are navigable; (d) surface reads/predictions on the
:8085 dashboard. Fork to decide with the user: seed a working reader (fast, Rule 5) vs. force
reading to **evolve** from scratch under the read-economy (the real Rule 9 test, slow).

### 🔴 P1 — Physics correctness — ✅ DONE (2026-07-10)
- ✅ Cosmic radiation targets *living* genomes (germline), not the empty arena.
- ✅ Graded STDP: receptor amplitudes scaled by `STDP_SCALE` so a spike can't slam the rail.
- ✅ Honest per-cycle metabolism (neuron update 1 cyc + activity-gated STDP cost) replacing
     the `0.1` idle discount — the core Rule 7 efficiency-selection fix (A/B in Result.md Exp 3).

### 🟠 P2 — Toward the Prime Directive (Rule 6)
- ✅ Long-term memory across reproduction: Lamarckian 50/50 blend of learned STDP weights
     into offspring DNA at birth.
- ✅ Efficiency is now *selected* emergently by honest cycle costs; `elite_iq = age/footprint`
     is surfaced to the dashboard **observation-only** (wiring it into selection is forbidden
     by Rule 5/9).
- [ ] **Capability-normalised efficiency:** show that at *equal capability* the lower CPU/RAM
      lineage wins — requires first defining a capability/task measure.
- [ ] Explicit recurrent/working-memory pathway beyond STDP + Lamarckian consolidation.
- [ ] **Population self-sustainability (root cause of the Exp 4 collapse loop):** organisms
      coast on the `initial_energy` seed buffer instead of closing a food→energy→reproduction
      loop, so each identical reseeded cohort drains its buffer over a near-fixed ~8,640-tick
      period and dies together. Shrink the seed buffer and rebalance metabolism/food so a
      population survives on renewable income with no Ark resurrection.
- [ ] **Reseed diversity:** cohorts are >95% identical (≤12 near-clonal fossils, shared physics
      header); restore standing variation so eras desynchronise and selection has material.
- [ ] **Observation-only capability probes (Rule 9 ↔ 6):** measure learning/reasoning progress
      toward the Prime Directive without wiring rewards into selection (as `elite_iq` already
      is) — sandbox-test the elite brain on held-out tasks that never affect survival.

### 🟡 P3 — Toward the Autotelic Imperative (Rules 9/10)
- ✅ Dead-DNA fossil pool + crossover (HGT) reseed, so recovery is more bottom-up than
     cloning a single Ark genome.
- ✅ Viscosity keys on synaptic density (s/n), not spatial crowding — real Rule 11/13
     sparsity pressure.
- [ ] Reduce reliance on human-injected food/oracle/curriculum; let survival problems arise
      from agent–agent competition (predation, trade, defence).
- [ ] Real-time **somatic** entropy: expose *running* phenotypes to radiation, not just their
      offspring (a phenotype is still decoded once at spawn).
- [ ] **Break instantaneous total wipes (Rule 10):** extinction is detected only at population
      0 and reseeds the whole world at once — the exact anti-pattern the Tectonic-Gradient
      Principle forbids (it prevents learning). Add spatial refugia / partial die-off so hazards
      become gradients organisms can evolve against.

### 🟢 P4 — Rule 17 constant sweep & hygiene
- ✅ Removed the arbitrary `0.1` idle-metabolism discount (now honest 1 cycle/neuron).
- [ ] The energy economy is still footprint-blind and hand-tuned: `SEED_ENERGY = 5000` food /
      `20000` books (was `initial_energy = 250000`), `CYCLES_PER_EAT_GAIN = 15000` food / `16`
      books (was `1024`; env `GENESIS_EAT_GAIN`), `ATP_MAX = 1e6`, `GLOBAL_CYCLE_POOL = 3000`,
      threshold offset `+128`, `SYN_DENSITY_SCALE`/`STDP_SCALE = 8`. Bring these closer to real
      footprint scale (or DNA-encode) so efficiency bites without the deep-time buffer delay.
- [ ] **Absolute-footprint** pressure: let contention/viscosity also rise with
      `(n+s)/UNIVERSE_MAX`, so large *sparse* brains are not effectively free (audit finding).
- [ ] Remove the stale `tests/sim_test.py` / `tests/verify_baseline.py` (they import the
      deleted graph engine); `tests/smoke_test.py` is the working replacement.
- [ ] **Brain-size bloat ratchet:** growth-biased `mutate_dna` + Ark preserving longest-lived
      (bloated) genomes ratchets brain size up each era (throughput ~12.5k→~4.5k ticks/s in
      Exp 4), defeating Rule 7 efficiency selection because longevity tracks the seed buffer,
      not efficiency; couple the fix to the seed-buffer shrink (P2).
- ▶ **Milestone (2026-07-11):** `CYCLES_PER_EAT_GAIN` is now env-tunable (`GENESIS_EAT_GAIN`);
      the sweep `tests/eat_gain_sweep.py` produced the **first self-sustaining foraging population
      (Ark off, eat-gain ≥ 4096 on a food carpet)** — the eat-gain/burn wall is crossable
      (Result.md Exp 4). Still open: choose a *principled* operating point (modest meal-value +
      moderate density, so foraging skill closes the loop, not a fat handout) paired with a
      food-seeking sense (Rules 5/10); then re-derive the meal-value from real reclaimed compute
      (Rule 17) rather than a magic constant.
