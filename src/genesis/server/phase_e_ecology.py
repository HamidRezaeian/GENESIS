"""
GENESIS Phase-E: Physical Ecology & 2D Resource Landscape (Vectorized GPU Engine).
Authoritative formulation for Open-Ended Evolutionary ALife (GLM 5.3 Multi-World Batching).

Invariants:
- Rule 7: Emergent efficiency through honest environmental resource dynamics.
- Rule 13: Grounded spatial contention and open-ended resource competition.
- Rule 15: Substrate-grounded abstraction (No free energy; conservation laws apply).
- Rule 21: Physical grounding without authored game mechanics or synthetic rewards.
- Rule 23: Pure PyTorch tensor operations with zero Python per-organism loops.
"""

import math
from typing import Dict, Any, Tuple, Optional
import torch
import torch.nn.functional as F
import numpy as np


class EcologyField:
    """
    Multi-World Batched Physical Resource Landscape.
    Executes W worlds simultaneously using grouped convolutions and batched indexing.
    """
    def __init__(
        self,
        n_worlds: int = 32,
        grid_size: int = 32,
        max_food_capacity: float = 5.0,
        regeneration_rate: float = 0.005,
        diffusion_rate: float = 0.08,
        harvest_efficiency: float = 12.0,
        T_season: float = 2000.0,
        A_season: float = 0.6,
        kappa: float = 0.01,
        sigma_ou: float = 0.003,
        drift_speed: float = 0.005,
        patch_sigma: float = 0.02,
        omega: float = 0.001,
        device: Optional[str] = None,
        seed: int = 42
    ):
        self.W = n_worlds
        self.grid_size = grid_size
        self.max_cap = max_food_capacity
        self.regen_rate = regeneration_rate
        self.diff_rate = diffusion_rate
        self.harvest_eff = harvest_efficiency
        
        # GLM 5.3 Non-Stationary Dynamics Parameters
        self.T_season = T_season
        self.A_season = A_season
        self.kappa = kappa
        self.sigma_ou = sigma_ou
        self.drift_speed = drift_speed
        self.patch_sigma = patch_sigma
        self.omega = omega
        
        self.dev = torch.device(device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.rng = np.random.RandomState(seed)
        
        # [W, G, G]
        self.resources = torch.zeros((self.W, grid_size, grid_size), dtype=torch.float32, device=self.dev)
        
        # Dynamic Migrating Patch Centers [W, n_patches, 2]
        self.n_patches = 8
        self.patch_centers = torch.rand(self.W, self.n_patches, 2, device=self.dev) * 0.8 + 0.1
        self.patch_amplitudes = torch.full((self.W, self.n_patches), self.max_cap, device=self.dev)
        self.phi_0 = torch.rand(self.W, device=self.dev) * 2 * math.pi
        
        # Precomputed Normalized Coordinate Grids [G, G]
        coords = torch.arange(self.grid_size, device=self.dev, dtype=torch.float32) / self.grid_size
        self.grid_y, self.grid_x = torch.meshgrid(coords, coords, indexing='xy')
        
        # 2D Diffusion kernel for F.conv2d [1, 1, 3, 3]
        kernel_np = np.array([
            [0.05, 0.10, 0.05],
            [0.10, -0.60, 0.10],
            [0.05, 0.10, 0.05]
        ], dtype=np.float32)
        self.diff_kernel = torch.tensor(kernel_np, dtype=torch.float32, device=self.dev).unsqueeze(0).unsqueeze(0)
        
        # Direction vectors [4, 2]
        self.d_vecs = torch.tensor([
            [0.0, -0.03],
            [0.03, 0.0],
            [0.0, 0.03],
            [-0.03, 0.0]
        ], dtype=torch.float32, device=self.dev)
        self.tick_count = 0
        
        # Stigmergy fields [W, K, G, G]
        self.K_symbols = 4
        self.stigmergy = torch.zeros((self.W, self.K_symbols, self.grid_size, self.grid_size),
                                      dtype=torch.float32, device=self.dev)
        self.stig_max = 3.0
        self.stig_deposit_rate = 0.6
        self.stig_decay = 0.002
        self.stig_diff_rate = 0.12

        self.E_deposit = 0.008

        # Locked resources [W, G, G]
        self.locked_resources = torch.zeros((self.W, self.grid_size, self.grid_size),
                                             dtype=torch.float32, device=self.dev)
        self.lock_threshold = 3
        self.lock_max = 15.0
        self.harvest_radius = 1
        
        # Pre-allocated buffers (Zero-Allocation HPC Invariant)
        self._target_field = torch.zeros((self.W, grid_size, grid_size), dtype=torch.float32, device=self.dev)
        self._gaussian_patches = torch.zeros((self.W, grid_size, grid_size), dtype=torch.float32, device=self.dev)
        self._macro_update_period = 4
        self._diffusion_period = 8
        self._sensory_inputs = torch.zeros((self.W, 128, 20), dtype=torch.float32, device=self.dev)
        self._harvested_energy = torch.zeros((self.W, 128), dtype=torch.float32, device=self.dev)
        
        self.w_idx = torch.arange(self.W, device=self.dev)
        
        self._seed_all_worlds()

    def _seed_all_worlds(self):
        for w in range(self.W):
            self._seed_world(w)

    def _seed_world(self, w: int, num_patches: int = 8, num_locked: int = 4):
        res_np = np.zeros((self.grid_size, self.grid_size), dtype=np.float32)
        for _ in range(num_patches):
            cx = self.rng.randint(2, self.grid_size - 2)
            cy = self.rng.randint(2, self.grid_size - 2)
            amount = self.rng.uniform(2.0, self.max_cap)
            for x in range(max(0, cx - 4), min(self.grid_size, cx + 5)):
                for y in range(max(0, cy - 4), min(self.grid_size, cy + 5)):
                    d2 = (x - cx)**2 + (y - cy)**2
                    res_np[x, y] = np.clip(res_np[x, y] + amount * math.exp(-d2 / 4.0), 0.0, self.max_cap)
        self.resources[w].copy_(torch.tensor(res_np, dtype=torch.float32, device=self.dev))
        
        locked_np = np.zeros((self.grid_size, self.grid_size), dtype=np.float32)
        for _ in range(num_locked):
            cx = self.rng.randint(4, self.grid_size - 4)
            cy = self.rng.randint(4, self.grid_size - 4)
            amount = self.rng.uniform(8.0, self.lock_max)
            for x in range(max(0, cx - 3), min(self.grid_size, cx + 4)):
                for y in range(max(0, cy - 3), min(self.grid_size, cy + 4)):
                    d2 = (x - cx)**2 + (y - cy)**2
                    locked_np[x, y] = np.clip(locked_np[x, y] + amount * math.exp(-d2 / 3.0), 0.0, self.lock_max)
        self.locked_resources[w].copy_(torch.tensor(locked_np, dtype=torch.float32, device=self.dev))

    @torch.no_grad()
    def update_environment(self):
        """
        GLM 5.3 Macro-Rate Non-Stationary Ecology Update:
        - Full Gaussian mesh & patch migration: every 4 ticks
        - Lightweight intra-macro linear inertia: every tick
        - Grouped 2D Diffusion: every 8 ticks
        """
        self.tick_count += 1
        t = float(self.tick_count)
        
        # ═══════════════════════════════════════════════════════
        # 1. Macro-Rate Update (every 4 ticks)
        # ═══════════════════════════════════════════════════════
        if self.tick_count % self._macro_update_period == 0:
            season = (self.A_season * math.sin(2 * math.pi * t / self.T_season) 
                      + 0.3 * math.cos(4 * math.pi * t / self.T_season))
            season_factor = max(0.3, 1.0 + season)
            
            # Migrate patch centers
            drift_angle = self.omega * t + self.phi_0
            drift_vec = torch.stack([
                self.drift_speed * torch.cos(drift_angle),
                self.drift_speed * torch.sin(drift_angle)
            ], dim=-1).unsqueeze(1)
            
            noise = torch.randn_like(self.patch_centers) * self.patch_sigma
            self.patch_centers.add_(drift_vec + noise).clamp_(0.05, 0.95)
            
            # Reconstruct dynamic Gaussian field
            gx_exp = self.grid_x.unsqueeze(0).unsqueeze(0)
            gy_exp = self.grid_y.unsqueeze(0).unsqueeze(0)
            cx = self.patch_centers[..., 0].unsqueeze(-1).unsqueeze(-1)
            cy = self.patch_centers[..., 1].unsqueeze(-1).unsqueeze(-1)
            amps = self.patch_amplitudes.unsqueeze(-1).unsqueeze(-1)
            
            d2 = (gx_exp - cx)**2 + (gy_exp - cy)**2
            torch.sum(amps * season_factor * torch.exp(-d2 / 0.015), dim=1, out=self._gaussian_patches)
            
            # Multiplicative OU noise
            ou_noise = torch.randn_like(self.resources) * self.sigma_ou * torch.sqrt(torch.clamp(self._gaussian_patches, min=0.0))
            self._target_field.copy_(self._gaussian_patches).add_(ou_noise).clamp_(0.0, self.max_cap)
            
            # Full inertia step
            self.resources.add_(self.kappa * (self._target_field - self.resources)).clamp_(0.0, self.max_cap)
        else:
            # Lightweight intra-macro inertia step
            alpha = self.kappa / self._macro_update_period
            self.resources.add_(alpha * (self._target_field - self.resources)).clamp_(0.0, self.max_cap)
            
        # ═══════════════════════════════════════════════════════
        # 2. Diffusion (every 8 ticks)
        # ═══════════════════════════════════════════════════════
        if self.tick_count % self._diffusion_period == 0:
            res_4d = self.resources.unsqueeze(1)
            laplacian = F.conv2d(res_4d, self.diff_kernel, padding=1).squeeze(1)
            self.resources.add_(self.diff_rate * 4.0 * laplacian).clamp_(0.0, self.max_cap)
            
            stig_4d = self.stigmergy.view(-1, 1, self.grid_size, self.grid_size)
            stig_lap = F.conv2d(stig_4d, self.diff_kernel, padding=1)
            self.stigmergy.add_(self.stig_diff_rate * stig_lap.view(self.W, self.K_symbols, self.grid_size, self.grid_size)).clamp_(0.0, self.stig_max)

        self.locked_resources.add_(0.0008 * (self.lock_max - self.locked_resources))
        self.stigmergy.mul_(1.0 - self.stig_decay)

    @torch.no_grad()
    def process_interactions(
        self,
        positions: torch.Tensor,     # [W, N, 2]
        orientations: torch.Tensor,  # [W, N]
        actions: torch.Tensor,       # [W, N]
        alive_mask: torch.Tensor,    # [W, N]
        energy: torch.Tensor,        # [W, N]
        device: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        W, N = positions.shape[:2]
        alive = alive_mask.bool()
        
        turn_l = (actions == 1) & alive
        turn_r = (actions == 2) & alive
        orientations[turn_l] = (orientations[turn_l] - 1) % 4
        orientations[turn_r] = (orientations[turn_r] + 1) % 4
        
        fwd = (actions == 0) & alive
        cur_dirs = orientations[fwd] % 4
        step_vecs = self.d_vecs[cur_dirs]
        positions[fwd] = torch.clamp(positions[fwd] + step_vecs, 0.01, 0.99)
        
        gx = torch.clamp((positions[..., 0] * self.grid_size).long(), 0, self.grid_size - 1)
        gy = torch.clamp((positions[..., 1] * self.grid_size).long(), 0, self.grid_size - 1)
        w_grid = self.w_idx.unsqueeze(1).expand(W, N)
        
        harvest = (actions == 3) & alive
        if self._harvested_energy.shape[:2] != (W, N):
            self._harvested_energy = torch.zeros((W, N), dtype=torch.float32, device=device)
        self._harvested_energy.zero_()
        
        if torch.any(harvest):
            hw = w_grid[harvest]
            hx = gx[harvest]
            hy = gy[harvest]
            avail = self.resources[hw, hx, hy]
            take = torch.clamp(avail, max=0.8)
            self.resources[hw, hx, hy] -= take
            self._harvested_energy[harvest] += take * self.harvest_eff
            
        emit = (actions == 4) & alive
        if torch.any(emit):
            ew = w_grid[emit]
            ex = gx[emit]
            ey = gy[emit]
            symbol_channels = (orientations[emit] % self.K_symbols).long()
            self.stigmergy[ew, symbol_channels, ex, ey] = torch.clamp(
                self.stigmergy[ew, symbol_channels, ex, ey] + self.stig_deposit_rate,
                0.0, self.stig_max
            )
            
        if self._sensory_inputs.shape[:2] != (W, N):
            self._sensory_inputs = torch.zeros((W, N, 20), dtype=torch.float32, device=device)
        self._sensory_inputs.zero_()
        
        self._sensory_inputs[..., 0] = self.resources[w_grid, gx, gy] / self.max_cap
        
        f_dirs = orientations % 4
        f_vecs = self.d_vecs[f_dirs]
        f_pos = torch.clamp(positions + f_vecs, 0.01, 0.99)
        fgx = torch.clamp((f_pos[..., 0] * self.grid_size).long(), 0, self.grid_size - 1)
        fgy = torch.clamp((f_pos[..., 1] * self.grid_size).long(), 0, self.grid_size - 1)
        self._sensory_inputs[..., 1] = self.resources[w_grid, fgx, fgy] / self.max_cap
        
        l_dirs = (orientations - 1) % 4
        l_vecs = self.d_vecs[l_dirs]
        l_pos = torch.clamp(positions + l_vecs, 0.01, 0.99)
        lgx = torch.clamp((l_pos[..., 0] * self.grid_size).long(), 0, self.grid_size - 1)
        lgy = torch.clamp((l_pos[..., 1] * self.grid_size).long(), 0, self.grid_size - 1)
        self._sensory_inputs[..., 2] = self.resources[w_grid, lgx, lgy] / self.max_cap
        
        r_dirs = (orientations + 1) % 4
        r_vecs = self.d_vecs[r_dirs]
        r_pos = torch.clamp(positions + r_vecs, 0.01, 0.99)
        rgx = torch.clamp((r_pos[..., 0] * self.grid_size).long(), 0, self.grid_size - 1)
        rgy = torch.clamp((r_pos[..., 1] * self.grid_size).long(), 0, self.grid_size - 1)
        self._sensory_inputs[..., 3] = self.resources[w_grid, rgx, rgy] / self.max_cap
        
        self._sensory_inputs[..., 4] = positions[..., 0]
        self._sensory_inputs[..., 5] = positions[..., 1]
        self._sensory_inputs[..., 6] = (orientations % 4).float() / 4.0
        self._sensory_inputs[..., 7] = torch.clamp(energy / 200.0, 0.0, 1.0)
        
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for s_idx, (ox, oy) in enumerate(offsets):
            ngx = torch.clamp(gx + ox, 0, self.grid_size - 1)
            ngy = torch.clamp(gy + oy, 0, self.grid_size - 1)
            self._sensory_inputs[..., 8 + s_idx] = self.resources[w_grid, ngx, ngy] / self.max_cap

        for k in range(self.K_symbols):
            self._sensory_inputs[..., 16 + k] = self.stigmergy[w_grid, k, gx, gy] / self.stig_max
            
        self.update_environment()
        
        return self._sensory_inputs, self._harvested_energy

    def get_render_grid(self, world_idx: int = 0) -> np.ndarray:
        res_cpu = self.resources[world_idx].detach().cpu().numpy()
        return np.clip(res_cpu / max(1e-3, self.max_cap), 0.0, 1.0)
