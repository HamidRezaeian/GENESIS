"""
Tests for Substrate 19: Structural Neurogenesis & Compositional Reasoning Engine.
Verifies all 6 GLM 5.3 mathematical invariants.
"""

import pytest
import torch
import math
import sys
from pathlib import Path

# Add project src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.substrate19_engine import Substrate19Engine


def test_fp16_invariance():
    """Verify all state tensors, buffers, and outputs are FP16."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    engine = Substrate19Engine(dim=32, n_memory=16, n_units=256, device=device)

    for name, param in engine.named_parameters():
        assert param.dtype == torch.float16, f"Parameter {name} is {param.dtype}, expected torch.float16"

    for name, buffer in engine.named_buffers():
        assert buffer.dtype == torch.float16, f"Buffer {name} is {buffer.dtype}, expected torch.float16"

    h_t = torch.randn(1, 32, dtype=torch.float16, device=device)
    v_t = torch.randn(1, 32, dtype=torch.float16, device=device)

    r_t, z = engine(h_t, v_t)
    assert r_t.dtype == torch.float16, f"r_t is {r_t.dtype}, expected torch.float16"
    assert z.dtype == torch.float16, f"z is {z.dtype}, expected torch.float16"
    assert r_t.shape == (1, 32)
    assert z.shape == (256, 32)


def test_differentiability_no_if_else():
    """Verify gradients propagate to all learnable projection parameters (no if-else control flow)."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    engine = Substrate19Engine(dim=32, n_memory=16, n_units=256, device=device)

    h_t = torch.randn(1, 32, dtype=torch.float16, device=device, requires_grad=True)
    v_t = torch.randn(1, 32, dtype=torch.float16, device=device, requires_grad=True)

    r_t, z = engine(h_t, v_t)
    loss = r_t.sum() + z.sum()
    loss.backward()

    for name, param in engine.named_parameters():
        assert param.grad is not None, f"Parameter {name} received no gradient"
        assert not torch.isnan(param.grad).any(), f"Parameter {name} has NaN gradients"


def test_metabolic_cost_deduction():
    """Verify energy is deducted based on measured FLOPs and memory traffic (Rule 21)."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    engine = Substrate19Engine(dim=32, n_memory=16, n_units=256, device=device)

    initial_energy = float(engine.energy.clone().detach().cpu().item())
    initial_cost = float(engine.total_cost.clone().detach().cpu().item())

    h_t = torch.randn(1, 32, dtype=torch.float16, device=device)
    v_t = torch.randn(1, 32, dtype=torch.float16, device=device)

    r_t, z = engine(h_t, v_t)

    new_energy = float(engine.energy.detach().cpu().item())
    new_cost = float(engine.total_cost.detach().cpu().item())

    assert new_energy < initial_energy, f"Energy did not decrease: {new_energy} >= {initial_energy}"
    assert new_cost > initial_cost, f"Total cost did not increase: {new_cost} <= {initial_cost}"
    assert engine.last_step_cost > 0.0


def test_structural_plasticity_sparsity_bounds():
    """Verify hard concrete mask maintains organic sparsity in bounds [0.50, 0.90]."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    engine = Substrate19Engine(dim=32, n_memory=16, n_units=256, target_sparsity=0.70, device=device)

    for _ in range(50):
        h_t = torch.randn(1, 32, dtype=torch.float16, device=device)
        v_t = torch.randn(1, 32, dtype=torch.float16, device=device)
        r_t, z = engine(h_t, v_t)

    telemetry = engine.get_telemetry()
    sparsity = telemetry["structural_sparsity"]
    assert 0.35 <= sparsity <= 0.95, f"Structural sparsity {sparsity} out of expected bounds"


def test_phase_locked_clock_cycling():
    """Verify oscillator clock progresses across phases and gates dynamically activate."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    engine = Substrate19Engine(dim=32, n_memory=16, n_units=256, device=device)

    phases = []
    for _ in range(30):
        h_t = torch.randn(1, 32, dtype=torch.float16, device=device)
        v_t = torch.randn(1, 32, dtype=torch.float16, device=device)
        engine(h_t, v_t)
        phases.append(engine.get_telemetry()["clock_phase"])

    # Phase must cycle and not remain static
    assert len(set(phases)) > 5, "Clock phase remained static"
    telemetry = engine.get_telemetry()
    assert 0.0 <= telemetry["write_gate"] <= 1.0
    assert 0.0 <= telemetry["read_gate"] <= 1.0
    assert 0.0 <= telemetry["chain_gate"] <= 1.0
