# Phase 5 Specification: Multimodal Grounded Language & Dual-Memory Sleep Consolidation (Substrate 8)

## 1. Mathematical Formalism

### 1.1 Multimodal Unified Latent Space
Let observation $O_t \in \mathbb{R}^{H \times W \times C}$ be the egocentric visual tensor ($7 \times 7 \times 6 = 294$), and $T = (w_1, w_2, \dots, w_L)$ be a sequence of discrete language tokens with vocabulary $V = 64$.

1. **Visual Embedding:**
   $$z_{\text{vis}} = \text{LayerNorm}(O_t W_{\text{vis}} + W_{\text{pos}}^{\text{vis}}), \quad W_{\text{vis}} \in \mathbb{R}^{294 \times d_{\text{model}}}$$
2. **Text Instruction Embedding:**
   $$z_{\text{lang}} = \frac{1}{L} \sum_{i=1}^L (W_{\text{lang}}[w_i] + W_{\text{pos}}^{\text{lang}}[i]), \quad W_{\text{lang}} \in \mathbb{R}^{V \times d_{\text{model}}}$$
3. **Multimodal Fusion & Causal Self-Attention:**
   $$z_{\text{fuse}} = \text{LayerNorm}(z_{\text{vis}} W_{\text{fuse}}^{\text{vis}} + z_{\text{lang}} W_{\text{fuse}}^{\text{lang}})$$
   $$Q = z_{\text{fuse}} W_q, \quad K = z_{\text{fuse}} W_k, \quad V = z_{\text{fuse}} W_v$$
   $$z_{\text{ctx}} = z_{\text{fuse}} + \text{Softmax}\left(\frac{Q K^T}{\sqrt{d_{\text{model}}}}\right) V W_{\text{out}}$$
   $$s_t = z_{\text{ctx}} + \text{MLP}(z_{\text{ctx}})$$

---

## 2. Dual-Memory Complementary Learning System (CLS)

### 2.1 Fast Hippocampal Episodic Buffer ($\mathcal{D}_{\text{hippo}}$)
Stores salient transitions $(s_t, a_t, r_t, s_{t+1}, T)$ with prioritized surprise weighting:
$$P(i) \propto \left( \| s_{t+1} - \hat{s}_{t+1} \|_2^2 + | r_t - \hat{r}_t | + \epsilon \right)^\alpha$$

### 2.2 Synaptic Importance Matrix (Empirical Fisher Information)
For any task $k$, the sensitivity of parameter $\theta_j$ is accumulated online without human priors:
$$\Omega_j = \mathbb{E}_{(s, a, r, s') \sim \mathcal{D}} \left[ \left( \frac{\partial \mathcal{L}_{\text{model}}}{\partial \theta_j} \right)^2 \right]$$

### 2.3 Consolidated Biological Sleep Phase
During rest cycles (offline replay):
$$\mathcal{L}_{\text{sleep}} = \mathcal{L}_{\text{replay}}(\theta) + \frac{\lambda_{\text{EWC}}}{2} \sum_j \Omega_j (\theta_j - \theta_j^*)^2$$
Where $\theta_j^*$ represents consolidated synaptic weights from previously mastered competencies.

---

## 3. Thermodynamic Grounding (Rule 21 Invariants)
- No arbitrary task bonuses or game multipliers.
- Instruction processing costs $\mathcal{O}(L \cdot d_{\text{model}})$ measured compute work.
- Synaptic consolidation penalties $\Omega_j$ are strictly derived from Fisher second-order gradient moments.
