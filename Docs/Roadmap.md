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
- ✅ **Population self-sustainability — SOLVED on the live loop (Exp 11, 2026-07-12).** The live
      `sim_loop` was net-negative at every density (colony rode the refuge floor `pop=12`). Root
      cause was **world structure, not the exchange rate**: the library was scattered short passages
      ("confetti"), so a saccading reader (Exp 9) walked off the end of a fragment into vacuum and
      starved crossing the gap to the next (`enc_frac`~0.5, half the colony always in transit). Fix
      = lay the same bytes as **one contiguous scroll** (`inject_contiguous_library`): `enc_frac`
      0.5→0.98, reading income beats metabolism, and the live loop now sustains `pop=596–600/600`
      with `refuge=0`, `ext=0` at **both** 9 % and 37 % density. Supporting fixes: event-driven
      sensing (remove the flat 32-cycle/tick scan double-charge, Rule 11) and on-text seeding (place
      organisms by org-grid occupancy, not `g_ram==0x00` — a solid scroll has no interior vacuum, so
      the old rule stranded the cohort off-text: the live-only bug that made the *probe* thrive while
      the *live* loop hit floor-12). Growth rides native `OUT_REPRODUCE`; carrying capacity is the
      600 array cap (non-destructive reading = infinite food). Residual: does the colony *ascend*
      (capability over deep time), a food-scarcity ceiling below 600 if wanted, and a non-lethal peer
      coupling (P3).
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
- 🟡 **First agent–agent survival problem — zero-sum peer prediction (Exp 10B, 2026-07-12).**
     `GENESIS_PEER=1`: an organism that vocalises the byte a neighbour is emitting drains that
     neighbour's energy by the matched bits (`energy[predictor] += g; energy[speaker] −= g`,
     clamped to holdings). Zero-sum ⇒ **unfarmable** (no free energy); the only way to earn is to
     out-model a neighbour and the only defence is to be unpredictable — a Red-Queen push toward
     informative signalling (proto-language), no human curriculum, no imposed fitness. Verified
     firing crash-free on the live loop (`peer=50–332`/interval). **Emergence unproven** — and Exp 11
     found a new blocker: with the economy now net-positive (contiguous library), `GENESIS_PEER=1`
     **collapses the thriving 600-colony back to floor-12** — zero-sum predation drains victims faster
     than the arms race evolves a defence, extinguishing the substrate before defensive signalling can
     emerge. Peer is default-OFF so the shipped economy is unaffected, but the autotelic layer now
     needs a **non-lethal predation coupling** (drain a fraction, or a much larger sustained pop)
     before it can run. Still human-supplied otherwise: food/oracle/books.
- [ ] Real-time **somatic** entropy: expose *running* phenotypes to radiation, not just their
      offspring (a phenotype is still decoded once at spawn).
- ✅ **Instantaneous total wipes broken — refugium gradient (Exp 10A, 2026-07-12).** Extinction was
     detected only at population 0, reseeding the whole world as 300 synchronised clones (the exact
     Tectonic-Gradient violation). `genesis_lab.seed_refuge` now tops the living population back up
     to a derived floor (`len(fossil_pool)` — one living rep per banked lineage, ≤ 12) from the
     hall-of-fame *before* it hits 0, so eras overlap and death is a continuous gradient. Measured
     live: total wipes **6 → 0** over a longer span (`refuge_events=51`, `ext=0`), pool ratchet
     intact. It softens the cliff, it does **not** clamp population (a net-positive economy grows
     past the floor and the refuge falls silent) — so the residual is the net-negative live economy
     (P2), not the wipe dynamic.

### 🟢 P4 — Rule 17 constant sweep & hygiene
- ✅ Removed the arbitrary `0.1` idle-metabolism discount (now honest 1 cycle/neuron).
- ✅ **Economy game constants REMOVED (2026-07-11 "remove all game constants"; Result Exp 7).**
      `CYCLES_PER_EAT_GAIN` (15,000/16), `READ_REWARD_SCALE` (64), the loose `×8` per-bit read payout,
      and `SEED_ENERGY` (5,000/20,000) are gone — all replaced by ONE derived exchange rate
      `CELL_STATES = 2**BITS_PER_BYTE = 256` (an 8-bit cell's microstate capacity). Eating reclaims a
      whole cell (256); solving pays `(net_bits/8)×256`; the abiogenesis seed is the founder's own
      footprint × `CELL_STATES`. The `GENESIS_EAT_GAIN` / `GENESIS_READ_SCALE` env knobs and their
      NUMBA-cache keys are retired. **Measured:** books cohort reads (peak 58 correct/tick) and depth
      selects emergently 7.65→2.0, but the economy is **net-negative** and coast-collapses (~550 ticks)
      — see next bullet.
- [ ] **Remaining honest magnitudes (NOT game constants, but next to derive/justify):** `ATP_MAX =
      1e6` (energy ceiling — arbitrary; candidate = `RAM_SIZE × CELL_STATES`), `SYN_DENSITY_SCALE` /
      `STDP_SCALE = 8`, viscosity denominator `1000`, `FOOD_SCAN_RADIUS = 16`. `+128` (int8 bias) and
      the `1 cycle/op` costs are hardware-real — keep.
- ✅ **Flat-membrane blocker FIXED — event-driven membrane (Exp 8, 2026-07-12):** the membrane now
      charges `CYCLES_PER_NEURON_UPDATE × n_spiked` (per action potential), not `× n_count` (per neuron).
      On a 20 W substrate the spike is the energy event; idle neurons draw ~nothing (Rule 11). Result:
      books economy flips **terminal → survivable** (pop grows 300→358, stabilises ~260, lives ~1449 vs
      ~550 ticks; 37–45 correct reads/tick while on text; Rule 7 depth-selection intact 8.5→2.0). No new
      constant — same 1-cycle unit billed on the real event. Food mode unaffected.
- ✅ **Library renews in place (`regrow_passage`, 2026-07-12):** restock now grows the next passage
      adjacent to existing text instead of teleporting a random page across the ring. Reading is
      destructive (solved byte → `0x00`), so non-local restock stranded the colony in the vacuum it ate;
      regrow-in-place **doubled mid-game read rate** (corr/t ~5–8 vs ~2–4). Wired into live `sim_loop`
      restock + `find_birth_pos` (offspring born text-adjacent). Live loop verified crash-free.
- ✅ **Redundant seek wiring (2026-07-12):** seek is now 2 synapses/direction (mirroring redundant echo)
      so mutation can't erase foraging in one flip. Confirmed the seek-loss mechanism — read rate/`enc_frac`
      hold ~2× longer. Kept; food mode unaffected.
- ✅ **Structural encounter wall BROKEN — graze-along-the-line + non-destructive read (Exp 9, 2026-07-12).**
      The reading model is now a **saccade**: a successful decode (`net>0`) advances the head +1 onto the
      next cell, so a reader *walks* the passage symbol-to-symbol. That move also retires destructive
      reading — the saccade moves the head off the cell, so re-reading means circling the whole 65 536-ring
      (never net-positive); the movement *is* the anti-farm, so reads are **non-destructive** (books stay
      intact, a following reader gets the same text, the library is never strip-mined). No new constant
      (step = unit adjacency, cost = existing `CYCLES_PER_MOVE`). Measured: `enc_frac` 0.05 → **0.4–0.76**
      (was density-invariant, now responds to the world); the type-3 **prediction path came alive**
      (`pred/t` 0 → up to 44); `att/t` 100 → ~1 (efficiency, Rule 7). **The cap is now density-TRACTABLE,
      not structural:** at 9 % density the colony still slowly bleeds (long passage-to-passage vacuum
      transit), but at **37 % density the economy is net-positive** — mean energy *rises* 42k→44k and
      `dE/t` > 0 over the back 600 ticks, self-sustaining on reading income at carrying capacity ~165.
      Food mode + live `sim_loop` verified crash-free.
- ▶ **Remaining economy work (post-Exp 9):** (a) population-level self-sustain at *low* text density —
      the residual limiter is passage-to-passage transit (a grazer earns nothing crossing vacuum between
      books), tractable via denser/curriculum layout or a cheaper cross-vacuum seek; (b) the orthogonal
      **deep-time/Ark collapse** (Exp 4: monoculture reseed + total-wipe) still mass-extincts the *live*
      loop independent of the now-working economy — that is the next real blocker for ascension.
- [ ] **Absolute-footprint** pressure: let contention/viscosity also rise with
      `(n+s)/UNIVERSE_MAX`, so large *sparse* brains are not effectively free (audit finding).
- [ ] Remove the stale `tests/sim_test.py` / `tests/verify_baseline.py` (they import the
      deleted graph engine); `tests/smoke_test.py` is the working replacement.
- [ ] **Brain-size bloat ratchet:** growth-biased `mutate_dna` + Ark preserving longest-lived
      (bloated) genomes ratchets brain size up each era (throughput ~12.5k→~4.5k ticks/s in
      Exp 4), defeating Rule 7 efficiency selection because longevity tracks the seed buffer,
      not efficiency; couple the fix to the seed-buffer shrink (P2).
- ~~**Milestone (2026-07-11):** `CYCLES_PER_EAT_GAIN` env-tunable; sweep found first self-sustaining
      foraging at eat-gain ≥ 4096 on a food carpet (Exp 4).~~ **SUPERSEDED (Exp 7):** the meal value is
      no longer a tunable constant — a food byte reclaims a cell for `CELL_STATES = 256` (derived), so
      `eat_gain_sweep.py` / `book_read_test.py` / `tierra_trap_test.py` (which set `GENESIS_EAT_GAIN`/
      `GENESIS_READ_SCALE` and one of which asserts `ne.CYCLES_PER_EAT_GAIN`) are now **obsolete** and
      should be retired or rewritten to the CELL_STATES currency.
