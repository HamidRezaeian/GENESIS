# GENESIS vs Brain — Gap Analysis (2026-08-04)

> **Purpose (Rule 16 honesty):** map where the live engine matches the brain's
> computational principles and where it diverges, WHY each divergence exists, and which
> divergences are the substrate-pivot candidates if Exp 99 falsifies (Rule 18, triggered
> 2026-08-01). User-stated goal (2026-08-03): strong intelligence on WEAK hardware, like
> the brain (~20 W) — not datacenter-scale models. This is the neuromorphic bet; nobody
> has reached AGI on it yet (Loihi, TrueNorth are active research, not AGI).

---

## 1. Comparison table

| Property | Brain | GENESIS (current) | Gap | Why the gap exists |
|---|---|---|---|---|
| Energy model | ~20 W, event-driven metabolism | Event-driven charging: per-spike `CYCLES_PER_SYNAPSE_READ`, per-STDP `CYCLES_PER_STDP_UPDATE`, per-spike membrane cost (engine :1695, :1848, :1886); flat per-tick scan tax removed (:1618-1630) | **SMALL** — the honest-accounting layer is the strongest match | — |
| Neuron model | LIF: integrate, leak, threshold, spike, refractory | Full LIF: leak `v += (v_rest-v)/tau*DT` (:1740), threshold/spike/reset (:1742-1748), refractory (:1718-1719) | **SMALL** | — |
| Learning | STDP + neuromodulation + sleep/wake consolidation | STDP3C per-bit credit + homeostasis to a STATIC DNA anchor (:2193); NO consolidation (Exp 99 pending) | **MEDIUM** | consolidation never implemented; Exp 99 is the test |
| Execution control | Physics (ions, membrane, energy) | **Code conditionals**: viscosity coin-flip stall (:1650), stochastic input firing (:1696), refractory countdown, 20+ compile-time flags | **LARGE** | each was an engineering shortcut for speed/simplicity or an A/B-science necessity |
| Reproduction | Sexual: two parents, recombination | **Asexual fission only** in kernel (:2665-2748, :2762-2779); crossover exists ONLY host-side for fossil/Ark reseed (genesis_lab :1310, :1401, :1482) | **LARGE** | fission is cheaper and simpler; two-parent mating needs mate-finding + kernel complexity |
| Variation | mutation + recombination | cosmic-radiation 2-bit flips (:1361-1372) + Lamarckian 50/50 blend at birth (:2698-2731) | **LARGE** | consequence of asexual fission |
| Compute depth | recurrent, continuous | `n_steps` = longest input→node path + 1, per-organism architecture-derived (genesis_lab :1229); world clock = deepest live brain (genesis_lab :1795, :1881) | **MEDIUM** | feed-forward-per-tick approximation; recurrence exists via RAM/scratch loops only |

---

## 2. "Remove the conditionals and just let it run?" — honest analysis

The user's per-neuron list (integrate voltage, leak, threshold check, spike record,
weight read/apply, STDP, energy accounting) — **ALL already run event-driven in the
kernel**. What the user means by "remove the ifs" is the NEXT layer up:

- **Viscosity stall** (:1650): a coin-flip `random.random() < viscosity[org]` standing in
  for real computational-delay physics. Removing it honestly means modelling delay from
  the substrate (e.g. synaptic density → propagation time), not deleting the cost.
- **Stochastic input firing** (:1696-1716): sensors fire with probability ∝ activation
  instead of a real sensor-membrane dynamic.
- **Compile-time flags** (20+): necessary for A/B science NOW; the end-state product
  should have ONE physics with no flags. Each flag is a branch the final substrate
  must not contain.

**The principle is correct and already partially held:** control must come from
environmental physics (energy out → death :2781; cell fuel out → hunger; niche crowding →
income split :2418-2421) not from code gates. GENESIS has this at the ECONOMY layer but
not yet at the NEURON-EXECUTION layer.

---

## 3. Sexual reproduction — the biological wisdom is real

Two-parent recombination combines two successful evolutionary lineages; variation per
generation is orders of magnitude above mutation-alone. It directly attacks the measured
monoculture ceiling (Exp 22: demand-limited collapse to one behaviour).

**Current state:** kernel = strict asexual fission (parent pays copy cost, child gets
energy/2, byte-copy genome). `crossover_dna` exists but is only invoked for dead-DNA
fossil reseeding, never between two LIVE organisms.

**Implementable design (post-Exp-99 pivot candidate):**
- Mate = nearest spatial neighbour above an energy floor (proximity is already scanned
  for the crowding sense — no new constant, Rule 17).
- Both parents pay half the copy cost; child genome = single-point crossover of the two
  parent genomes + the existing radiation mutation.
- Lamarckian blend applies to each parent's contributed segment from that parent's
  learned weights.
- Cost: kernel complexity + mate search. Benefit: recombination breaks monocultures.

---

## 4. Pivot priority (binding order if Exp 99 falsifies)

1. **Finish Exp 99 first** — the registered decisive test; no pivot before its verdict.
2. If falsified → substrate pivot on THREE axes, in this order:
   a. **Two-parent sexual reproduction in-kernel** (attacks the monoculture ceiling —
      the measured diversity failure).
   b. **Physics-driven execution control** (replace viscosity coin-flip and stochastic
      input firing with substrate-derived dynamics; flags collapse to one physics).
   c. **Consolidation** (only if Exp 99's gate-pass/advantage-null outcome says the
      mechanism was right but the locus was wrong).

---

## 5. What is NOT a gap

The energy/event-driven accounting, the LIF core, the autotelic reading economy, and the
honest cycle measurement (Rule 21) are genuine matches to the brain-inspired low-power
thesis. The 20 W goal is not blocked by these layers — it is blocked by the control and
reproduction layers above.

---

## 6. Colony-for-training / elite-for-inference (user directive 2026-08-03)

The system is NOT one brain — it is a POPULATION of brains whose competition is the
engine of progress (fuel contention, niche split, death at zero energy). No single
organism is "smart"; the COLONY finds the evolutionary path, exactly as in nature.

The end-user interaction model is therefore asymmetric by design:

- **Training/learning: population-level.** ~512 concurrent organisms compete; selection
  over the population is the learning signal. This is the only known mechanism that
  produces open-ended capability without a human curriculum (Rule 9).
- **Inference/answering: individual elite.** When the user asks a question, the answer
  comes from the BEST organism — the winner of survival competition, not a hand-picked
  one. The Elite Ark / fossil pool (genesis_lab :1324-1345) already checkpoints the
  longest-lived genomes; the inference artifact is that elite (e.g.
  `Brain/Brain_Elite_AGI.npz`), run standalone.

Rule-7 compliance note: "best" must remain defined by SUBSTRATE survival (age/energy
under honest accounting), never by an authored IQ score — the current elite criterion
(longest-lived) satisfies this; any future capability-ranked elite selection would
violate Rule 7 unless the ranking is itself an emergent substrate quantity.
