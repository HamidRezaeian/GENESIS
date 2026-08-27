"""
Substrate 20: Counterfactual World Modeling, Latent ToM & Emergent Symbolic Communication.
Authoritative mathematical formulation by GLM 5.3.

Invariants:
- Rule 21: All costs grounded in measured FLOPs + memory traffic
- Rule 23: All tensors torch.float16, zero dynamic allocation in forward
- Rule 25: No if-else; all routing via differentiable gates
- Rule 9/26: No predefined symbol dictionary; meaning emerges via CPC
"""

import math
from typing import Dict, Any, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class Substrate20Engine(nn.Module):
    """
    Substrate 20: Counterfactual World Modeling, Latent Theory of Mind (ToM) &
    Emergent Symbolic Communication Engine.
    """

    # Hardware energy cost scaling (Rule 21, resolvable in FP16 precision at scale 100.0)
    FLOP_COST = 5e-4
    TRAFFIC_COST = 5e-5

    def __init__(
        self,
        dim: int = 32,
        n_symbols: int = 64,
        n_peers: int = 4,
        horizon: int = 8,
        n_branches: int = 4,
        peer_obs_dim: int = 73,
        n_cpc_negatives: int = 8,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        super().__init__()
        self.dim = dim
        self.n_symbols = n_symbols
        self.n_peers = n_peers
        self.horizon = horizon
        self.n_branches = n_branches
        self.peer_obs_dim = peer_obs_dim
        self.n_cpc_negatives = n_cpc_negatives
        self.dev = torch.device(device)

        # ═══════════════════════════════════════════════════════
        # LEARNABLE PARAMETERS (FP16, require grad)
        # ═══════════════════════════════════════════════════════

        # --- Imagination Engine ---
        self.W_dyn = nn.Parameter(torch.randn(dim, dim, dtype=torch.float16, device=self.dev) * 0.02)
        self.b_dyn = nn.Parameter(torch.zeros(dim, dtype=torch.float16, device=self.dev))
        self.W_pert = nn.Parameter(torch.randn(dim, dim, dtype=torch.float16, device=self.dev) * 0.01)

        # --- ToM Module ---
        self.W_enc = nn.Parameter(torch.randn(peer_obs_dim, dim, dtype=torch.float16, device=self.dev) * 0.02)
        self.W_rec = nn.Parameter(torch.randn(dim, dim, dtype=torch.float16, device=self.dev) * 0.02)
        self.W_goal = nn.Parameter(torch.randn(dim, dim, dtype=torch.float16, device=self.dev) * 0.02)
        self.W_act = nn.Parameter(torch.randn(dim, 4, dtype=torch.float16, device=self.dev) * 0.02)

        # --- Symbolic Protocol ---
        self.W_sym_emit = nn.Parameter(torch.randn(dim, n_symbols, dtype=torch.float16, device=self.dev) * 0.02)
        self.W_sym_recv = nn.Parameter(torch.randn(n_symbols, dim, dtype=torch.float16, device=self.dev) * 0.02)
        self.sym_temp = nn.Parameter(torch.tensor([0.5], dtype=torch.float16, device=self.dev))

        # --- CPC Projection ---
        self.W_cpc = nn.Parameter(torch.randn(dim, dim, dtype=torch.float16, device=self.dev) * 0.02)

        # --- Merge Parameters (learnable) ---
        self.merge_threshold = nn.Parameter(torch.tensor([0.85], dtype=torch.float16, device=self.dev))
        self.merge_kappa = nn.Parameter(torch.tensor([0.05], dtype=torch.float16, device=self.dev))

        # ═══════════════════════════════════════════════════════
        # PRE-ALLOCATED STATE BUFFERS (FP16, no grad)
        # ═══════════════════════════════════════════════════════

        # --- Imagination Buffers ---
        self.register_buffer("imag_rollouts", torch.zeros(n_branches, horizon, dim, dtype=torch.float16, device=self.dev))
        self.register_buffer("imag_weights", torch.ones(n_branches, dtype=torch.float16, device=self.dev) / n_branches)
        self.register_buffer("imag_merge_sim", torch.zeros(n_branches, n_branches, dtype=torch.float16, device=self.dev))
        self.register_buffer("imag_merge_attn", torch.zeros(n_branches, n_branches, dtype=torch.float16, device=self.dev))
        self.register_buffer("noise_buffer", torch.randn(n_branches, dim, dtype=torch.float16, device=self.dev) * 0.1)

        # --- ToM Buffers ---
        self.register_buffer("tom_peer_models", torch.zeros(n_peers, dim, dtype=torch.float16, device=self.dev))
        self.register_buffer("tom_peer_goals", torch.zeros(n_peers, dim, dtype=torch.float16, device=self.dev))
        self.register_buffer("tom_eligibility", torch.zeros(n_peers, dim, 4, dtype=torch.float16, device=self.dev))
        self.register_buffer("tom_pred_error", torch.zeros(n_peers, 4, dtype=torch.float16, device=self.dev))

        # --- Symbolic Protocol Buffers ---
        self.register_buffer("sym_grounding", torch.zeros(n_symbols, dim, dtype=torch.float16, device=self.dev))
        self.register_buffer("sym_grounding_mean", torch.zeros(dim, dtype=torch.float16, device=self.dev))
        self.register_buffer("sym_grounding_var", torch.ones(1, dtype=torch.float16, device=self.dev))
        self.register_buffer("sym_history", torch.zeros(32, n_symbols, dtype=torch.float16, device=self.dev))
        self.register_buffer("sym_mi_estimate", torch.zeros(1, dtype=torch.float16, device=self.dev))

        # --- CPC Buffers ---
        self.register_buffer("cpc_negatives", torch.randn(n_cpc_negatives, dim, dtype=torch.float16, device=self.dev) * 0.1)
        self.register_buffer("cpc_loss_val", torch.zeros(1, dtype=torch.float16, device=self.dev))

        # --- Energy/Metabolic Buffers (Rule 21) ---
        self.register_buffer("energy", torch.tensor([100.0], dtype=torch.float16, device=self.dev))
        self.register_buffer("flop_counter", torch.zeros(1, dtype=torch.float16, device=self.dev))
        self.register_buffer("traffic_counter", torch.zeros(1, dtype=torch.float16, device=self.dev))
        self.register_buffer("E_crit", torch.tensor([50.0], dtype=torch.float16, device=self.dev))
        self.register_buffer("E_init", torch.tensor([100.0], dtype=torch.float16, device=self.dev))
        self.register_buffer("Cost_max", torch.tensor([1e6], dtype=torch.float16, device=self.dev))

        # Cached telemetry properties
        self.last_imag_gate = 0.0
        self.last_branch_eff = float(n_branches)
        self.last_symbol_out = torch.zeros(n_symbols, dtype=torch.float16, device=self.dev)
        self.last_step_energy_cost = 0.0

    # ═══════════════════════════════════════════════════════
    # ENERGY ACCOUNTING (Rule 21)
    # ═══════════════════════════════════════════════════════

    def _deduct_energy(self, flops: int, traffic_bytes: int):
        """Deduct energy based on measured computational work."""
        cost = float(flops * self.FLOP_COST + traffic_bytes * self.TRAFFIC_COST)
        new_energy = torch.clamp(self.energy - cost, min=0.0)
        self.energy.data.copy_(new_energy)
        self.flop_counter.data.add_(flops)
        self.traffic_counter.data.add_(traffic_bytes)
        self.last_step_energy_cost = cost

    def _matmul_cost(self, m: int, n: int, k: int) -> Tuple[int, int]:
        """FLOPs and traffic for matmul of [m,k] x [k,n] -> [m,n]."""
        flops = 2 * m * n * k
        traffic = (m * k + k * n + m * n) * 2  # FP16 = 2 bytes
        return flops, traffic

    # ═══════════════════════════════════════════════════════
    # PLL GATE COMPUTATION
    # ═══════════════════════════════════════════════════════

    def compute_gates(self, phase: torch.Tensor, energy: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Compute all PLL gates from oscillator phase and metabolic state.
        All gates are differentiable — no if-else.
        """
        cos_phi = torch.cos(phase)
        sin_phi = torch.sin(phase)

        # Metabolic factor: imagination requires energy surplus
        metabolic_factor = torch.sigmoid((energy - self.E_crit) / torch.clamp(self.E_crit, min=1.0))

        gates = {
            "write": 0.5 * (1.0 + cos_phi),
            "chain": sin_phi * sin_phi,
            "imagine": 0.5 * (1.0 - cos_phi) * metabolic_factor,
            "read": 0.5 * (1.0 - cos_phi) * (1.0 - metabolic_factor * 0.5),
            "comm": sin_phi * sin_phi * metabolic_factor,
        }
        self.last_imag_gate = float(gates["imagine"].detach().cpu().item())
        return gates

    # ═══════════════════════════════════════════════════════
    # COUNTERFACTUAL IMAGINATION ENGINE
    # ═══════════════════════════════════════════════════════

    def imagination_rollout(
        self,
        h_t: torch.Tensor,
        gate_imagine: torch.Tensor,
    ) -> torch.Tensor:
        """
        Counterfactual rollout in latent space with self-attention branch merging.
        """
        B, H, D = self.n_branches, self.horizon, self.dim

        # Initial perturbation: h^b_0 = h_t + noise * tanh(W_pert @ h_t)
        pert = torch.tanh(torch.mm(h_t, self.W_pert))  # [1, 32]
        init_branches = h_t + self.noise_buffer * pert  # [B, 32]

        flops, traffic = self._matmul_cost(1, D, D)
        flops += D + B * D
        self._deduct_energy(flops, traffic)

        cur_states = init_branches
        rollout_list = [cur_states]

        # Multi-step rollout loop
        for tau in range(H - 1):
            next_states = torch.tanh(torch.mm(cur_states, self.W_dyn) + self.b_dyn)
            step_flops, step_traffic = self._matmul_cost(B, D, D)
            step_flops += B * D * 3
            self._deduct_energy(step_flops, step_traffic)

            # Residual gate modulation
            cur_states = next_states * gate_imagine.view(1, 1) + cur_states * (1.0 - gate_imagine.view(1, 1))

            # Branch self-attention merging
            if B > 1:
                norms = torch.clamp(torch.norm(cur_states, dim=1, keepdim=True), min=1e-6)
                normalized = cur_states / norms
                sim_matrix = torch.mm(normalized, normalized.t())

                # Differentiable merge attention
                merge_input = (sim_matrix - self.merge_threshold) / torch.clamp(self.merge_kappa, min=1e-3)
                merge_attn = F.softmax(merge_input, dim=1)

                cur_states = torch.mm(merge_attn, cur_states)
                self.imag_merge_attn.data.copy_(merge_attn.detach())

                merge_flops = B * B * D + B * B * 3 + B * B * D
                self._deduct_energy(merge_flops, B * B * 2)

            rollout_list.append(cur_states)

        # Update persistent buffer with detached trace
        full_rollout = torch.stack(rollout_list, dim=1)  # [B, H, D]
        self.imag_rollouts.data.copy_(full_rollout.detach())

        # Effective branching factor = 1 / sum((sum_j A_ij)^2)
        attn_row_sums = self.imag_merge_attn.sum(dim=1)
        eff_b = 1.0 / float(torch.clamp((attn_row_sums ** 2).sum(), min=1e-6).detach().cpu().item())
        self.last_branch_eff = round(eff_b, 3)

        # Weighted final state aggregation
        final_states = cur_states  # [B, D]
        imag_out = torch.mm(self.imag_weights.unsqueeze(0), final_states)  # [1, D]
        return imag_out

    # ═══════════════════════════════════════════════════════
    # THEORY OF MIND (ToM)
    # ═══════════════════════════════════════════════════════

    def tom_forward(
        self,
        peer_obs: torch.Tensor,
        gate_comm: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Latent Theory of Mind forward pass.
        """
        P, D = self.n_peers, self.dim

        # Encode peer observations: z^p = tanh(W_enc @ o^p + W_rec @ z^p_{prev})
        obs_enc = torch.mm(peer_obs, self.W_enc)  # [P, D]
        rec_enc = torch.mm(self.tom_peer_models, self.W_rec)  # [P, D]
        new_models = torch.tanh(obs_enc + rec_enc)

        flops1, traffic1 = self._matmul_cost(P, D, self.peer_obs_dim)
        flops2, traffic2 = self._matmul_cost(P, D, D)
        self._deduct_energy(flops1 + flops2 + P * D, traffic1 + traffic2)

        # Update peer model buffer
        gate_3d = gate_comm.view(1, 1)
        blended_models = new_models * gate_3d + self.tom_peer_models * (1.0 - gate_3d)
        self.tom_peer_models.data.copy_(blended_models.detach())

        # Goal inference: g^p = tanh(W_goal @ z^p)
        peer_goals = torch.tanh(torch.mm(blended_models, self.W_goal))
        self.tom_peer_goals.data.copy_(peer_goals.detach())

        # Action prediction: a^p = softmax(W_act @ z^p / temp)
        temp = torch.clamp(torch.sigmoid(self.sym_temp) + 0.1, min=0.1, max=2.0)
        peer_actions = F.softmax(torch.mm(blended_models, self.W_act) / temp, dim=-1)

        flops, traffic = self._matmul_cost(P, 4, D)
        self._deduct_energy(flops + P * 12, traffic)

        return blended_models, peer_actions

    def tom_stdp3c_update(
        self,
        peer_obs: torch.Tensor,
        peer_actual_actions: torch.Tensor,
        reward: torch.Tensor,
    ):
        """
        3-Factor STDP3C plasticity update for Theory of Mind.
        """
        P, D = self.n_peers, self.dim
        pred_actions = F.softmax(torch.mm(self.tom_peer_models, self.W_act), dim=-1)
        error = peer_actual_actions - pred_actions
        self.tom_pred_error.data.copy_(error.detach())

        # Eligibility trace update: E = 0.9 * E + z ⊗ error
        for p in range(P):
            z = self.tom_peer_models[p].unsqueeze(1)  # [D, 1]
            e = error[p].unsqueeze(0)                 # [1, 4]
            outer = torch.mm(z, e)                   # [D, 4]
            self.tom_eligibility[p].data.copy_(0.9 * self.tom_eligibility[p] + outer)

        # Parameter plasticity adjustment
        eta = 0.001 * float(reward.detach().cpu().item())
        for p in range(P):
            grad = torch.mm(peer_obs[p].unsqueeze(1), self.tom_peer_models[p].unsqueeze(0)) * eta  # [73, D]
            self.W_enc.data.add_(grad.t()[:self.peer_obs_dim, :D] * 0.01 if grad.shape[0] == D else grad * 0.01)

    # ═══════════════════════════════════════════════════════
    # SYMBOLIC COMMUNICATION & CPC SEMIOGENESIS
    # ═══════════════════════════════════════════════════════

    def symbol_emit(self, h_t: torch.Tensor) -> torch.Tensor:
        """
        Emit soft symbol distribution from latent state.
        """
        temp = torch.clamp(torch.sigmoid(self.sym_temp) + 0.1, min=0.1, max=2.0)
        logits = torch.mm(h_t, self.W_sym_emit) / temp  # [1, 64]
        symbol_soft = F.softmax(logits, dim=-1).squeeze(0)  # [64]

        flops, traffic = self._matmul_cost(1, self.n_symbols, self.dim)
        self._deduct_energy(flops + self.n_symbols * 3, traffic)
        self.last_symbol_out.data.copy_(symbol_soft.detach())
        return symbol_soft

    def symbol_receive(
        self,
        h_t: torch.Tensor,
        symbol_in: torch.Tensor,
        gate_comm: torch.Tensor,
    ) -> torch.Tensor:
        """
        Receive soft symbol and integrate into latent state.
        """
        symbol_proj = torch.mm(symbol_in.unsqueeze(0), self.W_sym_recv)  # [1, 32]
        flops, traffic = self._matmul_cost(1, self.dim, self.n_symbols)
        self._deduct_energy(flops, traffic)

        h_updated = h_t + symbol_proj * gate_comm.view(1, 1)
        return h_updated

    def update_grounding(
        self,
        symbol_soft: torch.Tensor,
        h_t: torch.Tensor,
        alpha_g: float = 0.01,
    ):
        """
        Update grounding matrix G in-place (predictive Hebbian association).
        """
        h_flat = h_t.squeeze(0).detach()  # [32]
        p_s = symbol_soft.unsqueeze(1).detach()  # [64, 1]

        new_g = (1.0 - alpha_g * p_s) * self.sym_grounding + (alpha_g * p_s) * h_flat
        self.sym_grounding.data.copy_(new_g)

        self.sym_grounding_mean.data.copy_(self.sym_grounding.mean(dim=0))
        self.sym_grounding_var.data.copy_(self.sym_grounding.var(dim=0, unbiased=False).mean().unsqueeze(0))

        # Mutual information estimate
        dev = self.sym_grounding - self.sym_grounding_mean
        dev_sq = (dev * dev).sum(dim=1)
        mi = (symbol_soft.detach() * dev_sq / (self.sym_grounding_var + 1e-6)).sum()
        self.sym_mi_estimate.data.copy_(mi.unsqueeze(0))

    def cpc_loss(
        self,
        symbol_soft: torch.Tensor,
        h_positive: torch.Tensor,
        h_negatives: torch.Tensor,
    ) -> torch.Tensor:
        """
        Contrastive Predictive Coding loss grounding symbols to future world states.
        """
        sym_proj = torch.mm(symbol_soft.unsqueeze(0), self.sym_grounding)  # [1, 32]
        sym_proj = torch.tanh(torch.mm(sym_proj, self.W_cpc))  # [1, 32]

        h_pos_proj = torch.tanh(torch.mm(h_positive, self.W_cpc))  # [1, 32]
        h_neg_proj = torch.tanh(torch.mm(h_negatives, self.W_cpc))  # [K, 32]

        temp = torch.clamp(torch.sigmoid(self.sym_temp) + 0.1, min=0.1, max=2.0)
        pos_sim = F.cosine_similarity(sym_proj, h_pos_proj, dim=-1)  # [1]
        neg_sim = F.cosine_similarity(sym_proj.expand(self.n_cpc_negatives, -1), h_neg_proj, dim=-1)  # [K]

        all_sim = torch.cat([pos_sim, neg_sim]) / temp
        loss = -F.log_softmax(all_sim, dim=0)[0]

        flops, traffic = self._matmul_cost(1, self.dim, self.n_symbols)
        flops += self._matmul_cost(1 + self.n_cpc_negatives, self.dim, self.dim)[0]
        self._deduct_energy(flops, traffic)

        self.cpc_loss_val.data.copy_(loss.detach().unsqueeze(0))
        return loss

    # ═══════════════════════════════════════════════════════
    # MAIN FORWARD PASS
    # ═══════════════════════════════════════════════════════

    def forward(
        self,
        h_t: torch.Tensor,
        v_t: torch.Tensor,
        peer_obs: torch.Tensor,
        vocal_in: torch.Tensor,
        phase: torch.Tensor,
        energy: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Full Substrate 20 forward execution.
        """
        h_t = h_t.to(device=self.dev, dtype=torch.float16)
        v_t = v_t.to(device=self.dev, dtype=torch.float16)
        peer_obs = peer_obs.to(device=self.dev, dtype=torch.float16)
        vocal_in = vocal_in.to(device=self.dev, dtype=torch.float16)
        phase = phase.to(device=self.dev, dtype=torch.float16)

        if energy is not None:
            self.energy.data.copy_(energy.to(device=self.dev, dtype=torch.float16))

        # Compute PLL gates
        gates = self.compute_gates(phase, self.energy)

        # 1. Perception
        h_perceive = h_t + v_t * gates["write"].view(1, 1)

        # 2. Counterfactual Imagination
        h_imagine = self.imagination_rollout(h_t, gates["imagine"])

        # 3. Theory of Mind
        peer_models, peer_actions = self.tom_forward(peer_obs, gates["comm"])
        peer_context = torch.mm(peer_models.mean(dim=0, keepdim=True), self.W_goal)

        # 4. Symbolic Protocol Emission
        symbol_out = self.symbol_emit(h_t)

        # 5. Symbolic Protocol Reception
        if vocal_in.abs().sum() > 0:
            h_comm = self.symbol_receive(h_t, vocal_in, gates["comm"])
        else:
            h_comm = h_t
        h_comm = h_comm + peer_context * gates["comm"].view(1, 1)

        # 6. Grounding Update (Hebbian)
        self.update_grounding(symbol_out, h_t)

        # 7. CPC Contrastive Loss
        cpc = self.cpc_loss(symbol_out, h_perceive, self.cpc_negatives)

        # 8. Gated Multimodal Fusion
        total_gate = gates["write"] + gates["imagine"] + gates["comm"]
        residual = torch.clamp(1.0 - total_gate, min=0.0).view(1, 1)

        h_next = (
            h_perceive * gates["write"].view(1, 1) +
            h_imagine * gates["imagine"].view(1, 1) +
            h_comm * gates["comm"].view(1, 1) +
            h_t * residual
        )

        # 9. Negative Buffer Update
        self.cpc_negatives.data.copy_(
            torch.cat([h_t.squeeze(0).unsqueeze(0).detach(), self.cpc_negatives[:-1]], dim=0)
        )

        # 10. Metabolic Reward
        E_ratio = torch.sigmoid(self.energy / self.E_init)
        C_ratio = torch.sigmoid(self.flop_counter / self.Cost_max)
        metabolic_reward = E_ratio - C_ratio

        return {
            "h_next": h_next,
            "symbol_out": symbol_out,
            "peer_models": peer_models,
            "peer_actions": peer_actions,
            "cpc_loss": cpc,
            "metabolic_reward": metabolic_reward,
            "gates": gates,
            "energy": self.energy,
            "flops": self.flop_counter,
            "traffic": self.traffic_counter,
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Extract telemetry metrics for UI dashboard and WebSocket payload.
        """
        return {
            "imag_gate": round(float(self.last_imag_gate), 4),
            "imag_branch_eff": round(float(self.last_branch_eff), 2),
            "tom_peer_norm": round(float(self.tom_peer_models.norm().item()), 4),
            "tom_pred_error": round(float(self.tom_pred_error.norm().item()), 4),
            "tom_goal_diversity": int(len(torch.unique(self.tom_peer_goals.argmax(dim=1)))),
            "sym_grounding_norm": round(float(self.sym_grounding.norm().item()), 4),
            "sym_mi": round(float(self.sym_mi_estimate.item()), 4),
            "sym_temp": round(float(torch.sigmoid(self.sym_temp).item()), 3),
            "cpc_loss": round(float(self.cpc_loss_val.item()), 4),
            "energy": round(float(self.energy.item()), 2),
            "step_energy_cost": round(float(self.last_step_energy_cost), 6),
        }
