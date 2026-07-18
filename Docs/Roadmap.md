# GENESIS Roadmap

> **STRATEGIC PIVOT (2026-07-16): the design loop is CLOSED. See `Docs/Ascent.md` (binding).**
> Experiments 13–29 formed an open-ended "build a lever → hit a new wall → build the next lever" loop
> that accumulated economy mechanics (DEPLETE, STIGMERGY, SUPER-RENT, PERSIST, LEASE, CANVAS…) without
> approaching the Rule-6 goal. Root cause (now fixed by **Rule 18**): "ascent" was only ever defined
> NEGATIVELY (every run a "not yet"), and the project's **load-bearing assumption — that the brain LEARNS
> within its lifetime — was never validated** against a control. `Docs/Ascent.md` now fixes a
> pre-registered, quantitative finish line (A: capability +25% sustained 5M ticks; B: learning is
> load-bearing vs an STDP-ablation control; C: efficiency holds) AND a kill-criterion that falsifies the
> substrate if learning cannot be made load-bearing. **The next experiment is NOT another economy lever
> — it is the learning-ablation A/B (STDP ON vs OFF), the highest-information test and the one that should
> have been Exp 1.** Validate the mind first; shape the economy that selects for it second.

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
- 🟠 **"Does it ascend?" — measured NO; economy made information-honest, blocker isolated to
      ABUNDANCE (Exp 12, 2026-07-13).** Direct live measurement of the Exp 11 colony: it survives but
      **decays** — brain sheds 7.7 % (`Universe N` 25 918→23 929) and prediction dies by tick ≈62k.
      **Root cause:** echo-reading paid full `CELL_STATES` for naming the byte *under* the pointer,
      which is already on the reading-eye inputs — a **zero-surprise bit-copy** any reflex farms
      forever, so capability is never selected and Rule-7 efficiency grinds the brain down. **Fix (no
      new constant):** reward only **predicting the next, unsensed cell** (`pos+1`); echo now pays
      nothing (0 surprise → 0 energy), so comprehension *is* the income (Rules 6/9). This **cliffs
      cold** on repeat-free text (`01_Alphabet`, `03_Phrases` → `pop=12`, `reads=0`) — a random genome
      predicts nothing — so it is bootstrapped by a **graded difficulty curriculum** `00_Graded`
      (run-length ramp `10→5→3→2→1`; on a run "next = current", so an echo reflex is already a correct
      predictor and seeds income). Result: survival restored (`pop≈600`, `refuge=0`), prediction kept
      **alive** (0–10 vs echo's death-to-0), brain **no longer sheds** (flat ~24 500) — a strictly
      better substrate. **But still no ascent:** `reads` drifts 78→58, `pred` flat over 400k ticks.
      **Isolated blocker = ABUNDANCE:** 600 orgs on a 10 %-full scroll means easy text is plentiful, so
      nothing forces an organism up the difficulty ramp; efficiency even trims the unused capability.
      The gradient is in the text; the *pressure* is not. **Next lever = scarcity/competition** — a
      carrying capacity below the array cap so cracking harder symbols is the only way to eat, which
      promotes the "food-scarcity ceiling below 600" item from a nicety to the load-bearing mechanism
      for ascension. **Three constant-free scarcity levers were tried and FAILED (measured, Exp 12.7):**
      (1) higher density/crowding on `00_Graded` (33 %) — `reads` stays ~85, `pred`~0; the existing
      event-driven crowding cost is too weak and a *flat* crowding charge is forbidden (it is the
      von-Neumann scan tax retired in Exp 11, Rule 11); (2) spatial scarcity (`00_Frontier`: small easy
      nursery + large hard frontier) — **cliffs** (`pop=12`), because the graze-along-the-line saccade
      means an org *cannot camp* easy text: it walks off the nursery into the hard wall and starves.
      Root tension: **non-destructive reading = infinite resource = no carrying capacity**, and every
      simple scarcity collides with the saccade-walk (walls cliff), event-driven honesty (no flat tax),
      or re-opens transit-starvation (destructive reading + a regen constant). **(3) Finite per-tick
      information (Exp 13): BUILT + FAILED — and the failure is decisive.** Dividing the prediction
      reward by `crowd_count` (±16 readers) collapsed the colony (`pop=12`) because reading is
      **spatially exclusive** — each org reads its OWN cell (`pos+1`), so neighbours don't contend for
      the same information; the ±16 split is a crowding tax in disguise that kills the bootstrap, while
      the *honest* same-target-cell split is `n=1` almost always and never triggers. **Structural
      conclusion:** non-destructive, spatially-exclusive, saccade-walked text reading is intrinsically
      an **infinite, uncontested resource** — a carrying capacity cannot be imposed without relaxing a
      load-bearing constraint. **Ascent therefore routes through PEER competition, not text scarcity**
      (see P3): peer prediction is the only genuinely scarce, contested (zero-sum) resource — the text
      economy's job is survival (done), the peer economy's job is ascent, if made non-lethal.
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
- 🟡 **Non-lethal peer coupling — the autotelic layer now RUNS without self-extinguishing (Exp 14,
     2026-07-13).** The lethality is fixed with a **derived, constant-free floor**: peer predation may
     skim only the speaker's **surplus above body-subsistence** (footprint × `CELL_STATES`, the same
     quantity as the abiogenesis seed), never pushing it below the cost of its own body. Still zero-sum
     and unfarmable; the Red-Queen race is now over reproductive *surplus*, not survival. **Measured
     live** (`00_Graded`, `GENESIS_PEER=1`, ~456k ticks): colony **SURVIVES** (`pop=600`, `refuge=0`) —
     Exp 11's collapse is gone — and **self-organises into a peer economy** (`peer` 21→135, text `reads`
     110→28: orgs shift from reading text to predicting each other). **BUT it plateaus, not ascends:**
     `peer` settles ~135, `Universe N` flat over 300k ticks — the zero-sum race equilibrates without
     capability rising. Peer stays **default-OFF** (now *safe* to run but it replaces rather than
     improves the reading economy).
- ✅ **Observation-only signal-diversity probe — plateau is NOT a degenerate code (Exp 15, 2026-07-13).**
     Built the Rule-9↔6 probe (Shannon entropy of vocal bytes per window, `Hpeer`/`Hread`+`nd`, pure
     telemetry, never wired to selection) and **measured to ~3.1 M ticks** (~7× deeper than Exp 14). The
     degenerate-code guess is **falsified**: `Hpeer` ≈ **3.8 bits / ~19 distinct signals**, rock-stable,
     *richer* than the reading channel (`Hread` ≈ 1.4 / 8). Capability stays flat not because signals are
     poor but because peer prediction is **spatially confounded with reading** — a neighbour's vocal byte
     is guessable from the predictor's own reading eye, so the task is **solvable without modelling the
     other agent**. **Corrected ascent lever (b′):** *decouple the peer target from the predictor's own
     sensory field* — predict a neighbour's *future* signal / *hidden-state*-driven action, not its
     current shared-text read — so out-modelling a *mind* (theory-of-mind), not re-reading a *page*,
     becomes the only way to win. (Supersedes the old (a)/(b) plan above.)
- 🟡 **(b′) theory-of-mind coupling built — sustains but does NOT ascend (Exp 16, 2026-07-13).**
     Implemented the corrected lever: peer prediction now pays only for *surprise* — score the neighbour's
     FRESH byte against the frozen `vocal_prev` (t−1, what was sensed) and reward **only the bits that
     CHANGED**, so echoing a sensed voice earns 0 and only anticipating a change earns (mirrors the Exp 12
     reading fix; no new constant, zero-sum, non-lethal floor retained). Caught + reverted a reading-killer
     (also sensing `vocal_prev` collapsed the colony to `pop=12/reads=0`; live 3-input compressed voice
     sense is too lossy to farm, so kept). **Measured live** (`00_Graded`, `GENESIS_PEER=1`, ~1.9 M ticks):
     the colony **slowly bleeds to a LOWER stable plateau** (`pop` 600→282, `Universe N` 26k→12.4k — brain
     HALVED — then level; `refuge=0`, `ext=0`) — it does not ascend, it re-equilibrates *smaller*. Cause:
     graded text is built from **long same-letter runs** (for the reading bootstrap), so neighbours seldom
     change signal → the anticipatable-change income is rare (`peer` 0–45) → can't fund the brain vs Rule-7
     shedding. **The blocker moved from the coupling to the SUBSTRATE:** reading-bootstrap wants long
     predictable runs, peer-ascent wants frequent signal change — opposite statistics. (b′) is the right
     coupling but needs a varying substrate / a hidden-state peer target. Default reading economy (peer-OFF)
     re-verified sustaining with all Exp 16 shared-code changes in place. **Next:** give the peer channel a
     high-change substrate or couple the target to a neighbour's hidden internal state (not its long-run
     reading output).
- ❌ **High-change-substrate branch CLOSED (Exp 17, 2026-07-13).** Tested branch (2) directly — feed the
     working (b′) coupling a higher-change book (zero code change, new book + `GENESIS_BOOK_NAME`). Both
     candidates **cliffed reading cold** (`pop=12`, `reads=0`): `00_Churn` (long `ABCDEFGHIJ` succession
     body) and `00_Churn2` (uniform run-2 body). Reading sustains ONLY on long low-change runs — any
     frequent change makes the saccade-walker hit a mispredicted transition every ~1–2 cells and starve
     before bootstrap. But long runs are exactly what starves peer (Exp 16). **The two economies make
     opposite, incompatible demands on the same bytes** → no shared reading/peer scroll can satisfy both.
     Diagnostic books removed; `00_Graded` still default. **Only remaining ascent route = branch (1):**
     decouple the peer target to a neighbour's HIDDEN internal state (next action / movement / energy
     trend), a separate constant-free hidden-but-modellable channel that can be high-change without
     touching the reading scroll. That new mechanism is the next build.
- ⚠️ **Branch (1) BUILT — sustains + ignites income but does NOT ascend (Exp 18, 2026-07-13).** Peer
     target decoupled from the shared scroll to the neighbour's **hidden motor action** `best_a∈{0..5}`
     (one-hot `1<<best_a`, surprise-gated, precision-graded `1/s_bits/8×CELL_STATES`, non-lethal floor;
     no new constant). Live 1.84 M ticks (`GENESIS_PEER=1`, `00_Graded`): colony **sustains**
     (`pop=569–600`, `ext=0 refuge=0`) and peer income **ignites** (`peer=1–44`, vs ≈0 in Exp 16) —
     but `Hpeer≈0/nd1` (thin **monomorphic** "predict-the-jump" code), `Universe N` −6.6 % then levels
     ~24500. Decoupling was **necessary** (killed the confound + starvation) but **insufficient**: the
     hidden action is *itself* low-entropy in a reading monoculture (everyone saccades). **Blocker moved
     from confound/starvation to LOW TARGET ENTROPY** — a theory-of-mind economy cannot ascend without
     behavioural diversity to model. **Next lever (unbuilt): Red-Queen** — reward the *prey* for being
     unpredictable (anti-prediction / evasion income) so a predator's improving model meets an evolving
     policy, pumping action entropy. Peer default-OFF; peer-OFF baseline re-verified — no regression.
- ❌ **Red-Queen branch CLOSED — rewarding unpredictability does NOT ascend + the Exp 18 premise was an
     artifact (Exp 19, 2026-07-13).** Built the prey half of the duel (`GENESIS_REDQUEEN`, default-OFF):
     a predictor's **clean single-bit wager** that misses transfers its stake to the mispredicted prey
     (zero-sum, unfarmable, non-lethal, same `CELL_STATES/BITS_PER_BYTE` rate, no new constant). Added an
     observation-only **`Hact`** probe (live action distribution). Live A/B (books, matched windows):
     both configs **sustain** (`pop≈595`, `ext=0 refuge=0`); **neither ascends** (`Universe N` decays then
     levels in both); mean `Hact` **1.75** (Red-Queen) vs **1.82** (peer-only) — unpredictability income
     **does not raise** action entropy, if anything lowers it; evasion income stays thin (`evade≈42/100k`)
     because precision-graded predator income lets predators earn *without* committing a clean wager, so
     they dodge the penalty and the duel goes quiet. **`Hact` exposes the Exp 18 error:** the action
     distribution is already `nd6` (not monomorphic — the `Hpeer≈0/nd1` was only *winning-prediction*
     entropy; only the modal action is monetizable, the rest are present-but-noisy). **Redirect:** ascent
     needs a **structured, modelable (predictable-but-hard-to-compute)** target — *compressible complexity*
     the predictor is rewarded for learning to compute — **not** raw surprise. Red-Queen default-OFF;
     peer-OFF baseline byte-identical + re-verified healthy. `Hact` probe retained.
- ❌ **Complexity-without-scarcity branch CLOSED — a cognitive-difficulty ramp does NOT self-generate
     ascent; re-derives the Exp 13 abundance wall on the difficulty axis (Exp 20, 2026-07-14).** Built
     `Books/generate_ascent.py` → `00_Ascent.txt`: one monotonic 6000-glyph scroll ramping **cognitive
     complexity** (bootstrap runs → successor +1 → carry 00–99 → arithmetic `a+b=c` mod 10), each stage a
     **compressible** rule so learning-the-rule out-earns memorising (the Exp 19 redirect, tested on the
     peer-independent *reading* economy; world structure only, no new constant). Added an observation-only
     **ascent-frontier probe** (`frontier b/s/c/a/off` + mean offset %, Rules 9↔6, never selects). Live
     (`GENESIS_BOOK_NAME=00_Ascent`, ~150 k ticks): colony **sustains** (`pop=587–600, ext=0 refuge=0`) but
     the frontier **collapses INTO the bootstrap band** (`~597/3/0/0/0`, mean offset pinned ~53 % at the
     bootstrap→successor boundary); computational bands (carry/arith) go **permanently empty** — organisms
     spawned there die, nobody climbs in. **Cause = the Exp 13 abundance wall on the *difficulty* axis:** the
     easy band is an infinite uncontested resource for 600 orgs, so there is **zero pressure to cross into
     the hard frontier** — grazing easy forever beats starving at the boundary. **Verdict: a single-agent
     reading economy has no scarcity → no ascent, whether you make text quantitatively (Exp 13) OR
     qualitatively (Exp 20) harder.** Reconfirms: **ascent must route through PEER**, with a **compressible-
     complexity** target (Exp 19). `00_Ascent` + frontier probe kept as instruments; peer-OFF `00_Graded`
     baseline re-verified over ~3 M ticks — no regression. Branches closed: 13, 15, 17, 19, **20**.
- ❌ **Peer-target design space EXHAUSTED on the current substrate — the ceiling is behavioral expression,
     not the coupling (Exp 21, 2026-07-14, design-space result, NO engine change).** Adversarial
     design-and-refute panel: 5 independent compressible-complexity peer-target proposals (future-action,
     running-aggregate, future-position, energy-trend, iterated-map), each attacked by independent
     scarcity/confound + depth/constant-free lenses → **all 5 FATAL, unanimous, every one reducing to
     branch 18.** Root cause (data-processing inequality): theory-of-mind is capped at the action-stream's
     own entropy = **`Hact≈1.8 bits` (Exp 19), hard-ceilinged by `N_OUTPUT=6`** (`log2 6=2.58` absolute).
     Every target (shift register / integral / LFSR / aggregate) just **re-encrypts the same low-entropy
     stream** — none co-evolves new complexity. Three traps each design hit: (1) width≠depth (a window is N
     parallel Exp-18 reflexes, not an N-deep chain); (2) monoculture erases cross-agent variance, and the
     only regime with variance is unsurvivable (Exp 17/20 wall); (3) the `net>0` gate is farmable by a
     constant-byte reflex. **Unifying verdict: you cannot model a mind richer than it can act — a 6-way
     motor argmax + 8-bit vocal byte has no room to express depth, so there is nothing deep to predict. The
     lever is WIDENING BEHAVIORAL EXPRESSION, not a cleverer target.** Sharpening for the next build
     (supply vs demand): Exp 19 saw `Hact≈1.8 < 2.58` with all 6 actions present but skewed → the colony
     does NOT saturate the actions it has, so the ceiling may be DEMAND-limited (no task rewards diverse
     behavior) not SUPPLY-limited (too few bits). Cheap pre-build probe: does `Hact` climb toward 2.58 under
     an environment that pays for behavioral diversity? Gates which substrate change is worth the
     genome-decode risk. Candidate levers (unbuilt fork): (a) widen/compositionalise the action space;
     (b) structured/stigmergic environment where agents build RAM artifacts and peers predict what a
     neighbour BUILT. Frontier redirected from "what should peers predict?" (exhausted) to "how does an
     organism's behavior become worth predicting?" Branches closed: 13, 15, 17, 19, 20, **21**.
- ✅ **Supply-vs-demand SETTLED empirically — the ceiling is behavioral COLLAPSE to the single monetized
     action; demand-limited, not supply (Exp 22, 2026-07-14).** Built `GENESIS_ACTPROBE` (compile-time,
     observation-only, default-OFF, kernel byte-identical when off): records `best_a` on the peer-OFF path
     and prints the full 6-way histogram `act fwd/bck/f10/b10/eat/rep` + `Hact`. Live-measured both
     economies to equilibrium: **reading collapses to an `eat`-monoculture (73–86%, Hact~0.8–1.2); the peer
     run (pre-ignition) collapses to a `fwd`-monoculture (88–95%, Hact~0.35–0.6).** Each economy pays for
     ONE behavior → the colony converges onto THAT one → distribution is dictated by WHAT PAYS, not
     repertoire size. Early `Hact~2.2` was founder diversity BURNING OFF (the Exp 19/21 ~1.8 was a
     time-average across the decay; equilibrium is LOWER). **`f10`/`b10` (jump±10) structurally DEAD (~0%)
     in both → effective repertoire ~4, at equilibrium ~1.** **VERDICT: widening `N_OUTPUT` (supply) adds
     capacity a single-reward economy won't use — WRONG lever. The lever is DEMAND for behavioral diversity:
     an economy where DIFFERENT behaviors pay DIFFERENT organisms (niche structure / division of labour) so
     the population can't collapse onto one action.** Re-ranks the fork: **(b) structured/stigmergic env
     favoured over (a) action-space widening.** Next concrete test: does a SECOND orthogonal energy source
     (paying a different action than reading) split the colony into 2 behavioral niches + hold `Hact` up at
     equilibrium? `GENESIS_ACTPROBE` kept as instrument; default (probe OFF) re-verified byte-identical, no
     regression (`pop 506–600`, reads healthy, `ext=0 refuge=0` — after killing a rogue leftover sim that
     had cliffed the first check via CPU contention, the Exp-18 live-loop lesson re-validated). Supply
     hypothesis ELIMINATED; demand/niche-structure CONFIRMED as the lever.
- ⚠️ **A second energy niche LIFTS Hact, but a passive lattice does NOT recruit the targeted jump gait
     (Exp 23, 2026-07-14, partial).** Built `GENESIS_NICHE` (default-OFF, pure driver change, no new
     constant): ambient food stocked ONLY on a stride-`LONG_JUMP_STRIDE` lattice (=10, the SAME distance the
     jump10 actuator moves — named the literal `10` into a constant so the lattice DERIVES from the actuator).
     Intent: meals reachable meal-to-meal by jump10, +1-drift starves between → forager niche. **POSITIVE:**
     at matched food rate 20, the lattice holds a TWO-mode equilibrium (`fwd`+`bck` coexist, `Hact≈1.7`) vs
     uniform food collapsing to a `bck`-monoculture (`Hact≈1.1`) — first intervention that RAISES equilibrium
     Hact; confirms Exp 22 demand thesis in direction. **NEGATIVE:** `f10`/`b10` stayed dead (~0–9%) — the
     added diversity is `fwd`+`bck`, not the jump gait. Passive stride-10 spacing does NOT FORCE a jump (a +1
     walker still lands on lattice cells, `bck` sweeps them too) = "option ≠ pressure" (same Exp-20 failure on
     the foraging axis). **Next:** to force a specific gait the drift gaits must FAIL — lattice cells behind a
     true energy BARRIER only a long-jump crosses (Exp-13-style), or a moving lattice that outruns drift. But
     even a perfect 2-niche split gives a peer predictor only a 1-bit reader-vs-forager label — reinforces
     that generic action diversity ≠ MODELABLE depth. **Stronger route remains (b) STIGMERGY** (diversity in
     open-ended BUILT artifacts, not a fixed gait menu); the lattice is a down-payment proving spatial-demand
     structure moves Hact. `GENESIS_NICHE`+`GENESIS_FOOD_RATE` kept as instruments (default OFF/0.1); default
     byte-identical, no regression (killed a 3rd rogue leftover sim mid-run — leftover sims are the standing
     hazard, always verify procs clean before a live A/B).
- ✅ **Stigmergy design space names two WALLS; bounding reading income BREAKS Wall 1 + forms a carrying
     capacity (Exp 24, 2026-07-14).** (A) Adversarial workflow vetted 5 stigmergy economies (trails,
     construct-consume, external-memory, niche-construction, minimal-write) × 2 refute lenses → ALL 5 FATAL,
     0 survivors, but converge on TWO named walls: **WALL 1** = reading income is MINTED on a non-destructive
     infinite scroll, so any AUTHORED royalty-charging cell is strictly dominated by the free book → builders
     earn nothing → building selected out (lessons 13/22); **WALL 2** = the vocal byte is confounded with the
     shared text — peer-adjacency=reading-adjacency, so a peer reads a neighbour's "authored" byte off its own
     eye (15/17/21), and flat royalty is maximised by PREDICTABILITY not depth (selects AGAINST complexity,
     18/20). Escape recipe the critiques prescribe: destructive/rivalrous built cells + authored value
     decoupled from the reading eye + depth-pays-more-per-cell. (B) Attacked Wall 1 directly (the deeper
     enabler, live build not vetted — it's one falsifiable physics change): `GENESIS_DEPLETE` (default-OFF, no
     new constant, byte-identical when off) makes reading DRAW from a finite per-cell fuel reservoir
     (`read_fuel`, cap=CELL_STATES) instead of minting; driver regrows `GENESIS_DEPLETE_REGROW`/iteration.
     **Live sweep: regrow 128 = CARRYING CAPACITY FORMS** — pop oscillates 400–598 (never pinned at cap, first
     time in the whole arc), `Hact≈1.2–2.5` (HIGHEST sustained action entropy yet, vs 0.8 eat-monoculture),
     reads compressed 150→30–50, sustains 114k+ ticks no extinction. regrow 256≈unbounded (barely binds);
     regrow ≤64 cold-cliffs (starves the bootstrap = Exp-20 bootstrap-vs-scarcity tension on the energy axis).
     **Wall 1 is not a law of the substrate — it was a consequence of MINTING, and it's breakable.** This is
     the missing precondition for stigmergy: with reading no longer infinite-free, an authored economy is no
     longer dominated. Fixed a bug (regrow was gated on the slow restock cadence → starved; moved to
     per-iteration) + caught a missed 2nd kernel call site (warmup) via the live-loop rule. Follow-up: per-tick
     in-kernel regrow for finer carrying-capacity control (driver granularity is coarse). `GENESIS_DEPLETE`+
     `GENESIS_DEPLETE_REGROW` kept as instruments (default OFF/CELL_STATES); default byte-identical, no
     regression. **NEXT: build stigmergy ON TOP OF bounded reading using the Part-A escape recipe.**
- ⚠️ **Stigmergy BUILT — first persistent agent-authored substrate structure, but shallow + needs seeding +
     does not yet ascend (Exp 25, 2026-07-14).** `GENESIS_STIGMERGY` (default-OFF, requires DEPLETE, no new
     constant, byte-identical off): overload OUT_CONSUME (keeps N_OUTPUT=6, zero genome-decode risk) — CONSUME
     on a writable cell + printable emission AUTHORS the vocal byte there, claims ownership
     (`cell_owner[pos]`), cost=CELL_STATES; reading an OWNED cell pays the author a per-bit royalty slice
     (zero-sum, non-lethal, depth-scaled). **(25a) vacuum-only authoring FAILED** (`authored=0`): survival
     glues every org to the readable scroll (off-scroll≈0), so no org ever stands on vacuum → CONSUME-on-text
     is a no-op → build/read locations DISJOINT ("option≠pressure" as a LOCATION mismatch). **(25b) FIX:
     author a DEPLETED scroll cell** (printable + fuel exhausted = exactly where readers are AND stopped
     paying; reclaiming it is rivalrous/destructive per Exp-24 recipe) → **authoring EMERGES + persists:
     authored≈270-278 cells, authors≈150 orgs, stable at pop=600. FIRST persistent agent-authored readable
     structure in GENESIS.** **HONEST LIMITS:** shallow (150 authors × ~2 cells = broad thin dabbling, not a
     builder/reader division; authored plateaus not grows); does NOT ascend (N≈23.9k slightly BELOW depletion
     baseline, Hact≈1.1-1.5 below depletion's 2.2); needs SEEDING (unseeded cold-cliffs — write reflex too
     rare to express from cold gene pool). **Diagnosis: plumbing works but economics too FLAT** — the royalty
     is a thin per-bit slice so authoring is marginal side-income ~150 orgs dabble in, not a niche a specialist
     lives in. **Missing = Exp-24 recipe's 3rd leg: depth must pay SUPER-LINEARLY more per cell** (dedicated
     author of hard content out-earns solo reader → real builder niche → only then can division of labour lift
     Hact/capability, Exp 22). Also authored byte is still the org's READING emission (scroll-tracking), not
     text-INDEPENDENT → deeper half of Wall 2 remains. `GENESIS_STIGMERGY`+`GENESIS_STIG_SEED` instruments
     (default OFF); default byte-identical, no regression (4th rogue-leftover-sim recurrence cliffed an interim
     check, killed+re-verified). NEXT: super-linear depth-scaled rent + text-independent authored value.
- ⚠️ **Super-linear rent PRESERVES diversity + concentrates traffic, but NO specialist forms without
     TERRITORY PERSISTENCE (Exp 26, 2026-07-14).** Added the Exp-24 recipe's 3rd leg: royalty fraction scales
     with a cell's cumulative READ-TRAFFIC (`read_hits` counter, reset on authoring) — 1 read pays
     1/BITS_PER_BYTE of reader gain, a hot cell up to (BITS_PER_BYTE-1)/BITS_PER_BYTE (no new constant, pure
     integer-hit ratio × reader gain; zero-sum reader keeps ≥1/8; non-lethal). +telemetry `tophold` (max
     cells/author), `toptraf` (peak cell traffic). **POSITIVE:** vs Exp-25 flat rent (which SUPPRESSED Hact to
     ~1.3), super-linear rent keeps Hact ELEVATED ~2.0-2.45 (pure-depletion level) + `toptraf` climbs 894→9879
     (heavy-traffic hotspots form = the mechanism engages, doesn't collapse diversity). **NEGATIVE:** `tophold`
     caps at 4-6 — NO author accumulates a holding to LIVE on; `authors` keeps climbing (31→185, broad
     dabbling persists). **Diagnosis: super-linear rent rewards HOLDING high-traffic cells but nothing lets an
     author HOLD them** — any org re-authors a depleted cell + seizes ownership → constant churn → income can't
     concentrate. Rent DEPTH is necessary but insufficient; missing = **ownership PERSISTENCE / territory
     defense** (a held cell resists overwrite, or owner cheaply refreshes it). Late-run Hact decays 2.4→1.06 +
     pop dips = churn is actively destabilising, not neutral. **NEXT: give ownership persistence** (re-authoring
     an owned+fuelled cell costs more than claiming vacuum/depleted; or owner's cheap refresh keeps held cells
     live) so a specialist defends territory → income concentrates → stable builder/reader division lifts
     capability (Exp 22). `read_hits`+`tophold`/`toptraf` kept as obs-only instruments; default byte-identical,
     no regression. Branches: flat-rent-shallow closed (25); super-rent-needs-territory-persistence (26).
- ⚠️ **Absolute ownership persistence FREEZES the map — both extremes fail, answer is a DECAY GRADIENT
     (Exp 27, 2026-07-14).** Added the property right `GENESIS_STIG_PERSIST` (default-OFF, requires STIGMERGY,
     no new constant): a LIVING owner's cell is NOT seizable (non-owner may author only vacuum/unowned/
     dead-owner); the OWNER may refresh its OWN cell at any fuel level (defend + keep live, retains earned
     traffic); owner DEATH releases the cell (emergent turnover, Rule 10). **Result = a HARD ECONOMIC FREEZE,
     not specialisation:** `authored/authors` LOCK at exactly 112/91 for 150k+ ticks, `toptraf` explodes
     unbounded → 106,810 (a handful of founder cells become permanent toll-booths every reader funnels
     through), `Hact` COLLAPSES monotonically 2.0→0.1 (monoculture), `tophold` still 4 (freeze locked in
     BEFORE any author could accumulate a holding → 91 orgs each own ~1 permanent cell forever). **NO new
     authoring ever happens** (all viable depleted-cell territory locked by living owners). **Opposite failure
     from Exp 26 (total churn) and WORSE for capability** (churn kept Hact~2.2; freeze kills it). **Diagnosis:
     BOTH EXTREMES FAIL** — no persistence (26) churns/no-concentration; absolute persistence (27)
     ossifies/diversity-dies; concentration happened on CELLS (toptraf) but not AUTHORS (tophold) because
     founders locked claims before selection could sort winners. **Missing = Tectonic Gradient Principle
     (Rule 10) on the OWNERSHIP axis: a claim must DECAY over time** (owner keeps paying/refreshing to hold;
     unrefreshed claim weakens → contestable) so territory recycles SLOWLY — persistent enough a better
     builder holds + out-earns, impermanent enough it never ossifies into a founder toll-booth cartel. Same
     arc lesson (gradient not cliff) now on the property-right axis. `GENESIS_STIG_PERSIST` kept as the frozen
     A/B extreme (default-OFF); default byte-identical, no regression. **NEXT: decaying/leaky ownership (a
     refresh-to-hold claim that weakens if unattended).**
- ⚠️ **Leaky ownership DESTABILISES the colony — holding-cost on shared-scroll cells cannibalises the reading
     substrate (Exp 28, 2026-07-14).** Built the Rule-10 decay gradient `GENESIS_STIG_LEASE` (default-OFF,
     implies PERSIST, no new constant): owned cells lose full free regrow → owner must actively REFRESH (pay
     CELL_STATES) to hold; neglected cell drains → claim LAPSES → recycles. Two variants: (a) binary (owned
     get ZERO regrow), (b) partial (owned regrow at 1/BITS_PER_BYTE of free rate, hardware-derived).
     **BOTH COLD-CLIFF the colony (pop→12), seeded AND unseeded.** binary+seed: authored→0 (authoring strictly
     a loss); partial unseeded: pop 288→12 (cliffs WITHOUT the seed too = the lease mechanic itself, not just
     the seed). **TWO structural failure mechanisms:** (1) **authoring CANNIBALISES the reading substrate** —
     authoring targets DEPLETED SCROLL cells (Exp 25b), so an authored cell IS a scroll cell; under lease it
     gets reduced regrow → orgs convert live reading territory into slow-refuelling owned cells that drain +
     lapse + churn the scroll to low-fuel → reading income (survival) drops → collapse. (2) seeded write-spam
     bankrupts the bootstrap (~82 founders each pay 256 to author, can't recoup under lease → mass energy
     drain). **Diagnosis: the decay gradient is RIGHT but authoring must NOT sit on the reading scroll.** Exp
     27 (freeze) + Exp 28 (leak) bracket the persistence axis, but Exp 28 exposes the deeper coupling carried
     since Exp 25b: authoring reuses depleted scroll cells, so ANY holding-cost on owned cells is a
     holding-cost on the shared reading substrate → the two economies fight over the same fuel. **Clean fix =
     the OPEN HALF OF WALL 2: authoring needs its own TEXT-INDEPENDENT territory** (a region/value channel NOT
     the reading scroll) so ownership upkeep/lapse/rent operate on AUTHORED resource without draining READING
     fuel. Until authoring + reading are decoupled in SPACE/SUBSTRATE (not just byte value), every
     property-right refinement collides with survival. `GENESIS_STIG_LEASE` kept as the destabilising A/B
     extreme (default-OFF); default byte-identical, no regression. **NEXT: decouple authoring from the reading
     scroll — a text-independent authored territory (the open half of Wall 2).**
- ⚠️ **Substrate decoupling BUILT — the fuel coupling breaks + migration works, but a NEW energy-currency
     coupling bankrupts the colony (Exp 29, 2026-07-14).** Adversarially vetted 5 decoupling designs (workflow,
     2 refute lenses); built the surviving synthesis `GENESIS_CANVAS` (default-OFF, requires DEPLETE+STIGMERGY,
     no new constant, N_OUTPUT=6 kept): a CANVAS band `[LIB_START+BOOK_TARGET_BYTES, +BOOK_TARGET_BYTES)` laid
     after the scroll, authoring INDEX-CONFINED to it (a scroll cell can never be owned → ownership upkeep/lapse
     structurally cannot touch survival fuel = the Exp-28 fix), abutting the scroll so readers walk onto it,
     royalty SURPRISE-GATED (echo/constant-run pays zero rent = Wall-2 anti-farm), optional `GENESIS_CANVAS_SEED`
     tiles the book in so it pays from t=0. **TWO FIRST-TIME POSITIVES:** (1) the fuel decoupling WORKS — reading
     fuel is never cannibalised (Exp-28 collapse mechanism structurally impossible); (2) reader MIGRATION works —
     `oncanvas` climbs 40→168→**596**, readers colonise authored territory en masse, defeating the Exp-25b
     barrenness that blocked every prior stigmergy build. **BUT still collapses (pop→12) via the vetting-PREDICTED
     failure: energy-currency coupling.** Fuel pools are decoupled but ENERGY is one shared currency — once
     migration succeeds, hundreds author simultaneously at CELL_STATES/cell (`authored→5910`, whole band), draining
     collective energy faster than royalty returns → mass starvation. Parameter sweep brackets it: seeded+reflex →
     migration over-succeeds into a build-frenzy → bankruptcy; unseeded → barren (no migration) or founders author
     vacuum and never bootstrap. **Authoring is a tragedy-of-the-commons in the shared energy pool: individually
     rational, collectively bankrupting when synchronous.** Decoupling is NECESSARY + now proven ACHIEVABLE but
     INSUFFICIENT alone — needs a THROTTLE on collective energy→territory conversion (author cost scaling with
     canvas already owned = diminishing returns; or a scarcer prerequisite than raw energy; or a slower migration
     pull). `GENESIS_CANVAS`/`_SEED` kept as instruments (default-OFF); default byte-identical, no regression.
     Branches: churn (26), freeze (27), leak-cannibalises-reading (28), **energy-currency-frenzy (29)**.
- 🛑 **DESIGN LOOP CLOSED + the load-bearing assumption FAILS: in-lifetime STDP is net-NEGATIVE (Exp 30,
     2026-07-16).** Per the strategic pivot (Rule 18 / `Docs/Ascent.md`), the first validation of the
     project's core assumption — does the brain LEARN in-lifetime? — was built (`GENESIS_NOLEARN`,
     compile-time STDP-Phase-3 deletion, default-OFF, byte-identical when off) and run as a live A/B on the
     default books economy. **Ablating learning is BETTER on every axis:** pop 596→**423** (ON, decaying) vs
     **599** flat (OFF); Universe N 25834→**17441** (−34%, brain sheds) vs 25790 flat (OFF); reading
     solve-rate **~23%** (ON) vs **~51%** (OFF); reads ~60 vs ~148. **Criterion B fails harder than "OFF≈ON":
     STDP is actively HARMFUL** — the whole-project "sustains but decays" signature (brain sheds, prediction
     dies, Exp 12+) is now causally attributed to STDP driving decode-good genetic weights toward noise. Every
     Exp 13–29 economy lever was built on a learning rule that was eroding the capability it tried to grow.
     **This falsifies the current learning RULE, not (yet) the substrate** — 3 repairable causes to diagnose:
     wrong-sign/target plasticity (most likely — shedding-under-learning = destructive drift), STDP metabolic
     overhead, or task mismatch (fixed reflex beats changing weight on next-symbol prediction). **NEXT = a
     DIAGNOSIS not a new lever (Rule 18):** ON-vs-OFF on a task whose answer CHANGES within a lifetime (only
     there can a real learner beat a fixed reflex) + isolate STDP energy cost from weight-update effect. Only
     if a corrected sign-correct task-matched plasticity still loses is the SNN-on-RAM substrate falsified.
     Operative now: **fix or remove STDP before any further capability work; treat the engine as
     reflex-evolution-only until a learning rule is shown to help.** `GENESIS_NOLEARN` kept as a permanent A/B
     instrument.
- 🔬 **STDP diagnosed + first repair beats ablation EARLY (Exp 31–32, 2026-07-16) — the MIND is now the
     work.** Exp 31 (diagnosis, `GENESIS_STDP_COSTONLY`/`GENESIS_STDP_DIV`): STDP sign is CORRECT (Hebbian);
     three real causes of net-negativity — (1) bang-bang step (~12% of range/event) slams good weights to the
     rail → shedding+collapse, FIXED by small steps (DIV=32 → pop/N flat); (2) metabolic overhead (COSTONLY
     cold-cliffs bootstrap); (3) **ROOT = no supervision** — even graded STDP makes reading slowly die
     (23%→3%) because plain Hebbian is blind to whether a prediction was CORRECT. Exp 32 (`GENESIS_STDP3`):
     built the fix — a three-factor neuromodulator scaling the weight update by the org's own reading reward
     (Rule-9 autotelic, bio-faithful). **First learning rule to beat the no-learning baseline: solve-rate ~78%
     early (vs NOLEARN 51%) — CONSTRUCTIVE LEARNING IS POSSIBLE on this substrate, substrate NOT falsified.**
     But it doesn't HOLD (decays to ~29%): the modulator gates plasticity TIMING, not DIRECTION — when reading
     pays, full STDP still blindly reinforces every coincident synapse. **Residual problem = CREDIT ASSIGNMENT**
     (which synapses caused the correct output). NEXT = a credit-assigning third factor (potentiate synapses
     onto neurons that drove the CORRECT vocal bits, depress wrong ones) = true reward-modulated STDP, then A/B
     for a rule that HOLDS above ablation. All flags kept as instruments; default byte-identical.
- ✅ **Credit-assigning STDP HOLDS above ablation — criterion B met (Exp 33, 2026-07-17).** `GENESIS_STDP3C`
     (per-vocal-bit signed eligibility trace): steady solve-rate 60% vs NOLEARN 51%, no brain shedding, no pop
     decay across 400k ticks — first durable net-positive learning rule (`Ascent.md` §4e). But on a task a
     FIXED reflex also solves, so it doesn't yet prove *construction* of new mappings.
- 🛑 **Within-lifetime remap test — the learner CANNOT re-track: STDP prunes but cannot RECRUIT (Exp 34,
     2026-07-18).** Built §4-step-2 (the affirmative test, never built before): `GENESIS_REMAP` (default-OFF,
     compile-time gated, byte-identical off) makes the reading-reward target SWAP two vocal bits on a wall-clock
     phase that is on NO sensory input — a fixed genome provably cannot pre-encode it, only in-lifetime plasticity
     can track it. Measured in a survival-DECOUPLED sandbox (`tests/remap_sandbox_probe.py`, real kernel, frozen
     energy-pinned 120-clone cohort, per-bit accuracy). **DECISIVE NEGATIVE:** in swapped phases the learner's
     swap-bit accuracy is ~40% FLAT (no within-phase recovery, no cumulative gain over 5 phase-cycles) —
     statistically indistinguishable from NOLEARN ~42%, while unchanged bits hold 99% (cohort healthy). Mechanism
     (pre-registered prediction, confirmed): STDP3C's credit is OUTPUT-GATED — it updates only on a POST-synaptic
     spike, so it can LTD-PRUNE a wrong-firing route but cannot RECRUIT a silent-but-wanted neuron (no spike → no
     eligibility → no gradient). Exp 33's win is real but NARROW: it *tunes/prunes an already-firing* reflex, it
     does not *construct* a new input→output mapping — the difference between tuning a circuit and building one,
     and building is what reasoning (Rule 6) needs. **Does NOT trigger the kill-criterion — localises the defect:
     the rule carries a REWARD signal, not an ERROR signal.** NEXT = a SUBSTRATE change to the plasticity rule
     (NOT another economy lever): inject a small TARGET CURRENT into the vocal neurons the target byte says should
     be ON (org's own reading target, Rule 9 autotelic, constant-free) so a wanted-silent neuron spikes and its
     afferents become LTP-eligible; re-run this exact sandbox A/B. If swap-bit accuracy then climbs and holds
     above NOLEARN → substrate can construct mappings in-lifetime (first evidence it can support reasoning); if
     not → kill-criterion genuinely in play. `GENESIS_REMAP` + sandbox probe kept as permanent instruments.
- ✅ **Error/teaching signal RECRUITS — the substrate CONSTRUCTS a new mapping in-lifetime (Exp 35,
     2026-07-18).** Built the pre-registered Exp-34 fix: `GENESIS_STDP_TARGET` (default-OFF, compile-time gated,
     byte-identical off) — a local DELTA RULE on eye→vocal synapses, `err_b = target_b − output_b`, that
     POTENTIATES a wanted-but-SILENT neuron's active eye afferents with NO post-spike required (the recruitment
     gradient STDP3C lacks). Biologically the dendritic-error/teaching current of predictive-coding SNNs, NOT
     backprop; autotelic (target = org's own read target, Rule 9) + constant-free (reuses STDP_DIV/CELL_STATES).
     **BREAKTHROUGH in the sandbox A/B:** STDP_TARGET re-tracks the swap **56%→~99% within ~2000 ticks EVERY phase
     flip** (recovery curve absent in Exp 34), re-learning faster each cycle, unchanged bits hold 99%; NOLEARN +
     STDP3C stay flat ~40%. **First in-lifetime CONSTRUCTION of a new input→output mapping in the project** — the
     substrate can BUILD a pathway, not only tune/prune one (Exp 33). Affirmative criterion B on a reflex-proof
     task; kill-criterion NOT in play, substrate validated one level deeper. **Honest scope:** proven in the
     ISOLATED sandbox (frozen energy-pinned cohort, seeded 2-bit fabric); NOT yet shown to beat NOLEARN on the
     LIVE books economy or to generalise to evolved topology. NEXT (in order): (1) live-loop A/B STDP_TARGET vs
     NOLEARN vs STDP3C on 00_Graded (holds above ablation on the real economy? fixes Exp-33 residual drift?);
     (2) criterion-A push (make held capability RISE) on a rule that can now construct. `GENESIS_STDP_TARGET` kept
     as permanent instrument; default byte-identical (re-verified). Full write-up: `Ascent.md` §4g, `Result.md` Exp 35.
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
