"""
GENESIS Phase-E: Rule 18 Cognitive Emergence Metrics & Mann-Kendall Trend Tracking.
Authoritative formulation by GLM 5.3.

Invariants:
- Rule 2: Pre-registered quantitative falsification criteria.
- Rule 7: Pure observation metrics with zero selection or survival coupling.
- Rule 18: Falsifiable finish line verification (Monotonic complexity ascent).
"""

import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import torch


class PhaseEEmergenceTracker:
    """
    Observation-only cognitive emergence tracking suite for open-ended evolutionary ALife.
    Computes trajectory spatial entropy, behavioral diversity, predictive state error,
    and non-parametric Mann-Kendall trend statistics Z without any authored fitness feedback.
    """
    def __init__(self, history_len: int = 500, grid_bins: int = 16):
        self.history_len = history_len
        self.grid_bins = grid_bins
        
        # Spatial occupation histogram [grid_bins, grid_bins]
        self.spatial_counts = np.zeros((grid_bins, grid_bins), dtype=np.float32)
        
        # Time-series history buffers
        self.action_history: List[np.ndarray] = []
        self.pred_errors: List[float] = []
        self.emergence_indices: List[float] = []
        self.diversity_history: List[float] = []
        
        # Latent state transition buffer for self-modeling
        self.prev_states: Optional[np.ndarray] = None
        self.W_pred = np.random.randn(16, 16).astype(np.float32) * 0.05

    def observe_step(
        self,
        positions: torch.Tensor,
        actions: torch.Tensor,
        states: torch.Tensor,
        alive_mask: torch.Tensor
    ) -> Dict[str, Any]:
        """
        Record one population step and update non-parametric emergence statistics.
        """
        alive_np = alive_mask.cpu().numpy()
        pos_np = positions.cpu().numpy()[alive_np]
        act_np = actions.cpu().numpy()[alive_np]
        st_np = states.cpu().numpy()[alive_np]
        
        n_alive = len(pos_np)
        if n_alive == 0:
            return self._empty_telemetry()

        # 1. Update Spatial Trajectory Histogram
        for i in range(n_alive):
            bx = int(np.clip(pos_np[i, 0] * self.grid_bins, 0, self.grid_bins - 1))
            by = int(np.clip(pos_np[i, 1] * self.grid_bins, 0, self.grid_bins - 1))
            self.spatial_counts[bx, by] += 1.0
            
        total_visits = np.sum(self.spatial_counts) + 1e-9
        p_spatial = self.spatial_counts / total_visits
        p_valid = p_spatial[p_spatial > 0]
        traj_entropy = float(-np.sum(p_valid * np.log2(p_valid + 1e-9)))

        # 2. Behavioral Action Diversity (Entropy across current actions)
        act_counts = np.bincount(act_np.astype(int), minlength=4)
        p_act = act_counts / (np.sum(act_counts) + 1e-9)
        p_act_valid = p_act[p_act > 0]
        act_entropy = float(-np.sum(p_act_valid * np.log2(p_act_valid + 1e-9)))
        self.diversity_history.append(act_entropy)
        if len(self.diversity_history) > self.history_len:
            self.diversity_history.pop(0)

        # 3. Environmental Next-State Modeling Error
        curr_sensory = st_np[:, :16]
        pred_err = 0.5
        if self.prev_states is not None and self.prev_states.shape[0] == curr_sensory.shape[0]:
            predicted = np.tanh(np.dot(self.prev_states, self.W_pred))
            err = np.mean((predicted - curr_sensory) ** 2)
            pred_err = float(err)
            # Local gradient for observer model W_pred
            dW = np.dot(self.prev_states.T, (curr_sensory - predicted)) * 0.001
            self.W_pred += np.clip(dW, -0.05, 0.05)
            
        self.prev_states = curr_sensory.copy()
        self.pred_errors.append(pred_err)
        if len(self.pred_errors) > self.history_len:
            self.pred_errors.pop(0)
            
        mean_pred_err = float(np.mean(self.pred_errors))

        # 4. Composite Emergence Index
        emergence_index = float(traj_entropy * act_entropy * (1.0 / (1.0 + mean_pred_err)))
        self.emergence_indices.append(emergence_index)
        if len(self.emergence_indices) > self.history_len:
            self.emergence_indices.pop(0)

        # 5. Non-Parametric Mann-Kendall Trend Test (Z)
        mk_z, p_val = self._compute_mann_kendall(self.emergence_indices)

        return {
            "traj_entropy": traj_entropy,
            "behavioral_diversity": act_entropy,
            "prediction_error": mean_pred_err,
            "emergence_index": emergence_index,
            "mann_kendall_z": mk_z,
            "is_emergence_certified": bool(mk_z >= 2.576 and len(self.emergence_indices) >= 100)
        }

    def _compute_mann_kendall(self, series: List[float]) -> Tuple[float, float]:
        """
        Compute non-parametric Mann-Kendall S statistic and standardized Z-score.
        """
        n = len(series)
        if n < 20:
            return 0.0, 1.0
            
        arr = np.array(series, dtype=np.float64)
        # S = sum_{i < j} sgn(x_j - x_i)
        diffs = arr[:, None] - arr[None, :]
        s_stat = float(np.sum(np.sign(diffs[np.triu_indices(n, k=1)])))
        
        # Variance calculation
        var_s = float(n * (n - 1) * (2 * n + 5)) / 18.0
        
        if s_stat > 0:
            z = (s_stat - 1.0) / math.sqrt(var_s)
        elif s_stat < 0:
            z = (s_stat + 1.0) / math.sqrt(var_s)
        else:
            z = 0.0
            
        # Standard normal two-sided p-value approximation
        p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
        return float(z), float(p_val)

    def _empty_telemetry(self) -> Dict[str, Any]:
        return {
            "traj_entropy": 0.0,
            "behavioral_diversity": 0.0,
            "prediction_error": 1.0,
            "emergence_index": 0.0,
            "mann_kendall_z": 0.0,
            "is_emergence_certified": False
        }
