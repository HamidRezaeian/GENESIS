# Substrate 22: Multi-Task Conditional World Model & Self-Play Policy Distillation Architecture Specification

**Status:** Authoritative Architecture Specification (GLM 5.3 Verified & Certified)  
**Version:** 1.1.0  
**Date:** 2026-08-28  
**Rules Reference:** Rule 6 (Prime Directive), Rule 9 (Autotelic Imperative), Rule 18 (Falsifiable Finish Line), Rule 21 (Thermodynamic Grounding), Rule 23 (FP16 Tensor Cores), Rule 24 (5 Task Families Replication Certification), Rule 26 (Unified Model Invariant)

---

## 1. Executive Summary & Problem Formulation

In Substrate 21, GENESIS achieved **Level 1 Statistical Replication Certification** on Task 4 (Dynamic Spatial Navigation) with a massive effect size of $d_z = +1.040$ ($p = 0.0344 < 0.05$ across Series 1200 Seeds 1201–1210). Furthermore, the integration of the `WorkingMemoryBuffer` (persistent activity context decay $\gamma = 0.92$) and **Modulo-Decoupled MCTS** unlocked positive separation on Task 3 (Compositional Arithmetic, $25.33\%$ vs $23.33\%$).

Following GLM 5.3's authoritative mathematical audit, Substrate 22 resolves dynamic interference and fast policy extraction through four core innovations:
1. **FiLM + Bottleneck Residual Task-Conditioned World Model ($W_{\text{dyn}}(\tau)$):** Bottleneck dimensionality compression ($32 \to 16 \to \text{GELU} \to 32$) with LayerNorm and FP16 clamping to maximize task separability without parameter explosion.
2. **Adaptive Distillation Temperature ($\tau_{\text{temp}}$):** Entropy-modulated linear annealing from $\tau_{\text{init}} = 1.5$ down to $\tau_{\text{final}} = 0.5$ over 40 epochs.
3. **Phase-Dependent Multi-Objective Loss Scheduling:** Dynamic shifting of loss priorities across 3 training phases (World Model focus $\to$ Policy Distillation focus $\to$ Synaptic Consolidation).
4. **Adaptive Curriculum Scheduler:** Online task selection weighted by task forgetting rate, recency, and inverted learning progress to eliminate sequential catastrophic forgetting.

---

## 2. Mathematical Formulation

### 2.1 Task-Conditioned World Model with FiLM + Bottleneck Residual

Let $s_t \in \mathbb{R}^{D}$ ($D=32$), $a_t \in \{0, \dots, |A|-1\}$ ($|A|=4$), and $\tau \in \{0, \dots, K-1\}$ ($K=5$ task families).

The concatenated transition input is:
$$\phi_t = [s_t \,\|\, \mathbf{e}_{a_t}] \in \mathbb{R}^{36}$$

The linear projection and FiLM modulation with FP16 clamp protection are:
$$\hat{z}_{t+1} = \phi_t W_{\text{dyn}} + b_{\text{dyn}}$$
$$\gamma(\tau) = \text{clamp}(W_{\gamma}[\tau] + 1.0, -3.0, 3.0)$$
$$\beta(\tau) = \text{clamp}(W_{\beta}[\tau], -2.0, 2.0)$$
$$\tilde{z}_{t+1} = \gamma(\tau) \odot \hat{z}_{t+1} + \beta(\tau)$$

The Bottleneck Residual and next-state prediction are given by:
$$\text{Bottleneck}(\tilde{z}) = \text{GELU}(\tilde{z} W_{\text{bn1}} + b_{\text{bn1}}) W_{\text{bn2}} + b_{\text{bn2}}, \quad W_{\text{bn1}} \in \mathbb{R}^{32 \times 16}, W_{\text{bn2}} \in \mathbb{R}^{16 \times 32}$$
$$\hat{s}_{t+1} = \tanh\left( \text{LayerNorm}(\tilde{z}_{t+1} + \text{Bottleneck}(\tilde{z}_{t+1})) \right)$$

---

### 2.2 Adaptive MCTS Policy Distillation ($\mathcal{L}_{\text{distill}}$)

The target MCTS visitation distribution uses adaptive temperature $\tau_{\text{temp}}$:
$$\pi_{\text{MCTS}}(a \mid s_0) = \frac{N(s_0, a)^{1/\tau_{\text{temp}}}}{\sum_{b} N(s_0, b)^{1/\tau_{\text{temp}}}}$$

where:
$$\tau_{\text{base}} = \tau_{\text{init}} + \min\left(1.0, \frac{\text{epoch}}{\text{anneal\_epochs}}\right) (\tau_{\text{final}} - \tau_{\text{init}}), \quad (\tau_{\text{init}}=1.5, \tau_{\text{final}}=0.5, \text{anneal\_epochs}=40)$$
$$\tau_{\text{temp}} = \text{clamp}\left( \tau_{\text{base}} \cdot (1.0 + 0.3 \cdot \mathcal{H}_{\text{MCTS}}), 0.1, 3.0 \right)$$

The distillation loss is:
$$\mathcal{L}_{\text{distill}} = - \sum_{a=0}^{|A|-1} \pi_{\text{MCTS}}(a \mid s_0) \log \left( \pi_{\theta}(a \mid s_0) + 10^{-6} \right)$$

---

### 2.3 Phase-Dependent Loss Scheduling

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{task}} + \lambda_1 \mathcal{L}_{\text{dyn}} + \lambda_2 \mathcal{L}_{\text{distill}} + \lambda_3 \mathcal{L}_{\text{CPC}} + \lambda_4 \mathcal{L}_{\text{SI}} + \lambda_5 \mathcal{L}_{\text{meta}}$$

| Phase | Epochs | Focus | $\lambda_1$ ($\mathcal{L}_{\text{dyn}}$) | $\lambda_2$ ($\mathcal{L}_{\text{distill}}$) | $\lambda_3$ ($\mathcal{L}_{\text{CPC}}$) | $\lambda_4$ ($\mathcal{L}_{\text{SI}}$) | $\lambda_5$ ($\mathcal{L}_{\text{meta}}$) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 1: Foundation** | 1–20 | World Model Accuracy | $0.60$ | $0.20$ | $0.15$ | $0.25$ | $0.03$ |
| **Phase 2: Expansion** | 21–40 | Policy Extraction | $0.40$ | $0.50$ | $0.10$ | $0.30$ | $0.05$ |
| **Phase 3: Consolidation** | 41–60 | Fine-Tuning & SI Memory | $0.30$ | $0.55$ | $0.08$ | $0.35$ | $0.08$ |

---

### 2.4 Adaptive Curriculum Scheduler

Each task $k \in \{0, 1, 2, 3, 4\}$ is assigned an execution priority:
$$P_k = 0.40 \cdot \text{Forgetting}_k + 0.30 \cdot \ln(1 + \Delta t_k) + 0.30 \cdot (1 - \text{Progress}_k)$$

Task selection follows softmax sampling:
$$p(k) = \frac{\exp(P_k)}{\sum_{j} \exp(P_j)}$$

---

## 3. Hardware Grounding & Computational Budget (Rule 21 & 23)

- **Precision:** Pure `torch.float16` across all weight tensors with Turing/Ampere Tensor Cores.
- **Latency:** $< 2.8\text{ ms/tick}$ during online MCTS search and distillation.
- **Memory:** $< 26\text{ MB}$ total footprint for 50k transitions and canonical neural weights.
