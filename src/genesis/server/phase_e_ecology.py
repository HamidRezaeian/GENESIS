"""
GENESIS Phase-E: Physical Ecology & 2D Resource Landscape (Vectorized GPU Engine).
Authoritative formulation for Open-Ended Evolutionary ALife.

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
    2D continuous/discrete physical resource landscape with dynamic nutrient replenishment,
    chemical diffusion, sensory receptive field mapping, and multi-organism spatial interaction.
    Fully vectorized in PyTorch CUDA tensor operations for maximum HPC throughput.
    """
    def __init__(
        self,
        grid_size: int = 32,
        max_food_capacity: float = 5.0,
        regeneration_rate: float = 0.005,
        diffusion_rate: float = 0.08,
        harvest_efficiency: float = 12.0,
        device: Optional[str] = None,
        seed: int = 42
    ):
        self.grid_size = grid_size
        self.max_cap = max_food_capacity
        self.regen_rate = regeneration_rate
        self.diff_rate = diffusion_rate
        self.harvest_eff = harvest_efficiency
        self.dev = torch.device(device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.rng = np.random.RandomState(seed)
        
        # 2D Resource Field R(x, y) on device
        self.resources = torch.zeros((grid_size, grid_size), dtype=torch.float32, device=self.dev)
        self._seed_resource_patches(num_patches=8)
        
        # 2D Diffusion kernel for F.conv2d [1, 1, 3, 3]
        kernel_np = np.array([
            [0.05, 0.10, 0.05],
            [0.10, -0.60, 0.10],
            [0.05, 0.10, 0.05]
        ], dtype=np.float32)
        self.diff_kernel = torch.tensor(kernel_np, dtype=torch.float32, device=self.dev).unsqueeze(0).unsqueeze(0)
        
        # Direction displacement vectors [4, 2]: [0: N, 1: E, 2: S, 3: W]
        self.d_vecs = torch.tensor([
            [0.0, -0.03],
            [0.03, 0.0],
            [0.0, 0.03],
            [-0.03, 0.0]
        ], dtype=torch.float32, device=self.dev)
        self.tick_count = 0

    def _seed_resource_patches(self, num_patches: int = 8):
        """Seed initial Gaussian nutrient concentrations."""
        res_np = np.zeros((self.grid_size, self.grid_size), dtype=np.float32)
        for _ in range(num_patches):
            cx = self.rng.randint(2, self.grid_size - 2)
            cy = self.rng.randint(2, self.grid_size - 2)
            amount = self.rng.uniform(2.0, self.max_cap)
            for x in range(max(0, cx - 4), min(self.grid_size, cx + 5)):
                for y in range(max(0, cy - 4), min(self.grid_size, cy + 5)):
                    d2 = (x - cx)**2 + (y - cy)**2
                    res_np[x, y] = np.clip(
                        res_np[x, y] + amount * math.exp(-d2 / 4.0),
                        0.0,
                        self.max_cap
                    )
        self.resources.copy_(torch.tensor(res_np, dtype=torch.float32, device=self.dev))

    @torch.no_grad()
    def update_environment(self):
        """Regenerate resources and diffuse chemicals across space on GPU."""
        self.tick_count += 1
        # 1. Regeneration
        self.resources += self.regen_rate * (self.max_cap - self.resources)
        
        # 2. Vectorized 2D Diffusion via conv2d (every 4 ticks for maximum throughput)
        if self.tick_count % 4 == 0:
            res_4d = self.resources.unsqueeze(0).unsqueeze(0)
            laplacian = F.conv2d(res_4d, self.diff_kernel, padding=1).squeeze(0).squeeze(0)
            self.resources = torch.clamp(self.resources + self.diff_rate * 4.0 * laplacian, 0.0, self.max_cap)

    @torch.no_grad()
    def process_interactions(
        self,
        positions: torch.Tensor,
        orientations: torch.Tensor,
        actions: torch.Tensor,
        alive_mask: torch.Tensor,
        energy: torch.Tensor,
        device: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Pure GPU-vectorized spatial motion, resource harvesting, and sensory receptive field construction.
        """
        pop_size = positions.shape[0]
        alive = alive_mask.bool()
        
        # Actions: 0: Forward, 1: Turn Left, 2: Turn Right, 3: Harvest
        # 1. Turn Left / Right
        turn_l = (actions == 1) & alive
        turn_r = (actions == 2) & alive
        orientations[turn_l] = (orientations[turn_l] - 1) % 4
        orientations[turn_r] = (orientations[turn_r] + 1) % 4
        
        # 2. Move Forward
        fwd = (actions == 0) & alive
        cur_dirs = orientations[fwd] % 4
        step_vecs = self.d_vecs[cur_dirs]
        positions[fwd] = torch.clamp(positions[fwd] + step_vecs, 0.01, 0.99)
        
        # 3. Grid Coordinates [pop]
        gx = torch.clamp((positions[:, 0] * self.grid_size).long(), 0, self.grid_size - 1)
        gy = torch.clamp((positions[:, 1] * self.grid_size).long(), 0, self.grid_size - 1)
        
        # 4. Harvest Resource
        harvest = (actions == 3) & alive
        harvested_energy = torch.zeros(pop_size, dtype=torch.float32, device=device)
        
        if torch.any(harvest):
            h_gx = gx[harvest]
            h_gy = gy[harvest]
            avail = self.resources[h_gx, h_gy]
            take = torch.clamp(avail, max=0.8)
            self.resources[h_gx, h_gy] -= take
            harvested_energy[harvest] = take * self.harvest_eff
            
        # 5. Vectorized Sensory Observation Field [pop, 16]
        sensory_inputs = torch.zeros((pop_size, 16), dtype=torch.float32, device=device)
        
        # Sensor 0: Center chemical density
        sensory_inputs[:, 0] = self.resources[gx, gy] / self.max_cap
        
        # Sensor 1: Front chemical density
        f_dirs = orientations % 4
        f_vecs = self.d_vecs[f_dirs]
        f_pos = torch.clamp(positions + f_vecs, 0.01, 0.99)
        fgx = torch.clamp((f_pos[:, 0] * self.grid_size).long(), 0, self.grid_size - 1)
        fgy = torch.clamp((f_pos[:, 1] * self.grid_size).long(), 0, self.grid_size - 1)
        sensory_inputs[:, 1] = self.resources[fgx, fgy] / self.max_cap
        
        # Sensor 2: Left chemical density
        l_dirs = (orientations - 1) % 4
        l_vecs = self.d_vecs[l_dirs]
        l_pos = torch.clamp(positions + l_vecs, 0.01, 0.99)
        lgx = torch.clamp((l_pos[:, 0] * self.grid_size).long(), 0, self.grid_size - 1)
        lgy = torch.clamp((l_pos[:, 1] * self.grid_size).long(), 0, self.grid_size - 1)
        sensory_inputs[:, 2] = self.resources[lgx, lgy] / self.max_cap
        
        # Sensor 3: Right chemical density
        r_dirs = (orientations + 1) % 4
        r_vecs = self.d_vecs[r_dirs]
        r_pos = torch.clamp(positions + r_vecs, 0.01, 0.99)
        rgx = torch.clamp((r_pos[:, 0] * self.grid_size).long(), 0, self.grid_size - 1)
        rgy = torch.clamp((r_pos[:, 1] * self.grid_size).long(), 0, self.grid_size - 1)
        sensory_inputs[:, 3] = self.resources[rgx, rgy] / self.max_cap
        
        # Sensors 4..7: Spatial coordinates & internal status
        sensory_inputs[:, 4] = positions[:, 0]
        sensory_inputs[:, 5] = positions[:, 1]
        sensory_inputs[:, 6] = (orientations % 4).float() / 4.0
        sensory_inputs[:, 7] = torch.clamp(energy / 200.0, 0.0, 1.0)
        
        # Sensors 8..15: 8-neighbor spatial texture
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for s_idx, (ox, oy) in enumerate(offsets):
            ngx = torch.clamp(gx + ox, 0, self.grid_size - 1)
            ngy = torch.clamp(gy + oy, 0, self.grid_size - 1)
            sensory_inputs[:, 8 + s_idx] = self.resources[ngx, ngy] / self.max_cap
            
        self.update_environment()
        
        return sensory_inputs, harvested_energy

    def get_render_grid(self) -> np.ndarray:
        """Normalized 2D resource buffer for UI observation deck [grid_size, grid_size]."""
        res_cpu = self.resources.detach().cpu().numpy()
        return np.clip(res_cpu / max(1e-3, self.max_cap), 0.0, 1.0)
