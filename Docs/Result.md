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
is the intended thermodynamic negative feedback. *Caveat:* this is a 500-tick run; deep-time
robustness across many extinction/Ark cycles has since been measured (**Experiment 4**) and is
**negative** — the engine settles into a clockwork extinction/Ark loop, not sustained stability.

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

## 🧪 Experiment 3 — Efficiency-Selection Alignment (Rule 6/7/11)
**Objective:** Test whether the physics actually *select* for the ~20 W paradigm —
low-hardware brains (few CPU cycles + small RAM footprint) — or merely *measure* it.

**Method:** An adversarial multi-agent audit (5 independent efficiency lenses over the live
source, then 3-vote adversarial verification of the load-bearing conclusions) followed by a
controlled before/after A/B in `tests/smoke_test.py` (now mirroring `sim_loop`'s food
respawn + Ark reseed so the harness matches the real economy).

**Finding (verified):** Efficiency was only *weakly, second-order* selected. The single
per-tick cost that scaled with brain size, idle metabolism, was charged at an arbitrary
`0.1 × n_neurons` (a Rule 17 magic discount), ~10× too small to compete with food (`+1024`)
and the `250,000` seed-energy buffer. The synapse/plasticity RAM footprint had **zero**
per-tick holding cost, and `elite_iq` (age ÷ footprint) was pure dashboard telemetry, never
fed into survival. Net: a bloated brain survived almost as well as a lean one.

**Change (honest raw-cycle accounting — emergent, never a fitness function):**
1. Neuron membrane update billed at its true **1 cycle/neuron** (was `0.1×`); constant
   `CYCLES_PER_NEURON_UPDATE`.
2. STDP weight update billed **1 cycle**, **activity-gated** (only when a synapse actually
   potentiates/depresses) — closes the "plasticity is free" exploit while rewarding *sparse
   firing*, not *few synapses* (Rule 11).
3. `sense()` hoisted out of the LIF sub-step loop (its inputs are invariant within a tick) —
   a pure, behaviour-identical engine speedup.

**Results (A/B, identical harsh food = 0.02, seed 300, 2500 ticks):**

| Metric | Old fudge `0.1` | Honest `1.0` |
|---|---|---|
| Equilibrium population | ~514–592 (near cap) | ~170–205 (margin-bound) |
| Avg energy | 20k–32k (coasting) | 3k–5k (near the death margin) |
| **Neurons the ecosystem sustains** | **~20,000** | **~6,500** |
| Extinction→Ark cycles | 1 | 4 (all recovered) |
| Wall-clock | 8.1 s | 2.7 s |

**Analysis:** Under honest cost the *same* food supply sustains **~3× less neural tissue**
and holds organisms at the energy margin, where a cheaper brain decisively out-survives a
costlier one — Rule 7 selection is now first-order and emergent (energy only), with no
top-down metric. At the realistic food rate (`0.1`) the population is stable with the
designed boom-bust + Ark recovery (one buffer-burndown transient per ~500 ticks, always
recovered). The honest engine is also ~3× faster (fewer neurons + hoisted `sense()`),
serving the "runs on less hardware" goal directly. *Caveat:* this shows the selection
*gradient* is now strong and correctly signed; it does not yet prove a leaner brain of
*equal capability* wins (capability is still unmeasured — see below).

---

## 🧪 Experiment 4 — Deep-Time Robustness & the Ark Collapse Loop (Rules 10/14)
**Objective:** Characterise stability across millions of cycles and many extinction/Ark
recovery cycles — the deep-time robustness listed as unmeasured in Exp 1 and as Future Work
in `Article_Draft.md`.

**Setup:** A live `genesis_lab.py` run under the default economy (`initial_energy = 250000`,
`GLOBAL_CYCLE_POOL = 3000`, `MAX_ORGANISMS = 600`, food byte `0x55`) observed from cold start
to `LIF Time ≈ 621,000` (~70 extinction/Ark cycles).

**Results (from the run log):**
- **Clockwork extinction:** total-population extinction recurs every **~8,640 LIF-time units**
  with striking regularity (successive inter-extinction intervals 9152, 8811, 8670, 8659, 8643,
  8632, 8671, 8639, 8630, 8645, 8628, 8625, 8652 …; σ ≈ 0.5% after the startup interval).
- **No ascension:** population holds at **~272–357 / 600 (mean ≈ 300)** with a single excursion
  to 507; neither the inter-extinction interval nor the population shows any upward trend across
  ~70 cycles. The system does not become more evolved era to era.
- **Throughput decay:** simulator speed falls monotonically from **~12,500 to ~4,500
  world-ticks/s** over the run.

**Root-cause audit (read-only, three independent source audits):**
1. **Ark fossil-capture freeze (bug — fixed 2026-07-10).** `max_ark_age` was a persistent
   all-time record set once before the loop and never reset, so after the first "golden era"
   `remember_fossil()` never fired again; the fossil pool froze onto a single lineage and
   reseeded every subsequent era from it. Primary driver of zero ascension. Fixed by resetting
   `max_ark_age` per era (`genesis_lab.py`).
2. **Monoculture reseed.** Each reseed draws 300 organisms from ≤12 near-clonal fossils; the
   cohort is **>95% genetically identical**, shares one physics/STDP header, and starts with
   identical `initial_energy` and age 0 → synchronised burnout.
3. **Metabolic death-spiral + all-or-nothing extinction.** `dynamic_lif_steps =
   GLOBAL_CYCLE_POOL / alive_count` makes each survivor burn *faster* as the population falls,
   and extinction is only detected at `alive_count == 0` (no partial path) → instantaneous total
   wipes. This is precisely the instantaneous, unpreventable wipe Rule 10's Tectonic-Gradient
   Principle forbids because it prevents learning.
4. **Brain-size bloat ratchet (not a memory leak).** Frees are balanced; instead, growth-biased
   `mutate_dna` (~+0.4 bytes/replication) plus the Ark preserving the *longest-lived* (hence
   bloated) genomes ratchets mean neuron/synapse counts up each era, raising per-organism LIF
   work and halving throughput. Efficiency selection (Exp 3) is defeated because, under the
   oversized seed buffer, longevity tracks the starting buffer rather than metabolic efficiency
   within the short pre-wipe epoch.

**Analysis:** The population is **not food-self-sustaining** — it coasts on the `initial_energy`
seed buffer, which each identical cohort drains over a near-fixed period, and is then
resurrected on a timer by the Ark. The extinction/Ark loop is therefore not evidence of survival
under hardship but of a substrate that never establishes self-sustaining life, with the Ark
masking that failure. The freeze bug is fixed; population self-sustainability, reseed diversity,
and the total-wipe dynamic remain open (see `Roadmap.md` P2/P3).

**Preliminary controlled sweep (`tests/self_sustain_test.py`, 40-tick horizon).** With the Ark
disabled (extinction terminal) and the seed buffer swept, survival time scales directly with the
seed buffer — `initial_energy` 2000 / 10000 / 50000 / 250000 → 7 / 31 / 40+ / 40+ ticks survived —
the signature of a cohort **coasting on its buffer**, not living on income; mean energy declines
monotonically in every configuration (no positive equilibrium is reached). Critically, a **10×
increase in food rate (0.1 → 1.0) changed nothing** — identical survival and energy curves —
indicating the binding constraint is *not* food scarcity but that **metabolic burn vastly exceeds
any achievable food income**, so the food→energy→reproduction loop never closes. A subsequent horizon-600 sweep (Ark off) confirmed the buffer-coasting law at scale (survival
31 / 153 / 485 ticks for buffer 10k / 50k / 250k) and, decisively, showed that a **400× increase
in food supply (1 → 400 bytes/tick) barely changed survival (31 → 36 ticks)** or the energy
trajectory — ruling out food *scarcity* as the binding constraint. Inspection of the seeded
feeding reflex (`create_intelligent_ancestor`) and the motor path (winner-take-all `best_a` in
`neuromorphic_engine.py`) locates the real bottleneck: **organisms convert almost none of the
available food into energy.** The reflex is present (bias→move, RAM-byte→consume/stop) but
(i) motor arbitration is winner-take-all, so the always-on forward drive makes organisms *skate
over* food rather than linger and consume; (ii) landing on a `0x55` cell does **not** itself feed
(`neuromorphic_engine.py:441` excludes `0x55` from the move-and-absorb path) — eating requires a
*separate* CONSUME action to win on the following tick while stationary on the byte; and (iii) the
oversized seed buffer keeps the energy sensor saturated, so the energy→reproduce drive dominates
and the population breeds to the cap and starves rather than foraging. Net: **no population has
ever been food-self-sustaining; all observed life runs on birth-buffers plus Ark resurrection.**
Making a single organism net-positive by foraging — before scaling populations or rebalancing the
wider economy — is the true next milestone (Roadmap P2).

A first attempt at that milestone — retuning the seeded reflex (`create_intelligent_ancestor`:
gentler search drift, decisive halt-and-consume on contact, weaker reproduce drive) while keeping
deliberate CONSUME — was **necessary but insufficient**: survival and the energy trajectory were
essentially unchanged. A follow-up saturating-food test (Ark off, 10k buffer) is decisive: raising
supply to ~100% substrate density (5000 bytes/tick) roughly **doubles survival (31 → 58 ticks) and
triples late energy**, confirming organisms *do* forage and respond to food — yet they **still go
extinct with energy declining**. Even on a complete carpet of food the population cannot break
even. This falsifies both the food-supply and the reflex-tuning hypotheses and localises the wall
to the **eat-gain-per-meal vs metabolic-burn economy**, plus a foraging-bandwidth limit (realised
intake sits well below the ~1-meal-per-2-ticks ceiling the winner-take-all motor allows). The next
lever is the arbitrary `CYCLES_PER_EAT_GAIN = 1024` vs honest per-cycle burn ratio (Roadmap P4)
and/or a food-seeking gradient sense to raise encounter rate (Rules 5/10).

**Economy-rebalance sweep (`tests/eat_gain_sweep.py`, Ark off, 10k buffer, meal-value env-tunable
via `GENESIS_EAT_GAIN`).** Raising the meal value closes the loop: at **4096 (4× default) on a food
carpet, the first self-sustaining population in the project's history appears** — energy *climbs*
(29k → 116k → 182k), population holds (~299), and it survives the full horizon with the Ark OFF
(`SUSTAIN=True`). The transition sits between 1024 (dies at ~59 ticks) and 4096 (lives). Higher
values widen the survivable food density: at 16384 the carpet population pins at the 600 cap, and at
65536 even *moderate* density (100 bytes/tick) self-sustains. This confirms the wall was the
eat-gain/burn economy and that it is crossable. **Caveat (Rules 7/10):** large meal-values are *too*
lush — energy runs away to the cap with no selective margin, the opposite failure. The principled
target is a *modest* meal-value at *moderate* food density — a regime where organisms survive only
by foraging well — so that a food-seeking sense (Rules 5/10) and efficiency (Rule 7) become
thermodynamic necessities rather than luxuries. The default `CYCLES_PER_EAT_GAIN` remains 1024
(unchanged); the sweep used the env override only. **[Correction 2026-07-11: the code default was
later raised to `15000` (`GENESIS_EAT_GAIN`), and the `books` economy sets `16`; the sentence above
reflects the state at the time of Exp 4.]**

**Food-seeking sense (added 2026-07-11; `neuromorphic_engine.sense`, `N_INPUT` 15→17).** To make
foraging a survival *skill* (Rule 10) rather than luck, two sensory inputs now report local food
(0x55) density in the ±16-byte window ahead vs behind the pointer (a nearby-memory scan charged 32
cycles/tick, Rule 17), and the seeded ancestor wires them to steer toward food (with a fix so
CONSUME still wins on contact). Result: under the current **uniform-random** food seeding this
yields **no survival advantage** — with food scattered evenly there is no spatial gradient to climb
(ahead ≈ behind), and at sparse density the ±16 window is usually empty, so the two channels carry
~no information while adding scan cost. The sense is mechanically correct (still self-sustains at
eat-gain 4096 on a carpet) but its value is contingent on **spatially-structured (patchy) food** —
exactly the environmental gradient Rule 10 calls for. Demonstrating that seeking beats blind drift
under patchy food at a modest meal-value is the next experiment.

## 🧪 Experiment 5 — Life by Reading: Energy from Solving Books (Rules 6/9/10)
**Objective:** Move the energy source from mindless food (0x55, which breeds mere survivors —
"weeds") to **solving the Books curriculum** — the Prime Directive's first rung: gain energy by
correctly reading a symbol, not by eating.

**Setup & fixes.** The engine already rewards reading (land on a printable ASCII symbol and
vocalize it), but three defects made it impossible: (i) the RAM byte was sensed as one analog
scalar while the vocal cords need 8 exact bits — so an 8-bit **reading eye** was added (`N_INPUT`
15→17→25; inputs 15–22 = the 8 bits of the byte under the pointer); (ii) no wiring mapped byte→
vocal, so an **echo reflex** was seeded (two max-weight copy synapses per bit, since one w=127 <
the v_rest+128 threshold); (iii) the read reward only fired on movement and checked the
*destination* cell (predict-next-cell), so a **stationary "solve the symbol under the pointer"**
reward (partial credit = correct_bits − wrong_bits, gradient not cliff) replaced it, and the
redundant move-branch read was removed. Random scratchpad synapses were also kept off the vocal
outputs so noise cannot corrupt speech.

**Results (`tests/book_read_test.py`, Ark off, RAM flooded 90 % with A–Z, food effectively off at
`eat_gain=1`):**

| Read reward ×  | Survived / 800 | Final pop | Correct reads | Accuracy |
|---|---|---|---|---|
| 64  | 40   | 0   | 1,562  | 95 % |
| 128 | 116  | 0   | 3,987  | 95 % |
| **256** | **799 (full)** | **19** | **17,906** | 95 % |
| **512** | **799 (full)** | **167** | 18,422 | 96 % |

**Analysis.** With food removed, at a sufficient read reward a population **survives the entire run
fed purely by correctly reading book-symbols** — the first demonstration in this project of energy
earned by solving a cognitive task rather than by mindless consumption. Read accuracy is ~95 %
(clean 8-bit echo). **Honest limits:** (1) text is flooded at 90 % density, so organisms never have
to *seek* books — reducing density (so foraging-for-text becomes a navigational skill, reusing the
food-seeking sense) is the next step; (2) "reading" here is symbol **echo** (reading-aloud, rung 1),
not yet reasoning (e.g. `2+2=`→`4`); (3) the reader is a **seeded** Intelligent-Ancestor reflex
(Rule 5), a substrate for evolution to refine, not yet an evolved capability. The result proves the
economy *can* select for reading; making reading emerge and deepen up the curriculum is the
programme.

**Arithmetic frontier (echo vs computation).** A distinct **prediction** reward was added: on moving
onto a symbol, partial credit if the organism's vocalization matches the symbol it steps *onto* —
i.e. it *anticipated* the next symbol. On the Addition curriculum (contiguous `1+1=2` equations),
walking across `1+1=` and predicting the `2` requires *computing*, not echoing. Result
(`book_read_test.py … math`, food off): the seeded reader scores **147–187 correct echo reads
(reads the digits fine) but exactly 0 correct predictions** — no organism computes an answer. This
cleanly localises the Prime-Directive boundary: **literacy (symbol echo) is solved and can pay for
survival; reasoning (holding operands in working memory and computing) is unsolved and currently
zero.** The prediction reward now provides a selective gradient toward computation, but a
seeded copy-reflex has no working-memory/arithmetic circuit — those must *emerge* (evolved recurrent
structure), which is the open research programme, not a hand-wiring.

---

## 🧪 Experiment 6 — Live Book Economy: Reading as a Navigable Skill + Honest Compute (M1)
**Objective (Roadmap P0/M1):** make the LIVE `sim_loop` book economy *self-sustain* on reading — not
the 90 %-flood harness — with all costs derived from hardware, no game constants.

**Live-path crash (found + fixed).** The `GENESIS_ECONOMY=books` sim_loop had never actually run: the
book-restock check divided by `dynamic_lif_steps` one statement *before* it was assigned, so books
mode raised `UnboundLocalError` on tick 1 (food mode dodged it via `and` short-circuit). The test
harnesses reimplement the loop body, so they never exercised it — a live path can rot uncaught.

**Measured collapse (`tests/_m1_econ_probe.py`).** With the crash fixed, books still died at tick ~43:
`enc_frac ≈ 0.00` — organisms almost never stand on text. Text is injected as *contiguous passages*;
`seed_universe` spawns on empty cells scattered away from them; the seeking sense hunted `0x55` food
(near-absent in books). Income ≈ 0, pure seed-buffer burndown (~460/tick).

**Two structural fixes (skill, not flood).** (1) **Text-seeking** — in books mode the ahead/behind
seek-scan (`sense`, `SEEK_TEXT` baked from economy) targets printable symbols, so the ancestor's
existing `FOOD_AHEAD→JMP` wiring becomes a text-seeker for free. (2) **Born-in-library** —
`seed_universe` (books) spawns on empty cells with text within ±`FOOD_SCAN_RADIUS`. Together:
`enc_frac 0.00→0.38`, correct reads `0.3→55/tick`, predictions appear. Reading income now fires at
scale — but burn still exceeded it.

**Architecture-derived compute (the honest metabolism).** The dominant burn was the
`steps = GLOBAL_CYCLE_POOL/alive` pool — un-physical (an organism's burn depended on how many *others*
were alive) and a death-spiral. Replaced with **per-organism LIF steps = the organism's own
synapse-graph depth** (longest input→node path +1, computed at spawn). **Result:** efficiency
selection *emerges* — deep ancestors (mean depth 8) burn ~4× and are culled; the population selects
down to **depth-2 echo readers** carrying *high* energy (21–27 k, above seed). A cohort now lives
~700–1000 world-ticks on reading income (vs instant collapse), Rule 7 arising from physics with no
imposed step constant.

**Honest limit (still open).** Not yet full-population sustain: cohorts **spatially leak** — offspring
are born at the parent's drifting position and restocked passages land at random cells, so readers and
text diffuse apart over generations (`enc_frac` decays), shrinking the population to a small (~23)
stable reader pod before the Ark reseeds. The next levers are **spatial co-location** (restock near
the population / offspring born in the library) and a **reclaimed-compute read value** (derive the
read reward from RAM actually freed, retiring the `READ_SCALE` knob) — closing the loop without magic
multipliers.

---

## 🧪 Experiment 7 — Remove ALL Game Constants: One Derived Matter↔Energy Exchange (2026-07-11)

**Directive.** "All game constants must be removed." The economy still ran on invented numbers:
`CYCLES_PER_EAT_GAIN` (a food byte = 15,000 cycles from nowhere), `READ_REWARD_SCALE` (×64), a loose
`×8` per-bit read payout, and `SEED_ENERGY` (5,000/20,000). Each is "game design," not raw-hardware
physics.

**One derivation retires all four.** A RAM cell is an 8-bit register: it holds one of `2**8 = 256`
microstates. Its energy content = that capacity, `CELL_STATES = 2**BITS_PER_BYTE = 256`. Every
matter→energy event pays this one rate: **eating** a `0x55` cell reclaims the whole cell (`+256`);
**solving** a symbol reclaims the fraction of bits resolved (`+(net_bits/8)×256`, a gradient — Rule 10);
the abiogenesis **seed** is a founder's own footprint (genome+neurons+synapses) valued at
`CELL_STATES`/cell. No multipliers, no per-economy knobs, no `GENESIS_EAT_GAIN`/`READ_SCALE` env. Food
and text share one currency; reading can only out-earn grazing *emergently* (chained predictions +
dense text), never by a rigged payout.

**Measured (books, `_m1_econ_probe.py`), the honest arc:**
- **Exchange-rate-1 first attempt** (a byte pays its literal value, 0x55→85): **EXTINCT tick 2.** Face
  value (0–255) is far below per-tick burn — the old 15,000 was the hidden exchange rate all along.
- **CELL_STATES = 256, tiny seed (one cell):** still **EXTINCT tick 3** — 256 seed = ~1.6 ticks of
  runway (burn ~161/tick), founders die before navigating onto text (`corr/t = 0`), even at 61 %
  density. The blocker was seed, not the rate.
- **CELL_STATES + body-footprint seed (~57 k):** population **lives 550 ticks, reads well (peak 58
  correct/tick), and efficiency selects emergently — mean depth 7.65 → 2.0** (Rule 7 intact with zero
  magic). BUT `dE/t` is persistently **negative (~−150/tick)**: per-org reading income (~0.17 reads/tick
  × 256 ≈ 44) < per-tick burn (~161), so it **coasts down the seed and dies** — Exp-4 coast-collapse,
  now with literacy and no constant hiding it.

**What Exp 7 proves + exposes.** The game constants are gone; the physics is internally consistent
(every reward/seed traced to byte width). Removing the multiplier did NOT break reading or efficiency
selection — both survive on honest currency. It **exposed the true wall:** a full read (256) is less
than the **flat membrane burn** (`CYCLES_PER_NEURON_UPDATE × n_count` ≈ 125 for 44 neurons × depth).
That `1 cycle/neuron/step` is hardware-honest but **clock-driven, not the event-driven 20 W paradigm
(Rule 11)** — it charges idle neurons. The clean next lever (needs a design call) is an **activity-gated
membrane** (charge only neurons that spike, as STDP already is), which would let sparse reading pay for
a sparse brain and shift Rule 7 selection from "fewer neurons" to "fewer spikes." Food mode still runs
without error (smoke_test coasts on its own 250 k default seed, unaffected).

---

## 🧪 Experiment 8 — Event-Driven Membrane: The 20 W Paradigm Made Literal (2026-07-12)

**Directive.** "Do whatever it takes to reach the goal by modeling the human brain; amend the rules if
they contain errors." Exp 7 exposed the last clock-driven tax: the membrane charged `1 cycle × n_count`
**every step for every neuron, including idle ones**. That is not how a 20 W brain (or event-driven
neuromorphic silicon) works — its energy is dominated by the **action potential** (depolarise + restore
the ion gradient), while an unfired neuron draws ~nothing. The flat charge was a modelling error against
Rule 11, not honest physics.

**The fix (one line of physics).** Count action potentials per step (`n_spiked`) and charge the membrane
per **spike**, not per neuron: `total_atp += CYCLES_PER_NEURON_UPDATE × n_spiked`. Forward-prop (synapse
reads) and STDP were already spike-gated, so this makes the *entire* metabolism event-driven. No new
constant — the same `1 cycle` unit, now billed on the real energy event.

**Measured (books, `_m1_econ_probe.py`, `SEED_MODE=lib`, 9 % text density):**
- **Before (flat membrane, Exp 7):** coast-collapse, dead ~tick 550, `dE/t ≈ −150`.
- **After (spike-gated):** population **grows 300 → 358** (tick 75), **stabilises ~260, survives to
  tick ~1449** (2.6× longer) with births replacing deaths. Early epochs read **37–45 correct/tick** —
  reading is now **net-positive while on text**. Efficiency still selects (depth 8.5 → 2.0, Rule 7 intact
  on the new "fewer spikes" axis). Food mode unaffected (smoke_test final pop 358).

**What Exp 8 proves + exposes.** Event-driven metabolism flips the books economy from **terminal to
survivable** with zero tuning — an organism standing on text funds itself. It also cleanly exposes the
**next** wall, now a *different* mechanism: the kill is no longer burn but **`enc_frac → 0`** — the
colony drifts OFF the sparse static text into vacuum, reads nothing, and dies of starvation-in-the-desert.
Burn-limited → **encounter/seeking-limited** (Rule 10). Worse, spike-gating makes Rule 7 select *so* hard
for the cheap depth-2 echo reflex that it discards the deeper seek-and-halt skill: **cheap-drifter
out-reproduces competent-reader** because drifting isn't fatal *faster* than complexity is expensive.

**Spatial follow-ups (measured, 2026-07-12).** Two honest levers were tried against `enc_frac` collapse:
- **Offspring born in the library** (`find_birth_pos`, books mode): a child mallocs its body on a
  text-adjacent free cell near the parent, not scattered into vacuum. *Result: neutral* (~1449→1490
  ticks) — conceptually right and kept, but not the bottleneck.
- **Library regrows in place** (`regrow_passage`): reading is **destructive** (a solved byte → `0x00`),
  and the restocker was teleporting fresh pages to random cells — so the colony ate a vacuum hole
  around itself while its food reappeared across the ring. Regrowing the next passage *adjacent to
  existing text* (renew where grazed, like a field) **doubled mid-game read rate** (corr/t ~5–8 vs
  ~2–4) and encounter (~0.04 vs ~0.01). Kept in the live loop. *But over-concentrating (one contiguous
  shelf + 300 seeded organisms) causes crowding collapse* — so prestock stays scattered, only restock
  regrows.

**The deep wall is evolutionary, not spatial.** All three levers only *delay* the same end: the
population converges to **depth-2 echo-only reflexes that have lost the seek circuit**, then drifts off
text and starves. Root cause: the echo wiring is redundant (2 synapses/bit × 8 bits) but each **seek
synapse is singular**, so mutation erodes seeking far faster than echoing; and because founders are
*born on text*, seeking carries no immediate selective advantage to protect it. By the time a grazed-out
colony *needs* to navigate back to text, the trait is already gone. This is the genuine Rule 9 frontier —
**reading/foraging must be kept under continuous selection (or evolve), not seeded once and eroded** —
and it is orthogonal to the (now-fixed) metabolism. Verified: live books `sim_loop` runs clean with all
three changes (no crash, Ark-reseed cycles as before); food-mode `smoke_test` unaffected (final pop 358).

**Testing the mechanism + finding the real cap (2026-07-12).** Two further probes:
- **Redundant seek wiring** (2 synapses/direction, mirroring the redundant echo): *confirmed the
  mechanism* — `enc_frac` and read rate now hold ~2× longer (corr/t ~4–5 through tick 850 vs decaying to
  ~2), because seeking survives mutation like echoing does. Kept (honest, symmetric, improves survival);
  food mode unaffected (`smoke_test` pop 347). But collapse is only delayed, not stopped.
- **Density sweep** (9 % → 37 % text): the decisive result — **`enc_frac` stayed ~0.05 even at 37 %
  density** (4× the text barely moved encounter). The cap is NOT density: because reading is
  **destructive**, an organism is *always standing on the vacuum it just ate*, so encounter is capped by
  the rate of *stepping onto fresh unread text*, which a spread-out population cannot sustain. Mean energy
  bleeds because the ~95 % not-currently-on-fresh-text pay their spike cost with no income.

**Net.** Exp 8's metabolism fix is real and kept (terminal → survivable); the spatial + wiring levers are
honest improvements and kept. But full self-sustain is blocked by a **structural** property of the reading
model itself: destructive reading + sparse-spread population caps encounter income below break-even at any
tractable density. The next levers are genuine design decisions on the *reading model* — e.g. a "graze
along the line" head that reliably steps symbol-to-symbol (the type-3 prediction path, currently ~0), or a
non-destructive read with a different anti-farming rule (diminishing returns on re-reading) so a reader can
hold position — not another metabolism or placement tweak.

---

## 🧪 Experiment 9 — The Reading MODEL: Graze-Along-the-Line + Non-Destructive Read (2026-07-12)

**Hypothesis.** Exp 8 left a wall the docs called *structural*: destructive reading + a stationary
head means a reader is always standing on the vacuum it just ate, so `enc_frac` was capped ~0.05 at
**any** density. The fix is not more metabolism or placement — it is the *reading model itself*.

**Change (engine, `neuromorphic_engine.py`).** Reading is now a **saccade**. A successful decode
(`net>0`) advances the read head +1 onto the adjacent cell (forward, the direction text is laid
down), so a reader **walks the passage symbol-to-symbol** instead of freezing. That single move also
removes the need for destructive reading: the old byte-consume was purely an anti-farm hack ("don't
stand still spamming one char"), and the saccade makes it redundant — a rewarded read moves the head
*off* the cell, so re-reading it means walking the entire 65 536-cell ring back (never net-positive).
So reading is now **non-destructive**: a book is not burned by being read (brain-honest), a following
reader gets the same text (many students, one book), and the library is never strip-mined. **No new
constant** — the step is unit adjacency, the cost is the existing `CYCLES_PER_MOVE` (3), trivially
net-positive against a read (≤256). Only a real decode sweeps, so *walking the library requires
actually reading it* (Rule 9). This supersedes the Exp 7 "consume on attempt" anti-farm (§6.1).

**Measured (M1 econ probe, Ark OFF = terminal, library `English/01_Alphabet`).**

| metric | pre-graze (Exp 8) | graze, density 0.09 | graze, density 0.37 |
|---|---|---|---|
| `enc_frac` (on-text fraction) | ~0.05 (capped, density-invariant) | **0.70–0.76** sustained | **0.40–0.68** sustained |
| corr reads / tick | ~5 (collapsed) | ~130 sustained | ~120 sustained |
| `pred/t` (type-3 prediction) | ~0 | 4–16 | **up to 44** |
| library bytes | strip-mined | **intact (6016, never depletes)** | **intact (24 015)** |
| mean-energy trend (back half) | bleed to extinction | slow decline (transit-limited) | **RISING 42k→44k, dE/t > 0** |

- **The structural cap is gone.** `enc_frac` went from a density-invariant ~0.05 to 0.4–0.76 that
  *responds to the world* — readers now walk lines and stay on fresh text.
- **The prediction path came alive.** Type-3 "anticipate the next symbol" reads were ~0 for the whole
  project; grazing readers moving forward onto text they vocalized now log `pred/t` up to 44 — the
  real cognitive leap above reading-aloud, emergent, unrewarded by any special multiplier.
- **The wall is now density-TRACTABLE, not structural.** At 9 % density the colony still slowly
  declines (a grazer finishes a passage then crosses long vacuum to the next, earning nothing in
  transit — `enc_frac` ~0.5, the off-text half starves). At **37 % density the economy is net-positive**:
  mean energy *rises* 42k→44k over the back 600 ticks and `dE/t` is positive, the surviving population
  self-sustaining on reading income while settling to the library's carrying capacity (~165). The old
  cap was dead at *any* density; reading income now scales with text supply, as a real reading ecology
  should.
- **Efficiency still selected (Rule 7):** wrong reads `att/t` fall 100 → ~1 and depth trims 8.3 → 2.0
  as the population evolves clean, cheap reading.

**No regressions.** All three modules compile; food-mode `smoke_test` unaffected (pop 300 → 353, peak
368 — graze excludes `0x55`, food path untouched); the **live `sim_loop`** (GENESIS_ECONOMY=books)
runs crash-free through the graze path (reads active, no traceback). The live loop still mass-extincts,
but that is the *separate, pre-existing* Ark/deep-time collapse loop (Exp 4: monoculture reseed +
total-wipe), not the reading economy — which self-sustains in the honest Ark-OFF terminal probe.

**Net.** The books economy is no longer capped by a structural encounter dead-end. With graze +
non-destructive reading it is a genuine reading ecology: readers walk intact books, anticipate the
next symbol, and — given adequate text density — live and accumulate energy on reading income alone,
with efficiency and prediction both emerging from the physics. Remaining open: population-level
sustain at *low* density (passage-to-passage transit cost) and the orthogonal deep-time/Ark collapse.

---

## 🧪 Experiment 10 — Dissolving the Total-Wipe Oscillator + Autotelic Peer Prediction (2026-07-12)

Two changes attacking the Exp 4 deep-time collapse from opposite ends: **(A) a refugium** that
converts the instantaneous total wipe into a Rule-10 gradient, and **(B) a zero-sum peer-prediction
economy** — the first true-autotelic (Rule 9) energy source, where a survival problem arises from
agent–agent interaction rather than human curriculum. Both verified on the **live `sim_loop`**
(Live-Loop rule: measured on the real path, never a reimplemented harness).

**A. Refugium (Tier B, `genesis_lab.seed_refuge`).** Extinction was detected only at population 0,
which reseeded the whole world as 300 synchronised clones — the exact instantaneous total wipe Rule 10
forbids (it makes evolution a clockwork oscillator with discrete, non-overlapping eras). The refugium
tops the living population back up to a small floor from the hall-of-fame gene bank *before* it can
hit 0. The floor is **derived, not a game constant**: `len(fossil_pool)` — one living representative
per banked lineage (≤ `FOSSIL_POOL_MAX = 12`) — so the refuge expresses exactly the standing diversity
the Ark holds. Each germ is an independent fossil recombination (diverse, not monoculture) and pays
its own way at `SEED_ENERGY`, so it **softens death into a gradient, it does not clamp population or
guarantee survival** (Rule 5-clean: reintroduces genes, imposes no fitness).

**Measured (live loop, `GENESIS_ECONOMY=books`, 9 % density, `GENESIS_MAX_TICKS=120000`):**

| metric | Tier A baseline (6-era probe) | + refugium (Tier B) |
|---|---|---|
| total wipes (`MASS EXTINCTION`) | **6** by LIF ~96k | **0** through LIF 120k |
| collapse mode | 300→0 clockwork, synchronised | continuous gradient (`refuge_events=51`) |
| population continuity | discrete era resets | rolling pop, overlapping ages |
| `pool_top_ages` ratchet (Tier A) | held | held `[20332,19734,18538,…]` |

The clockwork total-wipe oscillator is **dissolved**: over a *longer* span than the baseline's 6
wipes, the refugium produced **zero** total extinctions and 51 soft gradient top-ups instead.

**Honest limit exposed.** The population rides *at* the floor (`pop=12`) in every tested config —
books 9 %, and even books at **37 % density** (`BOOK_TARGET_BYTES=24000`, Exp 9's self-sustaining
point): `pop=12, refuge_events=435, ext=0`. So Exp 9's 37 % net-positive result was **harness-only
(Ark-OFF, controlled)** and does **not** transfer to the live loop — the live spatial drift keeps the
economy net-negative at every density tried. The refugium does its scoped job (cliff → gradient) but
**does not, and should not, make a net-negative economy net-positive**; it is a safety net, not a
clamp (it only *adds* organisms below the floor, so a net-positive economy would grow past 12 and the
refuge would fall silent). Live-loop self-sustain remains the real orthogonal blocker.

**B. Peer prediction (autotelic, `GENESIS_PEER=1`, `neuromorphic_engine.world_tick_numba`).** An
organism that vocalises the byte a **neighbour** is emitting has predicted it (from the voice sensed
on inputs 4–6); it reclaims the matched bits' state-space `(net/8)×CELL_STATES` **from that
neighbour** — `energy[predictor] += g; energy[speaker] −= g`, clamped to the speaker's holdings.
**Zero-sum by construction ⇒ unfarmable** (no free energy is minted; you can only take what a
neighbour holds). The only way to earn is to out-model a neighbour and the only defence is to be
*unpredictable* — a Red-Queen arms race toward informative signalling (proto-language), with no
human-authored text and no imposed fitness. It **redistributes** energy (selects for communication)
rather than adding it (sustenance stays the reading/refugium economy's job). Compile-time gated, so
food/books pay nothing when off; `NUMBA_CACHE_DIR` keyed on it so kernels never collide.

**Measured (live loop, `GENESIS_ECONOMY=food GENESIS_PEER=1`):** peer-prediction events fire
continuously (`peer=50–332` per 5 s interval), crash-free, `ext=0`, energy conserved by construction
(logged as read-log type 4; dashboard "peer" events). **Wiring verified; emergence not.** Whether the
arms race actually grows a communication code is unproven — it needs a net-positive economy plus many
generations of evolution to show, i.e. it is gated behind the same live-sustain blocker above. This
is the **first Rule-9 agent–agent survival problem** in the substrate (Roadmap P3), a foundation, not
a demonstrated language.

**No regressions.** Both modules `py_compile` clean; peer path is dead-code-eliminated when off;
refugium changes only the extinction path (the Live-Loop-Test-Gap harnesses never call `sim_loop`).
The default `food` economy now also survives as a gradient (`ext=0`) instead of clockwork wiping.

---

## 🧪 Experiment 11 — The Live Economy Goes Net-Positive: Contiguity Was the Lever (2026-07-12)

Exp 10 left one blocker: the live `sim_loop` was net-negative at every density, so the colony rode
the refuge floor (`pop=12`) while Exp 9's net-positive reading was "harness-only". This experiment
**closes that blocker** — the live loop now sustains a full colony on reading income alone — and the
root cause turned out to be neither the exchange rate nor reproduction, but **world structure**.

**The hunt (measured, `tests/_m1_econ_probe.py` + throwaway `/tmp` division probes).**
1. *Not an energy shortage.* On-text organisms sit **rich** (40–60k energy, `ATP_MAX`=1M). The colony
   declines while mean energy is roughly conserved — marginal organisms die, a fat core persists.
2. *Not encounter-by-density.* Raising text density 37 %→76 % made decline **worse** (300→105 vs
   300→153), not better — more text just means more mis-reads (net-negative reads) and crowding.
3. *Reproduction looked throttled* (native `OUT_REPRODUCE` rarely wins winner-take-all: ~0.3
   births/epoch while ~280/300 organisms could afford it — a classic Tierra non-breeder trap). But
   forcing energy-triggered cell-division **boom-busts to extinction**: non-destructive reading (Exp 9)
   made text infinite food, so there is *no carrying-capacity brake* and any division mechanic
   converts the seed buffer into an overshoot → collapse.
4. *The honest mitosis threshold never fires.* At `2 × body-energy` (2 × footprint × `CELL_STATES`,
   the derived cost of building a second body) **no organism ever qualifies** — they coast 59k→17k,
   net-*negative*. So reproduction was never the bind; **income < burn** was.

**Cause: "confetti" library.** A reading organism saccades +1 symbol-to-symbol along text it decodes
(Exp 9). The library was many short passages (the 52-byte alphabet file, tiled at random anchors), so
a reader walks to the **end of a fragment and steps into vacuum**, earning nothing while it crosses
the gap to the next fragment. Half the colony is thus always in transit (`enc_frac`~0.5), and that
**idle off-text burn — not the exchange rate — is what kept the economy net-negative at every
density.** Readers could not out-earn the gaps.

**Fix: one contiguous scroll (pure world structure, no reward change).** `inject_contiguous_library`
lays the *same bytes* as a single continuous scroll pinned at a fixed centred start (restocked in
place). A saccading reader almost never leaves the text: `enc_frac` **0.5 → 0.98**. Reading income
finally exceeds metabolism and the colony grows on reading alone (native reproduction) to carrying
capacity. Arguably *more* faithful to reading an actual book (continuous lines) than word-confetti.

**Two supporting fixes surfaced by the hunt:**
- **Event-driven sensing (Rule 11, same principle as the Exp 8 membrane fix).** The old flat
  `2*FOOD_SCAN_RADIUS` (=32 cycles/tick, ~40 % of the metabolic floor) charged every organism every
  tick *including* the ~50 % of ticks spent off-text — a clock-driven von-Neumann tax that also
  **double-charged** (the seeking sense's only job is to drive input neurons 23–24, already billed
  per-spike by the event-driven membrane). Removed (not retuned): survivor economy flips coast-down →
  break-even.
- **On-text seeding (the live-only bug).** `seed_universe` / `seed_refuge` required `g_ram[p]==0x00`
  to place an organism — a food-economy holdover ("don't spawn on food you'd instantly eat"). A solid
  scroll has **no interior `0x00` cells**, so that rule pushed the entire cohort off the scroll into
  vacuum where it starved. This is why the *probe* (which places organisms directly on the block)
  thrived at 600 while the first *live* run still hit floor-12. Placement now keys on org-grid
  **occupancy** (stand ON the page and read it), not the byte beneath — the real constraint.

**Measured (live `sim_loop`, Live-Loop rule — the real path, not a harness):**

| config | before (Exp 10) | after (Exp 11) |
|---|---|---|
| books, 37 % (`TARGET=24000`), ~117k ticks | `pop=12`, `refuge≈435`, net-negative | **`pop=596–600/600`, `refuge=0`, `ext=0`** |
| books, 9 % (`TARGET=6000`), ~80k ticks | `pop=12` (floor) | **`pop=591–600/600`, `refuge=0`, `ext=0`** |

`refuge=0` is the headline: the safety net **never fires** because the colony sustains itself. Exp 9's
net-positive reading now **transfers to the live loop**. Density was never the variable — the scroll is
a fixed block regardless of the surrounding vacuum; **contiguity was the lever.**

**Honest limits.**
- *Reproduction path.* Growth here rides the engine's native `OUT_REPRODUCE`, which fires once
  organisms are genuinely net-positive. Custom energy-triggered division was tested and **shelved** —
  without a carrying-capacity brake it overshoots. The chosen crowd-cost regulator (Rule 11/13) works
  in-probe but is **held**, not shipped: contiguity + native reproduction produces no overshoot to
  brake, and crowd cost only thinned a healthy 600-colony to ~43 with no benefit at `enc`=0.98.
- *Carrying capacity = the org array cap (600), not a food limit.* Non-destructive reading means the
  scroll is infinite food, so population is space-limited. A real food-scarcity carrying capacity
  (below the array cap) is future work if a logistic ceiling is wanted.
- *Peer prediction is incompatible for now.* Under the thriving colony, `GENESIS_PEER=1` **collapses
  it back to floor-12**: zero-sum predation drains victims faster than the arms race evolves a defence,
  culling the population before defensive signalling can emerge. Peer is default-OFF (opt-in), so the
  shipped net-positive economy is unaffected — but the Rule-9 autotelic layer now needs either a
  gentler (non-lethal) predation coupling or a much larger sustained population before it can run
  without extinguishing its own substrate. Recorded, not yet solved.

---

## 3. Open Questions (Not Yet Demonstrated)
Honest gaps between the engine's *capacity* and demonstrated *emergence*:
- **Learning efficacy:** STDP + Lamarckian memory are implemented, but we have not yet
  measured that they *improve survival on a task* over a non-learning control.
- **Communication/logic:** vocal cords, neighbour hearing and the Oracle channel exist, but
  no unsupervised language or logic-gate emergence has been measured on this engine.
- **Efficiency selection (Rule 7):** the per-cycle physics now select *for* leaner brains
  strongly and emergently (Experiment 3), but selection for efficiency *at equal capability*
  is still unproven because capability itself is unmeasured. `elite_iq` remains
  observation-only by design (wiring it into selection would violate Rule 5/9).
- **Autotelic end-state (Rule 9):** food/oracle/curriculum are still human-supplied
  scaffolds. **First agent-generated survival problem now exists** — zero-sum peer prediction
  (Exp 10B), where organisms earn by out-modelling neighbours, no human text. Wiring verified;
  emergence of a communication code unproven (gated behind live-loop self-sustain).
- **Deep-time robustness (Rules 10/14):** the Exp 4 clockwork loop is structurally dissolved
  — the `max_ark_age` freeze is fixed (2026-07-10), the fossil pool ratchets as a hall-of-fame
  (Tier A), and the **instantaneous total wipe is replaced by a refugium gradient** (Exp 10A:
  `ext` 6→0, continuous rolling population). **The economy beneath it is now net-positive too**
  (Exp 11): with a contiguous library the live loop sustains `pop=596–600/600` with `refuge=0`,
  `ext=0` at both 9 % and 37 % density — the population no longer rides the refuge floor. What
  remains open on top of a sustaining economy: (a) does the colony *ascend* (rising `elite_age`/
  capability) over long deep time, not merely persist; (b) a food-scarcity carrying capacity below
  the 600 array cap, if a logistic ceiling is wanted; (c) a peer-prediction coupling that does not
  extinguish its own substrate (Exp 11 found `GENESIS_PEER=1` collapses the thriving colony).

## 6. Critical Audit Fixes (2026-07-11)
A rigorous architectural review identified and fixed three critical engine flaws that compromised open-ended evolution:
1. **Infinite Reading Money:** The stationary reading reward did not consume the byte unless the read was a perfect match, allowing organisms to stand still and farm partial-credit energy forever without foraging. Originally fixed by consuming the byte on *any* vocalization attempt. **Superseded by Exp 9 (2026-07-12):** the graze-along-the-line saccade advances the head off the cell on every rewarded read, so re-reading requires walking the whole 65 536-cell ring — the movement *is* the anti-farm, and reading is now non-destructive (the byte-consume was removed). Same guarantee (no standing-still farm), but the library is no longer strip-mined.
2. **Hidden Neuron Ablation Bug:** A fragile boundary check in `count_genes` meant that any organism allocated past the start of the RAM heap counted zero genes. This meant all late-born organisms were spawned with zero hidden neurons, effectively crippling them.
3. **Viscosity Bloat Ratchet:** The computational viscosity formula penalised synaptic *density* (synapses/neuron) rather than hardware footprint. This perverse incentive rewarded organisms that bloated with idle, disconnected neurons to lower their density. Viscosity is now strictly driven by total footprint `(neurons + synapses)`.

## 4. Conclusion
The current neuromorphic engine is a working substrate: genome-encoded SNNs learn in-lifetime,
reproduce with heritable topology **and** partially-heritable learned weights, and are held in
bounded population dynamics by a thermodynamic compute budget. The Exp 4 deep-time collapse loop
is now **structurally dismantled**: the fossil-pool freeze is fixed, the pool ratchets as a
hall-of-fame (Tier A), and the instantaneous total wipe is replaced by a **refugium gradient**
(Exp 10A — `ext` 6→0, continuous rolling population, contra the old clockwork). A first
**agent-generated survival problem** (zero-sum peer prediction, Exp 10B) provides a Rule-9
autotelic pressure with no human curriculum. **The layer beneath the oscillator is now solved too**
(Exp 11): the live economy is **net-positive** — with a contiguous library instead of scattered
passages, `enc_frac` rises 0.5→0.98, reading income exceeds metabolism, and the live loop sustains a
full `596–600/600` colony with the refugium never firing (`refuge=0`, `ext=0`) at both tested
densities. Exp 9's reading economy now transfers to the live path; the root cause was world structure
(confetti transit gaps), not the exchange rate. The frontier moves up the stack: from *"can the
colony survive?"* (yes) to **"does it ascend?"** — whether capability/`elite_age` rises over long deep
time on a sustaining substrate, and whether the peer arms race can run without a lethal-predation
coupling that collapses its own population (Exp 11's open peer finding). Those are the next research
questions in `Roadmap.md`.
