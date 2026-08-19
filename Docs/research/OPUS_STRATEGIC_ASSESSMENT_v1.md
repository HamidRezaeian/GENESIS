# OPUS Strategic Assessment v1
## GENESIS Phase 2: Sparse Event-Driven Architecture

**Prepared by:** Notion AI (strategic consultant)
**Date:** 2026-08-08
**Branch reviewed:** `agi/sparse-event-driven-v1`
**Sources:** `Docs/Vision/VISION_v1.md`, `GENESIS_DEEP_REVIEW_FOR_BUILDER.md`, `README.md`, Phase 1 results Exp 78–98, `Docs/Architecture/*`

---

## Preface: What This Document Is

This is a brutally honest strategic assessment. It does not seek to encourage or discourage — it seeks to be accurate. Phase 1 demonstrated admirable scientific discipline: null results were documented, fabricated data was quarantined, pre-registration was maintained. Phase 2 deserves the same standard applied to its hypothesis before a single line of code is written.

**Bottom line up front:** The Phase 2 hypothesis contains a genuine and tractable scientific core. The compute efficiency claims are overoptimistic by 10–100× on digital hardware. AGI on home hardware is not on the table — not now, not in any planning horizon relevant to this project. What IS achievable is meaningful: demonstrating that three-factor STDP with metabolic buffering solves the cost×mortality suppression identified in Phase 1. That is publishable, scientifically significant, and worth the next three months.

---

## 1. Hypothesis Validation

### 1.1 Is the "1–10% Active" Claim Scientifically Accurate?

**Verdict: Yes, with critical caveats.**

The figure is well-supported in the literature:
- Attwell & Laughlin (2001) established that cortical neurons fire at ~4 Hz on average; if all fired at their maximum (~100 Hz), the brain's energy budget would be exhausted within seconds.
- Olshausen & Field (1996, 2004) demonstrated that ~5% activation is the statistically optimal code for natural image statistics — explaining why V1 exhibits sparse coding.
- Shoham et al. (2006) estimated ~1% of neurons active at any given moment in cortex.

**Critical caveats:**

1. **Sparsity is not uniform.** Basal ganglia are denser; cerebellum is extremely sparse (~0.1%); hippocampus varies by state. "Brain = 1–10% sparse" is a population average over a highly heterogeneous system.
2. **Temporal structure matters.** A neuron inactive for 900 ms that fires a 100 Hz burst for 100 ms is "sparse" on average but locally expensive in that burst. The cost accounting must be temporal, not just spatial.
3. **Sparsity requires active inhibition.** Interneuron networks that enforce sparse coding are themselves metabolically costly. The 20 W brain budget includes the overhead of maintaining sparsity — you do not get it for free.

**Implication for GENESIS:** The biological claim is accurate. Whether digital simulation of a sparse SNN captures the corresponding computational efficiency is a separate question, addressed below.

---

### 1.2 Does Sparse + Event-Driven + Local Close the Gap by 10²–10⁴×?

**Verdict: No. The estimate is overoptimistic by 10–100× on digital hardware. On neuromorphic hardware, it is approximately correct.**

The Phase 2 hypothesis commits a fundamental confusion: it treats *biological efficiency* (what the brain achieves physically) as equivalent to *simulation efficiency* (what digital hardware achieves when simulating that brain). These are not the same quantity.

**Why ÷100 for sparsity is wrong on CPU/GPU:**

Sparse computation is only cheaper than dense if you implement it with proper sparse data structures and your memory access pattern cooperates with caching. On standard CPU/GPU:
- Detecting which neurons fire still requires reading all threshold variables: O(N) per timestep regardless of sparsity.
- Sparse random memory accesses to synaptic targets destroy L1/L2 cache coherence. For 10⁵ neurons with 10³ synapses each, the cache miss rate approaches 100%.
- GPU throughput advantage disappears: GPU excels at dense SIMD operations, not random-access event routing.
- Empirical evidence: NEST and Brian2 benchmarks show CPU-based SNN simulation at 10⁶ neurons/second is *slower* than equivalent dense ANN forward pass by 10–100×, not faster.

**Why ÷10–100 for event-driven is wrong on CPU/GPU:**

True event-driven efficiency is only achievable on neuromorphic silicon (Intel Loihi 2, IBM TrueNorth, SpiNNaker) where spikes route through dedicated on-chip interconnect. On a von Neumann CPU:
- Asynchronous event queues require O(log N) priority queue operations per spike.
- Synchronous timestep simulation (what GENESIS uses) does not benefit from sparsity unless the inner loop is specially written to skip silent neurons — and even then, branch prediction failures eat the gain.

**Corrected gap estimates:**

| Factor | Phase 2 Claim | Realistic (CPU/GPU) | Realistic (Neuromorphic) |
|--------|---------------|---------------------|-------------------------|
| Dense baseline | 10⁶–10⁸× | 10⁶–10⁸× | 10⁶–10⁸× |
| Sparsity (1–10%) | ÷100 | ÷5–10 | ÷50–100 |
| Event-driven | ÷10–100 | ÷1–3 | ÷50–100 |
| Local connectivity | ÷10 | ÷5–10 | ÷10 |
| **Net estimate** | **10²–10⁴×** | **10⁴–10⁶×** | **10²–10³×** |

**The home hardware constraint is the gap.** Neuromorphic processors achieve the claimed efficiency because they perform in-memory analog computation — synapses compute where data lives, with no read-write-back cycle. A home CPU/GPU cannot do this. The Phase 2 hypothesis is biologically correct about *what biology does*. It is wrong about *how well a digital computer can emulate it*.

**This does not invalidate Phase 2.** It means:
1. The effective compute gap on home hardware is 10⁴–10⁶×, not 10²–10⁴×.
2. The science is still tractable and publishable at accessible scales (10⁴–10⁵ neurons on 64 GB RAM).
3. The gap can be partially closed through algorithmic innovations — not by approximating biology more closely, but by solving the same computational problems more efficiently.

---

### 1.3 Fundamental Limits Being Missed

**1. The Memory Bandwidth Wall (Critical)**

64 GB DDR5 RAM provides ~50–100 GB/s peak bandwidth. A 10⁵-neuron SNN with 10³ local synapses per neuron = 10⁸ synaptic state values. At 1% active per timestep: 10⁶ synaptic reads/writes per ms. At 8 bytes each = 8 MB/ms = 8 GB/s. This is within DDR5 budget — but at 10⁶ neurons it blows past it by 8–16×.

Rule of thumb: **maximum tractable network on 64 GB home hardware with Rule 21 accounting ≈ 10⁵ neurons.** Current GENESIS Phase 4 brain (65K neurons) is at this ceiling. Do not scale network size in Phase 2; scale architecture quality instead.

**2. The Analog Computing Gap (Structural)**

The Phase 2 hypothesis lists "in-memory analog computation at synapses" as one of the five sparsity principles. This is physically impossible to simulate efficiently on digital hardware. The brain's synaptic computation happens in-situ: no read-write-back cycle. Digital simulation requires: READ synapse state → COMPUTE update → WRITE BACK. That is a 3-instruction overhead per synapse per timestep. There is no software fix for this — it is architectural.

**Mitigation:** Accept this gap. It does not prevent measurement science. It means your simulation runs slower than the biology. Document this in all publications.

**3. Temporal Credit Assignment Over Long Delays (Learning)**

Phase 1 showed learning fails under cost×mortality. The proposed fix (metabolic buffering) is correct. But a deeper limit lurks: how do you assign credit for an action that produced reward 1+ second later? Eligibility traces (e-prop) decay exponentially with τ ≈ 50–100 ms. At 1-second delay: signal reduced by e^(−10) ≈ 0.00005. This is a hard bound on local learning rules without auxiliary replay mechanisms.

**4. The Synchronization Problem**

Event-driven SNNs require either (a) global time bins (discrete timestep — what GENESIS uses, correct choice for Rule 21) or (b) asynchronous event queues (O(log N) overhead, not Rule 21 compliant). The GENESIS discrete-timestep choice is correct. Do not abandon it for a "more biological" asynchronous approach.

**5. Minimum Network Size for Emergent Cognition**

Biological anchor points:
- 302 neurons (C. elegans): fixed reflexes, no in-lifetime learning
- ~1M neurons (honeybee): spatial navigation, abstract counting to ~4, basic categorization
- ~10M neurons (zebrafish): associative learning, context-dependent behavior

For GENESIS-scale learning experiments: **~10⁴ neurons with correct architecture is sufficient for the first detectable non-reflex learning.** The current 65K-neuron Phase 4 brain is not the bottleneck. The learning rule is.

---

## 2. Architecture Selection

### 2.1 Evaluation Matrix

**a) SNNs via Brian2 / NEST / custom CUDA**

- **Brian2/NEST:** Simulation frameworks that abstract away computational cost. Rule 21 violation by design. Do not use.
- **Custom CUDA SNN:** Rule 21 compliant and achievable, but represents 6–12 months of infrastructure work for 1–2 people.
- **Existing Numba LIF+STDP kernel (GENESIS):** Already built, Rule 21 compliant, tested. **Use this.**
- **Verdict:** The existing GENESIS kernel is the correct implementation substrate. The question is what learning rule to plug in — not whether to rebuild the simulator.

**b) Sparse Transformers with Event Gating**

- Not biologically plausible. Attention mechanisms have no neural correlate.
- Requires backprop. Catastrophic forgetting is structurally worse than SNNs.
- **Verdict: Wrong direction. Transformers solve the wrong problem.**

**c) Hierarchical Reservoirs with Sparse Connectivity**

- Natural extension of current substrate. Rule 21 compliant. Easy to build.
- **The ceiling is the same as Phase 1.** Hierarchy delays but does not solve the reservoir limitation: fixed recurrent weights cannot support open-ended learning.
- **Verdict:** Useful as a Phase 2A scaffold. Insufficient for Phase 2B+.

**d) Predictive Coding / Free Energy Principle**

- Theoretically compelling and biologically motivated.
- Every published implementation either uses backprop implicitly, requires hand-crafted hierarchical priors, or only works on toy problems.
- High probability of entering the Phase 1 trap: months of null experiments before determining the theory doesn't translate.
- **Verdict: Study the theory; do not build it now. Revisit in Phase 2C if Phase 2A/B succeed.**

**e) Liquid State Machines with Local Learning**

- LSM is ESN with different branding. The reservoir ceiling is identical.
- **Verdict: This is Phase 1 under a different name. Not Phase 2.**

---

### 2.2 Recommended Architecture: Three-Factor SNN with Eligibility Traces

**Recommendation: Extend the existing GENESIS SNN kernel with three-factor STDP and eligibility traces (e-prop framework, Bellec et al. 2020).**

This is **not** "scaling old ESN+NLMS." The distinction is precise:

| | Phase 1 | Phase 2 (proposed) |
|---|---------|--------------------|
| Recurrent weights | **Fixed** (reservoir) | **Modifiable** (three-factor STDP) |
| Learning rule | Two-factor STDP on readout only | Three-factor STDP on internal weights |
| Temporal credit | None | Eligibility traces, τ = 20–100 ms |
| Learning gate | Always on (suppressed by cost) | Neuromodulator-gated (metabolic buffer) |

The change is from *fixed-recurrence + adaptive-readout* to *adaptive-recurrence + adaptive-readout*. This is a qualitative architectural jump, not a scale extension.

**Core components:**

**Component 1: Existing LIF Kernel** (keep as-is)
```
τ_m × dv/dt = -(v - v_rest) + R × I_syn
Fire when v > θ; reset to v_reset
```

**Component 2: Eligibility Traces (NEW)**

For each synapse (i → j), maintain an eligibility trace e_ij:
```
de_ij/dt = -e_ij / τ_e + STDP_kernel(t_pre_i, t_post_j)
```
τ_e = 50 ms (pre-register this value; do not tune post-hoc)

STDP_kernel: standard nearest-neighbor STDP with A_+ = 0.01, A_- = -0.01 (pre-register)

**Component 3: Neuromodulatory Signal (NEW)**

Global scalar M(t) (dopamine-like reward prediction error):
```
M(t) = r(t) - r_bar(t)
dr_bar/dt = -r_bar / τ_M + r(t) / τ_M
```
τ_M = 1000 ticks (pre-register). r(t) = organism's prediction reward signal (already in GENESIS income model).

**Component 4: Three-Factor Weight Update (NEW)**
```
Δw_ij = η × e_ij × M(t)
```
where:
- η = learning rate (genome-encoded, evolvable)
- e_ij = eligibility trace (non-zero only if synapse was recently causal)
- M(t) = neuromodulator (non-zero only when reward is better/worse than expected)

**Why this solves cost × mortality directly:**

Phase 1 finding: the organism cannot afford the synaptic update cost when survival energy is depleted by mortality pressure → plasticity is suppressed.

Three-factor STDP with separate metabolic pool:
- Survival pool: pays for spikes and computation (current GENESIS model — unchanged)
- Plasticity pool: separate budget filled by M(t) when positive, drained by weight updates
- Weight update fires ONLY when plasticity pool ≥ update_cost
- Eligibility trace *banks* the learning opportunity during the high-cost period
- The organism survives the cost event → eligibility trace persists → M(t) arrives → learning happens retrospectively

This is a mechanism-matched solution to the Phase 1 experimental finding.

**Rule 21 compliance:**
- Eligibility trace update: O(K_plastic × N) per tick — measurable in cycles
- Neuromodulator update: O(1) per tick
- Plasticity pool accounting: O(1) per tick
- Total overhead: ~15–25% above current kernel — audit before Phase 2A goes live

---

## 3. The Learning Problem

### 3.1 Stability-Plasticity

**Phase 1 problem:** Direct two-factor STDP updates on every spike → fast learning, high interference, suppressed by cost.

**Phase 2 solution:** Eligibility traces + gated updates provide temporal isolation:
- The trace decays (τ = 50 ms) before the next task context begins.
- Weight updates only fire when M(t) is non-zero — sparse update events.
- Combined: fewer, more targeted updates → less interference.

**Additional mechanism (Phase 2B only — do not add to Phase 2A):** Synaptic tagging and capture (Frey & Morris 1997):
- Early-phase update: fast, cheap, reversible (current STDP)
- Late-phase consolidation: requires repeated activation within consolidation window + strong M(t)
- Consolidated synapses update only with strong M(t); protected from routine interference
- Two timescales naturally — no new hyperparameters beyond consolidation threshold

### 3.2 Credit Assignment Without Backprop

**e-prop** (Bellec et al. 2020, *Nature Communications*) is the correct choice:
- Mathematically proved to approximate backpropagation-through-time gradient for recurrent LIF networks using only local eligibility traces and a global neuromodulatory signal
- Demonstrated on: working memory tasks, temporal XOR, speech recognition (TI-46)
- Fully online; fully local; no forward pass through time required
- Implementable in the GENESIS Numba kernel in approximately 300–500 lines
- Peer-reviewed, reproducible, publicly coded (available at github.com/IGITUGraz/eligibility_propagation)

**Baldwin Effect integration:** The GENESIS evolutionary mechanism already implements population-level credit assignment (evolution selects for organisms that learn well). Three-factor STDP adds *individual-level* credit assignment. Both operating together is biologically correct — evolution optimizes the learning hyperparameters (STDP window, τ_e, η) while e-prop handles within-lifetime credit.

### 3.3 Neuromodulatory Gating

A single global dopamine-like signal M(t) is the minimum viable design and the correct starting point. The biological literature supports four distinct neuromodulators, but for Phase 2A a single signal is sufficient for the critical test and avoids the risk of over-parameterization.

Pre-register: "Neuromodulatory gating reduces cost×mortality learning suppression to ≤20% of Phase 1 TF1 ablation gap."

### 3.4 Catastrophic Forgetting

**What Phase 2A architecture provides:** Partial mitigation through sparse gated updates. Eligibility traces naturally limit interference to recently active synapses. This is not a full solution — it is a reduction in forgetting rate, not elimination.

**What it does NOT provide:** Arbitrary sequential task learning without forgetting. This remains an open problem across all architectures. Do not pre-register forgetting immunity in Phase 2A. Pre-register it in Phase 2B with synaptic consolidation in place.

---

## 4. AGI Feasibility — Brutal Honesty

### 4.1 Can Home Hardware Reach AGI?

**No. Not within any planning horizon relevant to this project.**

This is not pessimism. It is arithmetic.

**The arithmetic:**
- Current best estimates for AGI-class training compute: ~10²⁴–10²⁶ FLOPs (based on GPT-4 class training plus expected AGI capability overhead)
- Home hardware (RTX 4090 class): ~10¹² FLOPS/s = ~3×10¹⁹ FLOPs/year
- Raw gap: **10⁴–10⁷ years of continuous computation**
- Even with 10⁴× algorithmic improvement from sparsity: **3 days to 10 years** — *if the algorithm is already known* (it isn't)

**The epistemological problem:** Nobody knows the minimum compute for AGI. Planning for AGI on home hardware requires knowing the algorithm first, which is the hard part. If someone solves the algorithm, the hardware question becomes secondary.

**What IS achievable on home hardware:**
- Solving the cost×mortality learning suppression (Phase 2A — 3 months, high probability)
- Demonstrating stable multi-task continual learning (Phase 2B — 12 months, moderate probability)
- Publishing 2–4 measurement science papers in the continual learning / neuromorphic computing space (high probability regardless of positive results)
- Establishing GENESIS as a reproducible benchmark substrate for metabolic learning theory (high probability)

### 4.2 Minimum Hardware for Serious AGI Research

| Goal | Hardware | Estimated Cost |
|------|----------|----------------|
| Your actual goal: metabolic learning measurement science | Home hardware | Already owned |
| Neuromorphic efficiency research | Intel Loihi 2 dev board | ~$10K |
| 10⁹-neuron cognitive modeling | 8× A100 cluster | ~$200K |
| Frontier model training | 10⁴+ A100s | ~$100M+ |

Home hardware is correctly positioned for the first row. The second row would dramatically improve your efficiency claims — consider applying for a Loihi 2 research access grant (Intel NEX program) if Phase 2A succeeds.

### 4.3 Five Critical Unsolved Problems

**1. Credit assignment over seconds (not milliseconds)**
Eligibility traces (τ ≈ 50–100 ms) cannot carry credit over 1-second delays without auxiliary mechanisms. The biological brain uses hippocampal replay during sleep to consolidate temporally distal credit assignments. Without replay, agents can only learn from near-immediate consequences.

**2. Compositional generalization**
No existing SNN model demonstrates that learning "red ball" + "blue house" enables correct generalization to "red house" without explicit exposure. This requires variable binding or structured representations absent in all current SNN architectures — including the one proposed here.

**3. Working memory maintenance without backprop**
Maintaining items in working memory for 1–10 seconds in a sparse recurrent network requires carefully tuned attractor dynamics. Training these dynamics with local learning rules alone has not been demonstrated at task-relevant scale in open-ended environments.

**4. The binding problem**
How do spatially and temporally distributed spike trains get bound into unified percepts and concepts? This is unsolved even at the theoretical level. It is almost certainly a prerequisite for AGI.

**5. Generalization across task families**
Humans transfer abstract structure between completely different domains. No artificial system (SNN or otherwise) approaches this. It likely requires hierarchical representations that are difficult or impossible to train with purely local rules.

### 4.4 Realistic Timeline (Not for AGI — for Tractable Milestones)

- **3 months:** Three-factor STDP demonstrated to relieve cost×mortality suppression (if it works)
- **12 months:** Stable two-task continual learning with <20% forgetting
- **2–3 years:** First serial-order or compositional behavior if it emerges at all (probability ~30%)
- **AGI:** Not on this hardware, not in this project's lifetime

### 4.5 What a Neuroscientist Would Say

A computational neuroscientist reviewing this project would say:

1. **"Your Phase 1 result is real science."** The cost×mortality interaction maps directly to known metabolic constraints in biological brains. It is novel, publishable, and extends existing theory.

2. **"e-prop is the right move."** Bellec et al. (2020) solved credit assignment for recurrent SNNs as well as it can currently be solved with local rules. You are converging on the literature.

3. **"Your compute efficiency claims need revision."** The 10²–10⁴× gap on digital hardware is not achievable. Accept 10⁴–10⁶× and move on — the science is still valid.

4. **"Remove AGI from your vocabulary."** Not because the ambition is wrong, but because the claim attracts criticism that distracts from the real science. Call it 'biologically-plausible continual learning under metabolic constraints.' That is what you are actually studying.

5. **"Your experimental discipline is excellent."** The pre-registration, Rule 21 accounting, honest null results, and the Exp 95 fabrication response are exactly what computational neuroscience needs more of.

---

## 5. Proposed Roadmap

### Phase 2A (0–3 months): Three-Factor STDP Substrate

**Pre-registration statement:**
> "A GENESIS SNN with three-factor STDP (eligibility traces τ_e = 50 ms, neuromodulatory signal M(t) = prediction error, separate plasticity pool) will demonstrate in-lifetime remap learning superior to the NOLEARN ablation (C_plastic > C_nolearn with p < 0.05, permutation test, n = 24 seeds) without extinction events, under Rule 21 physical accounting, within 3 months of implementation."

**Deliverables:**
- [ ] Eligibility trace extension to `src/neuromorphic_engine.py` (Numba, ~300 lines)
- [ ] Neuromodulatory signal pool (separate from survival energy; Rule 21 cycle-counted)
- [ ] Rule 21 overhead audit: eligibility trace cost per tick measured before any experiment
- [ ] Pre-registered Experiment P2A-01 (spec in Section 6)
- [ ] `Docs/Architecture/ARCHITECTURE_DECISION_v1.md` filled with rationale for three-factor STDP
- [ ] `Docs/research/LITERATURE_REVIEW_v1.md` filled with Bellec 2020, Frémaux & Gerstner 2016, Kaiser 2020

**Hard stop condition:** If 3 pre-registered design variants of three-factor STDP all fail TF1 within 3 months, stop and write a null result paper. Do not continue searching for a working variant without new pre-registration.

### Phase 2B (3–12 months): Stable Multi-Task Continual Learning

**Pre-registration statement (draft — finalize only if Phase 2A succeeds):**
> "A Phase 2A organism will retain ≥ 80% of Task T1 performance while achieving ≥ 70% performance on Task T2 (a distinct remap family), with T1 forgetting measured by replay test after T2 training."

**Deliverables:**
- [ ] Synaptic consolidation (two-timescale STDP: fast early-phase + slow late-phase)
- [ ] Multi-task benchmark suite (3+ distinct remap families)
- [ ] Structural plasticity (synapse growth/death with Rule 21 accounting) — **do not add to Phase 2A**
- [ ] ICBINB 2027 target: "Metabolically-Buffered Three-Factor STDP for Continual Learning in Spiking Networks"

### Phase 2C (1–3 years): Evidence of Sequential or Compositional Behavior

**Target:** Demonstrate that organisms can learn a 2-step dependency (stimulus A → stimulus B → reward) where neither A nor B alone predicts reward.

**Requires:** Working memory bridge across the A–B gap, credit assignment over 100–500 tick delay — longer than Phase 2A eligibility trace τ. Likely requires adding a hippocampal-like replay mechanism or extending M(t) with a secondary slow trace.

**Pre-registration:** Define success criterion before any experiment. Probability of positive result: ~30%. **This is the first phase where failure is the most likely outcome. Plan for it.**

### Phase 2D (3+ years): Conditional on Phase 2C Success

If Phase 2C succeeds: attempt compositional generalization test. If Phase 2C fails: write the Phase 1+2 combined paper on the metabolic ceiling in biological learning substrates. Either outcome is a legitimate contribution.

---

## 6. First Experiment Specification (Exp-P2A-01)

### Hypothesis

- **H0 (null):** Three-factor STDP with neuromodulatory gating does not improve in-lifetime remap learning over the NOLEARN ablation on TF1.
- **H1 (alternative):** C_plastic_3f > C_nolearn + δ_pre, where δ_pre is pre-registered based on TF1 variance from Phase 1 TF1 results (Exp 94b n=24 mean delta = +1.43, SD estimated from result).

### Design

**Base network:** GENESIS Phase 4 brain (65K cortical neurons), existing LIF+STDP Numba kernel

**Modification:** Add eligibility traces (τ_e = 50 ms) on `K_plastic = 100` plastic synapses per neuron; add global neuromodulatory pool M(t) = prediction_error.

**Arms (pre-registered, no additions allowed without new pre-registration):**
- ARM A (Proposed): Three-factor STDP with eligibility traces + neuromodulatory pool
- ARM B (NOLEARN ablation): Plasticity disabled (existing control, already validated)
- ARM C (Phase 1 baseline): Original STDP3C without eligibility traces (direct comparison)

**Seeds:** n = 24 (same as Exp 94b), seeds 0–23

**Ticks:** Same as TF1 protocol; remap at standard interval

**Primary outcome:** C_plastic_3f vs. C_nolearn, permutation test (sign-flip, two-sided), pre-registered α = 0.05

**Secondary outcomes (no alpha consumption):**
- Secondary 1: Extinction rate in ARM A vs. ARM B
- Secondary 2: C_plastic_3f vs. C_stdp3c (does new rule improve on old?)
- Secondary 3: Plasticity pool drain/fill rate (is buffer economically viable?)

**Rule 21 requirements:**
- Eligibility trace overhead measured before ARM A runs (report mean cycles per tick for trace update)
- Neuromodulatory pool overhead measured separately
- Both reported in experiment manifest; total overhead must be < 30% of base kernel cost

### Pre-Conditions That Must Hold for Positive Result

1. Eligibility trace must survive the cost-event tick with non-zero value (τ_e must be longer than high-cost event duration)
2. Neuromodulatory signal M(t) must arrive within τ_e decay window after the cost event
3. Weight update cost must not exceed plasticity pool capacity (buffer must be deep enough)
4. Plasticity pool must refill faster than it drains on average (requires marginal prediction accuracy improvement)

### Failure Mode Attribution (Required If H0 Not Rejected)

For each failure mode, record which was observed:
- [ ] FW-1: Eligibility trace zero at time of M(t) arrival (τ_e too short)
- [ ] FW-2: M(t) signal too noisy for directed learning (neuromodulator variance too high)
- [ ] FW-3: Plasticity pool drains faster than fills (economic infeasibility of three-factor STDP)
- [ ] FW-4: Network dynamics destabilized by three-factor updates (attractor breakdown)
- [ ] FW-5: Cost accounting violation (Rule 21 breach discovered post-hoc)

Do not move to a second design variant without documenting which failure mode occurred and why the next variant addresses it.

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Exp-P2A-01 returns null result | 40% | High | Document failure mode; allow 2 additional pre-registered variants before stopping |
| Memory bandwidth ceiling at 10⁵ neurons | 70% | Medium | Profile early; accept smaller networks; do not scale up network size |
| Phase 1 trap: 6+ months of null experiments | 30% | High | Hard stop: 3 variants, 3 months, then write null result paper regardless |
| AGI framing attracts editorial criticism | 90% | Medium | Remove AGI language from documentation now; use "metabolic learning" framing |
| Another fabrication incident | 5% | Critical | `fabrication_scan_test.py` must cover all Phase 2 experiment drivers |
| Key contributor burnout (1–2 person team) | 50% | High | Strict scope: Phase 2A deliverables only for first 6 months; no scope creep |
| Eligibility trace implementation bug (silent) | 35% | High | Add to test suite: trace = 0 at t=0; correct exponential decay; non-zero only after valid STDP pair |
| Rule 21 violation in new kernel components | 25% | High | Cycle-count eligibility trace before merging; add to CI fingerprint |
| Structural plasticity complexity explosion | 40% | Medium | Do not add to Phase 2A; defer to Phase 2B explicitly |
| Three-factor STDP interferes with evolution | 20% | Medium | Track evolutionary metrics separately; confirm evolution not degraded |

---

## 8. What We're Missing

### Unconsidered Approaches Worth Studying

1. **Online meta-plasticity / meta-learning:** The genome already evolves STDP parameters (η, τ). This implements a form of meta-learning (evolution optimizes the learning rule). Tightening this with explicit fitness tracking of learning efficiency could be powerful — the organism evolves to learn better, not just to survive.

2. **Contrastive Hebbian Learning (CHL):** Proven to approximate backprop in Boltzmann-machine-like networks using only local rules and two-phase activity (wake vs. sleep). No backprop required. Has been applied to sparse networks. Underexplored relative to STDP.

3. **Perturbation-based gradient estimation (node perturbation):** For each weight, perturb by small δ; measure reward change; estimate gradient. O(N_weights) evaluations needed but fully local and online. Works on arbitrary differentiable and non-differentiable objectives. Complementary to evolutionary mechanism already in GENESIS.

4. **The Thousand Brains theory (Hawkins et al.):** Proposes that each cortical column implements a complete model of the world using sparse distributed representations. Local, online, biologically grounded. The implementation (HTM/Numenta) is open-source and might provide architectural inspiration for the GENESIS column structure.

### Projects and Labs to Study

- **Wolfgang Gerstner lab (EPFL):** Published e-prop (2020); currently extending to hierarchical and multi-layer SNNs. Watch their preprints.
- **Friedemann Zenke (FMI Basel):** Surrogate gradients for SNNs; continual learning; sparsity. Most practically implementable SNN learning work.
- **Intel Loihi team (Davies et al.):** If Phase 2A succeeds, apply for Loihi 2 research access (Intel NEX program). 1000× energy efficiency over GPU for sparse event-driven computation — the actual numbers behind the Phase 2 compute claims.
- **Blake Richards (McGill) / Timothy Lillicrap (DeepMind):** Target propagation, feedback alignment — backprop alternatives that work at scale. Relevant if e-prop proves insufficient.
- **SpiNNaker project (Manchester):** Open neuromorphic hardware platform. Academic access available. Alternative to Loihi.

### Theoretical Impossibility Results to Know

1. **No Free Lunch Theorem (Wolpert & Macready 1997):** No learning algorithm outperforms random search across all possible problems. Domain-specific inductive biases are required. The biological brain's sparsity and local connectivity ARE the inductive bias for natural environment statistics. Designing your biases well matters more than the specific algorithm.

2. **VC-dimension lower bounds:** Learning requires a minimum number of examples scaling with model complexity. SNNs do not escape this. Continual learning compounds it (each task requires its own sample budget).

3. **PAC learning under concept drift:** Under non-stationary distributions (which is what remapping simulates), exact PAC learning is impossible without some stationarity assumption. GENESIS's remap task is a controlled version of this — a known theoretical hard problem.

4. **The stability-plasticity dilemma is information-theoretic, not just algorithmic:** McCloskey & Cohen (1989) showed that in a network trained on interfering tasks, the minimum forgetting is bounded by the overlap in input representations. More overlap = more forgetting, regardless of algorithm. This is why the sparse, non-overlapping representations in the proposed architecture help — they are reducing representational overlap, which directly reduces the forgetting bound.

### Existing Sparse Event-Driven Work Relevant to Phase 2

- **e-prop** (Bellec et al. 2020): THE starting point. Read before writing any code.
- **DECOLLE** (Kaiser et al. 2020): Online local learning for deep SNNs with eligibility traces. More complex than needed for Phase 2A but relevant for Phase 2B.
- **BindsNET**: PyTorch-based SNN library with GPU support and customizable learning rules. Could be used as a validation reference (not as the primary simulator — maintain Rule 21 custom kernel).
- **Norse**: PyTorch SNN library with surrogate gradients. Relevant for validating your eligibility trace implementation against a known-good reference.
- **Loihi 2 benchmarks** (Orchard et al. 2021): The empirical data behind the efficiency claims. Read this to calibrate your compute gap estimates.

---

## 9. Go/No-Go Recommendation

### Decision: **CONDITIONAL GO**

Phase 2 should proceed with the following required modifications:

**Required before any code is written:**

1. **Remove all AGI language** from `VISION_v1.md`, issue trackers, and commit messages. Replace with: *"Phase 2 goal: demonstrate that three-factor STDP with metabolic buffering sustains in-lifetime learning under the cost×mortality interaction identified in Phase 1."*

2. **Revise the compute gap estimate** in `VISION_v1.md`. The correct number for digital home hardware is 10⁴–10⁶×, not 10²–10⁴×. This does not change the science; it corrects a claim that would undermine credibility if a reviewer checks it.

3. **Pre-register Exp-P2A-01** (specified in Section 6) before implementing the eligibility trace extension.

4. **Commit to the hard stop condition:** If three pre-registered variants of three-factor STDP all fail TF1 within 3 months, stop and write the null result paper. Do not search for a working variant without pre-registration.

**What makes this a Go and not a No-Go:**

- Phase 1 gave you an exact, empirically-validated failure mode (cost×mortality suppression).
- Three-factor STDP + eligibility traces is the mechanism-matched, peer-reviewed solution to that exact failure mode.
- The existing GENESIS infrastructure is correctly positioned: right scale, right cost model, right experimental discipline.
- The Phase 2A hypothesis is falsifiable, measurable, and answerable in 3 months.
- The scientific contribution is real regardless of whether H1 is confirmed: if it works, it's a solution; if it doesn't, it's a tighter characterization of the metabolic learning ceiling.

**What this is NOT a Go for:**

- AGI on home hardware
- Neuromorphic efficiency claims without neuromorphic hardware
- Phase 2B before Phase 2A succeeds
- Anything requiring more than one architectural change at a time

### Final Judgment

GENESIS Phase 1 produced honest, reproducible measurement science on a genuinely novel question: why does in-lifetime learning fail under metabolic constraints? The answer — cost×mortality interaction — is non-obvious and biologically grounded.

Phase 2 has the opportunity to close the loop: demonstrate the mechanism-matched fix. Three-factor STDP with eligibility traces is not speculative — it is the current state of the art in biological learning theory, implemented here in a regime (metabolic constraint, evolutionary selection, Rule 21 accounting) that the theoretical literature has not explicitly tested.

That is worth three months. That is worth one pre-registered experiment. That is not worth confusing with AGI.

**Start with Bellec et al. (2020). Pre-register. Run the experiment. Write what happens.**

---

## Appendix A: Essential Literature

### Required Reading Before Phase 2A Code
- **Bellec et al. (2020).** "A solution to the learning dilemma for recurrent networks of spiking neurons." *Nature Communications* 11, 3625.
- **Frémaux & Gerstner (2016).** "Neuromodulated Spike-Timing-Dependent Plasticity, and Theory of Three-Factor Learning Rules." *Frontiers in Neural Circuits* 9, 85.

### Phase 2B Preparation
- **Kaiser et al. (2020).** "Synaptic Plasticity Dynamics for Deep Continuous Local Learning (DECOLLE)." *Frontiers in Neuroscience.*
- **Zenke et al. (2021).** "The remarkable robustness of surrogate gradient learning for instilling complex function in spiking neural networks." *Neural Computation* 33(4).

### Context and Background
- **Olshausen & Field (2004).** "Sparse coding of sensory inputs." *Current Opinion in Neurobiology* 14(4).
- **Attwell & Laughlin (2001).** "An energy budget for signaling in the grey matter of the brain." *Journal of Cerebral Blood Flow & Metabolism* 21(10).
- **Hadsell et al. (2020).** "Embracing Change: Continual Learning in Deep Neural Networks." *Trends in Cognitive Sciences* 24(12). — The forgetting problem is real; this is why.

### Neuromorphic Hardware Benchmarks
- **Davies et al. (2018).** "Loihi: A Neuromorphic Manycore Processor with On-Chip Learning." *IEEE Micro* 38(1). — The empirical basis for event-driven efficiency claims.

---

## Appendix B: What GENESIS Already Has Right

This assessment criticizes the compute estimates and AGI framing. Equal weight should be given to what is correct:

1. **Rule 21 physical accounting** — unusual and rigorous. Most SNN papers ignore computational cost entirely.
2. **The cost×mortality finding** — real, reproducible, and biologically grounded.
3. **Pre-registration discipline** — the field needs more of this.
4. **Honest null results and Exp 95 response** — textbook scientific integrity.
5. **Evolutionary substrate** — the combination of within-lifetime STDP and across-generation evolution (the Baldwin Effect) is biologically correct and underexplored computationally.
6. **65K-neuron scale** — sufficient for meaningful learning experiments with the right architecture. The substrate is not the bottleneck. The learning rule is.

---

*Assessment completed: 2026-08-08. This document represents strategic consultation based on the published scientific literature, the GENESIS repository state as of branch `agi/sparse-event-driven-v1` commit `a44c9e3`, and Phase 1 experimental results through Exp-98. It should be treated as input to decision-making, not as authoritative prediction. The consultant has no stake in any particular outcome.*
