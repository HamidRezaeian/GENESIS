# Substrate 22: Multi-Task Conditional World Model & Self-Play Policy Distillation Architecture Specification

**Status:** Authoritative Architecture Specification  
**Version:** 1.0.0  
**Date:** 2026-08-28  
**Rules Reference:** Rule 6 (Prime Directive), Rule 9 (Autotelic Imperative), Rule 18 (Falsifiable Finish Line), Rule 21 (Thermodynamic Grounding), Rule 23 (FP16 Tensor Cores), Rule 24 (5 Task Families Replication Certification), Rule 26 (Unified Model Invariant)

---

## 1. Executive Summary & Problem Formulation

In Substrate 21, GENESIS achieved **Level 1 Statistical Replication Certification** on Task 4 (Dynamic Spatial Navigation) with a massive effect size of $d_z = +1.040$ ($p = 0.0344 < 0.05$ across Series 1200 Seeds 1201–1210). Furthermore, the integration of the `WorkingMemoryBuffer` (persistent activity context decay $\gamma = 0.92$) and **Modulo-Decoupled MCTS** unlocked positive separation on Task 3 (Compositional Arithmetic, $25.33\%$ vs $23.33\%$).

However, two fundamental architectural bottlenecks prevent broad multi-task mastery:
1. **Dynamic Interference in Shared Latent Transitions:** A single unconditional transition matrix $W_{\text{dyn}} \in \mathbb{R}^{(D + |A|) \times D}$ is forced to model radically distinct environmental physics simultaneously — grid-world navigation dynamics, bitwise XOR accumulators, compositional modular arithmetic, and Do-Calculus causal graphs. This creates catastrophic interference in shared weight space.
2. **Online Search Latency vs Fast Policy Execution:** AlphaZero PUCT MCTS provides high-quality search plans during runtime, but forward tree rollouts incur a computational search tax ($\mathcal{O}(N_{\text{sims}} \cdot d_{\text{max}} \cdot \text{FLOPs})$). Without policy distillation, the primary policy network $\pi_{\theta}(a|s)$ fails to internalize the search improvements into fast reflexive execution.

**Substrate 22 resolves these bottlenecks through four grounded architectural innovations:**
* **Innovation 1: Multi-Task Task-Conditioned World Model ($W_{\text{dyn}}(\tau)$):** Explicit conditioning of latent transition dynamics via a task-vector projection $\tau_{\text{task}} \in \mathbb{R}^{D_{\text{task}}}$ with FiLM (Feature-wise Linear Modulation) gating.
* **Innovation 2: AlphaZero PUCT Policy Distillation ($\mathcal{L}_{\text{distill}}$):** Continuous distillation of MCTS visit counts $\pi_{\text{MCTS}}(a|s)$ into the online policy head $\pi_{\theta}(a|s)$ via cross-entropy / KL divergence.
* **Innovation 3: Multi-Timescale Synaptic Consolidation (Circadian + Ultradian):** Coupling fast hippocampal adaptation ($\tau_{\text{fast}} = 1$ tick) with multi-frequency synaptic consolidation ($\tau_{\text{ultra}} = 100$ ticks, $\tau_{\text{circ}} = 2000$ ticks) guarded by Synaptic Intelligence path integrals ($\Omega$).
* **Innovation 4: Modulo-Decoupled MCTS Equivalence Routing:** Full mathematical integration of continuous-to-discrete modulo class summation within PUCT value backpropagation.

---

## 2. Mathematical Formulation

### 2.1 Task-Conditioned World Model ($W_{\text{dyn}}$ with FiLM Conditioning)

Let $s_t \in \mathbb{R}^{D}$ be the latent state at tick $t$, $a_t \in \{0, \dots, |A|-1\}$ the action one-hot vector $\mathbf{e}_{a_t} \in \mathbb{R}^{|A|}$, and $\tau_k \in \mathbb{R}^{D_{\text{task}}}$ the contextual task embedding (derived from instruction tokens or intrinsic autotelic goal discovery).

The concatenated state-action vector is:
$$\phi_t = [s_t \,\|\, \mathbf{e}_{a_t}] \in \mathbb{R}^{D + |A|}$$

The raw transition projection is:
$$\hat{z}_{t+1} = \phi_t W_{\text{dyn}} + b_{\text{dyn}}$$

To prevent task interference, FiLM modulation generates task-dependent affine transformation parameters $(\gamma(\tau_k), \beta(\tau_k))$:
$$\gamma(\tau_k) = \text{affine}(\tau_k W_{\gamma} + b_{\gamma}) + 1.0$$
$$\beta(\tau_k) = \tau_k W_{\beta} + b_{\beta}$$

The conditioned next latent state prediction is given by:
$$\hat{s}_{t+1} = \tanh\left( \gamma(\tau_k) \odot \hat{z}_{t+1} + \beta(\tau_k) \right)$$

**World Model Training Loss:**
$$\mathcal{L}_{\text{dyn}} = \frac{1}{B} \sum_{i=1}^B \| \hat{s}_{t+1}^{(i)} - s_{t+1}^{(i)} \|_2^2 + \lambda_{\text{rew}} ( \hat{r}_{t}^{(i)} - r_t^{(i)} )^2$$

---

### 2.2 AlphaZero PUCT Policy Distillation ($\mathcal{L}_{\text{distill}}$)

During MCTS planning at root state $s_0$, PUCT executes $N_{\text{sims}}$ rollouts using the world model $\hat{s}_{t+1}$ and value head $V(s)$. The empirical action visitation distribution is:
$$\pi_{\text{MCTS}}(a \mid s_0) = \frac{N(s_0, a)^{1/\tau_{\text{temp}}}}{\sum_{b} N(s_0, b)^{1/\tau_{\text{temp}}}}$$

The raw neural policy logits output by the brain transformer are:
$$p_{\theta}(a \mid s_0) = \text{softmax}(s_0 W_{\text{policy}})$$

The Policy Distillation Loss enforces that the neural policy $\pi_{\theta}$ absorbs the deep search policy discovered by MCTS:
$$\mathcal{L}_{\text{distill}} = \mathcal{H}(\pi_{\text{MCTS}}, \pi_{\theta}) = - \sum_{a=0}^{|A|-1} \pi_{\text{MCTS}}(a \mid s_0) \log \left( \pi_{\theta}(a \mid s_0) + \epsilon \right)$$

---

### 2.3 Persistent Activity Working Memory (DMTS Delay Sustaining)

For delay tasks (e.g. Task 1 DMTS blank period), sensory observation is zero ($\|x_t\|_2 \approx 0$). The `WorkingMemoryBuffer` maintains a decaying activity trace:
$$c_t = \frac{\sum_{i=1}^M \gamma^{t - t_i} s_{t_i}}{\sum_{i=1}^M \gamma^{t - t_i} + \epsilon}, \quad \gamma = 0.92$$

The transformer fusion layer injects the working memory context directly into self-attention:
$$\tilde{s}_t = \tanh\left( s_t + \alpha_{\text{WM}} c_t \right), \quad \alpha_{\text{WM}} = 0.30$$

---

### 2.4 Multi-Timescale Synaptic Consolidation ($\Omega$ Accumulators)

To adhere strictly to Rule 6 and Rule 21, catastrophic forgetting is mitigated via two biological consolidation loops:
1. **Ultradian Consolidation ($\tau_{\text{ultra}} = 100$ ticks):** Online path-integral accumulation of parameter importance weights:
   $$\omega_k \leftarrow \omega_k + \int_{\theta(t)}^{\theta(t+\Delta t)} \frac{\partial \mathcal{L}}{\partial \theta_k} d\theta_k$$
2. **Circadian Consolidation ($\tau_{\text{circ}} = 2000$ ticks / Sleep Cycle):** Synaptic stiffness parameter update:
   $$\Omega_k \leftarrow \Omega_k + \frac{\omega_k}{(\Delta \theta_k)^2 + \xi}$$
   $$\theta_k^* \leftarrow \theta_k, \quad \omega_k \leftarrow 0$$

**Synaptic Intelligence Regularization Loss:**
$$\mathcal{L}_{\text{SI}} = \sum_{k} \Omega_k (\theta_k - \theta_k^*)^2$$

---

### 2.5 Total Unified Loss Formulation

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{task}} + \lambda_1 \mathcal{L}_{\text{dyn}} + \lambda_2 \mathcal{L}_{\text{distill}} + \lambda_3 \mathcal{L}_{\text{CPC}} + \lambda_4 \mathcal{L}_{\text{SI}} + \lambda_5 \mathcal{L}_{\text{meta}}$$

Default Hyperparameters:
* $\lambda_1 = 0.50$ (World Model)
* $\lambda_2 = 0.40$ (MCTS Policy Distillation)
* $\lambda_3 = 0.10$ (Contrastive Semiogenesis)
* $\lambda_4 = 0.20$ (Synaptic Intelligence)
* $\lambda_5 = 0.05$ (Meta-Plasticity Regulation)

---

## 3. Substrate 22 Component Architecture

```
                                 ┌─────────────────────────────────┐
                                 │   Instruction / Task Context    │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
┌──────────────────┐               ┌───────────────────────────────┐
│ Visual Cortex    ├──────────────►│ Multi-Modal Fusion Core       │◄─────────────┐
│ (7x7x7 = 343D)   │               │ (Transformer + WM Buffer)     │              │
└──────────────────┘               └──────────────┬────────────────┘              │
                                                  │                               │
                                        State s_t │ (32D FP16)                    │
                                                  ▼                               │
                       ┌───────────────────────────────────────────────────────┐  │
                       │           AlphaZero PUCT MCTS Engine                  │  │
                       │                                                       │  │
                       │   ┌───────────────────────────────────────────────┐   │  │
                       │   │ Multi-Task World Model W_dyn(τ)               │   │  │
                       │   │ s_{t+1} = tanh( FiLM( [s_t, a_t] W_dyn, τ ) ) │   │  │
                       │   └──────────────────────┬────────────────────────┘   │  │
                       │                          │                            │  │
                       │                          ▼                            │  │
                       │   ┌───────────────────────────────────────────────┐   │  │
                       │   │ Leaf Evaluation Head V(s) & Reward Head R(s,a)│   │  │
                       │   └───────────────────────────────────────────────┘   │  │
                       └──────────────────────────┬────────────────────────────┘  │
                                                  │                               │
                                                  │ Search Policy π_MCTS          │
                                                  ▼                               │
┌───────────────────────────────┐  Distillation   ┌────────────────────────────┐  │
│ Online Policy Head π_θ(a|s)   │◄────────────────┤ Prioritized Experience     │  │
│ (Fast Inference Head)         │  L_distill      │ Hippocampus Buffer (50k)   ├──┘
└───────────────────────────────┘                 └────────────────────────────┘
```

---

## 4. Hardware Grounding & Computational Budget (Rule 21 & 23)

All operations are strictly bounded and measured on host hardware:
- **Precision:** `torch.float16` across all weight matrices and activations, utilizing NVIDIA Turing / Ampere Tensor Cores.
- **Inference Budget:**
  - Forward pass FLOPs: $\approx 1.2 \times 10^5 \text{ FLOPs/tick}$
  - MCTS Search FLOPs ($N_{\text{sims}} = 16, d_{\text{max}} = 6$): $\approx 4.8 \times 10^5 \text{ FLOPs/tick}$
  - Total latency per tick: $< 2.5 \text{ ms}$ (enabling $> 400 \text{ ticks/s}$ continuous throughput).
- **RAM Footprint:**
  - Neural Weights: $\approx 280 \text{ KB}$ (32D canonical model).
  - Hippocampal Buffer (50,000 slots): $\approx 18.5 \text{ MB}$.
  - Total Memory: $< 25 \text{ MB}$ (compliant with Rule 6 commodity hardware envelope).

---

## 5. Verification Plan & Finish Line Gate (Rule 18 & 24)

### 5.1 Level 2 Replication Certification Targets
Evaluation across $N=30$ independent seeds (Seeds 1201–1230) under fresh processes with 0-byte initial weight drift:
1. **Task 4 (Spatial Navigation):** Retain and exceed Level 1 certification ($\Delta \ge +5.0\%, p < 0.05, d_z \ge +0.8$).
2. **Task 1 (DMTS - Working Memory):** Achieve statistically significant separation ($\Delta \ge +15.0\%, p < 0.05$).
3. **Task 3 (Compositional Arithmetic):** Achieve statistically significant separation ($\Delta \ge +10.0\%, p < 0.05$).
4. **Task 5 (Causal Intervention):** Achieve statistically significant separation ($\Delta \ge +10.0\%, p < 0.05$).

### 5.2 Mandatory Ablation Controls (Rule 18 B)
Every evaluation run is paired with a matched `NOLEARN` control (frozen initial weights with identical seed layouts) to certify that all capability emergence is mathematically load-bearing.

---

## 6. Authoritative Approvals & Version History

- **v1.0.0 (2026-08-28):** Initial formal draft of Substrate 22 Specification following GLM 5.3 authoritative consultation.
