"""
GENESIS Phase-5: Dual-Timescale & Constructive Credit Plasticity Engine.
Binding specification: Docs/Architecture/PHASE5_DUAL_MEMORY_SPEC.md (§2.1, §2.3).

Formulas:
- W_fast[t+1] = W_fast[t] + eta_f(t) * M(t) * E(t) + eta_f(t) * err_i(t) * pre_j(t) * g_gate(t)
- W_slow[t+1] = W_slow[t] + eps(t) * (W_fast[t] - W_slow[t]) + eps(t) * err_i(t) * pre_j(t) * beta(info(t))
- W_eff[t]    = W_fast[t] + W_slow[t]

Invariants:
- g_gate(t): Surprise gate (Eq. 6) — plasticity fires ONLY on deviation from expectation.
- beta(info(t)): Information gate based on running median rank statistic [M] (Rule-17-safe: no arbitrary thresholds).
- W_fast structural clamp: [-4.0, +4.0] [S].
- Constructive error signal reaches silent-but-wanted neurons (Exp-35 pathway construction).
"""

from typing import Dict, Any, Tuple
import torch


class Phase5PlasticityEngine:
    """
    Dual-timescale plasticity engine managing fast re-tracking and slow consolidated memory.
    """
    def __init__(
        self,
        eta_f0: float = 0.05,
        eps0: float = 0.001,
        w_fast_rail: float = 4.0,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.eta_f0 = eta_f0
        self.eps0 = eps0
        self.w_fast_rail = w_fast_rail
        self.device = device
        self.running_eligibility_median = 0.01

    def update_synapses(
        self,
        W_fast: torch.Tensor,         # [W, N, S]
        W_slow: torch.Tensor,         # [W, N, S]
        pre_idx: torch.Tensor,        # [W, N, S]
        post_idx: torch.Tensor,       # [W, N, S]
        syn_active: torch.Tensor,     # [W, N, S]
        pre_spikes: torch.Tensor,     # [W, N, M]
        post_spikes: torch.Tensor,    # [W, N, M]
        eligibility: torch.Tensor,    # [W, N, S]
        modulator: torch.Tensor,      # [W, N] reward/metabolic factor M(t)
        prediction_error: torch.Tensor, # [W, N] surprise signal
        constructive_err: torch.Tensor  # [W, N, M] error gradient per post neuron
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Executes dual-timescale synaptic update.
        Returns updated (W_fast, W_slow, W_eff).
        """
        # 1. Compute surprise gate g_gate(t)
        # g_gate(t) = tanh(|prediction_error|)
        g_gate = torch.tanh(torch.abs(prediction_error)).unsqueeze(-1)  # [W, N, 1]

        # 2. Compute information gate beta(info(t)) via running median rank statistic [M]
        curr_median = torch.median(torch.abs(eligibility)).item()
        self.running_eligibility_median = 0.99 * self.running_eligibility_median + 0.01 * curr_median
        info_mask = (torch.abs(eligibility) > self.running_eligibility_median).float()  # [W, N, S]

        # 3. Fast Synaptic Update (W_fast)
        # STDP component: eta_f * M(t) * eligibility * g_gate
        m_broad = modulator.unsqueeze(-1)  # [W, N, 1]
        stdp_fast = self.eta_f0 * m_broad * eligibility * g_gate

        # Constructive component (Exp-35 pathway building for silent neurons):
        # err_post = constructive_err[post_idx], pre_act = pre_spikes[pre_idx]
        batch_w = torch.arange(W_fast.shape[0], device=self.device).view(-1, 1, 1)
        batch_n = torch.arange(W_fast.shape[1], device=self.device).view(1, -1, 1)
        
        post_err = constructive_err[batch_w, batch_n, post_idx]  # [W, N, S]
        pre_act = pre_spikes[batch_w, batch_n, pre_idx]          # [W, N, S]
        constructive_fast = self.eta_f0 * post_err * pre_act * g_gate

        dW_fast = (stdp_fast + constructive_fast) * syn_active.float()
        W_fast_new = torch.clamp(W_fast + dW_fast, -self.w_fast_rail, self.w_fast_rail)

        # 4. Slow Consolidation Update (W_slow)
        # eps * (W_fast - W_slow) gated by information trace beta(info)
        consolidation_drive = self.eps0 * (W_fast - W_slow) * info_mask
        constructive_slow = self.eps0 * post_err * pre_act * info_mask

        dW_slow = (consolidation_drive + constructive_slow) * syn_active.float()
        W_slow_new = W_slow + dW_slow

        # 5. Effective Drive
        W_eff = (W_fast_new + W_slow_new) * syn_active.float()
        return W_fast_new, W_slow_new, W_eff
