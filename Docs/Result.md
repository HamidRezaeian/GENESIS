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

## 🧪 Experiment 12 — Does It Ascend? The Information Economy & the Curriculum Cliff (2026-07-13)

Exp 11 closed the survival question (`pop=596–600/600`, `refuge=0`). The frontier became **"does it
*ascend*?"** — does capability *rise* over deep time, or does the colony merely persist? This
experiment measured that directly, found the answer was **no**, diagnosed why, fixed the economic
root cause, and uncovered the *next* blocker. It is a chain of five honest live measurements.

### 12.1 Measurement: the sustaining colony does NOT ascend — it decays
Running the Exp 11 economy (echo-read, books 9 %) for ~413k live ticks and watching the *capability*
signals, not just population:

| signal | early (t≈14k) | late (t≈413k) | trend |
|---|---|---|---|
| population | 598 | 600 | flat — survives |
| `reads` (symbols solved/interval) | ~265 | ~175 | flat/declining |
| `pred` (next-symbol *anticipated*) | 2–5 | **0 after t≈62k** | **died** |
| `Universe N` (total synapses = brain size) | 25 918 | 23 929 | **−1 989 (−7.7 %)** |

The colony **survives without ascending**. Worse, it *regresses*: the brain **sheds synapses** and the
one genuinely cognitive signal — *prediction* (anticipating the next symbol, which for "1+1=" means
*computing* "2", not echoing) — **goes extinct by tick ~62k**. Survival was solved by a trivial reflex,
so Rule-7 efficiency selection then ground the brain *down*. Capability is not selected, so it erodes.

### 12.2 Root cause: echo-reading pays for information the organism already holds
The reward named the byte **under** the pointer. But that byte is fed directly onto the reading eye
(`sense_buf` inputs `RAM_BIT0_INPUT..+7`) — the organism **already senses it**. Emitting it back is a
zero-surprise **bit-copy** (Shannon information *gained* = 0). Paying a full cell's state-space for a
copy is a free lunch a one-neuron identity reflex farms forever; there is no reason to evolve anything
harder. **This is why prediction died and the brain shrank.**

### 12.3 Fix: pay for surprise, not for copying (the information economy)
Reward only information the organism does **not** already sense — the **next** cell it is about to
step onto (`pos+1`), which is on *no* sensory input, so naming its bits requires *computing* the
sequence. Same exchange rate (`(net/8) × CELL_STATES`), same graze-along-the-line saccade, same
non-destructive contiguous scroll — but the step is now **earned by prediction**. Echo (naming the
sensed cell) pays nothing. **No new constant**: echo simply resolves 0 surprise → 0 energy. Capability
*becomes* the economy, so selection should climb comprehension by construction (Rules 6/9).
(`neuromorphic_engine.py`, the stationary-read block.)

### 12.4 The curriculum cliff (Rule 10, measured across three texts)
Shipping that economy on the old default `01_Alphabet` **collapsed the colony**: `pop → 12` (refuge
floor), `reads = 0`. Pure prediction with no bootstrap is a **cliff**, not a gradient — a cold-start
population of random genomes cannot predict anything, earns nothing, and starves. The cause is the
*curriculum*, not the economy:

| curriculum | structure | result |
|---|---|---|
| `01_Alphabet` `A B C …` | letter/space alternation, **no two adjacent like symbols** | **cliff** — `pop=12`, `reads=0` |
| `03_Phrases` (prose) | few repeats | **cliff** — `pop=12`, `reads=0` |
| `00_Runs` `AAAA…BBBB…` | 10-char runs | **sustains** — `pop≈597`, `reads>0` |

The runs case proves the economy is sound: on a run, "next symbol = current symbol", so a trivial echo
reflex is *already a correct predictor* — it seeds prediction income, and the colony lives. The
repeat-free texts simply give a random genome **no foothold** to start climbing. `01_Alphabet` is
nearly adversarial for prediction (`A`=`01000001` → next is space `00100000`, *zero shared bits*, so
even partial credit is negative).

### 12.5 The graded curriculum: survival + capability retention, but still no ascent
`00_Graded` lays a **difficulty ramp** (run-length `10→5→3→2→1`, ending in pure succession), tiled so
an easy runs-base always exists while a shrinking-run frontier demands progressively real
sequence-modeling — Rule 10 gradient, now in the *text*. Live (~400k ticks, books 9 %):

| signal | Exp 11 echo | Exp 12 graded (predict) |
|---|---|---|
| population | 596–600 | **596–600, `refuge=0`** (survival restored) |
| `pred` | dies to 0 by t≈62k | **stays alive, 0–10** (never dies) |
| `Universe N` | −1 989 (sheds) | **flat ~24 500** (brain held) |
| `reads` over deep time | flat | early 78 → **late 58 (drifts down)** |

The information economy + graded bootstrap is a **strictly better substrate**: survival restored,
prediction kept *alive* instead of extinct, brain no longer shed. But it **still does not ascend** —
`reads` drifts *down* and `pred` shows no upward trend over 400k ticks.

### 12.6 The real ascent blocker: abundance removes the pressure to climb
Diagnosis (measured, not guessed): 600 organisms on a 6000-byte scroll is ~10 % density — **90 % of
the substrate is empty**. Easy runs-text is *plentiful*, so nothing forces an organism up the
difficulty ramp: it cruises the easy regions, eats freely, and never needs to crack the hard
succession frontier. Efficiency selection then *trims* capability (`reads` 78→58) because the easy
text does not require it. **The gradient exists in the text; the *pressure* to climb it does not.**
Ascent therefore requires **scarcity/competition** — a carrying capacity where the easy text cannot
feed the whole population, so solving harder symbols becomes the only way to eat. That couples to the
already-open "food-scarcity carrying capacity below the 600 array cap" item, now revealed as the load-
bearing lever for ascension rather than a mere logistic nicety.

### 12.7 Scarcity attempts: why the obvious levers fail (measured)
Given the abundance diagnosis, three constant-free ways to add selective pressure were tried live.
**All failed, each for a principled reason** — a useful set of negative results that fences the design:

| lever | config | result | why |
|---|---|---|---|
| higher density (crowding) | `00_Graded`, 33 % density | `pop=600`, `reads`~85 flat, `pred`~0 | the *existing* event-driven crowding cost (denser → sensor-2 spikes → per-spike charge) is too weak to force the climb; a **flat** crowding charge is disallowed — it is exactly the von-Neumann scan tax retired in §12.3/Exp 11 (Rule 11) |
| spatial scarcity (small easy nursery + large hard frontier) | `00_Frontier`, 30 % density | **cliff** — `pop=12`, `reads=0` | the graze-along-the-line saccade means an organism **cannot camp** easy text — it walks forward off the short nursery straight into the hard `ABCD` frontier, mispredicts, stalls, and starves at the boundary (the Exp 11 transit-starvation, now at a difficulty wall) |

The through-line: **non-destructive reading is an infinite resource, so there is no carrying capacity
and no competition** — and every simple way to impose one collides with a core constraint. Making easy
text geometrically scarce fails because the saccade-walker is *forced through* the difficulty wall
rather than able to shelter behind abundance; adding a flat crowding/foraging cost fails because it
re-imposes the clock-driven tax that Rule 11 (event-driven metabolism) forbids; and making reading
destructive (the classic carrying-capacity source) would re-open the transit-starvation the contiguous
scroll was built to solve (Exp 11) and needs a regeneration-rate constant. Ascent therefore needs a
carrying-capacity mechanism that is **(a)** wall-free (compatible with the saccade-walk), **(b)**
event-driven (no flat tax), and **(c)** constant-free. The leading candidate was
**competition for finite per-tick information** — the Shannon content of a passage is finite *per
instant* (a book teaches many students over *time*, not infinite value in one tick), so co-located
readers *split* the predictable income (`1/n`, a derived fraction, no constant), which should make
dense easy regions pay less per organism and disperse lineages onto the uncontested hard frontier
without any wall. **It was built and tested (Exp 13) — and it fails**, for a reason that turns out to
be decisive for the whole text-scarcity programme (below).

**Net of Exp 12:** the economy was made information-honest (retiring the echo free-lunch that
*prevented* ascent), the curriculum was made a proper easy→hard gradient (retiring the cold-start
cliff), survival and capability-retention were restored, and the true remaining blocker was isolated
and fenced — **not** the economy or the curriculum, but the **absence of a carrying capacity** under
infinite (non-destructive) reading, with the obvious scarcity levers ruled out by measurement. Ascent
is now *possible* on this substrate; making it *happen* needs a wall-free, event-driven, constant-free
competition mechanism — most likely finite per-tick information split among co-located readers.

---

## 🧪 Experiment 13 — Text Cannot Be Made Scarce: Ascent Must Route Through Peer Competition (2026-07-13)

The finite-per-tick-information split (Exp 12.7's leading candidate) was implemented: the prediction
reward divided by `crowd_count` (organisms in the ±16 sensory neighbourhood — already computed for the
crowding sense), so co-located readers share a region's instantaneous predictable information. Live on
`00_Graded` it **collapsed the colony** (`pop → 12`, `reads = 0`) — it strangled the bootstrap.

But the failure is deeper than a magnitude problem, and it is **decisive**. Reading in this engine is
**spatially exclusive** (one organism per cell, `org_grid`) and each reader predicts **its own** next
cell (`pos+1`). Two organisms 10 cells apart are reading *different symbols* — they do **not** contend
for the same information. So dividing by the ±16 neighbour count is **not** honest shared-resource
competition; it is a **crowding tax in disguise**, and because it scales *earned* income it falls
hardest on the dense bootstrap phase, killing the seed. The *honest* version — split only among
organisms reading the **same target cell** — is `n = 1` almost always (exclusive occupancy), so it
**never triggers** and the economy stays infinite.

That is the crux. Across Exp 12.7 + Exp 13, **every** constant-free, wall-free, event-driven attempt to
impose a carrying capacity on the reading economy has failed, and now for a *structural* reason, not a
tuning one:

> **Non-destructive, spatially-exclusive, saccade-walked text reading is intrinsically an infinite,
> uncontested resource.** There is nothing to compete over — each organism reads its own cell forever,
> and the book is never consumed. A carrying capacity cannot be imposed without relaxing one of the
> load-bearing constraints (non-destructiveness → transit-starvation + a regen constant; exclusive
> per-cell reading → a different reading model; or the no-game-constant rule → a tuned crowding/
> depletion magnitude).

**The only genuinely scarce, contested resource already in the system is *peer prediction*** — modelling
what a **neighbour** emits is zero-sum (`GENESIS_PEER`, §2.5): the information the predictor gains is
information the predicted organism *loses*, it is bounded by that neighbour's holdings, and it is
inherently contested. That is a real carrying capacity with no curriculum and no imposed constant. The
catch is the one Exp 11 already found: zero-sum peer prediction is **lethal** (it drains victims to
death faster than a defence evolves, collapsing the colony). So the honest architecture that falls out
of Exp 12–13 is a **division of labour**: the *text* economy's job is **survival** (bootstrap literacy,
now solved), and the *peer* economy's job is **ascent** (an agent–agent arms race toward better
world-models and proto-language, Rule 9) — provided its coupling can be made **non-lethal**. Ascent
therefore routes through fixing peer prediction, **not** through text scarcity, which is now shown to be
structurally impossible under the current reading model. (The non-lethal peer coupling has its own
zero-sum-vs-farmable tension and is a design decision, not yet built.)

---

## 🧪 Experiment 14 — Non-Lethal Peer Coupling: The Autotelic Layer Runs Without Self-Extinguishing (2026-07-13)

Exp 13 concluded ascent must route through peer competition, blocked only by its lethality (Exp 11:
`GENESIS_PEER=1` collapses a thriving colony 600→12). This experiment removes that lethality with a
**derived, constant-free floor** and measures the result live.

**The coupling.** Un-floored peer prediction drained a neighbour's *capital* (clamped only to holdings),
so many predators killed a predictable prey before an unpredictability defence could evolve. The fix:
peer predation may skim only the speaker's **surplus above its body-subsistence** — its footprint
(neurons + synapses) valued at `CELL_STATES`, the *same derived quantity as the abiogenesis seed* (the
matter the organism is built from). A predator can rob a rich rival's growth capital but can **never**
starve it below the cost of its own body. Still zero-sum, still unfarmable (energy flows only on a real
prediction); the Red-Queen race is now over **reproductive surplus, not survival**. No new constant.

**Result (live, `00_Graded`, `GENESIS_PEER=1`, ~456k ticks):**

| signal | early (t≈67k) | late (t≈450k) | reading |
|---|---|---|---|
| population | 596 | **600, `refuge=0`, `ext=0`** | **survives** (Exp 11 collapsed to 12 here) |
| `peer` (neighbour predictions/interval) | 13–21 | **~135 (plateau)** | arms race ramps, then equilibrates |
| `reads` (text solves/interval) | ~110 | **~28** | text economy **cannibalised** by peer |
| `Universe N` | 25 579 | 25 140 | flat |

**Two honest halves.** The **win**: the non-lethal floor *works* — the autotelic agent–agent economy now
**runs on a surviving colony** (Exp 11's peer-collapse blocker is resolved), and the population
**self-organises** away from reading text toward predicting each other (`peer` 21→135, `reads` 110→28) —
a real, unforced behavioural adaptation. The **limit**: it **plateaus, it does not ascend** — `peer`
settles at ~135 and `Universe N` stays flat over 300k ticks; the Red-Queen race reaches an *equilibrium*
rather than spiralling up. We first suspected the equilibrium was **degenerate** — a low-energy state
emitting a shared, low-information code — but **Exp 15 measured this directly and *falsified* it**: the
peer channel carries ~3.8 bits over ~19 distinct signals (richer than the reading channel), stable to
3 M ticks. The true reason capability does not rise is that peer prediction is **spatially confounded
with reading** (a neighbour's vocal byte is guessable from the predictor's own reading eye), so the task
is solvable without modelling the other agent. It sustains, but it is not yet an escalating ladder of
world-models. **See Exp 15 for the measurement and the corrected ascent lever.**

**Net of Exp 14:** the peer economy is now **safe to run** (default-OFF is retained because it does not
improve the reading economy — it replaces it), and the last structural blocker to *running* an autotelic
arms race is cleared. What is still missing for **ascent** is an **escalation** pressure: the plateau
shows a non-lethal zero-sum race equilibrates without capability rising. Exp 15 then measured *why* and
corrected the design: it is **not** a degenerate code (signals are already ~3.8 bits) — the race stalls
because peer prediction is **solvable from shared text** without modelling the other agent. The corrected
next step is therefore **(b′): decouple the peer target from the predictor's own sensory field** (predict
a neighbour's *future* signal / *hidden-state*-driven action, not its current shared-text read), so
out-modelling a *mind* becomes the only way to win — see Exp 15.

---

## 🧪 Experiment 15 — Observation-Only Signal-Diversity Probe: The Plateau Is Not a Degenerate Code (2026-07-13)

Exp 14 left the peer plateau with a *guess*: that the Red-Queen race equilibrates at a **degenerate,
low-information code** (everyone hovers at the subsistence floor emitting one cheap symbol they all
trivially predict). This experiment **measures** that guess instead of assuming it — the disciplined
step before building an escalation coupling on an unverified diagnosis.

**The probe (Rule 9↔6, never wired to selection).** Each 5 s telemetry window computes the Shannon
entropy (bits) of the distribution of vocal bytes in two channels, straight off the already-drained
`read_log`: `Hpeer` over the bytes that *won* peer predictions, `Hread` over the bytes that solved a
comprehension read, each with its distinct-symbol count `nd`. Pure telemetry — printed only, never fed
into energy / reproduction / selection. Degenerate-code hypothesis ⇒ `Hpeer → ~0`, `nd` tiny. Rich /
escalating code ⇒ `Hpeer` high (ceiling `log2(alphabet)`).

**Result (live, `00_Graded`, `GENESIS_PEER=1`, run to ~3.1 M ticks — ~7× deeper than Exp 14):**

| signal | early (t≈93k) | late (t≈3.1M) | reading |
|---|---|---|---|
| population | 599 | 600, `ext=0`, `refuge=0` | fully sustains across deep time |
| `Universe N` | 25 198 | 25 103 | brain **dead-flat** (no growth, no shedding) |
| `peer` / interval | 100 | 100 | **plateau** — no upward trend over 3 M ticks |
| **`Hpeer` / `nd`** | **3.76 / 18** | **3.95 / 20** | **HIGH diversity, rock-stable** |
| `Hread` / `nd` | 1.22 / 8 | 1.30 / 8 | low (reads dominated by the long-run curriculum letters) |

**The hypothesis is FALSIFIED.** The peer channel is *not* a collapsed one-symbol code — it carries
**~3.8 bits over ~19 distinct signals**, sustained flat across 3 million ticks, and is *more* diverse
than the reading channel that feeds it (`Hpeer` ≈ 3.8 ≫ `Hread` ≈ 1.4). The plateau is not "everyone
says one thing."

**So why does capability stay flat with diverse signals?** Because the diversity is **inherited from
the text substrate, not invented by the agents**. An organism vocalises its reading-prediction of the
*next cell of the graded scroll*; neighbours are scattered across that same scroll, so their
vocalisations span the alphabet — which is exactly the ~3.8 bits we measure. Crucially, a predictor and
the neighbour it robs read **overlapping / spatially-correlated patches of the same text**, so the
neighbour's vocal byte is largely guessable **from the predictor's own reading eye** — no model of the
*other agent* is required. Peer prediction here is spatially confounded with reading: it is **solvable
locally**, which is why `peer` volume and `Universe N` both flatline. Rich signals, trivial task.

**This redirects the ascent design.** Exp 14's proposed lever (b) — "reward *informative* signalling
over a constant one" — is now **mis-targeted**: the signals are *already* informative (3.8 bits). Adding
a diversity incentive rewards what already exists and would not lift capability. The measured blocker is
different and sharper: **peer prediction is too easy because it rides shared text.** Ascent needs the
prediction target to be something the predictor **cannot already sense** — e.g. a neighbour's *next /
future* vocalisation, or an action driven by that neighbour's *hidden internal state* / a *distant* text
region — forcing a model of the other agent (theory-of-mind) rather than a re-read of shared substrate.
That is the corrected next design step: **decouple the peer target from the predictor's own sensory
field**, so out-modelling a *mind* — not re-reading a *page* — becomes the only way to win.

---

## 🧪 Experiment 16 — Theory-of-Mind Coupling (b′): Predict the Neighbour's *Change*, Not Its Echo (2026-07-13)

Exp 15 localised the plateau's cause: peer prediction was **spatially confounded with reading** (a
neighbour's byte is guessable from the predictor's own eye), so it demanded no model of the other agent.
This experiment builds the corrected lever **(b′): score the peer prediction the same way Exp 12 fixed
reading — pay only for *surprise*.**

**The coupling (no new constant, zero-sum, non-lethal retained).** Each tick, freeze the incoming
vocalisations into `vocal_prev` (the t−1 emissions — what an organism actually *sensed*). Peer
prediction is then scored against the neighbour's **fresh** emission (`vocal_cords`, t), but **only on
the bits that changed** since t−1: a bit that did not change was predictable by echoing the sensed voice
(zero surprise → pays 0); only correctly **anticipating a changed bit** earns. Winning therefore
requires modelling where the neighbour's state is *heading*, not re-reading the shared page. Same
exchange rate, same body-subsistence floor (Exp 14).

**A reading-killer, caught and reverted.** The first build *also* switched the neighbour-voice sense to
read `vocal_prev` (to stop an organism sensing a neighbour's fresh byte and echoing it). Measured live,
that **collapsed the whole colony** to the refuge floor (`pop=12`, `reads=0`) — the altered sensory
distribution destroyed the reading bootstrap. An isolation run (revert the sense change, keep the
surprise-scoring) **restored survival**, confirming the sense change alone was the culprit. Kept the
live neighbour-voice sense: it is only a 3-input *compressed* voice (not the clean 8-bit reading eye),
so echoing it precisely is lossy and the shortcut it would open is weak.

**Result (live, `00_Graded`, `GENESIS_PEER=1`, surprise-scoring, live sense, to ~1.9 M ticks):**

| t | population | `Universe N` | `peer` |
|---|---|---|---|
| 47k | 588 | 26 273 | 0 |
| 244k | 599 | 26 095 | 8 |
| 578k | 504 | 21 851 | 28 |
| 833k | 420 | 18 250 | 45 |
| 1.24M | 344 | 14 945 | 10 |
| **1.9M** | **282 (level)** | **12 400 (level)** | 9–75 |

**It sustains, but it does NOT ascend — it re-equilibrates *smaller*.** The colony slowly bleeds from
`pop≈600 / N≈26k` to a **lower stable plateau** (`pop≈282 / N≈12.4k`, brain **halved**), `refuge=0`,
`ext=0` throughout — a new equilibrium, not extinction. The surprise-scoring is correct by construction
(it strips the text confound and demands theory-of-mind), but on this substrate it **starves**: the
graded curriculum is built from **long same-letter runs** (needed for the *reading* bootstrap), so a
neighbour's signal seldom changes tick-to-tick — the anticipatable-change events are rare, `peer` income
stays 0–45, and it cannot fund the brain against Rule-7 efficiency shedding. So capability settles lower.

**The lesson — the two economies want opposite substrate statistics.** Reading-bootstrap wants **long,
predictable runs** (so a proto-reader can earn while learning); peer-ascent wants **frequent signal
change** (so anticipating a mind is a rich, recurring income). On graded text, (b′) honestly removes the
confounded income and correctly finds there is little genuine theory-of-mind signal left to earn — the
neighbours are *too predictable*. **The blocker moved from the coupling to the substrate.** (b′) is the
right coupling; it now needs a substrate (or a peer-target) whose signal genuinely varies — e.g. a
non-run text for the peer channel, or coupling the peer target to a neighbour's *hidden internal state*
rather than its (long-run, low-change) reading output. That is the next design step. Peer remains
**default-OFF**; the shipped reading economy (peer-OFF) was re-verified sustaining (`pop=599/600`,
`N≈25.8k`, `reads≈110`, `refuge=0`) with all Exp 16 shared-code changes in place.

---

## 🧪 Experiment 17 — The Shared-Substrate Branch Is Closed: Reading and Peer Want Incompatible Text (2026-07-13)

Exp 16 diagnosed the (b′) plateau as a **substrate** problem (graded runs too static for the peer
channel) and offered two next steps: (2) a higher-change substrate, or (1) a decoupled hidden-state peer
target. This experiment **tests branch (2) directly** — feed the working (b′) coupling a higher-change
book — with zero code change (new book + `GENESIS_BOOK_NAME`), and measures whether reading survives.

**Two candidate substrates, both measured live (`GENESIS_PEER=1`, ~0.7 M ticks each):**

| book | structure | reading | verdict |
|---|---|---|---|
| `00_Graded` (control) | 78 % long runs (10→5→3→2) + short succession | **sustains** (Exp 15/16) | peer STARVES |
| `00_Churn` | 29 % run-head + long `ABCDEFGHIJ` succession body | **cliffs cold** (`pop=12`, `reads=0`) | reading dies |
| `00_Churn2` | strong run-10 head + uniform run-2 body (`AABB…`) | **cliffs cold** (`pop=12`, `reads=0`) | reading dies |

**Result: the shared-scroll branch is empirically closed.** Reading sustains **only** on long low-change
runs — the moment the substrate carries frequent change (succession, or even run-length 2), the
saccade-walker hits a mispredicted transition every ~1–2 cells, income falls below subsistence, and the
colony cliffs to the refuge floor before it can bootstrap. But long low-change runs are *exactly* what
starves the peer channel (Exp 16). The two economies make **opposite, incompatible demands on the same
bytes**: reading wants long predictable runs, peer wants frequent change. No single shared reading/peer
text can satisfy both.

**Consequence — ascent must decouple the peer target from the reading text.** Branches (2) [high-change
shared substrate] is now closed alongside Exp 13's [text scarcity] and Exp 15's [the confound is real].
The only remaining route is **(1): the peer signal must be a separate observable derived from a
neighbour's *hidden internal state* (e.g. its next action / movement / energy trend), not its reading
output** — a channel that can be high-change without touching the reading scroll's run structure. That
is a genuine new mechanism (a distinct, constant-free, hidden-but-modellable prediction target), and the
clear next build. The failed diagnostic books were removed; `00_Graded` remains the default.

---

## 🧪 Experiment 18 — Branch (1) Built: Hidden-Action Peer Target Sustains and Ignites Income, but Does Not Ascend (2026-07-13)

Exp 17 closed every shared-scroll branch and named the only route left: decouple the peer target from
the reading text to a neighbour's **hidden internal state**. This experiment **builds that route** and
measures it live.

**Design (no new constant).** The peer target is decoupled from the shared scroll to the neighbour's
**hidden motor action** — the action `best_a ∈ {0..5}` it *decided* this tick (jump ±1, jump ±10,
consume, reproduce), one-hot encoded as `1<<best_a`. This channel is (a) **hidden** — an organism's
chosen action is on no sensory input of any neighbour and depends on that neighbour's own
energy/brain/occupancy, so it cannot be read off the shared scroll (kills the Exp 15 confound); and
(b) **high-change** — an action flips far more often than a long text run (attacks the Exp 16
starvation). The predictor emits its guess through its existing `org_char_val` vocal byte (a dedicated
output channel is impossible — growing `N_IO` remaps every saved genome via `dst % n_c`). Scoring is
**surprise-gated** (paid only when the neighbour's action actually *changed*, `action_now != action_prev`)
and **precision-graded** (Rule 10): reward = `1/s_bits / BITS_PER_BYTE * CELL_STATES` where `s_bits` =
set-bit count of the guess byte — a clean single-bit correct prediction earns the full `CELL_STATES/8`,
a busy text byte that merely happens to include the right bit earns a diluted fraction, so a genuine
modeller out-earns accidental overlap up to `s_bits`-fold along a climbable slope. Non-lethal floor
retained (drain a neighbour only above its body-subsistence `(neurons+synapses)×CELL_STATES`).

**Result (live, `GENESIS_PEER=1`, 1.84 M ticks):**

| metric | value | verdict |
|---|---|---|
| population | 569–600/600, `ext=0 refuge=0` | **SUSTAINS** (no collapse, no refuge dependence) |
| peer income | `peer=1–44` (was ≈0 in Exp 16) | **IGNITES** — beats the Exp 16 starvation |
| reading | unharmed alongside peer | economy division of labour intact |
| `Universe N` | 26340 → ~24600 (**−6.6 %**), then levels ~24500 | brain shrinks slightly then plateaus |
| `Hpeer` | ≈`0.00/nd1` (occasional `1.37/nd3`) | **monomorphic** — thin single-action code |

**Diagnosis — the plateau MOVED, it did not lift.** Decoupling the target from text (branch 1) was
**necessary** (it removed both the Exp 15 confound and the Exp 16 starvation — income finally ignites)
but **insufficient for ascent**. The hidden action is *itself* low-entropy in a reading monoculture:
every organism saccades/jumps along the scroll, so the dominant action is nearly always the same
forward-jump, and the peer channel collapses onto a thin monomorphic "predict-the-jump" code
(`Hpeer≈0/nd1`). There is almost no *behavioural diversity to model*, so anticipating a neighbour never
becomes a rich, escalating skill — capability never climbs. **The blocker moved from
confound/starvation (Exp 15/16) to LOW TARGET ENTROPY**: a theory-of-mind economy can only ascend if
the minds it models are behaviourally diverse.

**Consequence — the next lever is Red-Queen behavioural diversity (unbuilt).** For the action channel
to carry rising information, the *prey* must be rewarded for being **unpredictable** (an
anti-prediction / evasion income), so a predator's improving model is met by an evolving policy rather
than a fixed monoculture. That co-evolutionary pressure is what would pump action entropy up and give
the peer channel something worth climbing. Peer remains **default-OFF**; the shipped reading economy
(peer-OFF) was re-verified with all Exp 18 shared-code changes in place — no regression (`pop=591–600`,
reading healthy, `Universe N≈25.2k` stable, `ext=0 refuge=0`).

---

## 🧪 Experiment 19 — Red-Queen Prey Defence: Rewarding Unpredictability Does Not Ascend, and Corrects the Exp 18 Diagnosis (2026-07-13)

Exp 18 named the next lever: pay the **prey** for being unpredictable so the predator's improving
model meets an evolving policy (a Red-Queen arms race that pumps action entropy). This experiment
**builds and A/B-tests that lever** — and returns a clean negative that reframes the whole frontier.

**Design (no new constant, non-lethal, default-OFF).** A new compile-time flag `GENESIS_REDQUEEN`
adds the *prey half* of the peer duel inside the existing peer block. When a predictor emits a **clean
single-bit wager** (`s_bits == 1` = a committed bet on exactly one action) and the neighbour took a
**different** changed action, the mispredicted prey **reclaims the predictor's stake** (zero-sum:
`energy[prey] += g`, `energy[failed_predictor] -= g`). The stake is the *same* per-bit rate a correct
clean wager would have won (`CELL_STATES/BITS_PER_BYTE`), so winning and losing a one-bit bet are
symmetric. It is **unfarmable by construction** — a predator can only lose by wagering, and a
mis-wagering predator is selected against, so no free energy is minted and no stable collusion pays.
Non-lethal: capped at the predator's surplus above *its own* body-subsistence floor. Gated to clean
single-bit wagers so a busy multi-bit reading byte is never treated as a confident guess (reading is
never penalised). A new **observation-only `Hact` probe** (Rules 9↔6, never selects) reads the live
motor-action distribution straight from `action_now` — the exact quantity the ascent thesis is about.

**Result (live A/B, books economy, matched windows):**

| metric | peer-only (Exp 18) | peer + Red-Queen | verdict |
|---|---|---|---|
| population | 593–600/600, `ext=0 refuge=0` | 592–600/600, `ext=0 refuge=0` | **both SUSTAIN** (Red-Queen no regression) |
| `Universe N` | 26360 → ~24100, slow decay then level | 26337 → ~25130, slow decay then level | **neither ASCENDS** |
| mean `Hact` | **1.82**/nd6 | **1.75**/nd6 | Red-Queen **does not raise** action entropy — equal-or-lower |
| evasion income | — | `evade≈42` per 100 k ticks (thin) | mechanism ignites but too weak to shift selection |
| peer income | ignites in bursts, thins to 0 | same | `peer→0` in **both** by ~25–40 k (Exp 18 plateau, not a Red-Queen effect) |

**Diagnosis — the Exp 18 premise was a measurement artifact.** Exp 18 read "low target entropy" off
`Hpeer≈0/nd1` and concluded the actions were *monomorphic*. The direct `Hact` probe shows they are
**not**: the living action distribution is `nd6` (all ~6 actions in play), `Hact≈1.8`. The `Hpeer≈0/nd1`
measured only the entropy of *winning peer predictions* — monomorphic because only the **modal** action
(the dominant saccade/jump) is predictable *enough to monetize*, while the other five are already
present but too **noisy** to model profitably. So behavioural diversity was never the shortage.
Rewarding *more* unpredictability therefore cannot help — and empirically does not (`Hact` if anything
dips 1.82→1.75): adding noise to an already-noisy policy makes it **less** modelable, not more. The
evasion channel also stayed thin because the precision-graded predator income lets a predator earn from
busy multi-bit bytes **without ever committing** a clean single-bit wager, so predators simply dodge the
penalty and the duel goes quiet rather than escalating.

**Consequence — the frontier is redirected (branch CLOSED).** Ascent does **not** route through
raw unpredictability. The load-bearing insight: a theory-of-mind economy climbs only when the target is
**structured, complex, and *modelable* — predictable-in-principle but hard to compute** — not when it is
merely high-entropy. Red-Queen maximises the wrong quantity (surprise), when what selection needs is
*compressible complexity* the predictor is rewarded for learning to compute (e.g. a target that is a
deterministic **function of the neighbour's history/state**, so out-modelling it is a real, climbable
skill). Red-Queen is kept **default-OFF** (compile-time DCE'd when off; the peer-OFF reading economy is
byte-identical and was re-verified healthy — `pop=596–599`, `Universe N≈26.2k` stable, `ext=0 refuge=0`).
The `Hact` probe is retained: it is the honest action-entropy metric that exposed the artifact. Branches
now closed: text-scarcity (13), degenerate-code (15), high-change-substrate (17), raw-unpredictability (19).

---

## 🧪 Experiment 20 — Cognitive-Complexity Curriculum: Minds Bootstrap Then Camp the Easy Band, Never Climbing Into Computation (2026-07-14)

Exp 19 redirected the frontier from *raw surprise* to **compressible complexity** — a target that is
*predictable-in-principle but hard to compute*. This experiment tests that directly on the **reading**
economy (peer-independent), the first-principles form of the redirect: instead of ramping difficulty by
**run-length** (every prior curriculum, incl. `00_Graded` — even its hardest run=1 cycle is reflex-solvable
by a memorised lookup, no symbol's value must be *computed*), ramp **cognitive complexity** so that
predicting the next symbol progressively demands **computation over prior context** held in the SNN's own
recurrent state.

**Design (`Books/generate_ascent.py` → `00_Ascent.txt`; world structure only, no new constant).** One
monotonic 6000-glyph scroll matching `BOOK_TARGET_BYTES` (so the engine lays it in a single pass, no
tiling-induced easy→hard resets), difficulty rising **once, end to end**, in four **compressible** stages
(each a small rule that *generalises* across the stage, so learning the rule out-earns memorising the loop):
`bootstrap` 55 % (long shrinking A–J runs — the Exp 12/17 cold-ignition foothold) → `successor` 20 %
(cyclic +1) → `carry` 12 % (two-digit counting 00–99 = working memory over a cell) → `arithmetic` 13 %
(`a+b=c` mod 10 = compute over held operands, `=`→digit is bit-distant so echo scores badly — only
computing earns). Reading pays for predicting the **unsensed pos+1** (Exp 12) and an organism senses only
the current cell, so a correct next-symbol in the computational bands can *only* come from a mind carrying
context. **First iteration cliffed cold** (a short book tiled 5× left ~77 % of the standing scroll as hard
tail → `pop=12, reads=0`, the known cold cliff); rebuilt as the single bootstrap-dominant scroll above,
which ignites.

**Instrument — the ascent-frontier probe (`genesis_lab.py`, observation-only, Rules 9↔6, NEVER selects).**
Aggregate telemetry (`Universe N`) cannot see a *small advancing frontier*. The probe buckets every live
organism's scroll offset into the four stage bands + off-scroll and prints `frontier b/s/c/a/off` plus mean
offset %. **Where the colony lives on a monotonic-difficulty scroll = the difficulty it can sustain**, and a
rightward drift over deep time would be ascent *into computation*.

**Result (live, `GENESIS_BOOK_NAME=00_Ascent`, ~150 k ticks):**

| metric | value | verdict |
|---|---|---|
| population | 587–600/600, `ext=0 refuge=0` | **SUSTAINS** — bootstrap ignites, no cliff, no regression |
| `frontier b/s/c/a/off` | starts `536/37/8/18/1` → settles **`~597/3/0/0/0`** | **collapses INTO the bootstrap band** |
| mean offset | pinned at **~53 %** (the bootstrap→successor boundary) | colony piles at the boundary, **never crosses** |
| computational bands (carry/arith) | `0/0` after ~30 k ticks, stable 100 k+ | **permanently empty** — no mind ever climbs in |
| `Universe N` | 26.3 k → ~24.7 k then level | usual decay-then-plateau; no ascent |

**Diagnosis — this is the Exp 13 abundance wall, now proven on the *difficulty* axis.** The colony
bootstraps in the run-length head and *stays there*: the few organisms that spawn in the computational
bands **die** (can't read computation → can't earn → starve), and **nobody ever climbs in from the easy
end**. The reason is structural and identical to Exp 13: the easy band (3300 uncontested cells, reading is
non-destructive + spatially exclusive, the saccade-walker cannot camp but the *band* never runs out) is an
**infinite uncontested resource for 600 organisms**, so there is **zero selective pressure to cross into the
hard frontier** — grazing the easy band forever strictly beats starving at the boundary. Making text
*harder further along* does not force computation when the easy end is inexhaustible. A monotonic difficulty
scroll without scarcity is just a difficulty *option*, and evolution correctly declines it.

**Consequence — reading cannot self-generate ascent pressure (branch CLOSED), which re-derives Exp 13's
verdict from a new direction.** Exp 13 proved text cannot be made *quantitatively* scarce (non-destructive +
exclusive + walkable = infinite resource); Exp 20 proves it cannot be made *qualitatively* scarce either —
adding a hard frontier does not create carrying-capacity pressure toward it while an easy frontier remains.
**Both roads dead-end at the same wall: a single-agent reading economy has no scarcity, so it has no
ascent.** This *reconfirms the standing structural conclusion* — **ascent must route through PEER**
(agent–agent prediction is the only zero-sum, genuinely scarce resource) — and sharpens the peer target: it
must be **compressible complexity** (Exp 19), i.e. a deterministic function of a neighbour's private
history/state that is predictable-in-principle but hard to compute, so out-modelling it is a real climbable
skill *and* the loser genuinely loses a scarce resource. `00_Ascent` + the frontier probe are kept as
reusable instruments (the probe is the honest measure of *where on a difficulty ramp* a colony lives). The
default reading economy (`00_Graded`, peer-OFF) was re-verified with all Exp 20 shared-code changes in place
over ~3 M ticks — no regression (`pop=539–561`, reading healthy, `Universe N≈22 k` stable, `ext=0 refuge=0`).
Branches now closed: text-scarcity (13), degenerate-code (15), high-change-substrate (17),
raw-unpredictability (19), **complexity-without-scarcity (20)**.

---

## 🧪 Experiment 21 — The Peer-Target Design Space Is Exhausted on This Substrate: Behavioral Expression, Not the Coupling, Is the Ceiling (2026-07-14, design-space result)

Exps 15–20 converged on a precise specification for the ascent lever: a **peer** target (the only scarce
resource, Exp 13/20) that is **compressible complexity** (Exp 19) — a deterministic function of a
neighbour's *private* state that is predictable-in-principle but hard to compute, decoupled from the shared
text (Exp 15/17), with dense income (Exp 16) and no reflex ceiling (Exp 18). This experiment attacks that
specification **as a design problem before any build**, using an adversarial design-and-refute panel (five
independent target proposals from divergent seed angles — future-action, running-aggregate, future-position,
energy-trend, iterated-map — each then attacked by independent scarcity/confound and depth/constant-free
refutation lenses instructed to default to *refuted* under uncertainty).

**Result: all five candidate targets are FATAL — unanimous, every one reducing to branch 18.** The
proposals were concrete and clever (a k-step displacement integral, a hidden action-history shift register,
an action-kicked LFSR map, a stall-pattern positional wager). Each refutation is independent, yet they
converge on **one root cause**, which is the actual finding of the experiment:

**The data-processing inequality caps theory-of-mind at the action-stream's own entropy — measured at
`Hact ≈ 1.8 bits` (Exp 19), hard-ceilinged by `N_OUTPUT = 6`.** Any deterministic function of a neighbour's
hidden state — a shift register, an integral, an LFSR, an aggregate — can carry *at most*
`I(model; action-stream)` bits of predictable-but-hard content. Since the ultimate source is a 6-way motor
argmax (`log2(6) = 2.58` bits absolute ceiling, ~1.8 realised), every proposed target merely **re-encrypts
the same low-entropy stream**; none *co-evolves new complexity*. Three structural traps make this concrete,
and every design hit at least one:

1. **Width ≠ depth.** A shift-register / sliding-window target stores N past events *in parallel* — N
   independent Exp-18 reflexes, not an N-deep computation. Predicting bit *k* never requires first solving
   bits `0..k-1` (they are frozen past events, not an unrolled chain). "Each older bit needs one more step of
   forward-simulation" is dominated by "remember the newest parity and replay it into the deeper slots" — a
   bounded-state reflex at exactly the Exp-18 ceiling.
2. **Monoculture erases the variance to model.** In the only regime the colony *survives* (reading
   monoculture on low-change text), all private states converge, so any deterministic function of them is
   monomorphic across the population → "bet the population mode" is a zero-model reflex. The only regime with
   real cross-agent variance (heterogeneous competence / hard text) is the one the colony **cannot survive
   in** (the Exp 17/20 incompatibility wall). Scarcity of *energy* is not scarcity of *skill*: unbounded
   predictors can all correctly bet the mode, so the task has no carrying capacity (branch 20).
3. **The `net>0` reward gate is farmable.** Against a target that is pseudorandom w.r.t. any emission,
   `E[net⁺] > 0` for a *constant-byte* reflex → a dense, free, zero-sum skim with no modelling, which
   reproduces the "sustains-but-never-ascends" pattern exactly. Making the score symmetric to remove the
   lottery instead zeroes expected channel income and starves peer-specialists (Exp-16 bleed). Both horns
   are fatal.

**Diagnosis — the ceiling is the behavioral-expression bandwidth, not the peer coupling.** All 21
experiments unify here: peer prediction *is* the right scarce channel, but **you cannot model a mind richer
than that mind can act**, and a GENESIS organism's entire expressible behavior is a 6-way motor argmax plus
an 8-bit vocal byte. There is no room for a deep policy to *express* depth, so there is nothing deep to
predict. The lever was never a cleverer target function; it is **widening what an organism can express** so
that behavior *can* carry open-ended information.

**Sharpening — supply vs. demand (the fork for the next build).** A crucial nuance the panel did not
resolve: Exp 19 measured `Hact ≈ 1.8` with all six actions present (`nd6`) but *skewed* — the colony is
**not saturating the ~2.58 bits it already has**. So the ceiling may be a **demand** problem (no task
rewards diverse behavior — the reading monoculture funnels everyone to forward-saccade) rather than a
**supply** problem (too few action bits). If demand-limited, simply *adding* action bits (widening
`N_OUTPUT`) supplies unused capacity and will not help; the lever is a task/environment that **demands** rich
behavior. If supply-limited, the repertoire itself must grow. Distinguishing these is a cheap, pre-build live
probe (does `Hact` climb toward 2.58 under an environment that pays for behavioral diversity?), and it gates
which substrate change is worth the genome-decode risk. **No engine change was made this experiment** — it is
a design-space negative that redirects the frontier from *"what should peers predict?"* (exhausted) to
*"how can an organism's behavior become worth predicting?"* Candidate substrate levers (unbuilt, a genuine
fork): (a) widen/compositionalise the action space; (b) a structured/stigmergic environment where agents
build open-ended artifacts in RAM and peers predict what a neighbour *built*, not its motor bits. Branches
now closed: text-scarcity (13), degenerate-code (15), high-change-substrate (17), raw-unpredictability (19),
complexity-without-scarcity (20), **peer-target-on-6-action-substrate (21)**.

---

## 🧪 Experiment 22 — Grounding the Ceiling: The Action Distribution Collapses to a Single Monetized Action (2026-07-14)

Exp 21 concluded — from a scalar (`Hact ≈ 1.8`) plus theory — that behavioral expression, not the peer
coupling, is the ascent ceiling, and left a **supply-vs-demand** fork open: is `Hact` low because the
repertoire is too small (supply) or because no task rewards diversity (demand)? This experiment **measures it
directly** rather than inferring it.

**Instrument (`GENESIS_ACTPROBE`, compile-time, observation-only, Rules 9↔6, NEVER selects).** A default-OFF
flag records each organism's decided `best_a` into `action_now` even on the peer-OFF path (the write is
dead-code-eliminated when off, so the verified default kernel stays byte-identical), and the 5 s telemetry
prints the full 6-way histogram `act fwd/bck/f10/b10/eat/rep` alongside `Hact`. This exposes **which**
actions live, not just the aggregate entropy.

**Result (live, books economy, peer-OFF and peer-ON, to equilibrium):**

| phase | distribution | `Hact` |
|---|---|---|
| reading, early (founder diversity) | `fwd 57%` → spreads, `eat` rising | climbs to **~2.2** |
| **reading, equilibrium** | **`eat 73–86%`**, all else starved | collapses to **~0.8–1.2** |
| peer-ON, early | `fwd 42%`, `bck 33%` | ~1.8 |
| **peer-ON, equilibrium** | **`fwd 88–95%`**, all else starved | collapses to **~0.35–0.6** |
| **`f10` / `b10` (jump ±10), both economies** | **~0 % throughout** | 2 of 6 actions structurally dead |

**Diagnosis — the ceiling is behavioral *collapse to the single monetized action*, sharper than either
horn of the Exp 21 fork.** Three empirical facts settle it:

1. **It is a demand problem, decisively — not supply.** Each economy pays for exactly one behavior, and the
   colony collapses onto *that one*: the reading economy monetises standing-and-reading, so it converges to
   an **`eat`-monoculture** (`eat` = the CONSUME action that the reading reward is scored through); the peer
   run, before peer income ignites, is a pure reading-forage race and converges to a **`fwd`-monoculture**.
   Different economies → different surviving action → the distribution is dictated by *what pays*, not by the
   repertoire size. Adding action bits (widening `N_OUTPUT`) would supply capacity the current single-reward
   economy has no reason to use. **Confirmed: `Hact` is demand-limited.**
2. **The transient fooled the scalar.** Early ticks show `Hact ≈ 2.2` (near the `log2 6 = 2.58` ceiling) —
   but that is founder-cohort diversity *burning off*, not sustained richness. By equilibrium `Hact` falls to
   ~0.5–1.2. The Exp 19/21 figure of ~1.8 was a *time-average across that decay*; the **equilibrium** entropy
   the peer economy actually has to model is even lower (~0.5–1.0). This makes the Exp 21 ceiling argument
   *stronger*, not weaker: the action stream a theory-of-mind economy must predict is nearly monomorphic at
   steady state.
3. **Two of six actions are structurally dead.** `f10`/`b10` (jump ±10) never exceed noise in either economy
   — the saccade-walker never needs a long jump. The *effective* repertoire is ~4, and at equilibrium ~1.

**Consequence — the fork is resolved and re-pointed.** The lever is **not** widening the action space (supply)
— that adds unused capacity to a single-reward economy. The lever is **creating demand for behavioral
diversity**: an economy where *different behaviors pay off for different organisms*, so the population cannot
collapse onto one monetized action. This is the same conclusion the whole arc keeps reaching from new angles
— **ascent needs a niche structure / division of labour**, not a richer actuator — and it now has direct
per-action evidence. The two candidate substrate levers from Exp 21 are re-ranked by this: **(b) a structured
/ stigmergic environment** (agents build and consume open-ended RAM artifacts, so what pays depends on what
others built → endogenous niches → sustained behavioral diversity → a peer target with real entropy to model)
is favoured over **(a) widening the action space** (pure supply, which this experiment shows would not lift
the equilibrium). A minimal build-time test of (b): does introducing a *second, orthogonal* energy source
(one that pays a DIFFERENT action than reading) split the population into two behavioral niches and hold
`Hact` up at equilibrium? That is the next concrete experiment. **No selection pressure was added this
experiment** — `GENESIS_ACTPROBE` is pure telemetry; the default economy (probe OFF) is byte-identical and
was re-verified (`pop` healthy, `Universe N` stable, `ext=0 refuge=0`). Instruments retained:
`GENESIS_ACTPROBE` (the honest per-action measure). Branches now closed: text-scarcity (13),
degenerate-code (15), high-change-substrate (17), raw-unpredictability (19), complexity-without-scarcity (20),
peer-target-on-6-action-substrate (21); **supply-hypothesis eliminated, demand/niche-structure confirmed as
the lever (22)**.

---

## 🧪 Experiment 23 — A Second Energy Niche Lifts Action Entropy, but a Passive Lattice Does Not Recruit the Targeted Jump Gait (2026-07-14, partial)

Exp 22 concluded the ascent lever is **demand for behavioral diversity** — an economy where different
behaviors pay different organisms, so the colony cannot collapse onto one monetized action. This experiment
runs the minimal build-time test: add a **second, orthogonal energy niche** and ask whether it (i) holds
`Hact` up at equilibrium (the demand prediction) and (ii) recruits the two dead actions Exp 22 found
(`f10`/`b10` = jump ±10).

**Design (`GENESIS_NICHE`, default-OFF, no new constant, pure driver change).** In niche mode the ambient
`0x55` food (same total amount) is stocked **only on a stride-`LONG_JUMP_STRIDE` lattice** (`idx %
LONG_JUMP_STRIDE == 0`), where `LONG_JUMP_STRIDE = 10` is the *same* distance the `OUT_JMP_*_10` actuator
already moves (the literal `10` in the jump code was named into this constant so the lattice **derives** from
the actuator, not a tuned stride). The intent: a meal is reachable meal-to-meal by exactly the jump-10
action, while a `+1`-drift walker starves crossing the empty cells between lattice points → jump-10 becomes
the efficient foraging gait → a forager niche distinct from the readers. This is a Python-driver change (food
placement only), so the njit kernel is untouched and the default (niche OFF) economy is byte-identical.

**Result (live, books, `GENESIS_ACTPROBE`, matched food rate for the control):**

| condition | equilibrium distribution | `Hact` (equilibrium) |
|---|---|---|
| niche ON, food 0.1 (default rate) | `eat 85%` monoculture, `b10` **revived 8–9%** (from ~0) | ~0.8 |
| niche ON, food 20 (viable niche) | `fwd ~50%` + `bck ~25–40%` + reading, coexisting | **~1.6–1.8** |
| **control: uniform food 20 (niche OFF)** | **`bck 73–80%` monoculture** | **~1.0–1.1** |

**Two findings, one positive and one negative — reported honestly:**

1. **POSITIVE — a second niche lifts `Hact` (the demand prediction holds).** At matched food rate (20), the
   lattice sustains a **two-mode** locomotion equilibrium (`fwd`+`bck` coexisting, `Hact ≈ 1.7`), whereas
   uniform food of the same magnitude collapses to a **single-action** `bck`-monoculture (`Hact ≈ 1.1`).
   Spatial structure in *where* energy sits does hold action entropy up — direct support for Exp 22's
   demand/niche thesis, and the first intervention in the arc that *raises* equilibrium `Hact` rather than
   watching it collapse.
2. **NEGATIVE — the passive lattice does not recruit the *targeted* jump actions.** `f10`/`b10` stayed dead
   (~0–9 %); the added diversity came from `fwd`+`bck`, not the jump gait the lattice was designed to reward.
   The mechanism is too weak: stride-10 spacing does **not** *force* a jump, because a `+1`/`−1` drifter still
   lands on lattice cells by ordinary walking (and back-drift `bck` sweeps them just as well), so evolution
   never needs the long jump. Passive spacing creates *an option*, not a *requirement* — the same
   "option ≠ pressure" failure the reading-difficulty ramp hit in Exp 20, now on the foraging axis.

**Diagnosis + next step.** The demand thesis is *confirmed in direction* (niche structure ⇒ higher `Hact`)
but the specific instrument under-delivered: a **passive** resource lattice is walk-reachable, so it recruits
generic locomotion, not the intended specialised gait, and `Hact ≈ 1.7` is still a locomotion mix (two
actions), not the open-ended behavioral diversity a theory-of-mind economy needs. To force a *specific* gait
the niche must make the drift gaits **fail** — e.g. lattice cells that only *yield* to an arrival by a
long-jump (a gap the `+1` walker cannot cross because the intervening cells cost energy with no reward, an
Exp-13-style true barrier rather than a spacing preference), or a moving/refreshing lattice that outruns
drift. More fundamentally, this reinforces the Exp 21/22 conclusion that **generic action diversity is not
the same as *modelable* behavioral depth**: even a perfect two-niche split gives a peer predictor only a
1-bit "reader vs forager" label to model, not compressible complexity. The stronger route remains **(b)
stigmergy** — where the diversity is in open-ended *artifacts agents build*, not in a fixed menu of gaits —
and the lattice result is a useful down-payment: it proves spatial-demand structure moves `Hact`, so a richer
built-environment structure is worth the larger investment. `GENESIS_NICHE` + `GENESIS_FOOD_RATE` kept as
instruments (default-OFF / default-0.1); the default economy was re-verified byte-identical, no regression
(`pop` healthy, `ext=0 refuge=0`) after killing a rogue leftover sim that had cliffed an interim control via
CPU contention (the Exp-18 live-loop lesson, third recurrence — leftover sims are the standing hazard here).
Branches: passive-resource-lattice under-recruits the targeted gait (23, partial); demand/niche direction
still confirmed.

---

## 🧪 Experiment 24 — Stigmergy Design Space Names Two Walls; Bounding Reading Income Breaks Wall 1 and Forms a Carrying Capacity (2026-07-14)

Exp 22/23 pointed at a **stigmergic** substrate (agents build open-ended artifacts, so behavior expresses
with unbounded bandwidth and what-a-neighbour-built becomes a modelable peer target). This experiment first
**vets the stigmergy design space adversarially**, then acts on what the vetting reveals.

**Part A — stigmergy design vetting (workflow, 5 designs × 2 refutation lenses).** Five independent
stigmergy economies (pheromone trails, construct-consume, external-memory ledger, niche-construction,
minimal-write-action), each attacked by scarcity/collapse and depth/confound lenses. **All five FATAL,
0 survivors**, but — unlike Exp 21 — the failures converge on **two named walls**, and the critiques
collectively prescribe the escape:

- **WALL 1 — an infinite free resource dominates any authored economy (lessons 13/22).** Reading income is
  *minted* (`energy += net/8·CELL_STATES`, drawn from no cell) on a non-destructive 6000-cell scroll feeding
  ~600 orgs. Any *authored* cell that charges a royalty is strictly dominated by the free book sitting right
  there → consumers never switch → builders earn nothing → building is selected out. Structural and
  permanent, not a cold-start transient. **You cannot run a scarce authored economy beside an infinite free
  one.**
- **WALL 2 — the vocal byte is confounded with the shared text (lessons 15/17/21).** Every design reused
  `org_char_val` (the reading prediction) as the written/peer value. But peer-adjacency = reading-adjacency on
  a shared scroll: your neighbour stands on the cell you are about to read, so you predict its "authored" byte
  from your **own eye**, zero theory-of-mind; and one byte cannot be both slow reading-prediction (survival)
  and an independent register (building) — Exp 17 compressed into one byte. Plus a scoring lesson: **flat
  royalty is maximised by *predictability*, not depth** — a trivial `AAAA` run and a modelled hard cell both
  pay the reader `net=8`, so depth divides the reader pool without multiplying income; the economy selects
  *against* complexity (Exp 18/20 reflex ceiling re-derived).

**Part B — attack Wall 1 directly (the deeper enabler, live build).** Wall 1 has been the load-bearing
blocker since Exp 13; it is one falsifiable physics change, so it is built and measured rather than vetted.
`GENESIS_DEPLETE` (default-OFF, no new constant, compile-time gated → byte-identical when off) makes reading
**draw from a finite per-cell fuel reservoir** `read_fuel` (cap = `CELL_STATES` = the cell's own state-space)
instead of minting: a positive read pays out only `min(gain, read_fuel[cell])` and spends that fuel; the
driver regrows fuel by `GENESIS_DEPLETE_REGROW` per loop-iteration, capped at `CELL_STATES` (the renewal rate
= the sustained per-cell income ceiling). Income is no longer minted, so total reading energy per unit time
is bounded and a carrying capacity can form.

**Result (live sweep, books + `GENESIS_ACTPROBE`):**

| regrow / iter | outcome |
|---|---|
| 256 (≈unbounded) | bootstraps, rides ~590, occasional dips — barely binds |
| **128** | **carrying capacity forms** — pop **oscillates 400–598** (never pinned at cap), `Hact ≈ 1.2–2.5` (mean well above the 0.8 eat-monoculture baseline), reads compressed ~150→30–50, sustains 114 k+ ticks, no extinction |
| 64, 32 | cold-cliff (`pop=12, reads=0`) — the reservoir starves the founder bootstrap before ignition |

**Findings.**
1. **Wall 1 is real and breakable.** At regrow 128, bounding reading income does exactly what 13 experiments
   said was structurally impossible on the minted scroll: **population sits below the 600 cap and oscillates
   (boom–bust carrying-capacity dynamics)** instead of pinning at cap. The infinite-uncontested-resource wall
   is not a law of the substrate — it was a consequence of *minting*.
2. **Competition lifts behavioral diversity.** `Hact` at regrow 128 is the **highest sustained action
   entropy in the whole arc** (~1.2–2.5 vs ~0.8 eat-monoculture, ~1.7 niche) — scarcity for finite fuel makes
   different orgs do different things, direct further support for the Exp 22 demand thesis.
3. **Bootstrap vs. scarcity tension (the cost).** Tight bounds (regrow ≤ 64) cold-cliff: the founder cohort
   needs near-full income to ignite reading, exactly what depletion removes — the same
   bootstrap-requires-abundance tension as Exp 20, now on the *energy* axis. The viable window (regrow ~128)
   is narrow, and the driver-level per-iteration regrow granularity is coarser than per-tick consumption, so
   the carrying capacity is noisy; a per-tick in-kernel regrow would give finer control (noted for follow-up).

**Consequence.** Wall 1 — the blocker behind Exp 13/20/22 and the killer of every Exp-24 stigmergy design —
is **breakable**: a bounded reading economy forms a real carrying capacity and raises behavioral diversity.
This is the missing precondition for the stigmergy class: with reading no longer an infinite free substitute,
an authored/contested economy is no longer strictly dominated. The path re-opens — build a stigmergy economy
*on top of bounded reading*, using the Part-A escape recipe (destructive/rivalrous built cells + an authored
value decoupled from the reading eye + depth that pays more per cell, not flat royalty). `GENESIS_DEPLETE` +
`GENESIS_DEPLETE_REGROW` kept as instruments (default OFF / `CELL_STATES`); the default economy is
byte-identical and was re-verified with no regression. Branches: stigmergy-on-infinite-substrate closed
(24-A, two walls named); **Wall-1 broken — bounded reading forms a carrying capacity + lifts `Hact` (24-B)**.

---

## 🧪 Experiment 25 — Stigmergy Built: Agents Author Persistent Substrate Structure for the First Time (shallow, needs seeding, does not yet ascend) (2026-07-14)

With Wall 1 broken (Exp 24), the stigmergy class is buildable. This experiment implements the minimal
falsifiable primitive from the Exp-24 escape recipe and measures whether agent authoring emerges.

**Design (`GENESIS_STIGMERGY`, default-OFF, requires `DEPLETE`, no new constant, byte-identical when off).**
- **Write primitive:** overload `OUT_CONSUME` (keeps `N_OUTPUT=6`, zero genome-decode risk). When an org
  chooses CONSUME on a writable cell with a printable emission, it **authors** its vocal byte there, claims
  ownership (`cell_owner[pos]=org`), and refuels the cell; cost = `CELL_STATES` (the cell's state-space).
- **Royalty:** reading an *owned* cell transfers a per-bit slice of the reader's (fuel-bounded) gain
  reader→owner (zero-sum, non-lethal) — a builder-rent income stream distinct from solo reading, and
  depth-scaled (harder authored text → larger reader gain → larger rent).
- New observation-only telemetry: `authored` (owned-cell count) + `authors` (distinct live owners).

**Result — a two-stage debugging arc that is itself the finding:**

1. **Write-location matters (Exp 25a, vacuum-only authoring → FAILS).** First build wrote only to *vacuum*
   (`0x00`) cells, to keep authored bytes off the shared reading eye (the Wall-2 escape). Live: `authored=0`
   throughout — authoring **never fired**. Diagnosis via the action/frontier probes: survival glues every org
   to the readable scroll (`off-scroll ≈ 0`, mean offset 100 %), so no org ever *stands on vacuum*, and
   CONSUME-on-text is a pure no-op. **Authoring-requires-vacuum and survival-requires-the-scroll are
   spatially exclusive** — the build/read locations were disjoint, so the incentive could never engage.
   Seeding a `bias→CONSUME` write reflex did not help (CONSUME fired 13–47 %, but always on text/food, never
   on vacuum). "Option ≠ pressure," recast as a *location* mismatch.
2. **Co-locate build and read (Exp 25b, author a DEPLETED scroll cell → WORKS).** Fix: let an org author a
   *printable scroll cell whose fuel is exhausted* (as well as vacuum). A depleted cell is exactly where
   readers already are *and* has stopped paying, so refreshing it with one's own byte colonises live reading
   territory — and reclaiming a dead cell is rivalrous/destructive (the Exp-24 recipe). Live
   (`STIGMERGY + DEPLETE regrow 128 + seeded write`): **authoring emerges and persists** — `authored ≈ 270–278`
   cells held by `authors ≈ 150` orgs, stable across the whole run at full `pop=600`. **This is the first time
   in GENESIS that agents write persistent, readable structure into the substrate that other agents read.**

**Honest limits (what it is NOT, yet).**
- **Shallow, not specialised.** ~150 authors holding ~2 cells each = broad, thin authoring, not a
  builder/reader *division of labour*; `authored` plateaus (~278) rather than growing.
- **Does not ascend.** With authoring on, `Universe N ≈ 23.9 k` (slightly *below* the pure-depletion baseline)
  and `Hact ≈ 1.1–1.5` (below depletion's ~2.2) — authoring adds activity but not capability; no brain growth
  or entropy climb.
- **Needs seeding to bootstrap.** Unseeded, the write reflex is too rare to express and the colony
  cold-cliffs (a brief founder-window authoring of ~37 cells, then collapse). Authoring cannot yet *emerge*
  from a cold gene pool — it must be seeded, then selection tolerates but does not amplify it.

**Diagnosis + next step.** The plumbing works — persistent stigmergy is real and non-regressing — but the
*economics are too flat to drive ascent*: the royalty is a thin per-bit slice, so authoring is a marginal
side-income that ~150 orgs dabble in rather than a niche a specialist can live in. The Exp-24 recipe's third
leg — **depth must pay MORE per cell, not a flat royalty** — is the missing piece: rent must scale
super-linearly with authored difficulty so a dedicated author of hard content out-earns a solo reader and a
true builder niche forms (and, per Exp 22, only then can a stable division of labour lift `Hact`/capability).
The authored bytes are also currently the org's *reading* emission (scroll-tracking), so they are not yet a
text-*independent* authored value — the deeper half of Wall 2 remains. `GENESIS_STIGMERGY` +
`GENESIS_STIG_SEED` kept as instruments (default OFF); the default economy is byte-identical and was
re-verified with no regression (a rogue leftover sim cliffed an interim check to `pop=12` — the 4th
recurrence; killed and re-verified clean). Branches: vacuum-only authoring closed (25a, build/read must be
co-located); **persistent agent authoring achieved but shallow (25b) — next lever is super-linear
depth-scaled rent + a text-independent authored value**.

---

## 🧪 Experiment 26 — Super-Linear Rent Preserves Diversity and Concentrates Traffic, but No Specialist Forms Without Territory Persistence (2026-07-14)

Exp 25 authored persistent structure but stayed shallow: a *flat* per-bit royalty (~4 energy vs the ~32 a
read earns) made authoring marginal side-income ~150 orgs dabbled in. This experiment adds the Exp-24
recipe's third leg — **rent that scales super-linearly with a cell's usefulness** — to test whether a livable
specialist builder niche then forms.

**Design (no new constant; Rules 17/9/10 respected).** The authorship royalty fraction now grows with a
cell's cumulative **read-traffic** (`read_hits`, a per-cell integer counter reset on each authoring): a cell
read once yields the author `1/BITS_PER_BYTE` of the reader's gain, a heavily-read cell up to
`(BITS_PER_BYTE-1)/BITS_PER_BYTE`. So income **concentrates on whoever holds high-traffic (useful, hence
popular) territory** — a specialist should out-earn a dabbler. Constant-free (a pure integer-hit ratio ×
the reader's own gain), strictly zero-sum (the reader always keeps ≥ `1/BITS_PER_BYTE`), non-lethal (capped
at the reader's surplus above its body floor). New telemetry: `tophold` (max cells held by one author),
`toptraf` (peak per-cell traffic).

**Result (live, `STIGMERGY + DEPLETE regrow 128 + seeded write`, vs Exp 25 flat rent):**

| signal | Exp 25 (flat) | Exp 26 (super-linear) |
|---|---|---|
| `Hact` | ~1.1–1.5 (suppressed) | **~2.0–2.45 (elevated, matches pure-depletion)** |
| `toptraf` (peak cell traffic) | — | **894 → 9 879 (heavy-traffic cells form)** |
| `tophold` (max cells/author) | ~2 | **caps at 4–6 (still no specialist)** |
| `authors` | ~150 | 31 → 185 (still broad) |

**Two findings:**

1. **Super-linear rent preserves diversity + concentrates traffic (positive).** Unlike flat rent (which
   *suppressed* `Hact` to ~1.3), traffic-scaled rent keeps `Hact` elevated (~2.0–2.4, the pure-depletion
   level) for most of the run, and `toptraf` climbs into the thousands — some cells become heavily-read
   hotspots, so the super-linear mechanism genuinely engages and does **not** collapse behavioral diversity.
2. **No specialist forms — territory turnover is the wall (negative).** `tophold` never exceeds 6: no author
   accumulates a holding to *live on*, and `authors` keeps climbing (broad dabbling persists). Diagnosis:
   **super-linear rent rewards *holding* high-traffic cells, but nothing lets an author *hold* them** — any
   org can re-author a depleted cell and seize ownership, so cells churn constantly and income can never
   concentrate. Rent *depth* is necessary but insufficient; the missing mechanic is **ownership persistence /
   territory defense** (a held cell should resist overwrite, or the owner should refresh it cheaply, so a
   builder can defend a patch long enough to specialise). Late in the run `Hact` decays (2.4 → 1.06) and
   population dips as the churn destabilises — turnover is actively costly, not merely neutral.

**Consequence.** The economics moved the right way (depth-scaled rent lifts/keeps diversity and builds
traffic hotspots) but the **division of labour still does not crystallise** because there is no property
right — this is a *territory-persistence* gap, not a rent-shape gap. Next lever: give ownership persistence
(e.g. re-authoring an *owned, still-fuelled* cell costs more than claiming vacuum/depleted, or an owner's
cheap refresh resets fuel so held cells stay live) so a specialist can defend high-traffic territory, income
concentrates, and — per Exp 22 — a stable builder/reader division can finally lift capability. `read_hits`
and the `tophold`/`toptraf` probes are kept as instruments (observation-only, Rule 9↔6); the default economy
is byte-identical and was re-verified with no regression. Branches: flat-rent-too-shallow closed (25);
**super-linear rent lifts diversity + traffic but needs territory persistence for a specialist niche (26)**.

---

## 🧪 Experiment 27 — Absolute Ownership Persistence Freezes the Map: Both Extremes Fail, the Answer Is a Decay Gradient (2026-07-14)

Exp 26 showed super-linear rent concentrates read-traffic but not income, because any org can seize a
depleted cell → churn → no specialist can *hold* territory. This experiment adds the missing **property
right** and measures whether a specialist then forms.

**Design (`GENESIS_STIG_PERSIST`, default-OFF, requires `STIGMERGY`, no new constant).** A **living owner's
cell is not seizable** by others — a non-owner may author only vacuum, an unowned cell, or a dead-owner cell;
the **owner may refresh its own cell at any fuel level** (defend + keep it live, retaining its earned
traffic). Owner **death releases** the cell (turnover stays emergent, Rule 10). Combined with Exp-26
super-linear rent, a builder that defends a hot patch should collect concentrated rent, survive on it, and
hold it — a livable specialist niche.

**Result (live, `STIG_PERSIST + super-rent + DEPLETE regrow 128 + seeded`, ~418 k ticks):** a **hard
economic freeze**, not a specialisation.

| signal | early (≤30 k) | frozen equilibrium (150 k → 418 k) |
|---|---|---|
| `authored` / `authors` | growing (60/49 → 112/91) | **locked at exactly `112/91` for 150 k+ ticks** |
| `toptraf` (peak cell traffic) | ~2 k | **climbs unbounded → 106 810** |
| `tophold` (max cells/author) | 2–3 | **4 (still no specialist)** |
| `Hact` | ~2.0 | **collapses monotonically 2.0 → ~0.1** |

**Finding — persistence over-corrects into rent-seeking ossification.** By making cells unseizable, absolute
persistence **froze the map**: the ~91 founder-authored cells became permanent toll-booths, every reader
funnels through them (`toptraf` explodes to >100 k reads on a handful of cells), the colony collapses onto
pure read-through-owned-cells behaviour (`Hact → 0.1`, a monoculture), and **no new authoring ever happens**
because all viable depleted-cell territory is locked by living owners. `tophold` stays at 4 — the freeze
locked in *before* any author could accumulate a holding, so 91 orgs each own ~1 permanent cell forever.
This is the exact opposite failure from Exp 26 (total churn), and it is *worse* for capability: churn at
least kept `Hact` elevated (~2.2), whereas the freeze drives it to near-zero.

**Diagnosis — both extremes fail; the answer is a decay gradient (Rule 10).** No persistence (Exp 26) =
constant churn, income never concentrates, no specialist. Absolute persistence (Exp 27) = permanent capture,
map ossifies, diversity dies, still no specialist (concentration happens on *cells* via `toptraf`, but not on
*authors* via `tophold`, because the founders locked their claims before selection could sort winners). The
missing ingredient is neither extreme but the **Tectonic Gradient Principle applied to ownership**: a claim
must **decay over time** (an owner must keep *paying/refreshing* to hold territory, and an unrefreshed claim
weakens so it can be contested) so that territory recycles slowly — persistent enough that a genuinely better
builder can hold and out-earn, impermanent enough that it never ossifies into a founder toll-booth cartel.
This is the same lesson as the whole arc — a *gradient*, not a cliff — now on the property-right axis.
`GENESIS_STIG_PERSIST` kept as an instrument (default-OFF, the frozen extreme of the A/B); the default
economy is byte-identical and was re-verified with no regression. Branches: no-persistence-churns (26),
**absolute-persistence-freezes (27) — ownership needs a decay gradient, not a binary right**.

---

## 🧪 Experiment 28 — Leaky Ownership Destabilises the Colony: Holding-Cost on Shared-Scroll Cells Cannibalises the Reading Substrate (2026-07-14)

Exp 27's freeze pointed to a **decay gradient** for ownership (Rule 10): a claim should cost upkeep to hold
and lapse if neglected, so territory recycles slowly. This experiment builds that (`GENESIS_STIG_LEASE`) and
finds the *implementation* couples authoring to reading destructively.

**Design (`GENESIS_STIG_LEASE`, default-OFF, implies `STIG_PERSIST`, no new constant).** Owned cells no
longer receive the full free fuel-regrow; an owner must *actively refresh* (pay `CELL_STATES`) to keep a cell
fuelled and earning. A neglected owned cell drains to empty and its claim **lapses** (owner cleared → cell
recycles, contestable again). Two variants tested: (a) **binary** — owned cells get *zero* free regrow; (b)
**partial** — owned cells regrow at `1/BITS_PER_BYTE` of the free rate (hardware-derived), so holding still
costs ~7/8 upkeep but a hot cell nets positive.

**Result — both variants COLD-CLIFF the colony (`pop → 12`), with and without the seeded write reflex:**

| config | outcome |
|---|---|
| binary lease + seed | `pop 101 → 12`, `authored → 0` (authoring is strictly a loss) |
| binary lease, unseeded | volatile `pop 200–560`, `authored` flickers 0–2 (never accumulates) |
| **partial lease + seed** | `pop → 12`, authored freezes at `109/82` on a dead colony |
| **partial lease, unseeded** | `pop 288 → 12` — cliffs *without* the seed too |

**Two failure mechanisms, both structural:**

1. **Authoring cannibalises the reading substrate.** Authoring targets *depleted scroll cells* (Exp 25b), so
   an authored cell **is a scroll cell** — and under lease it now gets only reduced regrow. Orgs authoring
   scroll cells convert live reading territory into slow-refuelling owned cells, which drain, lapse, and churn
   the scroll into a low-fuel state → reading income (the survival economy) drops → collapse. The partial
   variant cliffs *unseeded* too, so this is the lease mechanic itself, not just the seed.
2. **Seeded write-spam bankrupts the bootstrap.** With the seed, ~82 founders each pay `CELL_STATES=256` to
   author during the ignition window; under lease those cells earn no free regrow, cannot recoup 256 in rent
   before draining, so the founder cohort mass-drains its energy and the colony crashes before reading
   stabilises.

**Diagnosis — the decay gradient is right, but authoring must not sit on the reading scroll.** Exp 27
(freeze) and Exp 28 (leak) together bracket the ownership-persistence axis, but Exp 28 exposes a deeper
coupling the whole stigmergy line has carried since Exp 25b: because authoring reuses *depleted scroll cells*
(the fix that made authoring fire at all), any holding-cost on owned cells is a holding-cost on the shared
reading substrate, and the two economies fight over the same fuel. The clean resolution is the **deeper half
of Wall 2, still open**: authoring needs its own **text-independent territory** (a region, or a value channel,
that is not the reading scroll) so that ownership upkeep, lapse, and rent operate on *authored* resource
without draining *reading* fuel. Until authoring and reading are decoupled in *space/substrate* (not just in
byte value), every property-right refinement will keep colliding with survival. `GENESIS_STIG_LEASE` kept as
an instrument (default-OFF, the destabilising extreme of the A/B); the default economy is byte-identical and
was re-verified with no regression. Branches: churn (26), freeze (27), **leak-cannibalises-reading (28) —
authoring and reading must be decoupled in substrate, not merely in byte value (the open half of Wall 2)**.

---

## 🧪 Experiment 29 — Substrate Decoupling (Parallel Canvas): The Fuel Coupling Breaks, but a New Energy-Currency Coupling Bankrupts the Colony (2026-07-14)

Exp 28 diagnosed the wall: because authoring reused depleted *scroll* cells, every ownership holding-cost was
a holding-cost on the shared reading fuel → cannibalisation → collapse. The fix is to give authoring its own
**spatially-separate territory**. This experiment was **adversarially vetted before building** (a 5-design
workflow panel — parallel-canvas, annotation-layer, food-plane, two-pool, migration-niche — each critiqued by
coupling and ascent lenses); the surviving synthesis was **Parallel-Canvas + surprise-gate**, built as
`GENESIS_CANVAS`.

**Design (default-OFF, requires DEPLETE+STIGMERGY, no new constant, N_OUTPUT=6 kept).** A **canvas band**
`[CANVAS_LO, CANVAS_HI)` of one scroll-width is laid immediately after the reading scroll (bounds derived from
`LIB_START + BOOK_TARGET_BYTES`). Authoring (CONSUME-overload) is **index-confined** to the canvas, so a
scroll cell can *never* be owned — ownership upkeep/lapse physically cannot touch survival fuel (the Exp-28
fix, structurally). The canvas abuts the scroll so a forward-saccading reader walks onto it; the scroll's
Exp-24 carrying capacity makes the uncrowded canvas the higher-marginal-income frontier readers migrate to.
Royalty is **surprise-gated** (rent pays only when the read cell differs from the previous — an echo/constant
run earns the builder zero, the Wall-2 anti-farm). Optional `GENESIS_CANVAS_SEED` tiles the book into the
canvas so it pays reading income from t=0.

**Result (live sweep across the seed/reflex parameter space):**

| config | population | authoring | migration (`oncanvas`) | outcome |
|---|---|---|---|---|
| seeded canvas + write-reflex | 585→590→264→**12** | `authored 5747→5910` (whole band), `authors 217→391` | 40→168→**596** | **migration works, mass-authoring bankrupts** |
| seeded canvas, no write-reflex | 236→48→**12** | `authored 5403→5606`, `authors ~188` | 121→37→23 | same bankruptcy |
| unseeded + write-reflex | cold **12** from t=1, `reads=0` | `authored 2` | 0 | founders author vacuum, never bootstrap reading |
| unseeded, no write-reflex | sustains 322→463 | `authored ~5` (barren) | ~2 | **sustains but barren** (Exp-25b) |

**Diagnosis — the intended wall broke; a new one replaced it.** Two genuinely new positive results, both
first-time achievements in the whole arc:
1. **The fuel decoupling WORKED.** Reading fuel was never cannibalised — the Exp-28 collapse mechanism (leak
   draining the survival substrate) is *structurally impossible* under index-confined ownership, and the runs
   confirm it (survival never died *from fuel starvation*).
2. **Reader migration WORKED.** `oncanvas` climbed 40→168→**596** — for the first time readers left the
   survival scroll and colonised the authored territory *en masse*, defeating the Exp-25b "nobody visits
   barren territory" barrenness that blocked every prior stigmergy build. The geometry (abutting band) +
   carrying-capacity gradient is a real migration pull, no artificial lure.

But the colony still collapses, via **the failure mode the vetting panel predicted precisely: energy-currency
coupling ("a new form of Exp-28").** The fuel pools are decoupled, but *energy* is one shared currency —
authoring costs `CELL_STATES` per cell, and once migration succeeds, hundreds of orgs pile onto the canvas and
author simultaneously (`authored → 5910`, nearly the entire 6000-cell band), draining collective energy far
faster than royalty returns it → mass starvation → `pop → 12`. Seeding makes the canvas attractive enough that
migration *over*-succeeds into a build-frenzy; not seeding leaves it barren (no migration, no authoring);
seeding the write-reflex without content makes founders author vacuum and never bootstrap. The three poles
bracket a coupling that the *spatial* decoupling does not address: **authoring is a collective-action /
tragedy-of-the-commons problem in the shared energy pool** — individually rational authoring (claim a cell,
hope for rent) is collectively bankrupting when everyone can do it at once with delayed, uncertain payoff.

**Consequence — the decoupling is necessary and now proven achievable, but insufficient alone.** The missing
piece is not more spatial separation (that works) but a **throttle on the rate of collective energy conversion
into authored territory** — authoring must be individually costly-enough or rate-limited-enough that it cannot
become a synchronous colony-wide drain, while still being profitable for a *specialist minority* (the Exp-22
division of labour). Candidate levers (unbuilt): author cost that scales with how much canvas one already owns
(diminishing returns → self-limits hoarding and frenzies); or authoring gated on a scarcer prerequisite than
raw energy; or a slower migration pull so builders and readers reach the canvas in balance rather than a mob.
`GENESIS_CANVAS`/`GENESIS_CANVAS_SEED` kept as instruments (default-OFF); the default economy is byte-identical
and was re-verified (`pop=600, Universe N≈25.6k, ext=0 refuge=0`, no canvas telemetry). Branches: churn (26),
freeze (27), leak-cannibalises-reading (28), **energy-currency-frenzy (29) — spatial fuel decoupling works +
migration works, but shared-energy authoring is a collective-action collapse that needs a conversion throttle**.

---

## 🧪 Experiment 30 — The Learning-Ablation Test: In-Lifetime STDP Is Net-NEGATIVE (the design loop closes, `Docs/Ascent.md`) (2026-07-16)

**Strategic pivot.** Experiments 13–29 formed an open-ended "build a lever → hit a new wall" loop that
reshaped the *economy* 17 times while never once validating the project's load-bearing assumption — that a
GENESIS brain **learns within its lifetime**. `Docs/Ascent.md` + `Rules.md` Rule 18 now fix a pre-registered
finish line (A capability rise, B learning load-bearing, C efficiency) and mandate validating that
assumption *before* adding any more mechanics. This experiment is that validation — the test that should
have been Exp 1.

**Design (`GENESIS_NOLEARN`, default-OFF, no new constant).** Compile-time deletion of STDP Phase 3: when
ablated, no in-lifetime weight update and no plasticity energy cost fire, so every synapse keeps its
DNA-decoded weight for life (Lamarckian inheritance auto-neutralises — a learned weight equals its decoded
weight when nothing is learned). Everything else — genomes, economy, physics — is byte-identical. The A/B
(ON vs OFF, default books economy) isolates the causal contribution of plasticity.

**Result (live A/B to equilibrium):**

| metric (equilibrium) | STDP **ON** (current default) | STDP **OFF** (ablated) |
|---|---|---|
| population | 596 → **423** (steady decay) | **599** (flat) |
| brain size `Universe N` | 25 834 → **17 441** (−34 %, sheds) | 25 790 (−2 %, flat) |
| reading solve-rate | **~23 %** | **~51 %** |
| reads / window | ~60 | **~148** |

**Verdict — criterion B fails, and fails HARDER than expected: learning is not merely non-load-bearing, it
is actively HARMFUL.** Ablating plasticity makes the colony *more* stable, keeps the brain *larger*, and
*doubles* comprehension. The whole-project "sustains but decays" signature (brain sheds, prediction dies —
Exp 12 onward) is now **causally attributed to STDP itself** driving the decode-good genetic weights toward
noise, not to economic abundance. Every economy lever of Exp 13–29 was built on top of a learning rule that
was silently eroding the capability those levers tried to grow.

**This does NOT yet falsify the substrate — it falsifies the current learning RULE**, which admits three
repairable causes (to be diagnosed, not assumed): (1) wrong-sign/wrong-target plasticity corrupting a good
evolved reflex — most likely, the *shedding under learning* is the signature of destructive weight drift;
(2) STDP metabolic overhead taxing a learner with no offsetting benefit (Rule 7 then grinds it down); (3)
task mismatch — next-symbol prediction is well-served by a *fixed* good reflex, so a changing weight only
adds variance. **Next step is a DIAGNOSIS (Rule 18), not a new economy lever:** test ON-vs-OFF on a task
whose answer *changes within a lifetime* (only there can a correct learner beat a fixed reflex) and isolate
the STDP energy cost from the weight-update effect. Only if a corrected, sign-correct, task-matched
plasticity still loses to ablation is the SNN-on-RAM substrate falsified. Operative conclusion for now: **the
current STDP rule is net-negative and must be fixed or removed before any further capability work; the engine
is effectively "reflex-evolution only" until a learning rule is shown to help.** `GENESIS_NOLEARN` kept as a
permanent A/B instrument (default-OFF); default (learning-on) byte-identical, re-verified.

---

## 🧪 Experiment 31 — STDP Diagnosis: Three Causes, and the Root Is No Supervision (2026-07-16)

Following Rule 18 (diagnose before adding mechanics), two orthogonal diagnostic ablations isolated *why*
STDP is net-negative (Exp 30). A code read first settled the cheapest hypothesis: **the STDP sign is
correct** — pre-before-post potentiates, post-before-pre depresses (Hebbian, not anti-Hebbian). The live
A/B then separated the rest (`GENESIS_STDP_COSTONLY` = keep energy cost, freeze weight; `GENESIS_STDP_DIV`
= scale steps down):

| mode | population | brain `N` | solve-rate |
|---|---|---|---|
| NOLEARN | 599 flat | 25.8k flat | **~51 %** |
| ON (full STDP) | 596 → 423 | −34 % sheds | ~23 % |
| DIV=32 (graded, small steps) | 599 flat | ~25k flat | ~5 % → **3 %** |
| COSTONLY (cost only) | cold-cliff → 12 | — | — |

**Three real causes:** (1) **bang-bang step** — the current rule could move a weight ~12 % of its range in
one event, slamming good decoded weights to the rail; this caused the shedding+collapse and is FIXED by
small steps (DIV=32 → population and N go flat). (2) **metabolic overhead** — COSTONLY cold-cliffs the
bootstrap, so the raw STDP energy tax alone can starve founders. (3) **ROOT: no supervision** — even the
corrected graded rule still makes reading slowly die (23 %→3 %), because plain STDP is *unsupervised*: it
reinforces any temporal coincidence with no reward/error signal, so it cannot tell a *correct* prediction
from a wrong one and drifts the decode-good weights toward task-irrelevant input correlations. Fixing the
step stops the catastrophe but not the slow rot, because the rule optimises coincidence, not correctness.

**Verdict — substrate NOT falsified; the learning rule is diagnosed and fixable in a specific direction.**
Pure two-factor Hebbian STDP cannot be load-bearing because the task rewards *correct* prediction and STDP
is blind to correctness. The indicated fix is **three-factor / neuromodulated plasticity**: multiply the
weight update by a success signal — the organism's own reading-reward energy — so a coincidence is
reinforced only when the prediction was actually right (eligibility × reward). This is more biologically
faithful (Rule 6/11: real synapses are neuromodulated), Rule-9 autotelic (the reward is the economy's own
reading income, not a human error label), and the first lever in the project that targets the MIND rather
than the market. `GENESIS_STDP_COSTONLY`/`GENESIS_STDP_DIV` kept as permanent diagnostic instruments
(default = current behaviour, byte-identical). Next: build three-factor STDP and A/B it against NOLEARN.

---

## 🧪 Experiment 32 — Three-Factor STDP Beats Ablation EARLY, Then Still Drifts: the Problem Is Credit Assignment (2026-07-16)

The Exp-31 fix was built: `GENESIS_STDP3` scales the weight update by a per-organism neuromodulator = the
organism's own normalised reading reward last tick (one-tick eligibility delay), so plasticity damps toward
zero when the organism is not comprehending. Combined with the small-step fix (`GENESIS_STDP_DIV=32`) — the
"corrected rule" — and A/B'd vs the NOLEARN baseline (solve ~51 % flat):

| phase | population | brain `N` | solve-rate |
|---|---|---|---|
| STDP3+DIV32, early | 599 | 26 267 | **~78 %** (project best) |
| STDP3+DIV32, steady | 599 → 251 | 26 267 → 10 611 (sheds) | 78 % → ~29 % |

**Partial success — a real milestone, plus a precise next target.** For the first time a learning rule pushed
comprehension *above* the no-learning baseline (78 % vs 51 %) — **constructive learning IS possible on this
substrate**, so the `Ascent.md` kill-criterion stays un-triggered and the substrate is alive. But it does not
hold: the colony decays to a lower plateau. The residual drift is diagnosed: the neuromodulator only **gates
the timing** of plasticity (learn while comprehending) — it does not fix **direction / credit assignment**.
When reading is paying, full-gain STDP is back on and still blindly reinforces *every* coincident synapse,
including those that did not cause the correct output. A reward *magnitude* is not an error *signal*: the third
factor must carry **which synapses deserve credit for the correct prediction**, not merely *that* a reward
occurred — the classic SNN credit-assignment problem. That is the specific, well-posed next target (not another
economy lever, not a blind STDP tweak). `GENESIS_STDP3` kept as an instrument. Next: a credit-assigning third
factor (potentiate only synapses onto neurons whose spikes drove the *correct* vocal bits; depress those onto
wrong bits) — true reward-modulated STDP — then A/B for a rule that *holds* above ablation.

---

## 🧪 Experiment 33 — Credit-Assigning Three-Factor STDP HOLDS Above Ablation: Criterion B Met for the First Time (2026-07-17)

The Exp-32 diagnosis was that the scalar `stdp_mod` gates the *timing* of plasticity but never its
*direction*: while reading pays, full-gain Hebbian STDP reinforces every coincident synapse — including
those driving the WRONG vocal bits — so the decode-good genetic weights still drift (the slow rot Exp 31
isolated). The fix is `GENESIS_STDP3C` (default-OFF, superset of STDP3): a **per-vocal-bit signed
eligibility trace**. Reading reward already scores each of the 8 vocal bits separately against the target
byte (`correct_bits` / `wrong_bits` in the reward block); that per-bit verdict is stored as
`org_elig[org, 0..7]` (+1 correct, −1 wrong, 0 silent, one-tick eligibility delay) and multiplies each
Phase-3 update whose destination is a vocal-bit neuron. LTP consolidates ONLY correct-bit drivers; LTD
reverses onto wrong-bit drivers; motor/hidden destinations keep the scalar `stdp_mod` (Exp-32 behaviour
preserved). Autotelic (the credit sign derives from reading's own per-bit correctness, never a human label
— Rule 9), constant-free (a pure per-bit ratio — Rule 17), compile-time gated (default byte-identical,
verified live), composes with `STDP_DIV=32` (small steps); STDP3C implies STDP3 (same dopamine ×
eligibility gain).

Live A/B on the default books economy (`00_Graded`), STDP3C vs the NOLEARN control, both to **400 000
LIF-ticks**, identical environment:

| metric | NOLEARN (ablation) | STDP3C (credit-assigning) |
|---|---|---|
| population | 599–600 flat | 597–599 flat |
| brain size `Universe N` | ~25 900 flat | ~26 050 flat (NO shedding) |
| solve-rate `reads/(reads+miss)`, early | ~54 % | **~72 %** |
| solve-rate, steady (~350 k ticks) | **~51 %** | **~60 %** |

**Criterion B (learning is load-bearing) is SATISFIED — and, unlike every prior rule, it HOLDS.** STDP3C
stays *above* the ablation baseline across the whole 400 k-tick run (steady 60 % vs 51 %), with **no brain
shedding** (`N` flat ~26 050 vs Exp-32's 26 267 → 10 611 collapse) and **no population decay** (599 flat vs
Exp-32's 599 → 251). Giving the third factor *which synapses deserve credit* — not merely *that* reward
occurred — is what makes in-lifetime learning net-positive AND stable on this substrate. This is the first
learning rule in the project's history that measurably and durably beats not-learning; the kill-criterion
stays un-triggered and the SNN-on-RAM substrate is now positively validated as a learner, not merely un-
falsified (see `Docs/Ascent.md` §4e).

Residual (next target = criterion A, not a new economy lever): a mild early-to-steady drift (72 % → 60 %) —
credit assignment is *sufficient to hold above ablation* but capability criterion A (a sustained ≥25 % RISE
in prediction-depth) is still not met. The frontier probe shows the colony sits ~93 % off-scroll in the
arithmetic band while `pred` ≈ 0 — it holds the hard region without yet earning compute-depth income.
Instrument notes: `GENESIS_STDP3C` kept as a permanent instrument (default = current behaviour); eligibility is
written only in the stationary-read scoring block, so a jump-predict tick uses a one-tick-stale credit
vector (bounded harmless — the reward-gate zeroes plasticity when reading pays nothing). **Next: make the
held capability RISE — couple the credit trace to the prediction-DEPTH frontier, or run the §4-step-2 within-
lifetime remap task (correct answer changes mid-life, where only a credit-assigning learner tracks it) —
then A/B for the full A ∧ B ∧ C finish line.**

---

## 🧪 Experiment 34 — The Within-Lifetime Remap Test: the Learner Cannot RE-TRACK — STDP Prunes but Cannot RECRUIT (2026-07-18)

Exp 33 satisfied criterion B, but on a task (next-symbol prediction) a *fixed reflex also solves* — so
"learning holds above ablation" left open the strategy review's sharpest doubt (`Ascent.md` §3, 2nd
disconfirming hypothesis): is the substrate really *learning*, or is it evolving a fixed reflex? §4 step 2 —
the affirmative test, **never built before** — settles it by making the **correct answer change within one
lifetime** on a wall-clock phase that is on **no sensory input**, so a fixed genome provably cannot
pre-encode it and only genuine in-lifetime plasticity can track it.

**Task (`GENESIS_REMAP`, default-OFF, compile-time gated, byte-identical when off).** In a "swapped" phase the
reading-reward target has two designated vocal bits **exchanged** (SB0↔SB1); the identity phase is the ordinary
next byte. The other 6 bits echo normally (survival barely perturbed); the *only* thing that must be **learned**
is to re-route eye-bit SB0→vocal-bit SB1 when the phase flips. The ancestor is seeded with the two **cross
synapses at zero weight** (present but silent) so credit-assigning STDP has a physical route to potentiate — its
fairest shot. (A first design used a full 8×8 plastic eye→vocal fabric; under learning it **cold-cliffed** the
colony — 56 corruptible routes slam the echo — the first data point: *dense plastic input fabric + STDP =
catastrophic drift*. The 2-route form isolates the question cleanly.)

**Measurement — a survival-DECOUPLED held-out sandbox** (`tests/remap_sandbox_probe.py`, Rules 9↔6/14, drives
the REAL `world_tick_numba` — Live-Loop-Test-Gap rule). Every prior "does it learn?" result was confounded by
the economy: making reading harder drives the colony to the refuge floor (pop=12), masking learning behind
collapse. This probe removes the economy: a frozen cohort of 120 REMAP-ancestor clones stands on a fixed text
patch, **energy pinned high every tick** (no death, no reproduction → only weights change), the phase alternates
on the `REMAP_PERIOD` clock, and observation-only **per-bit accuracy** is split into the 2 swapped bits vs the 6
unchanged bits.

| phase (steady, all 5 phase-cycles identical) | STDP3C (learner, DIV=32) | NOLEARN (ablation) |
|---|---|---|
| unchanged-bit accuracy (health check) | **~99 %** | **~99 %** |
| identity-phase swap-bit accuracy | ~87 % | ~87 % |
| **swapped-phase swap-bit accuracy** | **~40 % (flat, no trend)** | **~42 % (flat, no trend)** |

**Decisive NEGATIVE: the learner does NOT re-track the swap — statistically indistinguishable from the
ablation** (~40 % vs ~42 %; the learner marginally *worse*, from weight noise). At 250-tick resolution across a
3000-tick swapped phase the swap-bit accuracy is **flat noise ~40 %** from first window to last — no recovery
curve, no cumulative gain across 5 phase-cycles. 120 organisms × 3000 ticks of in-phase experience produce
**zero** measurable learning of the new mapping, while the unchanged bits hold 99 % (cohort healthy, reading
fine; *only* the bits that require learning fail).

**Mechanism (exactly the pre-registered prediction): STDP3C's credit is OUTPUT-GATED — it updates a synapse
only on a POST-synaptic spike.** In a swapped phase the echo diagonal makes vocal-SB0 fire (now *wrong*) and
leaves vocal-SB1 **silent** (should fire). The rule can LTD-*prune* the wrong active route, but a silent
neuron generates no eligibility, so there is **no gradient that turns a silent-but-wanted neuron ON** — it
cannot **recruit** the new pathway. Exp 33's success is therefore real but **narrow**: STDP3C *tunes/prunes an
already-firing* reflex; it does **not** *construct* a new input→output mapping. That is the difference between
tuning a circuit and building one — and building is what reasoning/abstraction (Rule 6) requires.

**This does NOT trigger the kill-criterion — it localises the defect: the rule carries a REWARD signal, not an
ERROR signal.** A `was-I-right?` credit reaches only neurons that fired; a *teaching* signal must also reach
neurons that *should have fired and did not*. The pre-registered next step is a **substrate change to the
plasticity rule, not another economy lever**: on a rewarded read, inject a small **target current** into the
vocal neurons the target byte says should be ON (derived from the org's own reading target — Rule 9 autotelic,
constant-free), so a wanted-silent neuron spikes and its afferents become LTP-eligible — then re-run this exact
sandbox A/B. If swapped-phase accuracy then climbs within a phase and holds above NOLEARN, the substrate can
*construct* mappings in-lifetime (criterion B on a reflex-proof task; first real evidence it can support
reasoning). If it still cannot after a correct error-signal rule, the kill-criterion is genuinely in play.
`GENESIS_REMAP` + `tests/remap_sandbox_probe.py` kept as permanent instruments; default engine byte-identical
(re-verified: cache key `genesis_numba_books`, ancestor 31 synapses — no regression). Full write-up: `Ascent.md`
§4f.

## 🧪 Experiment 35 — The Error/Teaching Signal RECRUITS: the Substrate Constructs a New Mapping In-Lifetime (2026-07-18)

Exp 34 localised the defect precisely: STDP updates only on a post-synaptic spike, so it prunes wrong-firing
routes but cannot **recruit** a silent-but-wanted neuron — it carries a REWARD signal, not an ERROR signal. This
experiment builds the pre-registered fix and re-runs the *identical* sandbox.

**Rule (`GENESIS_STDP_TARGET`, default-OFF, compile-time gated, byte-identical off).** A local **delta rule** on
the reading-eye→vocal-bit synapses, in the reward block on a rewarded read: for each vocal bit b, `err_b =
target_b − output_b ∈ {+1,0,−1}`; each synapse from an **active** eye input onto vocal neuron b is nudged
`w += err_b·(CELL_STATES/8)/STDP_DIV`. `err_b=+1` (wanted but **silent**) POTENTIATES the silent neuron's active
eye afferents with **no post-spike required** — the recruitment gradient STDP3C structurally lacks; `err_b=−1`
depresses; `0` leaves them. The biologically-plausible teaching current of dendritic-error / predictive-coding
SNNs (a "should-fire" signal to the apical dendrite), NOT backprop. Autotelic (target = the org's own read
target, Rule 9), constant-free (reuses `STDP_DIV`/`CELL_STATES`, Rule 17), activity-gated cost.

**Result — sandbox A/B (identical to Exp 34):**

| rule | swapped-phase swap-bit accuracy | behaviour |
|---|---|---|
| NOLEARN | ~41 % flat | fixed reflex |
| STDP3C (Exp 34) | ~40 % flat | cannot recruit |
| **STDP_TARGET (Exp 35)** | **56 % → ~99 % within ~2000 ticks, every phase flip** | **constructs the mapping in-lifetime** |

Every phase transition now shows the recovery curve that was ABSENT in Exp 34: at a flip to SWAP, accuracy drops
to ~56 % (old mapping wrong) then climbs 84→86→98→99 % and holds; at the flip back it drops to ~50 % and
re-climbs to ~99 %; the re-learning repeats every cycle and speeds up. Unchanged bits hold 99 % throughout (the
teaching signal touches only the eye→vocal fabric). The NOLEARN control on the identical fabric stays flat ~41 %,
proving the recovery is real in-lifetime plasticity.

**This is the first in-lifetime CONSTRUCTION of a new input→output mapping in the project's history** — the
substrate can *build* a new pathway, not only tune/prune an already-firing one (Exp 33). Affirmative criterion B
on a reflex-proof task; first concrete evidence the substrate can support the circuit-construction reasoning
(Rule 6) needs. Kill-criterion NOT in play — substrate validated one level deeper than Exp 33.

**Honest scope + next.** Proven **in the isolated sandbox** (frozen energy-pinned cohort on the seeded 2-bit
cross-fabric). NOT yet shown that `STDP_TARGET` beats NOLEARN on the **live books economy** over deep time, nor
that it generalises to *evolved* topology beyond the seeded fabric. Next (in order): (1) live-loop A/B
`STDP_TARGET` vs NOLEARN vs STDP3C on `00_Graded` — does the recruiting rule hold above ablation on the real
economy + fix the Exp-33 residual drift?; (2) the criterion-A push (make held capability RISE) on a rule that can
now *construct*. `GENESIS_STDP_TARGET` kept as a permanent instrument; default byte-identical (re-verified). Full
write-up: `Ascent.md` §4g.


---

## 3. Open Questions (Not Yet Demonstrated)

Honest gaps between the engine's *capacity* and demonstrated *emergence*:
- **Learning efficacy:** STDP + Lamarckian memory are implemented, and were finally **measured against a
  non-learning control (Exp 30, `GENESIS_NOLEARN`) — the result is NET-NEGATIVE:** ablating STDP *improves*
  survival, brain retention, and comprehension (solve-rate ~23 %→~51 %). In-lifetime learning as currently
  ruled is harmful, not merely unproven. Diagnosing whether this is a fixable STDP-rule flaw (wrong sign,
  metabolic overhead, or task mismatch) or a substrate falsification is the open frontier (`Docs/Ascent.md`).
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
  `ext=0` at both 9 % and 37 % density — the population no longer rides the refuge floor. **Ascension
  was then measured directly (Exp 12) and the answer is *not yet*:** on the Exp 11 economy the colony
  survives but *decays* (brain sheds 7.7 %, prediction dies by t≈62k). The economic root cause —
  echo-reading pays for already-sensed information — was fixed (pay for *predicting* the unseen next
  symbol), and a graded bootstrap curriculum restores survival and keeps capability *alive* (no shed,
  prediction never dies). But it still does not ascend, because **abundance** (600 orgs, 10 % scroll
  density) removes any pressure to climb the difficulty ramp. What remains open: (a) a
  **scarcity/competition** mechanism (a carrying capacity where easy text cannot feed the whole
  population) so solving harder symbols is the *only* way to eat — now identified as the load-bearing
  lever for ascent; (b) a peer-prediction coupling that does not extinguish its own substrate (Exp 11
  found `GENESIS_PEER=1` collapses the thriving colony).

## 🧪 Experiment 36 — Rule-17 Hardening: Deriving the Last Magic Numbers from the Substrate (2026-07-18)

Prompted by the directive that **no constant may exist without a physical derivation** — we are building an AGI
substrate, not a game, so every number must fall out of the hardware/network environment or live in DNA, else we
have merely a simulator. Rule 17 was amended (three permitted classes: HARDWARE-DERIVED, DNA-ENCODED, or an
explicit STRUCTURAL BOUND; a bare literal is a *bug* to derive or move into DNA, never to tune). Six remaining
neural-physics literals were closed, each **live-A/B'd on the default books economy** (all: `pop=599–600, ext=0,
refuge=0`, no shedding):

| constant | was | now (derived) | rationale |
|---|---|---|---|
| `SYN_DENSITY_SCALE` | `8.0` | **deleted** | dead literal — defined, never referenced (a dead magic number is still a violation) |
| `STDP_SCALE` | `8.0` | `BITS_PER_BYTE` | the register's own bit-width maps a full receptor byte to one bit-plane of the weight range; the amplitudes themselves stay DNA-encoded |
| crowd divisor | `/33.0` | `/(2·FOOD_SCAN_RADIUS+1)` | the divisor IS the number of cells in the scan window (density = occupied / cells-looked-at) |
| `ATP_MAX` | `1e6` | `RAM_SIZE·CELL_STATES` (16.77M) | the honest ceiling on cycles one organism can bank = the total matter-energy in all of RAM |
| viscosity denom | `/1000.0` | `/(MAX_DNA_PER_ORG/2)` | 0.5 stall-cap at half the densest all-synapse decode of the largest allowed genome (`MAX_DNA/4` synapses) |
| indel/dup rates | `0.05/0.10/0.15` | per-byte `1/l` (one copy head) | see below |

**The mutation-rate derivation surfaced a real finding (a useful negative on the way).** First attempt derived the
structural-fault rate as "at least one per-byte slip over the whole genome," `1-(1-1/l)^l ≈ 0.63` — i.e. structural
and point faults each carry ~half the load. Live A/B: the colony **survived but reading collapsed** (`reads 132→~20`,
solve-rate ~47%→~10%, frontier fell back to the bootstrap band) — a **4× increase in structural churn shreds the
reading circuit faster than selection maintains it.** This exposed that the old hand-set `0.05` was silently holding
structural mutation low enough to preserve learned circuits. The corrected derivation is physically sharper: a
substitution can occur at **every** byte (l sites → ~1 expected/copy, the per-byte sweep), but a structural slip is a
**length change at the single copy head** — one site per replication — so `P(indel this copy) = 1/l`, making indels
**rarer than point mutations by exactly the factor l** (the biologically-correct ordering, derived from "one copy
head, per-byte fidelity 1/l", with no imported ratio). Re-A/B: `reads ~90–109`, capability preserved, indels down
~30× from the old 15% with no harm (structural churn was never load-bearing for survival, only destructive to
capability above a threshold). Point-mutation frequency is unchanged (it was already the honest `1/l` sweep).

**Net:** the physics engine now contains no un-derived neural-physics constant — every remaining literal is either a
hardware fact (`BITS_PER_BYTE`, `CELL_STATES`, `±128` int8 range, `1 cycle`/op), a structural capacity bound
(`MAX_ORGANISMS`, `UNIVERSE_MAX_*`, `MAX_DNA_PER_ORG`), or DNA-encoded (receptor amplitudes/thresholds/potentials).
Remaining tracked Rule-17 debt (logged in `Roadmap.md` P4, not silently left): the Lamarckian 50/50 consolidation
blend is still an inline literal — the honest fix is to **DNA-encode it** (a heritable per-lineage
acquired-inheritance fraction evolution tunes), which is a genome-format change deferred as its own task. Default
economy re-verified byte-identical for the *unchanged* paths; the derived paths are live-A/B-verified healthy.

## 🧪 Experiment 37 — Evolvable Sensors: the Organism Grows Its Own Senses (Phase A0, 2026-07-18)

Prompted by the directive that a **fixed sensorimotor spec is us limiting the organism**: biology did not receive
"eyes/ears" as a designed I/O layer — environmental pressure *grew* them from receptors coupled to physical
quantities that already existed (light, sound). Any hardcoded `N_INPUT=25 / N_OUTPUT=14` is the "video-game
abstraction" Rule 15 forbids and the behavioural-expression ceiling Exp 21 named. This experiment begins
dissolving it: the sensory apparatus becomes **DNA-encoded and mutable**, so evolution discovers *what to sense
and where*.

**Mechanism (`GENESIS_EVOSENSE`, default-OFF, compile-time gated, byte-identical off).** A new `SENSOR_MARKER`
gene (5 bytes `[marker, slot, aff_type, offset+128, param]`, modelled on the proven `RECEPTOR_MARKER` pattern)
declares a **sensor neuron** in the hidden band whose firing comes from a real hardware **affordance** sampled at
a DNA-chosen signed offset from the pointer — not from LIF integration. Six affordances, each a quantity the
substrate already exposes (Rule 15 — evolution can only couple to what the machine physically offers, exactly as
molecules bound the senses biology could build): RAM byte value, a single RAM bit (a digital photoreceptor), cell
occupancy (touch), neighbour energy (chemoreception), a neighbour vocal bit (hearing), own energy
(interoception). A sensor neuron is otherwise an ordinary **source** — synapses wire it into hidden/output
neurons — so the *validated* reward/STDP/REMAP machinery (which indexes the fixed vocal/eye neurons) is
completely untouched. Each affordance sample is a real memory read, **charged one honest cycle** (Rule 17), so a
bloated sensor array pays for itself and cannot be a free lunch. `decode_genome`/`count_genes` handle the marker;
`sense_affordance()` transduces once per tick; a per-neuron `sense_type`/`sense_meta` map carries the coupling.

**Results (live, `00_Graded`):**
- **Default byte-identical** (EVOSENSE off): ancestor 44 neurons/31 synapses, cache key `genesis_numba_books`,
  unchanged — the whole apparatus is dead-code-eliminated.
- **EVOSENSE on, zero sensor genes**: sustains `pop=600, ext=0, reads~103` — the gate is inert until a sensor
  gene exists (correct).
- **Seeded demo** (`GENESIS_EVOSENSE_SEED`: 2 sensor genes/founder — a "look-ahead eye" reading the RAM byte
  `LONG_JUMP_STRIDE` cells ahead, a sense the fixed reading eye *cannot* provide, plus a proximity/touch sensor):
  **evolution RETAINS and PROLIFERATES the self-wired senses.** Tick-cadence retention across 150 k ticks:
  total live sensor neurons **1163 → 1389 → 1611 → 1600**, with ~every organism carrying ≥1 (`orgs_with_sensor`
  596→599), `pop=600 ext=0 refuge=0` throughout. Starting from ~1200 seeded, the colony *grew* the count to
  ~1600 — the sensors are not costly dead weight pruned by Rule-7 efficiency; they earn their keep, and mutation
  actively generates new ones, so `SENSOR_MARKER` is a live evolutionary substrate.

**Significance + honest scope.** This is the first time in the project an organism's **senses are not a
designer-fixed layer** — they are genome-encoded, mutable, coupled only to real hardware, and demonstrably
retained under selection. It directly attacks the Exp-21 behavioural-expression ceiling from the *input* side and
the Rule-15/17 "fixed I/O is an abstraction" critique. **Scope (stated honestly): this is Phase A0** — an
*extension* sensor apparatus added *alongside* the innate fixed senses (which remain as the Rule-5 baseline). It
does **not** yet dissolve `N_INPUT`/`N_OUTPUT` as constants. The continuation is pre-registered in Roadmap P4:
**Phase B** (evolvable *actuators* + migrate the vocal/motor readout off the fixed indices — invasive, re-run
through the REMAP sandbox to confirm STDP_TARGET still recruits) and **Phase C** (migrate the innate senses into
SENSOR genes too, so `n_c` is fully genome-derived and I/O stops being a global constant). `GENESIS_EVOSENSE` +
`GENESIS_EVOSENSE_SEED` kept as instruments; default byte-identical (re-verified). `brain_io`'s fingerprint
already tracks `N_INPUT/N_OUTPUT` so any future I/O change auto-archives stale checkpoints.

## 🧪 Experiment 38 — Evolvable Actuators: the Organism Grows Its Own Effectors (Phase B, 2026-07-18)

The motor complement of Exp 37, and the direct attack on the Exp-21 cognition ceiling ("a mind cannot be modelled
richer than it can *act*"): the organism should grow its own **effectors**, not receive a designer-fixed 6-motor +
8-vocal output layer. Also part of the strategic reframe (`Ascent.md` §5): widening behavioural expression is the
load-bearing prerequisite for grounded cognition and for peer-prediction to have anything rich to model.

**Mechanism (`GENESIS_EVOACT`, default-OFF, compile-time gated, byte-identical off).** An `ACTUATOR_MARKER` gene
(`[marker, slot, act_idx, thresh, receptor]`) declares an ordinary LIF neuron in the hidden band that **also drives
a physical action when it fires** — its spike is added into `out_accum[act_idx]`, the *same* accumulator the innate
output neuron for that action uses (`act_idx % N_OUTPUT` picks one of the 14 physical outputs). So evolution grows a
**new route** to an action (e.g. a deep evolved circuit that has learned *when* to jump can trigger the jump
directly), mirroring how a SENSOR adds a new *source* — **without replacing the fixed output neurons**. This is the
critical safety property: the reward/STDP/REMAP machinery still reads `out_accum[0..13]` exactly as before.

**Verification:**
- **Default byte-identical** (EVOACT off): ancestor 44n/31s, cache `genesis_numba_books` unchanged.
- **CRITICAL — validated learning intact:** the REMAP sandbox was re-run with EVOACT on (and again with
  **EVOSENSE+EVOACT both on**): `STDP_TARGET` still recruits — swap-bit accuracy drops to ~45–50 % at each phase
  flip then re-climbs to ~98 %, identical to the pre-Phase-B behaviour. Widening the actuator apparatus does **not**
  disturb the in-lifetime construction mechanism (Exp 35). The seeded actuator decodes + fires + contributes to
  `out_accum` correctly (mechanism confirmed present and functional).
- **Retention finding (honest, and it reinforces the reframe):** a seeded demo actuator was **pruned** in the books
  economy — both a CONSUME-driver (starves a reader by eating text) and a JMP_FWD-driver (perturbs the finely-tuned
  reading saccade so the reader skates over cells) cliffed the colony to the refuge floor and were selected out
  within ~75 k ticks. This is **not** a mechanism failure — it is the Exp-22 result recurring: the books survival
  economy pays for exactly one behaviour (the tuned echo-reader), so it selects *against* any behavioural variation,
  including a new effector. Contrast Exp 37, where a new *sensor* was retained/proliferated (more input never hurts a
  reader; a new output route perturbs its single monetised action). **The apparatus is sound; the books monoculture
  simply offers no niche for behavioural diversity to be retained in.**

**Significance + honest scope.** Both halves of the sensorimotor expression channel are now DNA-encoded and mutable
(sensors Exp 37, actuators Exp 38), composing cleanly with the validated learning — the Exp-21 ceiling is attacked
from both sides. But Exp 38 also delivers a **decisive economy finding**: evolvable effectors will only be *retained
and elaborated* under an economy that **rewards behavioural diversity** — which the single-reward books economy does
not. This is direct empirical support for `Ascent.md` §5: Books must be demoted to a survival scaffold and the mind
path routed through **peer prediction + niche/diversity structure**, where a richer action repertoire actually pays.
That — a diversity-rewarding economy on top of the now-widened expression channel — is the pre-registered next
build (not another I/O mechanic). **Phase C** (dissolving the fixed `N_INPUT/N_OUTPUT` blocks entirely) remains
available but is lower priority than giving the existing evolvable apparatus an economy that selects for it.
`GENESIS_EVOACT`/`GENESIS_EVOACT_SEED` kept as instruments; default byte-identical (re-verified).

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
(confetti transit gaps), not the exchange rate. **Exp 12 then put the ascension question to a direct
live test** — and the answer, honestly, is *not yet*. The Exp 11 colony survives but does not ascend;
it *decays* (brain sheds 7.7 %, prediction dies), because echo-reading paid full price for information
the organism already sensed — a zero-surprise copy any reflex farms forever. That was fixed by paying
only for **predicting the unseen next symbol** (an information economy, no new constant), which cliffs
cold on repeat-free text and so is bootstrapped by a **graded difficulty curriculum**; together these
restore survival and keep capability *alive* (no shedding, prediction never dies) — a strictly better
substrate — but still do not produce ascent. The reason was isolated: **abundance**. With 600 organisms
on a 10 %-full scroll, easy text is plentiful and nothing forces an organism up the difficulty ramp.
The frontier is now precise: ascension needs **scarcity/competition** (a carrying capacity below the
array cap) so that cracking harder symbols is the only way to eat — the load-bearing lever, and the
next research question in `Roadmap.md`, alongside a non-lethal peer coupling (Exp 11's open finding).
