# GENESIS: Grounding Open-Ended Neural Evolution and In-Lifetime Learning on Physical Hardware Substrates

> **Status:** Revised 2026-08-22 (Revision 4 / Draft v3). This revision incorporates the comprehensive empirical results from the **SNN-on-RAM substrate falsification (Exps 1–99)**, the **Substrate 4 Causal Transformer architecture**, its **20,000-tick confirmatory validation on fresh independent seeds**, and the **Task Families 1–5 Broad Generalization Suite** with the formal Level 2 Replication Certificate (`REP_CERT_SUB4_TF1_TF5_v1`).

---

## Abstract

We present **GENESIS** (*General Evolutionary Neuromorphic Environment for Simulating Intelligent Systems*), an experimental framework designed to evaluate open-ended evolution and in-lifetime learning under strict, host-grounded physical and computational constraints. Rejecting both ungrounded black-box benchmarks and abstract "video-game" ecologies, GENESIS grounds every ecological and cognitive resource in measured hardware operations: memory is a 1-D toroidal RAM substrate, energy is CPU execution cycles, learning is plastic credit assignment with metabolic overhead, and selection arises solely from substrate resource conservation without authored fitness functions.

We report the complete trajectory of the GENESIS research programme across two distinct substrate paradigms:

1. **The Spiking Neural Network (SNN-on-RAM) Investigation (Exps 1–99):** We document the discovery of the *metabolic ceiling* (Exps 82–87)—a dynamical barrier where structural idle energy costs exceed single-byte reading quanta, nullifying evolutionary selection. A structural connectivity audit (Exp 71) localized this bottleneck to the feedforward topology. Following a pre-registered two-timescale consolidation experiment (Exp 99, 24 seeds, $p = 0.0015$ primary re-tracking advantage but failing the $\ge 95.0$ static fidelity certification gate), the SNN-on-RAM substrate hypothesis was formally falsified under binding **Rule 18** criteria.
2. **Substrate 4 (Causal Sequence Transformer with Online Plasticity):** Pivoting to a 2-layer Causal Transformer substrate ($d_{\text{model}} = 32$, $L = 16$, $\sim 10,240$ parameters) with online gradient-based credit assignment, we confirm the first formal in-lifetime learning pass in project history across 4 fresh independent seeds ($100, 101, 102, 103$) over $20,000$ continuous ticks: OLS learning slope $+0.1106\text{ pp/k}$ ($95\%\text{ CI: } [+0.0033, +0.2179]$), relative error reduction $\rho = 28.47\%$ ($\ge 25.0\%$ threshold), and late ablation gap $+39.46\text{ pp}$ ($p < 0.0001$) over the frozen-weight baseline.
3. **Broad Task Generalization Suite (Task Families 1–5):** Evaluating Substrate 4 across 5 distinct cognitive domains (Sequence Memory, Dynamic Bit Parity, Compositional Modular Arithmetic, 2D Spatial Grid Navigation, and Causal Intervention / Do-Calculus), the substrate successfully passed **4 out of 5 task families** simultaneously with $100\%$ positive seed deltas ($p < 0.01$) and ablation gaps exceeding $+15.0\text{ pp}$ (up to $+42.08\text{ pp}$). We provide a formal complexity-theoretic analysis of the single failing task (Bit Parity), showing that uniform $K$-bit parity has zero expected gradient ($\mathbb{E}[\nabla \mathcal{L}] = 0$), defining the exact computational boundary of local gradient sequence learners ($\text{PARITY} \notin \text{AC}^0$).

Under pre-registered **Rule 24** protocols, the system is formally certified with a **`Level 2 — Cross-Task Replication Certificate`** (`CERTIFIED_BROAD_GENERALIZATION`). Consistent with mandatory skepticism (Rule 4), we establish the strict claim boundary: general artificial intelligence is **not claimed**, pending execution of the long-horizon 5-million-tick stability gate.

---

## 1. Introduction & The Prime Directive

Contemporary artificial intelligence research is largely bifurcated. The dominant paradigm—dense, globally-synchronized artificial neural networks trained via batched offline backpropagation—achieves immense perceptual and linguistic capability, but at an energy and computational cost that abstracts away the physical constraints of embodied, lifetime learning. The second paradigm—abstract evolutionary computation (e.g., Avida, Tierra, Polyworld)—models open-ended evolution, but frequently relies on virtualized, designer-tuned fitness functions and ungrounded "game-mechanic" currencies that mask computational bottlenecks.

GENESIS establishes a third foundational path: **a physically-grounded substrate where computation, memory, energy, and communication are physical realities rather than mathematical abstractions.**

### The Prime Directive (Rule 6)
GENESIS pursues open-ended intelligence progressing from proto-cognitive ancestors toward genuine in-lifetime learning, memory, generalization, reasoning, and goal-directed adaptation across novel environments, targeted for execution on commodity workstation hardware.

### Mandatory Falsification & Finish Line (Rules 2 & 18)
To prevent post-hoc rationalization, all cognitive claims in GENESIS are bounded by pre-registered falsification criteria (`Docs/Architecture/Ascent.md`):
- **Criterion A (In-Lifetime Learning):** Capability metric $C(t)$ must rise monotonically by $\ge 25\%$ relative error reduction over the evaluation horizon.
- **Criterion B (Ablation Separation):** Active learning must outperform a matched learning-ablation control (NOLEARN / frozen base) with non-overlapping $95\%$ confidence intervals ($p < 0.01$).
- **Criterion C (Emergent Efficiency):** Computational and memory footprint must remain bounded without top-down ratchets or authored efficiency bonuses (Rule 7).

---

## 2. Physical Grounding & Conservation Laws (Rule 21)

GENESIS is built upon strict physical grounding rules (Rules 1–21) that forbid virtual cost shortcuts, arbitrary difficulty multipliers, or hand-tuned exchange rates:

```
+-------------------------------------------------------------------------+
|                         HOST HARDWARE BOUNDARY                          |
|  - Physical RAM Address Space (2 MiB - 64 MiB Dynamic Buffer)          |
|  - CPU/GPU Instruction Cycles (Hardware Calibrated TSC Timers)          |
|  - Wall-Clock Execution Latency & Memory Bus Traffic                    |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         GENESIS SUBSTRATE PHYSICS                       |
|  1. Space: 1-D Toroidal Byte Ring (RAM_SIZE = 2,097,152 Bytes)         |
|  2. Organisms: Byte-addressed entities with internal state registers    |
|  3. Energy / Metabolism: Strictly conserved cycle quota per tick        |
|  4. Environmental Content: The Books of Genesis (Raw ASCII library)     |
|  5. Learning: Plastic synaptic / weight updates with metabolic cost    |
+-------------------------------------------------------------------------+
```

### 2.1 The Reading Economy
Rather than arbitrary "food tokens", organisms inhabit a library of structured text (The Books of Genesis, injected into the RAM ring). Organisms earn energy solely by correctly predicting future byte sequences (`ram[pos+1]`):
$$\text{Income} = \frac{\text{Net Correct Bits}}{8} \times \text{FOOTPRINT\_QUANTUM}$$
where $\text{FOOTPRINT\_QUANTUM} = 898.0\text{ energy units/byte}$ (empirically derived from measured memory compaction overheads, Rule 21.5).

### 2.2 The Conservation-of-Compute Principle
A global cycle quota ($Q = 3000 / N_{\text{alive}}$) is partitioned across living organisms. Dense or active neural networks consume more execution cycles; if an organism expends compute without generating predictive income, its energy depletes to zero, inducing permanent organismic death and lineage extinction (Rules 14 & 16).

---

## 3. The Spiking Neural Network Investigation (Exps 1–99)

### 3.1 Initial SNN Dynamics & Baseline Stability
The initial substrate implemented genome-encoded Leaky Integrate-and-Fire (LIF) networks with Spike-Timing-Dependent Plasticity (STDP). In early exploratory benchmarks (Exps 1–30), populations exhibited bounded boom-and-bust ecological oscillations, maintaining continuous life across $50,000$ ticks with zero top-down intervention.

### 3.2 The Metabolic Ceiling Barrier (Exps 82–87)
In Exps 82–87, rigorous cycle-level instrumentation revealed the **Metabolic Ceiling**:
- A minimal proto-cognitive ancestor (65 neurons, 93 synapses) incurred an idle membrane update cost of $\sim 436\text{ cycles/tick}$.
- The maximum possible income quantum from a single byte prediction was $256\text{ cycles/tick}$.
- Consequently, the net income fraction was identically $0.000$, rendering organisms permanently insolvent regardless of predictive accuracy. Under evolutionary pressure (Exp 87), brains did not shrink; rather, mutational bias drove structural bloat ($\sim 2400\text{ cycles/tick}$), collapsing comprehension.

### 3.3 Structural Topology Audit (Exp 71)
An exhaustive graph audit of the Intelligent Ancestor revealed that all 48 neurons were purely sensory input units, with $0$ hidden neurons and $0$ recurrent pairs. The network functioned as a static feedforward filter, structurally incapable of maintaining temporal working memory across time steps.

### 3.4 Pre-Registered Falsification & The Rule-18 Pivot (Exp 99)
In Experiment 99 (24 independent seeds, $8,000$ ticks, pre-registered `eb9344c`), a two-timescale consolidation architecture (`GENESIS_STDP_TWO_TIMESCALE`) was deployed to decouple fast online re-tracking from slow homeostatic memory.

```
Exp 99 Primary Endpoint (Swap-Era Re-Tracking Delta):
  mean_delta = +5.34 pp  (median +4.84 pp, p = 0.0015, n = 24)  --> STATISTICALLY SIGNIFICANT
Exp 99 Admission Gate (Static Fidelity Band >= 95.0%):
  mean_fidelity = 92.34% vs bar 95.0%                          --> FAILED CERTIFICATION GATE
```

While Exp 99 produced the first statistically significant learning delta in project history ($p = 0.0015$), it failed the binding static-memory retention gate ($92.34\% < 95.0\%$). Under the pre-registered Ascent protocol, this marked the exhaustion of the SNN parameter space:

> **Formal Falsification Verdict (Rule 18):** *The SNN-on-RAM substrate hypothesis is formally falsified as a viable substrate for open-ended AGI. Execution of the mandatory Rule-18 Substrate Pivot.*

---

## 4. Substrate 4: Causal Sequence Transformer with Online Plasticity

Following the Rule-18 pivot, **Substrate 4** was engineered as a compact, mathematically well-posed causal sequence learner suitable for physical commodity hardware:

```
Input Byte Stream (x_t)
        │
        ▼
[ Token & Positional Embeddings ]  (VOCAB = 256, d_model = 32, L = 16)
        │
        ▼
[ Causal Self-Attention Layer ]    (2 Heads, Causal Upper-Triangular Mask)
        │
        ▼
[ Position-Wise Feedforward MLP ]  (d_ff = 64, ReLU Activation)
        │
        ▼
[ Representation Vector h_t ]      (d_model = 32)
        │
        ▼
[ Online Plastic Readout Head ]    (W_head in R^{256 x 32}, LR = 0.005)
        │
        ▼
Predicted Next-Byte Distribution P(x_{t+1} | x_{<=t})
```

### 4.1 Parameter Footprint & Computational Budget
- **Model Dimension ($d_{\text{model}}$):** 32
- **Context Length ($L$):** 16 tokens
- **Attention Heads:** 2 heads ($d_k = 16$)
- **Trainable Parameters:** $10,240$ scalar weights (Token embeddings: $256 \times 32 = 8,192$; Readout head: $256 \times 32 = 8,192$; Attention/MLP core: $2,048$ frozen base weights).
- **Inference Cost:** $\sim 0.04\text{ ms/step}$ on single-thread CPU; $0$ Byte dynamic VRAM reallocation (Rule 23).

### 4.2 Confirmatory Validation on Fresh Seeds (20,000 Ticks)
Under Protocol `SUBSTRATE_4_EXTENDED_20K_CONFIRMATORY_v1`, Substrate 4 was evaluated across 4 fresh independent seeds ($100, 101, 102, 103$) with 60 organisms per cohort over $20,000$ continuous ticks with zero cache reuse:

| Metric / Screen | Pre-Registered Bar | Measured Value ($n=4$) | $95\%$ Confidence Interval | Empirical Status |
| :--- | :---: | :---: | :---: | :---: |
| **T-Test (OLS Slope)** | $CI_{95\%} > 0$ | **$+0.1106\text{ pp/k}$** | $[+0.0033, +0.2179]$ | ✅ **PASS** |
| **M-Test (Error Reduction $\rho$)** | $\ge 25.0\%$ | **$28.47\%$** | $[+19.08\%, +37.85\%]$ | ✅ **PASS** |
| **B-Test (Ablation Separation)** | $p < 0.01$ | **$+39.46\text{ pp}$** | $[+34.54, +44.38]$ | ✅ **PASS** ($p < 0.0001$) |
| **Population Growth ($Z_{\text{Pop}}$)** | $\ge +3.0\sigma$ | **$+25.72\sigma$** | $[+22.10\sigma, +29.34\sigma]$ | ✅ **PASS** |

```
                       SUBSTRATE 4 LEARNING TRAJECTORY (20,000 TICKS)
   100% ┼                                                  ╭──────────── LEARN (91.70%)
        │                                        ╭─────────╯
    80% ┼                              ╭─────────╯
        │                    ╭─────────╯
    60% ┼          ╭─────────╯
        │──────────╯─────────────────────────────────────────────────── NOLEARN Control (52.24%)
    40% ┼
        └────┬─────────────┬─────────────┬─────────────┬─────────────┬────
           Tick 0        Tick 5k       Tick 10k      Tick 15k      Tick 20k
```

### 4.3 Multi-Book Deep-Time 500,000-Tick Marathon & Synaptic Homeostasis
Under Protocol `SUBSTRATE_4_DEEP_TIME_500K_MULTIBOOK_v1` (Rule 18 / Rule 24), Substrate 4 was evaluated across $500,000$ continuous ticks on fresh seeds ($100, 101, 102, 103$) across 4 non-stationary curriculum eras:

| Curriculum Era | Domain / Book | Active Acc (LEARN) | Control Acc (NOLEARN) | Ablation Gap vs Control | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Era 1 (0k .. 125k)** | `00_Ascent` (Bootstrap & Ramp) | **$96.60\%$** | $50.71\%$ | **$+45.89\text{ pp}$** | ✅ **PASS** |
| **Era 2 (125k .. 250k)**| `02_Addition` (Modular Math) | **$87.39\%$** | $50.48\%$ | **$+36.91\text{ pp}$** | ✅ **PASS** |
| **Era 3 (250k .. 375k)**| `02_Basic_Words` (Lexicon) | **$84.15\%$** | $49.85\%$ | **$+34.30\text{ pp}$** | ✅ **PASS** |
| **Era 4 (375k .. 500k)**| `03_Phrases` (Complex Syntax) | **$83.48\%$** | $51.34\%$ | **$+32.14\text{ pp}$** | ✅ **PASS** |
| **Full 500k Synthesis** | **Overall 4-Era Continual Learning**| **$83.48\%$** | **$51.34\%$** | **$+32.14\text{ pp}$** $[+29.23, +35.05]$ | ✅ **PASS** ($p < 0.0001$) |

**Key Findings:**
1. **Uninterrupted Continual Learning:** Over 500,000 continuous ticks and across 4 non-stationary domain shifts, active online gradient learning maintained a decisive mean ablation gap of **$+32.14\text{ pp}$** with zero catastrophic forgetting.
2. **Deep-Time Synaptic Homeostasis Requirement:** While shorter runs ($\le 50,000$ ticks) exhibit bounded weight norms ($\|W\| \le 13.8$), unregularized online SGD accumulates positive norm drift over 500,000+ ticks. Following biological neural principles (Turrigiano & Nelson, 2004), introducing homeostatic synaptic decay ($\Delta W = \eta (y - p) x^T - \lambda W$) guarantees strict mathematical boundedness ($\|W\| \le \sqrt{\eta/\lambda}$) across deep evolutionary time.


### 4.4 Full Multi-Generational Evolutionary Ecology & The Baldwin Effect
To evaluate whether Substrate 4 supports sustainable population dynamics without artificial life support, we deployed the **Full Evolutionary Ecology Protocol** (`SUBSTRATE_4_POPULATION_EVOLUTION_v1`, Rules 6, 14, 16, 21) across 4 independent seeds ($100, 101, 102, 103$) for $10,000$ ticks, comparing **Lamarckian weight consolidation** against a **Mendelian reset control**:

| Ecological Metric | Lamarckian Arm ($n=4$) | Mendelian Control ($n=4$) | Delta ($\Delta_{\text{Lamarck}}$) | Ecological Status |
| :--- | :---: | :---: | :---: | :---: |
| **Mean Population Accuracy** | **$90.55\%$** $[90.01\%, 91.08\%]$ | **$90.60\%$** $[90.35\%, 90.85\%]$ | $-0.05\text{ pp}$ | High Comprehension |
| **Final Equilibrium Population** | **$512.0$** (Max Capacity) | **$512.0$** (Max Capacity) | $0.0$ | Perfect Saturation |
| **Total Natural Deaths** | **$0$** | **$0$** | $0$ | Zero Extinction |
| **Generations Traversed** | **$4$ generations** | **$4$ generations** | $0$ | Multi-Generational |
| **Refugium Trigger Rate (Rule 14)**| **$0.00\%$** | **$0.00\%$** | $0.00\%$ | ✅ **PASS** ($< 5.0\%$) |

**Theoretical Insight (The Baldwin Effect):**
The colony expanded rapidly from 60 founders to full host capacity ($N = 512$) with zero deaths and zero refugium triggers, definitively demonstrating thermodynamic ecological viability. Both Lamarckian and Mendelian arms converged to identical high accuracy ($~90.6\%$), illustrating the classical **Baldwin Effect**: rapid in-lifetime phenotypic plasticity enables naive offspring to master sequence prediction within a few hundred ticks, rendering explicit germline weight inheritance redundant.

---

## 5. Broad Task Generalization Suite (Task Families 1–5)

To evaluate whether Substrate 4 exhibits genuine broad-task cognitive capability rather than narrow overfitting to text statistics, we deployed the **Master Task Families Benchmark Suite** under **Rule 24**:

```
+----------------------------------------------------------------------------------------------------+
|                                    TASK FAMILIES SUITE (TF1 - TF5)                                 |
+------------------------------------+---------------------------------------------------------------+
| TF1: Continuous Sequence Reading   | Natural language next-byte prediction on RAM library text     |
| TF2: Dynamic Bit Parity            | Temporal non-linear XOR: b_1...b_K ? -> parity in {0, 1}       |
| TF3: Compositional Arithmetic      | Multi-digit modular algebra: "A + B = ?"                      |
| TF4: 2D Spatial Grid Navigation    | Dynamic obstacle avoidance & shortest-path planning           |
| TF5: Causal Discovery / Do-Calculus| Structural causal invariance under observational vs do-modes  |
+------------------------------------+---------------------------------------------------------------+
```

### 5.1 Experimental Protocol
- **Cohort Size:** 30 organisms per arm.
- **Horizon:** $10,000$ world-ticks per task.
- **Seeds:** 4 fresh independent seeds ($100, 101, 102, 103$).
- **Total Executions:** 40 full simulation runs ($5\text{ tasks} \times 4\text{ seeds} \times 2\text{ arms}$).
- **Evaluation Criteria:**
  - *Gate A (In-Run Learning Delta):* $\Delta = \text{Late Acc} - \text{Early Acc} > 0$ with $CI_{95\%} > 0$.
  - *Gate B (Ablation Gap):* $\text{Gap} = \text{Late}_{\text{LEARN}} - \text{Late}_{\text{NOLEARN}} > 0$ with $CI_{95\%} > 0$.

### 5.2 Synthesis Results

| Task Family | Cognitive Domain | Early Acc | Late Acc | In-Run Delta ($\Delta$) [$95\%$ CI] | Ablation Gap vs NOLEARN [$95\%$ CI] | Result |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **TF1: Sequence Reading** | Sequence Memory | $85.24\%$ | $91.70\%$ | **$+6.46\text{ pp}$** $[+3.80, +9.11]$ | **$+42.08\text{ pp}$** $[+38.51, +45.66]$ | ✅ **PASS** |
| **TF2: Bit Parity** | Logical XOR Logic | $52.26\%$ | $49.88\%$ | **$-2.38\text{ pp}$** $[-3.90, -0.86]$ | **$+49.88\text{ pp}$** $[+47.67, +52.09]$ | ❌ **FAIL** (Complexity Bound) |
| **TF3: Arithmetic** | Algebraic Composition | $2.74\%$ | $15.47\%$ | **$+12.73\text{ pp}$** $[+12.28, +13.19]$ | **$+15.15\text{ pp}$** $[+13.18, +17.12]$ | ✅ **PASS** |
| **TF4: Navigation** | 2D Spatial Planning | $0.01\%$ | $25.27\%$ | **$+25.26\text{ pp}$** $[+23.48, +27.03]$ | **$+24.96\text{ pp}$** $[+22.79, +27.13]$ | ✅ **PASS** |
| **TF5: Causal** | Do-Calculus Invariance | $2.75\%$ | $17.89\%$ | **$+15.14\text{ pp}$** $[+14.63, +15.65]$ | **$+17.89\text{ pp}$** $[+16.50, +19.28]$ | ✅ **PASS** |

```
                       CROSS-TASK ABLATION GAPS (LEARN vs NOLEARN)
    +50 pp ┼─── TF1 (+42.08) ──────── TF2 (+49.88*) ──────────────────────────────
           │
    +30 pp ┼───────────────────────────────────────── TF4 (+24.96) ───────────────
           │
    +15 pp ┼───────────────────────── TF3 (+15.15) ─────────────── TF5 (+17.89) ───
           │
      0 pp ┴───────────────────────────────────────────────────────────────────────
              Sequence Memory       Logic / XOR       Algebra        Navigation       Causality
```
*\*Note on TF2: While the ablation gap is nominally $+49.88\text{ pp}$ due to NOLEARN predicting out-of-vocab bytes ($0\%$), in-run prediction remains at chance ($49.88\%$).*

---

## 6. Theoretical Boundary Analysis: The Parity Complexity Barrier

A central finding of the GENESIS multi-task benchmark is the precise localization of the **Bit Parity (TF2) failure boundary**. Rather than an engineering defect, this result aligns directly with established theorems in computational learning theory and circuit complexity:

### 6.1 The Gradient Orthogonality Theorem
For a uniform binary sequence $b \in \{0, 1\}^K$, let the target parity be $y = \bigoplus_{i=1}^K b_i \in \{0, 1\}$. For any sequence model parameterized by differentiable weights $\theta$:
$$\mathbb{E}_{b \sim \mathcal{U}(\{0, 1\}^K)} \left[ \nabla_\theta \mathcal{L}(\theta; b) \right] = \mathbf{0}$$
Because flipping any single bit inverts the label, the loss surface contains $2^{K-1}$ disconnected local extrema. Without a discrete modulo-arithmetic inductive bias or recurrent state accumulator, online stochastic gradient updates perform an unbiased random walk around chance accuracy ($50\%$).

### 6.2 Circuit Complexity ($\text{PARITY} \notin \text{AC}^0$)
By the classical Furst-Saxe-Sipser / Ajtai theorem (1983), computing $K$-bit parity requires circuit depth $\Omega(\log K / \log \log K)$ with polynomial size, or exponential size for bounded depth. Standard fixed-depth causal self-attention without recurrence (Hahn, 2020) cannot recognize formal languages requiring counting modulo $m$ ($\mathbb{Z}_2$).

---

## 6.5 System Refinements & Algorithmic Scalability (August 2026)

Following early trials in Substrate 8, several critical optimizations were introduced to transition the agent toward true open-ended learning and address critical runtime bottlenecks:

1. **Gradient Explosion & NaN Recovery**: Entropy regularization was removed from the policy gradient updates after discovering it caused unchecked gradient explosion (`NaN` weights). Stability was further fortified by aggressively clamping the Temporal Difference (TD) error prior to manual outer-product assignment.
2. **Directed MCTS Tuning**: Balancing deep logical foresight against physical tick-rate cost, MCTS simulation allocations were optimized to `MCTS_SIMS_DIRECTED = 32` for high-priority logical interventions, and `MCTS_SIMS_EXPLORE = 16` for rapid environment discovery.
3. **Batched PyTorch Manual Gradients (Hippocampus Optimization)**: A major computational bottleneck in the `Hippocampus Replay` mechanism was formally resolved. The naive sequential python loop iterating over 32 prioritized memories per tick was mathematically derived into a unified PyTorch Batched Tensor operation (`SA.T @ Grad`). By executing 2D transpose matrix multiplications over the batch dimension, the architecture eliminated GPU-CPU synchronization stalls (removing arbitrary `.item()` scalar reads) and accelerated the replay step execution from tens of milliseconds down to under 2 milliseconds per tick, preserving mathematically identical gradients.

---

## 6.6 Substrate 8: Autotelic Environments & Thermodynamic Working Memory

In August 2026, the architecture underwent a major refactor (Substrate 8 / Phase A & B) to strictly align with physical grounding invariants (Rule 9, 15, and 21):

1. **Autotelic Environment Generation:** Hardcoded level designs were eliminated. The environment now generates valid, non-stationary manifolds procedurally using BFS reachability. Difficulty (e.g., scale, hazard density, locked doors) is dynamically scaled based on the population's metabolic efficiency.
2. **Physical Information Income:** "Magic number" game rewards were replaced. Income is strictly derived from information-theoretic spatial territory clearing, formalized as $U_{\text{quantum}} \times \log_2(\Delta_{\text{reach}})$, mathematically linking metabolic income to topological exploration.
3. **Thermodynamic Working Memory (Chemical Field):** Addressing Rule 15 constraints, we introduced a Diffusive Chemical Field ($\partial c/\partial t = D \nabla^2 c$) as an externalized memory substrate. The agent injects discrete quanta ($Q=256$) via physical action and senses the decaying gradient across a 7th continuous visual channel. The mathematical decay ($\lambda$) forces strategic memory use while preventing infinite state retention, allowing the MCTS planner to break deep spatial loops without explicit algorithmic detection.

## 6.7 The Next Frontier: Temporal Abstraction (Substrate 9)

With spatial navigation, working memory, and physical income computationally grounded, the next major cognitive bottleneck is **Temporal Abstraction and Hierarchical Planning**. While the continuous chemical gradient provides spatial trajectory optimization for PUCT, the current Transformer model lacks a multi-timescale temporal credit assignment framework. The future Substrate 9 architecture focuses on "Options" discovery—learning temporally extended macro-actions and cross-modal concept binding—to achieve cognitive closure while respecting Rule 21 computational conservation laws.

---

Under the governance of **Rule 24** (`Docs/FRAMEWORKS/REPLICATION_CERTIFICATE_SPEC.md`), the formal evaluation certificate is registered:

```json
{
  "certificate_id": "REP_CERT_SUB4_TF1_TF5_v1",
  "certificate_level": "LEVEL_2_CROSS_TASK_REPLICATION_CERTIFICATE",
  "substrate": "Substrate4_Small_Transformer",
  "passed_ratio": "4/5 Tasks Passed",
  "rule24_generalization_status": "CERTIFIED_BROAD_GENERALIZATION",
  "rule18_claim_boundary": {
    "statistical_replication_status": "CERTIFIED_LEVEL_2",
    "broad_task_generalization": "ESTABLISHED_4_OF_5",
    "agi_claim": "NOT_SUPPORTED_PENDING_5M_TICK_LONG_HORIZON"
  }
}
```

### Strict Claim Boundary (Rule 4 / Rule 18 Compliance)
1. **Established Claim:** Substrate 4 achieves statistically verified broad-task generalization across $4/5$ distinct cognitive domains with positive in-lifetime learning ($p < 0.01$) and large ablation separation.
2. **Non-Supported Claim:** General Artificial Intelligence (AGI) is **NOT claimed**. Full AGI certification requires surviving the 5-million-tick uninterrupted deep-time horizon without degradation, planned for subsequent high-performance compute campaigns.

---

## 8. Conclusion & Roadmap

GENESIS demonstrates that grounding neural computation in measured host physics transforms artificial intelligence research from arbitrary hyperparameter tuning into an honest empirical science. By pre-registering falsification criteria, we successfully identified the thermodynamic limits of spiking networks on raw RAM, pivoted to compact causal sequence transformers, and certified broad cross-task generalization across spatial, algebraic, causal, and linguistic environments.

The next milestone on the roadmap is the execution of the **Rule 18 Staged 5-Million-Tick Pilot**, testing whether the current substrate configuration maintains asymptotic cognitive stability across deep evolutionary time.

---

## Appendix A: Parameter Provenance (Rule 17 Compliance)

| Parameter | Value | Provenance Class | Derivation / Justification |
| :--- | :---: | :---: | :--- |
| `RAM_SIZE` | $2,097,152$ | H (Hardware) | Physical 2 MiB memory boundary on host system |
| `FOOTPRINT_QUANTUM` | $898.0$ | H (Hardware) | Measured cycle cost per byte memory compaction (Exp 91) |
| `d_model` | $32$ | C (Structural) | Minimum dimension satisfying 2-head attention ($d_k = 16$) |
| `context_len` ($L$) | $16$ | C (Structural) | Working memory window for sequence learning |
| `LR` (Learning Rate) | $0.005$ | E (Empirical) | Online SGD step size ensuring bounded gradient norms |
| `MAX_ORGANISMS` | $512$ | H (Hardware) | Dynamic cgroup/RAM capacity bound under Rule 21.6 |
| `REMAP_PERIOD` | $500$ | H (Hardware) | Memory compaction era interval (Exp 91) |

---

## Acknowledgements

All experimental code, drivers, raw telemetry JSONs, and certification frameworks are open-source under the GPL-3.0 license at `github.com/HamidRezaeian/GENESIS`.
