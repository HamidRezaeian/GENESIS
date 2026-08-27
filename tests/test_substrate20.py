"""
Unit tests for Substrate 20: Counterfactual World Modeling, Latent ToM & Emergent Symbolic Communication.
Verifies all mathematical invariants and hardware constraints from GLM 5.3 formulation.
"""

import pytest
import torch
import math
import sys
from pathlib import Path

# Add project src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from genesis.server.substrate20_engine import Substrate20Engine


def test_fp16_invariance():
    """Verify all parameters and buffers are torch.float16."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Substrate20Engine(device=device)

    for name, p in model.named_parameters():
        assert p.dtype == torch.float16, f"Parameter {name} is {p.dtype}, expected torch.float16"
    for name, b in model.named_buffers():
        assert b.dtype == torch.float16, f"Buffer {name} is {b.dtype}, expected torch.float16"

    h = torch.randn(1, 32, dtype=torch.float16, device=device)
    v = torch.randn(1, 32, dtype=torch.float16, device=device)
    po = torch.randn(4, 73, dtype=torch.float16, device=device)
    vi = torch.zeros(64, dtype=torch.float16, device=device)
    ph = torch.tensor([1.0], dtype=torch.float16, device=device)

    out = model(h, v, po, vi, ph)
    assert out["h_next"].dtype == torch.float16
    assert out["symbol_out"].dtype == torch.float16
    assert out["peer_models"].dtype == torch.float16
    assert out["peer_actions"].dtype == torch.float16


def test_energy_deduction():
    """Verify energy decreases based on physical FLOPs and traffic (Rule 21)."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Substrate20Engine(device=device)
    e0 = float(model.energy.clone().detach().cpu().item())

    h = torch.randn(1, 32, dtype=torch.float16, device=device)
    v = torch.randn(1, 32, dtype=torch.float16, device=device)
    po = torch.randn(4, 73, dtype=torch.float16, device=device)
    vi = torch.randn(64, dtype=torch.float16, device=device)
    ph = torch.tensor([3.1415], dtype=torch.float16, device=device)  # imagination phase

    model(h, v, po, vi, ph)
    e1 = float(model.energy.detach().cpu().item())

    assert e1 < e0, f"Energy was not deducted: {e1} >= {e0}"
    assert float(model.flop_counter.item()) > 0, "No FLOPs recorded"


def test_branch_merging():
    """Verify counterfactual branches merge via self-attention without combinatorial explosion."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Substrate20Engine(device=device)
    h = torch.randn(1, 32, dtype=torch.float16, device=device)
    gate = torch.tensor([0.9], dtype=torch.float16, device=device)

    imag_out = model.imagination_rollout(h, gate)
    assert imag_out.shape == (1, 32)
    assert imag_out.dtype == torch.float16

    telemetry = model.get_telemetry()
    assert 0.0 < telemetry["imag_branch_eff"] <= float(model.n_branches)


def test_symbol_grounding():
    """Verify symbol grounding develops non-zero predictive association and MI."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Substrate20Engine(device=device)

    for _ in range(50):
        h = torch.randn(1, 32, dtype=torch.float16, device=device)
        sym = model.symbol_emit(h)
        model.update_grounding(sym, h)

    assert float(model.sym_grounding.norm().item()) > 0.0, "Grounding matrix remained zero"
    assert float(model.sym_mi_estimate.item()) >= 0.0, "Mutual information estimate is negative"


def test_tom_prediction():
    """Verify Theory of Mind predicts normalized peer action distributions."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Substrate20Engine(device=device)
    po = torch.randn(4, 73, dtype=torch.float16, device=device)
    gate = torch.tensor([0.9], dtype=torch.float16, device=device)

    models, actions = model.tom_forward(po, gate)
    assert models.shape == (4, 32)
    assert actions.shape == (4, 4)

    sums = actions.sum(dim=1).detach().cpu().numpy()
    for s in sums:
        assert math.isclose(s, 1.0, abs_tol=1e-2), f"Action distribution did not sum to 1.0: {s}"


def test_cpc_loss_and_differentiability():
    """Verify CPC contrastive loss computes positive scalar and propagates gradients."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Substrate20Engine(device=device)

    h = torch.randn(1, 32, dtype=torch.float16, device=device, requires_grad=True)
    v = torch.randn(1, 32, dtype=torch.float16, device=device, requires_grad=True)
    po = torch.randn(4, 73, dtype=torch.float16, device=device, requires_grad=True)
    vi = torch.randn(64, dtype=torch.float16, device=device, requires_grad=True)
    ph = torch.tensor([1.0], dtype=torch.float16, device=device)

    out = model(h, v, po, vi, ph)
    loss = out["h_next"].sum() + out["peer_actions"].sum() + out["cpc_loss"]
    loss.backward()

    for name, param in model.named_parameters():
        assert param.grad is not None, f"Parameter {name} received no gradient"
        assert not torch.isnan(param.grad).any(), f"Parameter {name} has NaN gradients"
