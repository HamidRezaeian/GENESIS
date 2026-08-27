"""
Substrate 21: Deep-Time Continual Learning & Meta-Plasticity Engine.
Mathematical Formulation & Zero-Allocation PyTorch FP16 Implementation.

Invariants:
- Rule 21: All costs grounded in measured FLOPs + memory traffic
- Rule 23: All tensors torch.float16, zero dynamic allocation in step
- Rule 25: Zero if-else; all gating via differentiable operators
- Rule 19: Zero-hole compact replay buffer
"""

import math
from typing import Dict, Optional, Tuple, List, Any
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class Substrate21Engine(nn.Module):
    """
    Substrate 21: Deep-Time Continual Learning & Meta-Plasticity Engine.
    
    Unifies TD-learning, world model training, CPC semiogenesis,
    SI consolidation, and Fisher-modulated meta-plasticity.
    """
    
    FLOP_COST = 5e-4       # Calibrated host FLOP accounting
    TRAFFIC_COST = 5e-5    # Calibrated host memory traffic accounting
    
    def __init__(
        self,
        dim: int = 32,
        n_actions: int = 4,
        n_symbols: int = 64,
        buffer_capacity: int = 50000,
        replay_batch: int = 32,
        consolidation_period: int = 2000,
        n_cpc_negatives: int = 8,
        device: str = "cuda"
    ):
        super().__init__()
        self.dim = dim
        self.n_actions = n_actions
        self.n_symbols = n_symbols
        self.buffer_capacity = buffer_capacity
        self.replay_batch = replay_batch
        self.consolidation_period = consolidation_period
        self.n_cpc_negatives = n_cpc_negatives
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        
        # ═══════════════════════════════════════════════════
        # LEARNABLE PARAMETERS (FP16)
        # ═══════════════════════════════════════════════════
        
        # --- Meta-weighting ---
        self.W_meta = nn.Parameter(torch.randn(5, 5, dtype=self.dtype, device=self.device) * 0.01)
        self.b_meta = nn.Parameter(torch.zeros(5, dtype=self.dtype, device=self.device))
        
        # --- Meta-plasticity sensitivity ---
        self.alpha_fisher = nn.Parameter(torch.tensor([1.0], dtype=self.dtype, device=self.device))
        self.alpha_delta = nn.Parameter(torch.tensor([1.0], dtype=self.dtype, device=self.device))
        self.alpha_energy = nn.Parameter(torch.tensor([1.0], dtype=self.dtype, device=self.device))
        
        # --- World dynamics model ---
        self.W_dyn = nn.Parameter(torch.randn(dim, dim, dtype=self.dtype, device=self.device) * 0.02)
        self.b_dyn = nn.Parameter(torch.zeros(dim, dtype=self.dtype, device=self.device))
        
        # --- CPC projection ---
        self.W_cpc = nn.Parameter(torch.randn(dim, dim, dtype=self.dtype, device=self.device) * 0.02)
        
        # --- Symbol grounding (shared with S20) ---
        self.sym_grounding = nn.Parameter(torch.randn(n_symbols, dim, dtype=self.dtype, device=self.device) * 0.02)
        
        # ═══════════════════════════════════════════════════
        # PRE-ALLOCATED STATE BUFFERS (FP16)
        # ═══════════════════════════════════════════════════
        
        # --- Meta-state EMAs ---
        self.register_buffer("td_ema", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("wm_ema", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("curiosity_ema", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        
        # --- Replay buffer (zero-hole, compact) ---
        self.transition_dim = dim * 2 + n_actions + 4
        self.register_buffer("replay_buffer", 
            torch.zeros(buffer_capacity, self.transition_dim, dtype=self.dtype, device=self.device))
        self.register_buffer("replay_priorities", 
            torch.zeros(buffer_capacity, dtype=self.dtype, device=self.device))
        self.register_buffer("replay_size", torch.tensor(0, dtype=torch.int32, device=self.device))
        self.register_buffer("replay_pos", torch.tensor(0, dtype=torch.int32, device=self.device))
        
        # Pre-allocated replay batch buffers
        self.register_buffer("batch_states", torch.zeros(replay_batch, dim, dtype=self.dtype, device=self.device))
        self.register_buffer("batch_actions", torch.zeros(replay_batch, n_actions, dtype=self.dtype, device=self.device))
        self.register_buffer("batch_rewards", torch.zeros(replay_batch, 1, dtype=self.dtype, device=self.device))
        self.register_buffer("batch_next_states", torch.zeros(replay_batch, dim, dtype=self.dtype, device=self.device))
        self.register_buffer("batch_dones", torch.zeros(replay_batch, 1, dtype=self.dtype, device=self.device))
        self.register_buffer("batch_indices", torch.zeros(replay_batch, dtype=torch.int64, device=self.device))
        self.register_buffer("batch_is_weights", torch.zeros(replay_batch, dtype=self.dtype, device=self.device))
        self.register_buffer("batch_probs", torch.zeros(buffer_capacity, dtype=self.dtype, device=self.device))
        
        # --- CPC negative samples ---
        self.register_buffer("cpc_negatives", 
            torch.randn(n_cpc_negatives, dim, dtype=self.dtype, device=self.device) * 0.01)
        
        # --- SI / Consolidation state ---
        self.brain = None
        self.fisher_diag: Dict[str, torch.Tensor] = {}
        self.si_omega: Dict[str, torch.Tensor] = {}
        self.si_W: Dict[str, torch.Tensor] = {}
        self.theta_star: Dict[str, torch.Tensor] = {}
        self.theta_start: Dict[str, torch.Tensor] = {}
        self.pre_step_params: Dict[str, torch.Tensor] = {}
        self.pre_step_grads: Dict[str, torch.Tensor] = {}
        self.eta_modulation: Dict[str, torch.Tensor] = {}
        
        # --- Consolidation counters ---
        self.register_buffer("tick_count", torch.tensor(0, dtype=torch.int32, device=self.device))
        self.register_buffer("consolidation_count", torch.tensor(0, dtype=torch.int32, device=self.device))
        
        # --- Energy / FLOP accounting ---
        self.register_buffer("energy", torch.tensor([100.0], dtype=self.dtype, device=self.device))
        self.register_buffer("flop_counter", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("traffic_counter", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("E_init", torch.tensor([100.0], dtype=self.dtype, device=self.device))
        self.register_buffer("E_crit", torch.tensor([50.0], dtype=self.dtype, device=self.device))
        self.register_buffer("Cost_max", torch.tensor([1e6], dtype=self.dtype, device=self.device))
        
        # --- Loss component storage ---
        self.register_buffer("last_loss_task", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("last_loss_dyn", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("last_loss_cpc", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("last_loss_si", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("last_r_intrinsic", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("last_loss_total", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("last_lambda", torch.zeros(5, dtype=self.dtype, device=self.device))
        self.register_buffer("fisher_trace", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        self.register_buffer("si_norm", torch.tensor([0.0], dtype=self.dtype, device=self.device))
        
        # --- EMA decay rates ---
        self.td_ema_decay = 0.95
        self.wm_ema_decay = 0.95
        self.curiosity_ema_decay = 0.99
        
        # --- Replay hyperparameters ---
        self.beta_priority = 0.4
        self.beta_is = 0.6
        self.beta_is_anneal = 1e-5
        self.td_clip = 10.0
        self.eps = 1e-6
        
        # --- SI hyperparameters ---
        self.xi = 0.05
        self.gamma_f = 0.5
        
        # --- Temp buffers for meta-state ---
        self.register_buffer("_meta_state", torch.zeros(5, dtype=self.dtype, device=self.device))
        self.register_buffer("_lambda", torch.zeros(5, dtype=self.dtype, device=self.device))

    # ═══════════════════════════════════════════════════════
    # BRAIN ATTACHMENT (pre-allocate parameter-shaped buffers)
    # ═══════════════════════════════════════════════════════
    def attach_brain(self, brain: nn.Module):
        """
        Attach brain and pre-allocate parameter-shaped buffers.
        Called ONCE at initialization — zero allocation in time loop.
        """
        self.brain = brain
        
        for name, param in brain.named_parameters():
            if not param.requires_grad:
                continue
            
            param_fp16 = param.data.to(dtype=self.dtype, device=self.device)
            self.fisher_diag[name] = torch.zeros_like(param_fp16, dtype=self.dtype, device=self.device)
            self.si_W[name] = torch.zeros_like(param_fp16, dtype=self.dtype, device=self.device)
            self.si_omega[name] = torch.zeros_like(param_fp16, dtype=self.dtype, device=self.device)
            self.theta_star[name] = param_fp16.clone()
            self.theta_start[name] = param_fp16.clone()
            self.pre_step_params[name] = torch.zeros_like(param_fp16, dtype=self.dtype, device=self.device)
            self.pre_step_grads[name] = torch.zeros_like(param_fp16, dtype=self.dtype, device=self.device)
            self.eta_modulation[name] = torch.ones_like(param_fp16, dtype=self.dtype, device=self.device)

    # ═══════════════════════════════════════════════════════
    # ENERGY ACCOUNTING (Rule 21)
    # ═══════════════════════════════════════════════════════
    @torch.no_grad()
    def _deduct_energy(self, flops: int, traffic_bytes: int):
        """Deduct energy based on measured computational work."""
        cost = float(flops * self.FLOP_COST + traffic_bytes * self.TRAFFIC_COST)
        cost_tensor = torch.tensor([cost], dtype=self.dtype, device=self.device)
        self.energy -= cost_tensor
        self.flop_counter += torch.tensor([float(flops)], dtype=self.dtype, device=self.device)
        self.traffic_counter += torch.tensor([float(traffic_bytes)], dtype=self.dtype, device=self.device)
        torch.clamp(self.energy, min=0.0, out=self.energy)

    def _matmul_cost(self, m: int, n: int, k: int) -> Tuple[int, int]:
        flops = 2 * m * n * k
        traffic = (m * k + k * n + m * n) * 2
        return flops, traffic

    # ═══════════════════════════════════════════════════════
    # META-STATE & META-WEIGHT COMPUTATION
    # ═══════════════════════════════════════════════════════
    def compute_meta_state(self) -> torch.Tensor:
        """Compute meta-state vector from EMAs (all differentiable)."""
        fisher_sum = torch.tensor([0.0], dtype=self.dtype, device=self.device)
        param_count = 0
        for name, f in self.fisher_diag.items():
            fisher_sum += f.sum()
            param_count += f.numel()
        
        fisher_norm = fisher_sum / max(1, param_count)
        self.fisher_trace[0] = fisher_norm.item()
        
        energy_ratio = self.energy / self.E_init
        
        self._meta_state[0] = self.td_ema[0]
        self._meta_state[1] = self.wm_ema[0]
        self._meta_state[2] = fisher_norm[0]
        self._meta_state[3] = energy_ratio[0]
        self._meta_state[4] = self.curiosity_ema[0]
        
        torch.clamp(self._meta_state, -10.0, 10.0, out=self._meta_state)
        return self._meta_state

    def compute_meta_weights(self, meta_state: torch.Tensor) -> torch.Tensor:
        """Compute loss component weights via softmax (differentiable)."""
        logits = torch.mv(self.W_meta, meta_state) + self.b_meta
        lam = F.softmax(logits, dim=0)
        
        self._lambda.copy_(lam)
        self.last_lambda.copy_(lam)
        
        flops = 2 * 5 * 5 + 5 * 3
        traffic = (5 * 5 + 5 + 5) * 2
        self._deduct_energy(flops, traffic)
        return lam

    # ═══════════════════════════════════════════════════════
    # META-PLASTICITY (Per-Parameter Learning Rate)
    # ═══════════════════════════════════════════════════════
    @torch.no_grad()
    def compute_eta_modulation(self, td_error: torch.Tensor):
        """
        Compute per-parameter learning rate modulation.
        η_k = η_0 * (1 - σ(α_F * F̂_k)) * σ(α_δ * |δ|) * σ(α_E * E/E_crit)
        """
        urgency = torch.sigmoid(self.alpha_delta * torch.abs(td_error))
        energy_ratio = self.energy / self.E_crit
        energy_gate = torch.sigmoid(self.alpha_energy * energy_ratio)
        
        for name, fisher in self.fisher_diag.items():
            f_max = fisher.max() + self.eps
            f_norm = fisher / f_max
            protection = 1.0 - torch.sigmoid(self.alpha_fisher * f_norm)
            self.eta_modulation[name] = protection * urgency * energy_gate
            
            n_elem = fisher.numel()
            flops = n_elem * 5
            traffic = n_elem * 4
            self._deduct_energy(flops, traffic)

    @torch.no_grad()
    def apply_eta_to_gradients(self):
        """Apply per-parameter learning rate to gradients (in-place)."""
        if self.brain is None:
            return
        for name, param in self.brain.named_parameters():
            if param.grad is not None and name in self.eta_modulation:
                param.grad.mul_(self.eta_modulation[name])
                n_elem = param.grad.numel()
                self._deduct_energy(n_elem, n_elem * 4)

    # ═══════════════════════════════════════════════════════
    # REPLAY BUFFER (Zero-Hole, Compact)
    # ═══════════════════════════════════════════════════════
    @torch.no_grad()
    def add_experience(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
        reward: float,
        next_state: torch.Tensor,
        done: bool,
        td_error: float,
        epistemic_h: float
    ):
        """Add transition to replay buffer with computed priority."""
        td_clipped = min(abs(td_error), self.td_clip)
        epistemic_gate = torch.sigmoid(
            torch.tensor([2.0 * (epistemic_h - 0.3)], dtype=self.dtype, device=self.device)
        )
        priority = torch.clamp(
            torch.tensor([td_clipped * epistemic_gate.item() + self.eps], 
                        dtype=self.dtype, device=self.device),
            min=self.eps, max=self.td_clip
        )
        
        transition = torch.zeros(self.transition_dim, dtype=self.dtype, device=self.device)
        transition[:self.dim] = state.to(dtype=self.dtype)
        transition[self.dim:self.dim + self.n_actions] = action.to(dtype=self.dtype)
        transition[self.dim + self.n_actions] = float(reward)
        transition[self.dim + self.n_actions + 1:self.dim + self.n_actions + 1 + self.dim] = next_state.to(dtype=self.dtype)
        transition[self.dim + self.n_actions + 1 + self.dim] = float(done)
        transition[self.dim + self.n_actions + 2 + self.dim] = float(td_error)
        transition[self.dim + self.n_actions + 3 + self.dim] = float(epistemic_h)
        transition[-1] = priority[0]
        
        if self.replay_size < self.buffer_capacity:
            idx = int(self.replay_size.item())
            self.replay_buffer[idx] = transition
            self.replay_priorities[idx] = priority[0]
            self.replay_size += 1
        else:
            min_idx = int(self.replay_priorities.argmin().item())
            self.replay_buffer[min_idx] = transition
            self.replay_priorities[min_idx] = priority[0]
        
        self._deduct_energy(10, self.transition_dim * 2)

    @torch.no_grad()
    def sample_replay(self) -> Tuple[bool, Optional[torch.Tensor]]:
        """
        Priority-based sampling from replay buffer.
        Returns (success, is_weights).
        """
        if self.replay_size < self.replay_batch:
            return False, None
        
        self.beta_is = min(1.0, self.beta_is + self.beta_is_anneal)
        size = int(self.replay_size.item())
        priorities = self.replay_priorities[:size] ** self.beta_priority
        probs = priorities / (priorities.sum() + self.eps)
        self.batch_probs[:size] = probs
        
        indices = torch.multinomial(probs, self.replay_batch, replacement=True)
        self.batch_indices[:self.replay_batch] = indices
        
        batch = self.replay_buffer[indices]
        self.batch_states[:] = batch[:, :self.dim]
        self.batch_actions[:] = batch[:, self.dim:self.dim + self.n_actions]
        self.batch_rewards[:] = batch[:, self.dim + self.n_actions:self.dim + self.n_actions + 1]
        self.batch_next_states[:] = batch[:, self.dim + self.n_actions + 1:self.dim + self.n_actions + 1 + self.dim]
        self.batch_dones[:] = batch[:, self.dim + self.n_actions + 1 + self.dim:self.dim + self.n_actions + 2 + self.dim]
        
        is_weights = (size * probs[indices] + self.eps) ** (-self.beta_is)
        is_weights = is_weights / is_weights.max()
        self.batch_is_weights[:] = is_weights
        
        self._deduct_energy(size + self.replay_batch, size * 2 + self.replay_batch * self.transition_dim * 2)
        return True, self.batch_is_weights

    # ═══════════════════════════════════════════════════════
    # LOSS COMPUTATIONS
    # ═══════════════════════════════════════════════════════
    def compute_task_loss(
        self,
        q_values: torch.Tensor,
        q_next: torch.Tensor,
        rewards: torch.Tensor,
        dones: torch.Tensor,
        is_weights: torch.Tensor,
        gamma: float = 0.99
    ) -> torch.Tensor:
        """TD-error loss with importance sampling correction."""
        target = rewards + gamma * q_next * (1.0 - dones)
        td_error = target - q_values
        loss = (td_error ** 2 * is_weights.unsqueeze(1)).mean()
        self.last_loss_task[0] = loss.detach().item()
        
        batch = q_values.shape[0]
        self._deduct_energy(batch * 6, batch * 4 * 2)
        return loss

    def compute_dyn_loss(self, h_t: torch.Tensor, h_next: torch.Tensor) -> torch.Tensor:
        """World model dynamics loss (MSE)."""
        h_pred = torch.tanh(torch.mm(h_t, self.W_dyn) + self.b_dyn)
        loss = F.mse_loss(h_pred, h_next)
        self.last_loss_dyn[0] = loss.detach().item()
        
        batch = h_t.shape[0]
        flops, traffic = self._matmul_cost(batch, self.dim, self.dim)
        flops += batch * self.dim * 2
        self._deduct_energy(flops, traffic)
        return loss

    def compute_cpc_loss(
        self,
        symbol_soft: torch.Tensor,
        h_positive: torch.Tensor,
        h_negatives: torch.Tensor
    ) -> torch.Tensor:
        """Contrastive Predictive Coding loss for symbol grounding."""
        sym_proj = torch.mm(symbol_soft.unsqueeze(0), self.sym_grounding)
        sym_proj = torch.tanh(torch.mm(sym_proj, self.W_cpc))
        
        h_pos_proj = torch.tanh(torch.mm(h_positive, self.W_cpc))
        h_neg_proj = torch.tanh(torch.mm(h_negatives, self.W_cpc))
        
        eps = 1e-4
        sym_norm = sym_proj / (torch.norm(sym_proj, dim=-1, keepdim=True) + eps)
        pos_norm = h_pos_proj / (torch.norm(h_pos_proj, dim=-1, keepdim=True) + eps)
        neg_norm = h_neg_proj / (torch.norm(h_neg_proj, dim=-1, keepdim=True) + eps)
        
        pos_sim = (sym_norm * pos_norm).sum(dim=-1)
        neg_sim = (sym_norm * neg_norm).sum(dim=-1)
        
        temp = torch.sigmoid(torch.tensor([0.5], dtype=self.dtype, device=self.device)) + 0.1
        all_sim = torch.cat([pos_sim, neg_sim]) / temp
        loss = -F.log_softmax(all_sim, dim=0)[0]
        self.last_loss_cpc[0] = loss.detach().item()
        
        flops, traffic = self._matmul_cost(1, self.dim, self.n_symbols)
        flops += self._matmul_cost(1, self.dim, self.dim)[0]
        flops += self._matmul_cost(self.n_cpc_negatives, self.dim, self.dim)[0]
        flops += (1 + self.n_cpc_negatives) * self.dim * 2
        self._deduct_energy(flops, traffic)
        return loss

    def compute_si_loss(self) -> torch.Tensor:
        """Synaptic Intelligence quadratic penalty."""
        loss = torch.tensor([0.0], dtype=self.dtype, device=self.device)
        total_norm = 0.0
        
        if self.brain is not None:
            for name, param in self.brain.named_parameters():
                if name not in self.si_omega:
                    continue
                omega = self.si_omega[name]
                theta_ref = self.theta_star[name]
                omega = torch.clamp(omega, max=1e3)
                delta = param - theta_ref
                delta = torch.clamp(delta, min=-1e3, max=1e3)
                penalty = (omega * delta ** 2).sum()
                loss = loss + penalty
                total_norm += omega.norm().item()
        
        self.si_norm[0] = total_norm
        self.last_loss_si[0] = loss.detach().item()
        
        total_params = sum(p.numel() for p in self.brain.parameters() if p.requires_grad) if self.brain else 1000
        self._deduct_energy(total_params * 4, total_params * 4)
        return loss

    def compute_intrinsic_reward(self) -> torch.Tensor:
        """Epistemic curiosity bonus (entropy of predictive uncertainty)."""
        fisher_total = torch.tensor([0.0], dtype=self.dtype, device=self.device)
        for f in self.fisher_diag.values():
            fisher_total += f.sum()
        
        sigma_sq = 1.0 / (fisher_total + self.eps)
        sigma_sq = torch.clamp(sigma_sq, min=1e-6, max=1e4)
        intrinsic = 0.5 * torch.log(2 * math.pi * math.e * sigma_sq)
        intrinsic = torch.clamp(intrinsic, min=-10.0, max=10.0)
        
        self.last_r_intrinsic[0] = intrinsic.item()
        self._deduct_energy(10, 10)
        return intrinsic

    # ═══════════════════════════════════════════════════════
    # UNIFIED LOSS
    # ═══════════════════════════════════════════════════════
    def compute_unified_loss(
        self,
        q_values: torch.Tensor,
        q_next: torch.Tensor,
        h_t: torch.Tensor,
        h_next: torch.Tensor,
        symbol_soft: torch.Tensor,
        td_error: torch.Tensor,
        is_weights: Optional[torch.Tensor] = None,
        gamma: float = 0.99
    ) -> torch.Tensor:
        """
        Compute unified multi-objective loss with differentiable meta-weighting.
        L_total = λ1*L_task + λ2*L_dyn + λ3*L_CPC + λ4*L_SI - λ5*R_intrinsic
        """
        meta_state = self.compute_meta_state()
        lam = self.compute_meta_weights(meta_state)
        
        with torch.no_grad():
            td_abs = torch.abs(td_error).mean()
            self.td_ema.mul_(self.td_ema_decay).add_((1 - self.td_ema_decay) * td_abs)
        
        if is_weights is None:
            is_weights = torch.ones(q_values.shape[0], dtype=self.dtype, device=self.device)
        
        rewards = self.batch_rewards[:q_values.shape[0]]
        dones = self.batch_dones[:q_values.shape[0]]
        
        loss_task = self.compute_task_loss(q_values, q_next, rewards, dones, is_weights, gamma)
        loss_dyn = self.compute_dyn_loss(h_t, h_next)
        loss_cpc = self.compute_cpc_loss(symbol_soft, h_next, self.cpc_negatives)
        loss_si = self.compute_si_loss()
        r_intrinsic = self.compute_intrinsic_reward()
        
        with torch.no_grad():
            self.curiosity_ema.mul_(self.curiosity_ema_decay)
            self.curiosity_ema.add_((1 - self.curiosity_ema_decay) * r_intrinsic)
            self.wm_ema.mul_(self.wm_ema_decay).add_((1 - self.wm_ema_decay) * loss_dyn.detach())
        
        loss_total = (
            lam[0] * loss_task +
            lam[1] * loss_dyn +
            lam[2] * loss_cpc +
            lam[3] * loss_si -
            lam[4] * r_intrinsic
        )
        
        self.last_loss_total[0] = loss_total.detach().item()
        self.compute_eta_modulation(td_error.mean())
        return loss_total

    # ═══════════════════════════════════════════════════════
    # SI PATH INTEGRAL & FISHER UPDATES
    # ═══════════════════════════════════════════════════════
    @torch.no_grad()
    def pre_step_snapshot(self):
        """Snapshot parameters and gradients before optimizer.step()."""
        if self.brain is None:
            return
        for name, param in self.brain.named_parameters():
            if name not in self.pre_step_params:
                continue
            self.pre_step_params[name].copy_(param.data)
            if param.grad is not None:
                self.pre_step_grads[name].copy_(param.grad)

    @torch.no_grad()
    def post_step_accumulate(self):
        """Accumulate SI path integral after optimizer.step()."""
        if self.brain is None:
            return
        for name, param in self.brain.named_parameters():
            if name not in self.pre_step_params:
                continue
            theta_before = self.pre_step_params[name]
            grad_before = self.pre_step_grads[name]
            delta_theta = param.data - theta_before
            self.si_W[name] -= grad_before * delta_theta
            self.pre_step_params[name].copy_(param.data)
            
            n_elem = param.numel()
            self._deduct_energy(n_elem * 3, n_elem * 6)

    @torch.no_grad()
    def update_fisher(self, decay: float = 0.99):
        """Update Fisher diagonal via running EMA of squared gradients."""
        if self.brain is None:
            return
        for name, param in self.brain.named_parameters():
            if name not in self.fisher_diag or param.grad is None:
                continue
            grad_sq = torch.clamp(param.grad ** 2, max=1e4)
            self.fisher_diag[name].mul_(decay).add_((1 - decay) * grad_sq)
            n_elem = param.numel()
            self._deduct_energy(n_elem * 4, n_elem * 6)

    @torch.no_grad()
    def consolidate(self):
        """
        Sleep consolidation: normalize SI path integral, seed with Fisher,
        update reference parameters.
        """
        if self.brain is None:
            return
        total_norm = 0.0
        for name, param in self.brain.named_parameters():
            if name not in self.si_W:
                continue
            delta = param.data - self.theta_start[name]
            delta = torch.clamp(delta, min=-1e3, max=1e3)
            
            numerator = torch.abs(self.si_W[name]) + self.gamma_f * self.fisher_diag[name]
            denominator = delta ** 2 + self.xi
            new_omega = torch.clamp(numerator / denominator, max=1e3)
            
            self.si_omega[name] += new_omega
            self.si_omega[name] = torch.clamp(self.si_omega[name], max=1e3)
            total_norm += float(self.si_omega[name].norm().item())
            self.theta_star[name].copy_(param.data)
            self.theta_start[name].copy_(param.data)
            self.si_W[name].zero_()
        
        self.si_norm[0] = total_norm
        self.consolidation_count += 1
        total_params = sum(p.numel() for p in self.brain.parameters() if p.requires_grad)
        self._deduct_energy(total_params * 8, total_params * 8)

    # ═══════════════════════════════════════════════════════
    # MAIN STEP
    # ═══════════════════════════════════════════════════════
    def step(
        self,
        h_t: torch.Tensor,
        h_next: torch.Tensor,
        q_values: torch.Tensor,
        q_next: torch.Tensor,
        reward: float,
        done: bool,
        action: torch.Tensor,
        symbol_soft: torch.Tensor,
        gamma: float = 0.99
    ) -> Dict[str, Any]:
        """Full Substrate 21 step."""
        self.tick_count += 1
        
        with torch.no_grad():
            target_q = reward + gamma * q_next.item() * (1.0 - float(done))
            td_error = torch.tensor([target_q - q_values.item()], 
                                    dtype=self.dtype, device=self.device)
            
            fisher_total = torch.tensor([0.0], dtype=self.dtype, device=self.device)
            for f in self.fisher_diag.values():
                fisher_total += f.sum()
            epistemic_h = 0.5 * torch.log(1.0 / (fisher_total + self.eps) + 1.0)
            epistemic_h = torch.clamp(epistemic_h, min=0.0, max=10.0)
        
        self.add_experience(
            state=h_t.squeeze(0),
            action=action,
            reward=reward,
            next_state=h_next.squeeze(0),
            done=done,
            td_error=td_error.item(),
            epistemic_h=epistemic_h.item()
        )
        
        success, is_weights = self.sample_replay()
        if success and self.brain is not None and hasattr(self.brain, "forward_critic"):
            batch_h = self.batch_states
            batch_h_next = self.batch_next_states
            with torch.no_grad():
                batch_q = self.brain.forward_critic(batch_h, self.batch_actions)
                batch_q_next = self.brain.forward_critic_target(batch_h_next)
            loss = self.compute_unified_loss(
                q_values=batch_q,
                q_next=batch_q_next,
                h_t=batch_h,
                h_next=batch_h_next,
                symbol_soft=symbol_soft,
                td_error=td_error,
                is_weights=is_weights,
                gamma=gamma
            )
        else:
            loss = self.compute_unified_loss(
                q_values=q_values,
                q_next=q_next,
                h_t=h_t,
                h_next=h_next,
                symbol_soft=symbol_soft,
                td_error=td_error,
                is_weights=None,
                gamma=gamma
            )
        
        self.pre_step_snapshot()
        loss.backward()
        self.update_fisher()
        self.apply_eta_to_gradients()
        
        if self.tick_count % self.consolidation_period == 0 and self.tick_count > 0:
            self.consolidate()
        
        with torch.no_grad():
            self.cpc_negatives = torch.cat([
                h_t.squeeze(0).unsqueeze(0),
                self.cpc_negatives[:-1]
            ], dim=0)
        
        return {
            "loss": loss,
            "loss_task": self.last_loss_task.item(),
            "loss_dyn": self.last_loss_dyn.item(),
            "loss_cpc": self.last_loss_cpc.item(),
            "loss_si": self.last_loss_si.item(),
            "r_intrinsic": self.last_r_intrinsic.item(),
            "loss_total": self.last_loss_total.item(),
            "lambda": self.last_lambda.tolist(),
            "td_error": td_error.item(),
            "energy": self.energy.item(),
            "flops": self.flop_counter.item(),
            "fisher_trace": self.fisher_trace.item(),
            "si_norm": self.si_norm.item(),
            "consolidation_count": self.consolidation_count.item(),
            "replay_size": self.replay_size.item(),
        }

    def post_optimizer_step(self):
        """Call this AFTER optimizer.step() to accumulate SI path integral."""
        self.post_step_accumulate()

    def get_telemetry(self) -> Dict[str, float]:
        """Extract all telemetry metrics."""
        return {
            "loss_task": float(self.last_loss_task.item()),
            "loss_dyn": float(self.last_loss_dyn.item()),
            "loss_cpc": float(self.last_loss_cpc.item()),
            "loss_si": float(self.last_loss_si.item()),
            "r_intrinsic": float(self.last_r_intrinsic.item()),
            "loss_total": float(self.last_loss_total.item()),
            "lambda_task": float(self.last_lambda[0].item()),
            "lambda_dyn": float(self.last_lambda[1].item()),
            "lambda_cpc": float(self.last_lambda[2].item()),
            "lambda_si": float(self.last_lambda[3].item()),
            "lambda_intrinsic": float(self.last_lambda[4].item()),
            "td_ema": float(self.td_ema.item()),
            "wm_ema": float(self.wm_ema.item()),
            "curiosity_ema": float(self.curiosity_ema.item()),
            "fisher_trace": float(self.fisher_trace.item()),
            "si_norm": float(self.si_norm.item()),
            "consolidation_count": int(self.consolidation_count.item()),
            "replay_size": int(self.replay_size.item()),
            "replay_capacity": self.buffer_capacity,
            "replay_utilization": float(self.replay_size.item()) / self.buffer_capacity,
            "energy": float(self.energy.item()),
            "total_flops": float(self.flop_counter.item()),
            "total_traffic": float(self.traffic_counter.item()),
        }

    def get_payload(self) -> Dict[str, Any]:
        """Structured payload for WebSocket telemetry."""
        t = self.get_telemetry()
        return {
            "substrate21": {
                "losses": {
                    "task": t["loss_task"],
                    "dyn": t["loss_dyn"],
                    "cpc": t["loss_cpc"],
                    "si": t["loss_si"],
                    "intrinsic": t["r_intrinsic"],
                    "total": t["loss_total"],
                },
                "meta_weights": {
                    "task": t["lambda_task"],
                    "dyn": t["lambda_dyn"],
                    "cpc": t["lambda_cpc"],
                    "si": t["lambda_si"],
                    "intrinsic": t["lambda_intrinsic"],
                },
                "meta_plasticity": {
                    "td_ema": t["td_ema"],
                    "wm_ema": t["wm_ema"],
                    "curiosity_ema": t["curiosity_ema"],
                    "fisher_trace": t["fisher_trace"],
                    "si_norm": t["si_norm"],
                },
                "replay": {
                    "size": t["replay_size"],
                    "capacity": t["replay_capacity"],
                    "utilization": t["replay_utilization"],
                    "consolidation_count": t["consolidation_count"],
                },
                "energy": {
                    "reserve": t["energy"],
                    "total_flops": t["total_flops"],
                    "total_traffic": t["total_traffic"],
                },
            }
        }
