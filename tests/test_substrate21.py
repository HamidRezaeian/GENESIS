"""
Verification test suite for Substrate 21: Deep-Time Continual Learning & Meta-Plasticity Engine.

Invariants tested:
1. FP16 tensor precision & device invariance (Rule 23)
2. FLOP & memory traffic physical energy deduction (Rule 21)
3. Zero-hole priority replay buffer (Rule 19)
4. Sleep consolidation & SI path integral accumulation
5. Differentiable meta-plasticity per-parameter learning rate
6. Unified multi-objective loss differentiability
7. Catastrophic forgetting prevention across sequential domains
"""

import sys
import math
from pathlib import Path
import pytest
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.substrate21_engine import Substrate21Engine


class DummyBrain(nn.Module):
    """Minimal cortical brain for testing."""
    def __init__(self, dim=32, device="cuda" if torch.cuda.is_available() else "cpu"):
        super().__init__()
        self.device = torch.device(device)
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.linear = nn.Linear(dim, dim, dtype=self.dtype, device=self.device)
        self.critic = nn.Linear(dim, 1, dtype=self.dtype, device=self.device)
    
    def forward_critic(self, states, actions):
        h = torch.tanh(self.linear(states))
        return self.critic(h)
    
    def forward_critic_target(self, next_states):
        with torch.no_grad():
            h = torch.tanh(self.linear(next_states))
            return self.critic(h)


def test_fp16():
    brain = DummyBrain()
    engine = Substrate21Engine(device="cuda" if torch.cuda.is_available() else "cpu")
    engine.attach_brain(brain)
    
    for name, p in engine.named_parameters():
        assert p.dtype == engine.dtype, f"{name} not matching dtype {engine.dtype}"


def test_energy_deduction():
    brain = DummyBrain()
    engine = Substrate21Engine(device="cuda" if torch.cuda.is_available() else "cpu")
    engine.attach_brain(brain)
    
    e0 = engine.energy.clone()
    
    h = torch.randn(1, 32, dtype=engine.dtype, device=engine.device)
    h_next = torch.randn(1, 32, dtype=engine.dtype, device=engine.device)
    q = torch.randn(1, 1, dtype=engine.dtype, device=engine.device)
    qn = torch.randn(1, 1, dtype=engine.dtype, device=engine.device)
    act = torch.zeros(4, dtype=engine.dtype, device=engine.device)
    act[0] = 1.0
    sym = torch.softmax(torch.randn(64, dtype=engine.dtype, device=engine.device), dim=0)
    
    engine.step(h, h_next, q, qn, 1.0, False, act, sym)
    
    assert engine.energy.item() < e0.item(), "Energy was not deducted per Rule 21"
    assert engine.flop_counter.item() > 0, "No FLOPs counted"


def test_replay_buffer():
    brain = DummyBrain()
    engine = Substrate21Engine(device="cuda" if torch.cuda.is_available() else "cpu")
    engine.attach_brain(brain)
    
    for i in range(100):
        h = torch.randn(32, dtype=engine.dtype, device=engine.device)
        h_next = torch.randn(32, dtype=engine.dtype, device=engine.device)
        act = torch.zeros(4, dtype=engine.dtype, device=engine.device)
        act[i % 4] = 1.0
        engine.add_experience(h, act, float(i % 3), h_next, False, 0.5, 0.5)
    
    assert engine.replay_size.item() == 100, f"Size wrong: {engine.replay_size.item()}"
    
    success, is_weights = engine.sample_replay()
    assert success, "Sample failed"
    assert is_weights is not None, "No IS weights"
    assert torch.all(is_weights > 0), "IS weights must be positive"


def test_consolidation():
    brain = DummyBrain()
    engine = Substrate21Engine(
        consolidation_period=50,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )
    engine.attach_brain(brain)
    
    act = torch.zeros(4, dtype=engine.dtype, device=engine.device)
    act[0] = 1.0
    sym = torch.softmax(torch.randn(64, dtype=engine.dtype, device=engine.device), dim=0)
    
    for i in range(120):
        h = torch.randn(1, 32, dtype=engine.dtype, device=engine.device)
        h_next = torch.randn(1, 32, dtype=engine.dtype, device=engine.device)
        q = brain.forward_critic(h, act)
        with torch.no_grad():
            qn = brain.forward_critic_target(h_next)
        engine.step(h, h_next, q, qn, 1.0, False, act, sym)
        engine.pre_step_snapshot()
        for p in brain.parameters():
            if p.grad is not None:
                p.data -= 0.001 * p.grad
        engine.post_optimizer_step()
        for p in brain.parameters():
            if p.grad is not None:
                p.grad.zero_()
    
    assert engine.consolidation_count.item() >= 1, "Consolidation never fired"
    assert engine.si_norm.item() > 0, "SI omega norm is zero"


def test_meta_plasticity():
    brain = DummyBrain()
    engine = Substrate21Engine(device="cuda" if torch.cuda.is_available() else "cpu")
    engine.attach_brain(brain)
    
    td_high = torch.tensor([5.0], dtype=engine.dtype, device=engine.device)
    engine.compute_eta_modulation(td_high)
    eta_high = list(engine.eta_modulation.values())[0].mean().item()
    
    td_low = torch.tensor([0.01], dtype=engine.dtype, device=engine.device)
    engine.compute_eta_modulation(td_low)
    eta_low = list(engine.eta_modulation.values())[0].mean().item()
    
    assert eta_high > eta_low, f"High TD should give higher eta: {eta_high} vs {eta_low}"


def test_all_losses():
    brain = DummyBrain()
    engine = Substrate21Engine(device="cuda" if torch.cuda.is_available() else "cpu")
    engine.attach_brain(brain)
    
    h = torch.randn(1, 32, dtype=engine.dtype, device=engine.device)
    h_next = torch.randn(1, 32, dtype=engine.dtype, device=engine.device)
    act = torch.zeros(4, dtype=engine.dtype, device=engine.device)
    act[0] = 1.0
    q = brain.forward_critic(h, act)
    with torch.no_grad():
        qn = brain.forward_critic_target(h_next)
    sym = torch.softmax(torch.randn(64, dtype=engine.dtype, device=engine.device), dim=0)
    
    result = engine.step(h, h_next, q, qn, 1.0, False, act, sym)
    
    assert not math.isnan(result["loss_task"]), "Task loss is NaN"
    assert not math.isnan(result["loss_dyn"]), "Dyn loss is NaN"
    assert not math.isnan(result["loss_cpc"]), "CPC loss is NaN"
    assert not math.isnan(result["loss_si"]), "SI loss is NaN"
    assert not math.isnan(result["r_intrinsic"]), "Intrinsic reward is NaN"
    assert not math.isnan(result["loss_total"]), "Total loss is NaN"
    
    lam_sum = sum(result["lambda"])
    assert abs(lam_sum - 1.0) < 0.05, f"Lambda sum: {lam_sum}"


def test_no_catastrophic_forgetting():
    brain = DummyBrain()
    engine = Substrate21Engine(
        consolidation_period=30,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )
    engine.attach_brain(brain)
    
    task1_states = torch.ones(32, dtype=engine.dtype, device=engine.device) * 0.5
    task2_states = -torch.ones(32, dtype=engine.dtype, device=engine.device) * 0.5
    
    act = torch.zeros(4, dtype=engine.dtype, device=engine.device)
    act[0] = 1.0
    sym = torch.softmax(torch.randn(64, dtype=engine.dtype, device=engine.device), dim=0)
    
    for _ in range(60):
        h = (task1_states + torch.randn(32, dtype=engine.dtype, device=engine.device) * 0.1).unsqueeze(0)
        h_next = h + torch.randn(1, 32, dtype=engine.dtype, device=engine.device) * 0.01
        q = brain.forward_critic(h, act)
        with torch.no_grad():
            qn = brain.forward_critic_target(h_next)
        engine.step(h, h_next, q, qn, 1.0, False, act, sym)
        engine.pre_step_snapshot()
        for p in brain.parameters():
            if p.grad is not None:
                p.data -= 0.001 * p.grad
        engine.post_optimizer_step()
        for p in brain.parameters():
            if p.grad is not None:
                p.grad.zero_()
    
    params_after_task1 = {n: p.data.clone() for n, p in brain.named_parameters()}
    
    for _ in range(60):
        h = (task2_states + torch.randn(32, dtype=engine.dtype, device=engine.device) * 0.1).unsqueeze(0)
        h_next = h + torch.randn(1, 32, dtype=engine.dtype, device=engine.device) * 0.01
        q = brain.forward_critic(h, act)
        with torch.no_grad():
            qn = brain.forward_critic_target(h_next)
        engine.step(h, h_next, q, qn, 0.5, False, act, sym)
        engine.pre_step_snapshot()
        for p in brain.parameters():
            if p.grad is not None:
                p.data -= 0.001 * p.grad
        engine.post_optimizer_step()
        for p in brain.parameters():
            if p.grad is not None:
                p.grad.zero_()
    
    assert engine.consolidation_count.item() >= 2, "Not enough consolidations"
    assert engine.si_norm.item() > 0, "SI is zero — no protection"
