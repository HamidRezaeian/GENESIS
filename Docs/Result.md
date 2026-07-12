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
  scaffolds; agent-generated survival problems are future work.
- **Deep-time robustness (Rules 10/14):** characterised in Exp 4 and found *negative* — a
  clockwork extinction/Ark loop with no ascension. The root-cause `max_ark_age` freeze is fixed
  (2026-07-10); population self-sustainability and the instantaneous total-wipe dynamic remain
  open.

## 6. Critical Audit Fixes (2026-07-11)
A rigorous architectural review identified and fixed three critical engine flaws that compromised open-ended evolution:
1. **Infinite Reading Money:** The stationary reading reward did not consume the byte unless the read was a perfect match, allowing organisms to stand still and farm partial-credit energy forever without foraging. Fixed by consuming the byte on *any* vocalization attempt, forcing physical exploration of text.
2. **Hidden Neuron Ablation Bug:** A fragile boundary check in `count_genes` meant that any organism allocated past the start of the RAM heap counted zero genes. This meant all late-born organisms were spawned with zero hidden neurons, effectively crippling them.
3. **Viscosity Bloat Ratchet:** The computational viscosity formula penalised synaptic *density* (synapses/neuron) rather than hardware footprint. This perverse incentive rewarded organisms that bloated with idle, disconnected neurons to lower their density. Viscosity is now strictly driven by total footprint `(neurons + synapses)`.

## 4. Conclusion
The current neuromorphic engine is a working substrate: genome-encoded SNNs learn in-lifetime,
reproduce with heritable topology **and** partially-heritable learned weights, and are held in
bounded population dynamics by a thermodynamic compute budget. However, deep-time
characterisation (Exp 4) shows the substrate is **not yet self-sustaining**: it settles into a
clockwork extinction/Ark loop with no ascension, driven by a now-fixed fossil-pool freeze plus
monoculture reseeding, an instantaneous total-wipe dynamic (contra Rule 10), and a brain-size
bloat ratchet. It provides the physical preconditions for emergent cognition, but establishing
self-sustaining, ascending populations — and then demonstrating that cognition — is the open
research programme in `Roadmap.md`.
