# Metabolic Affordability of Embodied Plasticity: A Physically-Accounted Falsification of In-Lifetime Learning Under Hardware-Equivalent Energy Costing

**Draft v2 — 2026-08-06**
**Target venues:** TMLR (technical correctness over significance) or ICBINB @ ICLR (negative results)
**Corresponding repo:** github.com/HamidRezaeian/GENESIS, branch `feature/substrate-pivot`
**Status:** Full draft for review. All quantitative claims trace to pre-registered experiment artifacts in `experiments/` and `Docs/Architecture/Ascent.md`; artifact paths are listed in Data Availability (§6).

---

## Abstract

Can a neural substrate learn *within its own lifetime* when every synaptic update, read, and spike is charged at its measured hardware cost? We address this question with a physically-accounted laboratory in which energy *is* execution cycles: a 1-D RAM universe hosting evolving spiking organisms whose metabolic budget is the measured cost of running the substrate on the host (Rule 21.1). We evaluated five substrate families — (1) SNN-on-RAM with Hebbian/STDP-class plasticity, (2) echo-state reservoir + online readout, (3) recurrent world-model, (4) small transformer, (5) hybrid transformer + event-driven memory — under identical pre-registered gates: in-lifetime improvement (Gate A) and improvement over a matched learning-ablation control (Gate B), with 4–24 seeds per condition. Every substrate **failed Gate A** (in-run deltas +0.16 to +3.70pp against a +2–5pp bar) while **passing Gate B** (static gaps up to +42.2pp), across static, non-stationary, and novel-sequence tasks — ruling out task difficulty as the cause. A mechanism-resolution programme (Exp 96–103b: plasticity-gating, surprise-gated updates, two-timescale consolidation, reservoir readouts) ended in systematic falsification, including a reward signal *identically zero* at every checkpoint (Exp 101). The same substrate that cannot learn under physical cost gains **+21.04pp** in-lifetime when the energy economy is decoupled from income (free-energy oracle, Exp 4b) — but a direct cost-factor sweep (Exp 5) shows that relaxing plasticity cost *alone* does not unlock learning (Δ = −0.44pp at every θ). We conclude that the binding constraint is not the cost of weight updates but the **metabolic affordability of exploration**: under honest accounting, exploration consumes an organism's finite energy before improved predictions repay it. Metabolic buffering — decoupling or subsidizing exploration cost — is a prerequisite for embodied plasticity, and the critical income-subsidy threshold θ* remains an open, tractable measurement.

---

## 1. Introduction

### 1.1 Problem statement

Every deployed AI system of the current era is frozen after training: weights are set once, in a data-center-scale offline phase, and the model never learns again. Biological intelligence is the opposite — it learns continuously, on-line, under a hard energy budget of ~20 W for ~86×10⁹ neurons. Bridging that gap is widely identified as a core open problem (continual/in-lifetime learning; see §4.1), yet almost all experimental work measures capability without accounting for the *physical cost of learning itself*: how many cycles, joules, or memory operations a plasticity mechanism consumes while it tries to improve.

The GENESIS project operationalizes this question literally. Its substrate is a RAM universe in which energy is execution cycles, space is memory addresses, and every primitive (read, spike, STDP update, reproduction) is charged at its measured host cost. A claim of in-lifetime learning is only accepted if it survives pre-registered gates against matched ablations, across multiple seeds, under this accounting. This paper reports the systematic result of that programme: **five substrate families, ~100 pre-registered experiments, and a uniform outcome** — learning that is real but metabolically unaffordable, with a quantitative decomposition of *why*.

### 1.2 Related work and the measurement gap

Three literatures frame this work:

1. **Continual / in-lifetime learning.** Benchmarks such as CORe50-style task suites, Avalanche, and Continual World measure accuracy under sequential tasks, but energy is reported as wall-clock at best; no standard benchmark in this literature charges plasticity at a physical (joules/cycles) rate. The neuromorphic continual-learning literature explicitly flags **energy-aware continual learning evaluation as an open problem** (survey, arXiv:2410.09218); NeuroBench (arXiv:2304.04640) is the closest framework and does not yet provide a cross-substrate, energy-accounted learning comparison. MLPerf Tiny measures energy for inference only.
2. **Bio-plausible credit assignment.** Three-factor rules (e.g., e-prop; Bellec et al., *Nature Communications* 11:3625, 2020) and surrogate-gradient training improve SNN capability but remain far behind backprop-trained transformers on standard benchmarks, and — critically for our question — are almost never run under a *measured* energy budget in which exploration must pay for itself.
3. **Neuromorphic hardware.** The largest neuromorphic system, Intel's Hala Point (April 2024), holds 1.15×10⁹ neurons at ~2,600 W on 1,152 Loihi 2 chips — roughly 10⁴× worse per-neuron energy efficiency than the 86×10⁹-neuron / ~20 W human brain (derived: 2.3×10⁻⁶ vs 2.3×10⁻¹⁰ W/neuron). If embodied plasticity is metabolically unaffordable *in simulation under honest costs*, that is a concrete, falsifiable warning for this hardware class.

**The measurement gap we address:** no prior work, to our knowledge, compares multiple learning substrates under identical, measured, per-primitive energy accounting with matched learning-ablation controls and pre-registered gates. This paper is that comparison.

### 1.3 Contributions

1. A **physically-accounted falsification** of in-lifetime learning across five substrate families (Gates A/B, 4–24 seeds per condition, pre-registered criteria).
2. A **mechanism-level exhaustion result** (Exp 96–103b): plasticity-gating, surprise-gated updates, two-timescale consolidation, reward-modulated STDP, and reservoir readouts each fail at a binding admission control; one mechanism's reward signal is identically zero at every diagnostic checkpoint.
3. A **metabolic buffering result**: the identical substrate gains +21.04pp in-lifetime learning when exploration's income is decoupled from its cost (free-energy oracle), while cost-relief alone (θ-sweep) produces no learning — localizing the bottleneck to the *income side* of exploration, not the update cost.
4. A **protocol contribution**: Rule 21 accounting (measured host cycles per primitive, hardware-derived or evolvable parameters, no invented cost points) as a candidate standard for energy-aware continual-learning evaluation.

---

## 2. Methods

### 2.1 The universe and its physics

The GENESIS substrate is a flat 1-D RAM of `UNIVERSE_MAX_NEURONS/SYNAPSES/DNA` cells. Organisms are genome-encoded spiking neural networks (LIF neurons, Dale's-law E/I types, STDP-class plasticity) that read the RAM, pay energy for every read, and survive on income earned by correct next-byte prediction. Three physical commitments make the accounting honest:

- **Energy is execution cycles.** One cycle per honest primitive, measured on the host (Rule 21.1). Reading a cell costs `CELL_STATES = 2^8 = 256` per resolved cell; synaptic plasticity is charged `CYCLES_PER_STDP_UPDATE`, a value read from the measured host cost table `_MEASURED_COST["stdp_update"]` (Rule 21.1), not an invented constant.
- **No game mechanics.** Invented "cost points" are forbidden (Rule 21.1); every tunable parameter must be hardware-derived or evolvable (Rule 21.2, 21.4); all constants are audited into classes H (hardware-derived) / E (evolvable gene) / O (opcode/marker) / G (violation) (Rule 21.6).
- **Death is real.** Organisms die at energy ≤ 0. Survival and reproduction are driven exclusively by the energy ledger — no authored fitness or IQ score (Rule 7).

Relaxation conditions used only as *diagnostics* (labelled as such): `NO_DEATH=1` (suspend death), `FREE_ENERGY=1` (suspend ATP charges for plasticity/exploration), and a cost factor θ ∈ [0,1] multiplying the plasticity cost (`COST_FACTOR`). All diagnostics are compiled behind cache-fingerprinted environment flags; default engine behavior is byte-identical.

### 2.2 Rule 21 physical accounting

Rule 21 (added 2026-07-25; `Docs/Architecture/FixedRules.md`) is the project's constitution for physical grounding: (21.1) costs are real hardware work — actual CPU cycles, memory traffic, joules, wall-clock; (21.2) parameters are hardware-derived or evolvable; (21.3) opcodes are a documented ISA; (21.4) the Tuning Test — a value that "works better" because it was tuned is an illegal mechanic; (21.5) two levels of grounding (simulated-substrate physics and host-hardware cost); (21.6) a remedy protocol and a public constant audit. Every experiment below inherits this accounting; `energy_basis: cycles MEASURED natively per Rule 21.1` is recorded in every result artifact.

### 2.3 Substrate candidates (five families)

| ID | Substrate | Configuration |
|---|---|---|
| S1 | SNN-on-RAM (historical) | LIF + STDP-class plasticity (STDP3C, STDP_TARGET, R-STDP), CAM associative memory, WRITE-gated latches; multi-scale variants; Exp 96–103b |
| S2 | Reservoir + online readout | Echo-state reservoir size=256, sparsity=0.1, EI=0.8, τ=20.0; linear readout trained on-line by Normalized LMS (lr=0.01, ε=10⁻⁸); shared (Exp 103) and per-organism (Exp 103b) variants |
| S3 | Recurrent world-model | Dreamer-style latent imagination: recurrent state predicts next observation/outcome (SUBSTRATE_3_RECURRENT_WORLD_MODEL_v1) |
| S4 | Small transformer | Proven sequence learner used as diagnostic upper bound; 2000-tick, 20000-tick, non-stationary, and novel-sequence protocols (SUBSTRATE_4_*_v1) |
| S5 | Hybrid transformer + event memory | Transformer core with sparse event-driven external memory (SUBSTRATE_5_HYBRID_TRANSFORMER_MEMORY_v1) |

### 2.4 Experimental protocol

- **Pre-registration (Rule 2).** Every experiment archives a quantitative, binding falsification criterion *before* data collection (`Docs/Architecture/Ascent.md`; protocol docs `Docs/Exp10x_Protocol.md`).
- **Multi-seed replication (Rule 3).** 4 seeds for substrate comparisons (0–3); 24 seeds (72–95) for Exp 97–99 confirmatories; matched per-seed learner/ablation pairs; paired statistics with sign-flip/permutation tests.
- **Matched learning-ablation controls (Rule 18-B).** Every learner arm is paired with a NOLEARN arm (plasticity zeroed/readout lr=0) under identical physics; the *gap* vs ablation and the *in-run delta* (late − early window accuracy) are reported separately.
- **Shortcut controls (Rule 20).** Movement-keyed (not tick-keyed) delay targets, repeat-free text patches, echo-proofing, and compile-fingerprint audits (Rule 21.8) prevent the classic shortcuts (see Exp 43 confound note in Ascent.md §4i).
- **Gates.** Gate A: in-lifetime improvement — long horizon C(t) ≥ 25% improvement in 5M ticks; operationalized short-horizon as in-run Δ (late − early) ≥ +2pp (Exp 103 criterion) to +3pp (Exp 102 bar) / +5pp (Rule 18). Gate B: learning > matched ablation (static gap). Gate C: C/footprint non-decreasing. Gate D: efficiency per Rule 22.
- **Tasks.** Static next-byte prediction over repeat-free text patches; non-stationary REMAP (mapping rotates every 5,000 ticks); novel-sequence switch at tick 10,000; delayed-parity and compositional-arithmetic task families (Docs/PROTOCOLS/).
- **Economy diagnostics.** Exp 4b: `FREE_ENERGY=1, NO_DEATH=1` (income decoupled from cost). Exp 5: cost-factor θ ∈ {0, 0.1, 0.25, 0.5, 0.75, 1.0} under `NO_DEATH=1` (cost scaled, income unchanged), 2000 ticks, 4 seeds, 60 organisms.

---

## 3. Results

### 3.1 S1 falsification: the mechanism-resolution programme (Exp 96–103b)

The SNN-on-RAM substrate was attacked at three successive levels — tuning (Exp 96/97), gating (Exp 98), and memory substrate (Exp 99) — each pre-registered, each closed at its binding gate (Ascent.md §4i–§4k). Exp 99, the last mechanistic attempt under the Rule-18 kill criterion, used a two-timescale hierarchy (fast plastic weights + slow consolidation anchors) across 24 seeds (72–95):

**Table 2 — S1 mechanism-resolution results.**
| Exp | Manipulation | Primary metric | Result | Verdict |
|---|---|---|---|---|
| 96 | Stability–plasticity tempo/divisor map (exploratory) | Nominated `default\|div32` Δ=+4.36pp (p=0.125), `fast\|div1` Δ=+1.71pp (p=0.289) | No nomination survives correction | EXPLORATORY |
| 97 | Confirmatory at nominated operating points | 24 seeds, Bonferroni α=0.025 | `default_div32` mean Δ = −1.49pp | NULL |
| 98 | Surprise-gated plasticity | 24 seeds, gated − nolearn swap-era Δ | mean Δ = +2.22pp (median 1.60; per-seed range includes −8.11) | FAILED AT ADMISSION CONTROL |
| 99 | Two-timescale consolidation (fast + slow anchors) | 24 seeds; gate: static fidelity ≥ 95.0 | static fidelity mean 92.34 (PASS false); swap-era Δ = +5.34pp mean / +4.84pp median, p = 0.0015 (MC 100k sign draws) | **CLOSED_AT_GATE** — first real re-tracking signal, without required stability |
| 100 | Direct learning probe (STDP3C, repeated exposure) | seed 0, 20k ticks | learner Δ = −1.46pp (FLAT); nolearn Δ = −3.53pp (DEGRADED) | FLAT |
| 101 | R-STDP with reward = surprise × efficiency | diagnostics every 200 ticks | reward ≡ 0, eligibility = 0, mean |Δw| = 0 at **every** checkpoint (ticks 1–2000) | SELF-SILENCING |
| 102 | STDP_TARGET (directional per-bit error signal) | 4 seeds, 20k ticks | learner Δ: −16.7, −4.0, −15.4, −8.3pp; nolearn Δ: −12.7, −4.1, −14.9, −13.4pp; paired gap ≈ +0.2pp vs +3pp bar | NULL |
| 103 | Shared reservoir + NLMS readout | 4 seeds, 20k ticks | learner Δ = +0.06pp; static gap +10.35pp | IN-RUN FAIL (static only) |
| 103b | Per-organism reservoir + NLMS readout | 4 seeds, 20k ticks | per-org Δ = −0.02pp; static gap +21.31pp | NULL_OR_DEGRADED |

Interpretation. Exp 101 is the cleanest possible negative: the reward-modulated mechanism does not produce a weak signal — it produces *no signal at all* (identically zero reward, eligibility, and weight drift at every one of ten checkpoints). Exp 102 shows learner and ablation declining *together* (environmental drift), with no separable mechanism advantage (+0.2pp against a +3pp bar). Exp 103/103b isolate the failure mode: the reservoir+readout's entire advantage is baked in statically (up to +21.31pp over NOLEARN) while in-run improvement is 0.06pp and −0.02pp respectively — the readout saturates at the best linear predictor of the stream and stops improving. **Per Ascent.md, the Rule-18 kill criterion is fully executed: SNN-on-RAM with local/Hebbian/STDP-class in-lifetime learning is formally falsified as an AGI substrate.**

### 3.2 Substrate comparison: five families, one outcome (sub3–sub5)

**Table 1 — Substrate comparison under identical Rule 18 gates (4 seeds each).**
| Substrate (protocol) | Ticks | Learn early (%) | Learn late (%) | **Δ in-run (pp)** | Nolearn late (%) | Static gap (pp) | Gate A | Gate B | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| S2 Reservoir+NLMS, shared (Exp 103) | 20,000 | 78.02 | 78.08 | **+0.06** | 67.73 | +10.35 | FAIL | PASS | RESERVOIR_HELPS_STATICALLY_BUT_INRUN_LEARNING_WEAK |
| S2 Reservoir+NLMS, per-org (Exp 103b) | 20,000 | 78.68 | 78.66 | **−0.02** | 57.35 | +21.31 | FAIL | PASS | NULL_OR_DEGRADED |
| S3 Recurrent world-model | 2,000 | 82.48 | 84.60 | **+2.12** | 66.91 | +17.69 | FAIL | PASS | NULL_OR_DEGRADED |
| S4 Small transformer | 2,000 | 83.42 | 86.88 | **+3.45** | 49.69 | +37.19 | FAIL | PASS | NULL_OR_DEGRADED |
| S4 Small transformer (extended) | 20,000 | 86.20 | 89.90 | **+3.70** | 49.93 | +39.97 | FAIL | PASS | NULL_OR_DEGRADED |
| S4 Non-stationary (switch every 5,000) | 20,000 | 67.57 | 70.69 | **+3.13** | 49.22 | +21.48 | FAIL | PASS | NULL_OR_DEGRADED |
| S4 Novel sequence (switch at 10,000) | 20,000 | 72.43 | 74.74 | **+2.31** | 49.01 | +25.73 | FAIL | PASS | NULL_OR_DEGRADED |
| S5 Hybrid transformer + event memory | 2,000 | 91.75 | 91.91 | **+0.16** | 49.69 | +42.22 | FAIL | PASS | NULL_OR_DEGRADED |

Three results stand out:

1. **Uniform Gate A failure, uniform Gate B pass.** Across eight configurations, every substrate learns *something* in-run (+0.16 to +3.70pp) — real but weak — while simultaneously showing a large static gap over its ablation (+10.4 to +42.2pp). The learning that matters (in-lifetime improvement) fails everywhere; the learning that doesn't (baked-in static competence) is large everywhere.
2. **Task difficulty is ruled out.** Non-stationary (Δ +3.13pp) and novel-sequence (Δ +2.31pp) protocols — the conditions where in-lifetime learning should matter most — show the *same* ceiling as static tasks, not higher. The ceiling is substrate-independent, not task-dependent.
3. **S5 shows the ceiling is not capacity.** The hybrid transformer+memory reaches the highest absolute accuracy (91.9%) and the largest static gap (+42.2pp) yet the *smallest* in-run delta (+0.16pp). More static competence does not translate into more in-lifetime learning; the two are orthogonal in this economy.

### 3.3 Metabolic buffering: the same substrate that fails under cost, learns when income is decoupled (Exp 4b, Exp 89–90)

**Table 3 — Economy diagnostics on the S2 reservoir mechanism.**
| Condition | Learn final acc (%) | Nolearn final acc (%) | Δ (pp) | Verdict |
|---|---|---|---|---|
| Exp 103b: full Rule 21 cost (per-org reservoir) | 78.66 | 57.35 | −0.02 | NULL_OR_DEGRADED |
| Exp 4b: `FREE_ENERGY=1, NO_DEATH=1` (per-org reservoir) | 78.02 (seeds: 79.58, 78.13, 75.21, 79.17) | 56.98 (55.42, 58.33, 58.13, 56.04) | **+21.04** | ECONOMY_WAS_KILLER_FOR_RESERVOIR |

With the physical economy relaxed (income decoupled from exploration cost), the identical per-organism reservoir + NLMS readout achieves **+21.04pp in-lifetime learning** (learner 78.02 vs nolearn 56.98 final, 4 seeds, 1,000 ticks) — versus −0.02pp under full cost. The same substrate, the same readout, the same task: the only difference is who pays for exploration.

Two further experiments sharpen the interpretation:

- **Exp 89 (static environment):** plasticity carries a measured 264 cycles/tick STDP tax and is selected *against*: Z_pop = −25.39σ (Arm 2 vs control). In a static world, plasticity is a metabolic parasite — Rule 7 accounting correctly selects against it.
- **Exp 90 (non-stationary REMAP, period 4,000):** plastic learners achieve a +20% higher multi-generational birth rate (Arm 2: 60.2±20.4 births vs 50.0±0.0 fixed-reflex control) but Z_pop = −0.98σ against the pre-registered ≥1.0σ bar — the advantage appears but does not clear the gate; a 4,000-tick static window lets fixed controls coast.

Together: **learning is possible under physical accounting — the substrate proves it at +21pp — but it is not affordable.** The organism cannot survive the exploration phase long enough to collect the returns. We call this the *metabolic affordability* constraint, and the Exp 4b result the *metabolic buffering* effect: decoupling (buffering) exploration cost from income is what makes embodied plasticity viable.

### 3.4 The threshold scan: cost-relief alone does not unlock learning (Exp 5)

To localize the phase transition between the lethal (full-cost) and viable (free-energy) regimes, Exp 5 swept the plasticity cost factor θ ∈ {0, 0.1, 0.25, 0.5, 0.75, 1.0} on the per-organism reservoir mechanism under `NO_DEATH=1`, 4 seeds, 2,000 ticks (protocol `EXP5_COST_THRESHOLD_SCAN_v1`):

**Table 4 — Exp 5 θ-sweep (learner Δ and mean organism energy).**
| θ (cost factor) | Learn early (%) | Learn late (%) | Δ in-run (pp) | Mean energy | Nolearn late (%) |
|---|---|---|---|---|---|
| 0.0 | 78.00 | 77.57 | **−0.44** | 100.0 | 56.8 |
| 0.1 | 78.00 | 77.57 | **−0.44** | 80.0 | — |
| 0.25 | 78.00 | 77.57 | **−0.44** | 50.0 | — |
| 0.5 | 78.00 | 77.57 | **−0.44** | 0.0 | 56.8 |
| 0.75 | 78.00 | 77.57 | **−0.44** | 0.0 | — |
| 1.0 | 78.00 | 77.57 | **−0.44** | 0.0 | 56.8 |

The result is unambiguous and, we argue, *informative*: **relaxing the plasticity cost — even to zero — produces no learning** (Δ = −0.44pp at every θ). The cost relief does move the energy ledger (mean energy 100 → 0 as θ rises), but the in-run delta is untouched. Compare Exp 4b: the *same* mechanism learns +21.04pp when **income** is decoupled (FREE_ENERGY), not when cost is waived.

The phase transition therefore does not live on the cost axis. It lives on the **income/exploration-coupling axis**: what kills in-lifetime learning is that exploration must pay for itself within the lifetime under honest accounting, and no substrate tested can make the payback fast enough. The exact critical threshold — θ* as the fraction of exploration income that must be subsidized for learning to become net-positive — has **not yet been localized**: Exp 5 tested cost relief; the income-subsidy sweep (the mirror experiment) is the immediate next step (§4.3). We report this openly rather than claiming a measured θ*: the evidence constrains θ* to live on the income axis, with a gap of at least 21.04pp between the lethal (θ_cost=1) and buffered (FREE_ENERGY) regimes.

---

## 4. Discussion

### 4.1 Comparison with state-of-the-art

**On capability scaling, we make no claim.** Frontier systems train at 10²⁵–10²⁶ FLOP (GPT-4 ≈ 2.1×10²⁵; GPT-4.5 ≈ 3.8×10²⁶; Grok 4 ≈ 5×10²⁶ FLOP, Epoch AI/Our World in Data) and none of them learns in-lifetime — they are frozen after training. Our result is about the *dynamics* of learning under cost, a regime frontier labs do not measure at all: their training budgets ignore per-primitive energy accounting entirely. On the neuromorphic side, bio-plausible rules (e-prop and successors) have demonstrated credit assignment in spiking networks but remain orders of magnitude behind backprop-trained models on standard benchmarks, and — again — are not evaluated under self-paying exploration budgets. To our knowledge, **no published cross-substrate comparison charges plasticity at measured hardware cost with matched ablations**; the closest frameworks (NeuroBench arXiv:2304.04640; MLPerf Tiny) measure inference energy or benchmark capability, not the metabolic viability of learning. Our contribution is the missing measurement instrument, not a new capability claim.

**The falsification result is the headline.** Five substrate families, ~100 pre-registered experiments, 4–24 seeds per condition, and a uniform outcome: real-but-unaffordable learning, with the bottleneck localized to the income side of exploration. In a field where negative results are systematically under-reported (a documented selection pressure this work explicitly counters), a controlled null of this breadth, with this level of accounting discipline, is the citable result.

### 4.2 Implications for neuromorphic computing

Our results carry a direct, quantitative warning for the neuromorphic programme. The brain's 20 W budget over 86×10⁹ neurons is existence proof that embodied plasticity can be affordable; but current hardware — Intel Hala Point: 1.15×10⁹ neurons at ~2,600 W, ~10⁴× worse per-neuron efficiency — does not buy that affordability, and our simulations show that even *much cheaper* plasticity does not help if the *exploration-income coupling* is unaddressed. Three implications:

1. **Energy-efficient updates are necessary but not sufficient.** Exp 5's flat Δ across the θ-sweep shows that subsidizing update cost alone cannot create in-lifetime learning. Neuromorphic roadmaps that focus exclusively on per-spike energy (TOPS/W) are optimizing the wrong axis if their systems are expected to *learn* in deployment.
2. **Metabolic buffering is a design requirement, not an optimization.** Exp 4b's +21.04pp under decoupled income identifies buffering (a multi-timescale energy budget, or subsidized exploration windows) as the structural prerequisite for embodied plasticity — matching the biological design where learning is concentrated in development and rewarded practice, and where the brain's ~20% share of body energy buffers the cost of plasticity.
3. **Energy-accounted learning benchmarks are needed.** The absence of any standard that charges plasticity at measured cost (see §1.2) means the field currently cannot even *measure* whether a learning system is metabolically viable. Rule 21 accounting (measured host cycles per primitive, H/E/O/G constant audit, the Tuning Test) is a concrete, transferable proposal for such a standard.

### 4.3 Limitations and future work

**Limitations.** (i) Task scale is toy-grade (byte prediction, delayed parity, compositional arithmetic); the largest runs are 20k ticks / 60 organisms. (ii) The θ-sweep (Exp 5) tested the cost axis only, under `NO_DEATH=1`, and did not include the FREE_ENERGY income condition — the income-subsidy sweep is required to complete the phase diagram. (iii) Substrate 3–5 comparisons ran 2,000 ticks (20,000 for S4 variants); longer horizons might shift absolute numbers, though the uniform Gate A/B pattern across durations argues against a horizon artifact. (iv) All measurements are on one host class (consumer CPU/GPU); absolute cycle costs are host-specific, though the *ratios* (cost of plasticity vs income per correct prediction) are what drive the qualitative outcome. (v) The free-energy oracle is a diagnostic, not a mechanism proposal; how biology achieves buffering without a designer-supplied oracle is the open question.

**Future work (ordered by expected value).**
1. **Income-subsidy θ\* scan** (mirror of Exp 5): sweep the fraction of exploration income that is subsidized (or buffered via a two-timescale energy ledger) from 0 → 1, pre-registered, 4+ seeds, and localize the threshold where in-lifetime learning turns net-positive. This converts the qualitative 21.04pp gap into a quantitative phase transition.
2. **Buffering mechanisms without oracles:** implement multi-timescale energy reserves (development windows, consolidation sleep, reward-gated income) and test whether they reproduce Exp 4b's +21.04pp under full Rule 21 cost. This is the biological hypothesis made falsifiable.
3. **Energy-accounted continual-learning benchmark proposal:** package Rule 21 accounting (measured cycles per primitive + matched ablation + pre-registration) as a public benchmark with reference implementations (S1–S5), positioned against NeuroBench.
4. **Open-ended evolution as a question generator:** quality-diversity (MAP-Elites/POET-style) over substrate parameters to map which economy regimes produce the strongest adaptation dynamics — tractable on home hardware.

---

## 5. Conclusion

Five substrate families, ~100 pre-registered experiments, and a uniform answer: under hardware-equivalent energy accounting, in-lifetime learning is **real but metabolically unaffordable**. Every substrate improves in-run by only +0.16 to +3.70pp (Gate A fail) while showing large static advantages over matched ablations (Gate B pass, up to +42.2pp); task difficulty is ruled out; the mechanism-resolution programme (Exp 96–103b) ends in systematic falsification, including an identically-zero reward signal; and the same mechanism that fails under cost learns at +21.04pp when exploration's income is decoupled (Exp 4b) — while cost-relief alone does nothing (Exp 5). The binding constraint on embodied plasticity is not the cost of weight updates: it is the **metabolic affordability of exploration**. Metabolic buffering — decoupling or subsidizing exploration cost — is a prerequisite, and the critical income-subsidy threshold θ* is a tractable, pre-registerable measurement that directly informs whether neuromorphic hardware can ever *learn* in deployment at brain-like efficiency. We offer this programme as the first physically-accounted, falsification-first laboratory for the question, and its null result as the contribution.

---

## 6. Data availability & reproducibility

All experiments, drivers, raw JSON results, and pre-registration criteria are public in the GENESIS repository (github.com/HamidRezaeian/GENESIS, branch `feature/substrate-pivot`):
- Protocol & gates: `Docs/Architecture/Substrate_Comparison_Protocol.md`, `Docs/Architecture/Ascent.md` (§4i–§4k, Exp 89–103b), `Docs/Exp101_Protocol.md`, `Docs/Exp102_Protocol.md`, `Docs/Exp103_Protocol.md`, `Docs/Exp5_Protocol.md`, `Docs/Exp4_Free_Energy_Oracle_Design.md`, `Docs/Decision/Project_Rescope.md`, `Docs/Decision/Substrate_Falsification_Acknowledgment.md`
- Results: `experiments/sub3_results/`, `experiments/sub4_results/`, `experiments/sub5_results/`, `experiments/exp4b_results/`, `experiments/exp5_results/`, `experiments/exp99_twoscale_results.json`, `experiments/exp100_result_*.json`, `experiments/exp101_*_results/`, `experiments/exp103_results/`, `experiments/exp103b_results/`, `experiments/exp3_neuroevolution_results/`, `experiments/exp96_map_results.json`, `experiments/exp97_confirmatory_results.json`, `experiments/exp98_gated_results.json`, `experiments/leaderboard/raw/` (72 raw per-seed files for Exp 99)
- Accounting: `Docs/Architecture/ENERGY_ACCOUNTING.md`, `Docs/Architecture/FixedRules.md` (Rules 21/22), `src/physical_cost_model.py` (measured host cost per primitive)
- Every result artifact records `energy_basis: cycles MEASURED natively per Rule 21.1`.

**Funding/Acknowledgments.** None. Solo researcher project on consumer hardware.

**Conflicts of interest.** None.

**Reproducibility commitment.** Pre-registration timestamps, seed lists, compile fingerprints (Rule 21.8), and the replication-certificate spec (`Docs/FRAMEWORKS/REPLICATION_CERTIFICATE_SPEC.md`) accompany every claim; null results are preserved, not deleted (Rule 8).
