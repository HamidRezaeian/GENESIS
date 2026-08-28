"""
Unit tests for Substrate 22: Multi-Task Conditional World Model & Policy Distillation.

Invariants:
- Rule 21: Bounded computational costs
- Rule 23: Pure PyTorch FP16 Tensor Core execution
- Rule 25: Zero if-else; continuous differentiability and bounded clamps
- Rule 26: Architectural spec compliance
"""

import sys
from pathlib import Path
import numpy as np
import torch
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.substrate22_engine import (
    FiLMConditionedWorldModel,
    AdaptiveDistillationTemperature,
    AdaptiveCurriculumScheduler,
    Substrate22Engine
)
from genesis.server.genesis_pytorch_brain import GenesisPyTorchBrain, D_MODEL, N_ACTIONS


def test_film_conditioned_world_model_fp16():
    """Verify FiLM + Bottleneck Residual runs on FP16 with distinct task separability."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    wm = FiLMConditionedWorldModel(dim=32, n_actions=4, n_tasks=5, device=device)
    
    phi = torch.randn(36, dtype=wm.dtype, device=wm.device)
    
    # Evaluate across distinct task IDs
    s_hat_0 = wm(phi, task_id=0)
    s_hat_1 = wm(phi, task_id=1)
    s_hat_3 = wm(phi, task_id=3)

    assert s_hat_0.shape == (32,)
    assert torch.all(torch.isfinite(s_hat_0))
    assert torch.all(torch.isfinite(s_hat_1))
    
    # Tasks must produce distinct outputs due to FiLM modulation
    diff_0_1 = float(torch.norm(s_hat_0 - s_hat_1).item())
    diff_0_3 = float(torch.norm(s_hat_0 - s_hat_3).item())
    assert diff_0_1 > 1e-4
    assert diff_0_3 > 1e-4


def test_film_batch_projection():
    """Verify batch projection dimensions [B, 36] -> [B, 32]."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    wm = FiLMConditionedWorldModel(dim=32, n_actions=4, n_tasks=5, device=device)
    
    batch_phi = torch.randn(16, 36, dtype=wm.dtype, device=wm.device)
    out = wm(batch_phi, task_id=2)
    assert out.shape == (16, 32)
    assert torch.all(torch.isfinite(out))


def test_adaptive_distillation_temperature():
    """Verify linear annealing and entropy modulation."""
    scheduler = AdaptiveDistillationTemperature(tau_init=1.5, tau_final=0.5, anneal_epochs=40)
    
    # Epoch 0
    t0 = scheduler.get_temperature()
    assert abs(t0 - 1.5) < 1e-3

    # Step 20 epochs (midpoint)
    for _ in range(20):
        scheduler.step()
    t20 = scheduler.get_temperature()
    assert abs(t20 - 1.0) < 0.05

    # Step 20 more epochs (final)
    for _ in range(20):
        scheduler.step()
    t40 = scheduler.get_temperature()
    assert abs(t40 - 0.5) < 0.05

    # Entropy modulation test
    t_entropy = scheduler.get_temperature(mcts_entropy=1.0)
    assert t_entropy > t40


def test_adaptive_curriculum_scheduler():
    """Verify curriculum task priority sampling."""
    curriculum = AdaptiveCurriculumScheduler(n_tasks=5)
    
    # Initially all tasks have equal history
    task_selected = curriculum.select_next_task()
    assert 0 <= task_selected < 5

    # Simulate task 0 high performance, task 1 forgetting
    curriculum.update(0, 1.0)
    curriculum.update(0, 1.0)
    curriculum.update(1, 1.0)
    curriculum.update(1, 0.0)  # Forgetting on task 1

    # Task 1 must have higher priority than Task 0
    p0 = curriculum.compute_task_priority(0)
    p1 = curriculum.compute_task_priority(1)
    assert p1 > p0


def test_phase_dependent_loss_coefficients():
    """Verify phase shifts across training epochs."""
    engine = Substrate22Engine(dim=32, device="cpu")
    
    # Phase 1
    c_p1 = engine.get_phase_coefficients(epoch=5)
    assert c_p1["lambda_1"] == 0.60
    assert c_p1["lambda_2"] == 0.20

    # Phase 2
    c_p2 = engine.get_phase_coefficients(epoch=25)
    assert c_p2["lambda_1"] == 0.40
    assert c_p2["lambda_2"] == 0.50

    # Phase 3
    c_p3 = engine.get_phase_coefficients(epoch=55)
    assert c_p3["lambda_1"] == 0.30
    assert c_p3["lambda_2"] == 0.55


def test_brain_substrate22_integration():
    """Verify full end-to-end integration of Substrate 22 in GenesisPyTorchBrain."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    brain = GenesisPyTorchBrain(device=device, seed=42)
    
    s_curr = np.random.randn(32).astype(np.float32)
    s_next = np.random.randn(32).astype(np.float32)
    
    # 1. Run MCTS with task conditioning
    mcts_info = brain.run_mcts(s_curr, policy_mode="DIRECTED", task_id=3)
    assert "probs" in mcts_info
    assert len(mcts_info["probs"]) == 4
    
    # 2. Update neural weights with MCTS distillation target
    res = brain.update_neural_weights(
        s_curr, action=1, reward=1.0, s_next_np=s_next,
        mcts_target_probs=np.array(mcts_info["probs"]),
        task_id=3
    )
    assert "loss" in res
    assert "vCurr" in res

    # 3. Telemetry inspection
    telem = brain.get_learning_telemetry()
    assert "substrate22" in telem
    assert telem["substrate22"]["is_level1_certified"] is True
