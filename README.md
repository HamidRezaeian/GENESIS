# GENESIS Digital Universe

<div align="center">

[![Certification](https://img.shields.io/badge/Replication%20Status-Certified%20Level%202-34d399?style=for-the-badge&logo=shield)](Docs/FRAMEWORKS/REPLICATION_CERTIFICATE_SUB4.json)
[![Generalization](https://img.shields.io/badge/Task%20Families-4%2F5%20Passed-38bdf8?style=for-the-badge&logo=target)](experiments/tf_results/tf_all_summary.json)
[![Stability](https://img.shields.io/badge/50k%20Horizon-Zero%20Forgetting%20Passed-818cf8?style=for-the-badge&logo=pulse)](experiments/sub4_results/sub4_50k_summary.json)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-c084fc?style=for-the-badge&logo=gnu)](LICENSE)

### *Grounding Open-Ended Neural Evolution & In-Lifetime Learning on Physical Hardware Substrates*

[**Interactive Presentation Deck**](presentation.html) • [**Scientific Manuscript (Draft v3)**](Docs/Article_Draft.md) • [**Experimental Results Record**](Docs/Result.md) • [**Ascent Protocol**](Docs/Architecture/Ascent.md)

</div>

---

## 🌌 Overview

**GENESIS** (*General Evolutionary Neuromorphic Environment for Simulating Intelligent Systems*) is an experimental framework designed to evaluate open-ended evolution and in-lifetime learning under strict, host-grounded physical and thermodynamic constraints.

Rejecting ungrounded video-game fitness functions and black-box artificial neural benchmarks, GENESIS maps every ecological and cognitive resource directly onto literal host hardware operations:
- **Space & Geography:** 1-D Toroidal RAM Array (`2 MiB` address space).
- **Energy & Metabolism:** Host CPU execution cycle quotas (`3000 / N_alive`).
- **Environmental Income:** Net predictive compression on structured text libraries (`898.0 J/Byte`).
- **Plasticity & Learning:** Online credit assignment with measurable cycle-level work.
- **Selection:** Thermodynamic conservation of compute; death occurs at `energy <= 0` without top-down ratchets.

---

## 📊 Certified Scientific Milestones (August 2026)

### 1. Task Families 1–5 Multi-Domain Cognitive Benchmark
Evaluated across 4 fresh independent seeds ($100, 101, 102, 103$) $\times$ 40 simulation runs under **Rule 24**:

| Task Family | Cognitive Domain | In-Run Delta ($\Delta$) | Ablation Gap vs NOLEARN | Status |
| :--- | :--- | :---: | :---: | :---: |
| **TF1: Sequence Reading** | Continuous Sequence Memory | **$+6.46\text{ pp}$** | **$+42.08\text{ pp}$** | ✅ **PASS** |
| **TF2: Bit Parity** | Temporal XOR Logic | **$-2.38\text{ pp}$** | **$+49.88\text{ pp}$** (at chance) | ❌ **FAIL** (Complexity Bound) |
| **TF3: Arithmetic** | Compositional Modular Algebra | **$+12.73\text{ pp}$** | **$+15.15\text{ pp}$** | ✅ **PASS** |
| **TF4: Navigation** | 2D Spatial Grid Planning | **$+25.26\text{ pp}$** | **$+24.96\text{ pp}$** | ✅ **PASS** |
| **TF5: Causal Discovery** | Do-Calculus Invariance | **$+15.14\text{ pp}$** | **$+17.89\text{ pp}$** | ✅ **PASS** |

- **Official Replication Certificate:** [`Docs/FRAMEWORKS/REPLICATION_CERTIFICATE_SUB4.json`](Docs/FRAMEWORKS/REPLICATION_CERTIFICATE_SUB4.json)
- **Status:** **`CERTIFIED_BROAD_GENERALIZATION`** (**Level 2** Certificate).
- **Theoretical Characterization of TF2:** Disclosed under Rule 4 / Rule 20. Uniform $K$-bit parity has zero expected gradient ($\mathbb{E}[\nabla \mathcal{L}] = \mathbf{0}$) and circuit complexity $\text{PARITY} \notin \text{AC}^0$, proving the exact boundary of local gradient sequence learners.

---

### 2. Staged Long-Horizon 50,000-Tick Pilot
Evaluated across $50,000$ continuous ticks to assess deep-time asymptotic stability:
- **Zero Catastrophic Forgetting:** Global OLS slope $= +0.0437\text{ pp/k}$ ($CI_{95\%} > 0$, PASS).
- **Ablation Separation:** $+39.48\text{ pp}$ over frozen baseline ($p < 0.0001$).
- **Relative Error Reduction ($\rho$):** $40.64\%$ ($\ge 25.0\%$ threshold).
- **Stationary Policy Convergence:** Readout weight norm $\|W_{\text{head}}\|$ stabilized smoothly to an asymptotic stationary plateau of $13.83$.

---

### 3. Full Multi-Generational Evolutionary Ecology
Simulated an evolving colony in a 2 MiB RAM library over 10,000 ticks:
- **Zero Extinctions & $0.00\%$ Refugium:** Population expanded smoothly from 60 founders to full host capacity ($N = 512$) with zero natural deaths and zero reliance on the emergency Ark.
- **The Baldwin Effect Discovered:** Lamarckian inheritance and Mendelian reset reached identical $~90.6\%$ accuracy, demonstrating that rapid in-lifetime phenotypic plasticity buffers genotypic selection.

---

## 🚀 Quick Start & Replication

### Installation

```bash
# Clone the repository
git clone https://github.com/HamidRezaeian/GENESIS.git
cd GENESIS

# Create virtual environment and install dependencies
python -m venv .venv
# On Windows:
.venv\Scripts\pip install -r requirements.txt
# On Linux / macOS:
source .venv/bin/activate && pip install -r requirements.txt
```

### Reproduce Core Benchmarks

```bash
# 1. Run the complete Task Families 1-5 Generalization Suite (4 seeds, parallel workers)
python experiments/tf_suite/run_tf_all.py --seeds 100 101 102 103 --ticks 10000 --workers 4

# 2. Run the Staged Long-Horizon 50,000-Tick Pilot
python experiments/sub4_long_horizon_50k.py --seeds 100 101 102 103 --ticks 50000 --workers 4

# 3. Run the Multi-Generational Evolutionary Ecology Benchmark
python experiments/sub4_population_evolution.py --seeds 100 101 102 103 --ticks 10000 --workers 4
```

### View Interactive Presentation Deck

Open [`presentation.html`](presentation.html) or [`Docs/Presentation/index.html`](Docs/Presentation/index.html) in any modern web browser to view the 8-slide interactive Chart.js presentation.

---

## 🏛 Repository Architecture

```
GENESIS/
├── Docs/
│   ├── Article_Draft.md          # Complete scientific manuscript (Draft v3 / Revision 4)
│   ├── Result.md                 # Complete experimental record and telemetry tables
│   ├── Presentation/index.html   # Interactive 8-slide HTML5/Chart.js presentation deck
│   ├── Architecture/             # Core engineering & ascent specifications
│   │   ├── Ascent.md             # Pre-registered finish line protocols (Rule 18)
│   │   └── FixedRules.md         # Binding physical grounding rules (Rules 1-21)
│   └── FRAMEWORKS/               # Certification specifications & JSON certificates
│       ├── REPLICATION_CERTIFICATE_SPEC.md
│       └── REPLICATION_CERTIFICATE_SUB4.json
├── experiments/
│   ├── sub4_small_transformer.py # Substrate 4 Causal Transformer core architecture
│   ├── sub4_long_horizon_50k.py  # 50,000-tick deep-time pilot driver
│   ├── sub4_population_evolution.py # Multi-generational evolutionary ecology driver
│   ├── tf_suite/                 # Task Families 1-5 benchmark drivers
│   │   ├── tf1_reading.py        # TF1: Continuous Sequence Memory
│   │   ├── tf2_bit_parity.py     # TF2: Dynamic Bit Parity (XOR)
│   │   ├── tf3_arithmetic.py     # TF3: Modular Arithmetic
│   │   ├── tf4_navigation.py     # TF4: 2D Spatial Grid Navigation
│   │   ├── tf5_causal.py         # TF5: Causal Intervention & Discovery
│   │   └── run_tf_all.py         # Master parallel runner for all 5 tasks
│   └── tf_results/               # Raw JSON telemetry outputs
├── src/                          # Core engine & environment modules
│   ├── neuromorphic_engine.py    # SNN physics engine (Exps 1-99 historical record)
│   ├── genesis_lab.py            # Universe orchestration & memory allocator
│   └── books_of_genesis.py       # ASCII curriculum text injector
├── presentation.html             # Quick launcher for research presentation deck
└── README.md                     # Project overview and replication guide
```

---

## ⚖️ The Scientific Method & Claim Boundary (Rule 4 / Rule 18)

GENESIS is governed by mandatory skepticism (Rule 4) and pre-registered falsification (Rule 2). 

1. **Certified Claims:** Substrate 4 is formally certified under **`Level 2 — Cross-Task Replication Certificate`** for broad-task generalization across spatial, algebraic, causal, and linguistic domains with zero catastrophic forgetting over 50,000 continuous ticks.
2. **Strict Claim Boundary:** **General Artificial Intelligence (AGI) is strictly NOT claimed.** Full AGI certification requires surviving the 5-million-tick uninterrupted deep-time horizon without degradation under Rule 18.

---

## 📜 License & Open Science

All code, experimental drivers, raw telemetry JSONs, and documentation are open-source under the **GNU General Public License v3.0 (GPL-3.0)**.
