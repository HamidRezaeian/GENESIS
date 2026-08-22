# Task Families Benchmark Suite Specification (v1.0)
**Identifier:** `TASK_FAMILIES_SPEC_v1`
**Rule Reference:** Rule 24 (Consolidation & Level 1 Replication Certification)

---

## 1. Executive Summary

This document specifies the 5 canonical Task Families designed to evaluate broad-task cognitive generalization across memory, logic, algebraic composition, spatial planning, and causal discovery in autonomous agents without human knowledge leakage.

---

## 2. Five Canonical Task Families

### Task Family 1 (TF1): Delayed Match-to-Sample & Static Sequence Reading
- **Domain:** Continuous byte-level text streams (Books economy / RAM library).
- **Core Cognitive Function:** Working memory, temporal sequence prediction, context buffering.
- **Evaluation Metric:** Byte / bit prediction accuracy, in-run learning delta $\Delta_{\text{in-run}}$, error reduction $\rho$.

### Task Family 2 (TF2): Dynamic Bit Parity (Logical / XOR Reasoning)
- **Domain:** Binary sequence streams of variable lengths $K \in [4, 16]$ with query tokens `?`.
- **Core Cognitive Function:** Non-linear parity state tracking, multi-step XOR computation.
- **Evaluation Metric:** Query-bit accuracy (Random baseline: $50\%$).

### Task Family 3 (TF3): Compositional Modular Arithmetic (Algebraic Composition)
- **Domain:** Tokenized multi-operator expressions ($a + b$, $a \times b$, $a + b \times c \pmod{10}$).
- **Core Cognitive Function:** Compositional binding, operator precedence, modular arithmetic.
- **Evaluation Metric:** Result token accuracy (Random baseline: $10\%$).

### Task Family 4 (TF4): 2D Spatial Grid Navigation (Planning & Spatial Reasoning)
- **Domain:** $16 \times 16$ 2D grid world with discrete coordinates and dynamic obstacles.
- **Core Cognitive Function:** Spatial representation, shortest-path planning, directional policy induction.
- **Evaluation Metric:** Optimal navigation step accuracy (Random baseline: $25\%$).

### Task Family 5 (TF5): Causal Intervention & Graph Discovery (Causal Reasoning)
- **Domain:** 3-variable Structural Causal Models (SCM) with observational and interventional ($do(X_2=v)$) queries.
- **Core Cognitive Function:** Disentangling correlation from causation, invariant prediction under intervention.
- **Evaluation Metric:** Interventional prediction accuracy (Random baseline: $10\%$).

---

## 3. Generalization Certification Criteria

1. **Task-Level Pass:**
   - In-Lifetime Learning Delta: $\Delta \ge +2.0\text{ pp}$ ($CI_{95\%} > 0$).
   - Ablation Gap vs NOLEARN: $\text{Gap} \ge +5.0\text{ pp}$ ($CI_{95\%} > 0$).
2. **Broad-Task Generalization Certification:**
   - Requires passing at least **4 out of 5 Task Families** under strict fresh-seed replication.
