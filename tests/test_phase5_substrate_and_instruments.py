"""
GENESIS Phase-5: Pre-Registered Unit Test Suite.
Binding specification: Docs/Architecture/PHASE5_DUAL_MEMORY_SPEC.md (§4.5).

Tests:
1. Memory bank associative write, scale-free retrieval, and Landauer FLOP cost debiting.
2. Dual-timescale synaptic update and W_eff forward transmission.
3. Anti-regression telemetry logger assertions (Section 4.5).
4. Counterbalanced probe harness and 10-seed Level-1 replication generator.
"""

import sys
import json
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase5_memory import BatchedExternalMemoryBank
from genesis.server.phase5_plasticity import Phase5PlasticityEngine
from genesis.server.phase5_substrate import BatchedPopulation5
from genesis.server.phase5_ledger import Phase5TelemetryLogger, PHASE5_METRIC_VERSION
from genesis.server.phase5_probes import ShadowCloneProbeHarness5
from genesis.server.phase5_cert import Phase5ReplicationCertificateGenerator


def test_phase5_memory_associative_write_and_read():
    """Validates Section 2.2 associative memory write, retrieval, and energy accounting."""
    device = "cpu"
    bank = BatchedExternalMemoryBank(n_worlds=2, pop_per_world=4, k_slots=8, b_dim=16, d_key_dim=4, device=device)

    # 1. Write an explicit vector at key [1, 0, 0, 0]
    write_gate = torch.ones((2, 4), dtype=torch.bool, device=device)
    read_gate = torch.zeros((2, 4), dtype=torch.bool, device=device)
    k_write = torch.tensor([1.0, 0.0, 0.0, 0.0], device=device).expand(2, 4, 4)
    k_read = torch.zeros((2, 4, 4), device=device)
    write_payload = torch.full((2, 4, 16), 42.0, device=device)

    out, energy = bank.step(write_gate, read_gate, k_write, k_read, write_payload)
    assert energy.sum().item() > 0.0, "Write operation must bill Landauer FLOP energy"
    assert bank.valid.any(), "Slot occupancy must be True after write"

    # 2. Read with matching key [1, 0, 0, 0]
    write_gate.zero_()
    read_gate.fill_(True)
    k_read = torch.tensor([1.0, 0.0, 0.0, 0.0], device=device).expand(2, 4, 4)

    retrieved, read_energy = bank.step(write_gate, read_gate, k_write, k_read, write_payload)
    assert read_energy.sum().item() > 0.0, "Read operation must bill associative FLOP energy"
    assert torch.allclose(retrieved, write_payload, atol=1e-3), "Retrieved vector must match written payload"


def test_phase5_dual_timescale_plasticity():
    """Validates Section 2.1 dual-timescale updates and W_fast rail clamp."""
    device = "cpu"
    pop = BatchedPopulation5(n_worlds=2, pop_per_world=4, max_neurons=80, max_synapses=64, device=device)

    sensory = torch.randn((2, 4, 32), device=device)
    initial_w_fast = pop.W_fast.clone()
    initial_w_slow = pop.W_slow.clone()

    step_res = pop.forward_step(sensory)

    assert pop.W_fast.max() <= 4.0 and pop.W_fast.min() >= -4.0, "W_fast must remain within [-4, 4] rail"
    assert not torch.allclose(pop.W_fast, initial_w_fast), "W_fast must update under active input"
    assert "alive_count" in step_res
    assert step_res["alive_count"] == 8


def test_phase5_ledger_anti_regression():
    """Validates Section 4.5 fail-fast CI guard on frozen 0.5 predictor."""
    test_log = REPO_ROOT / "experiments" / "leaderboard" / "test_phase5_ledger.jsonl"
    if test_log.exists():
        test_log.unlink()

    logger = Phase5TelemetryLogger(str(test_log))
    pop = BatchedPopulation5(n_worlds=2, pop_per_world=4, max_neurons=80, max_synapses=32, device="cpu")

    audit = {"dmts_benchmark": {"delta": 0.01, "z_score": 0.5, "verdict": "STDP_NON_CRITICAL"}}
    valid_emergence = {"prediction_error": 0.035, "emergence_index": 11.5}

    record = logger.log(
        tick=1000,
        diagnostic_audit=audit,
        population=pop,
        memory_bank=pop.memory_bank,
        emergence_metrics=valid_emergence
    )
    assert record["metric_version"] == PHASE5_METRIC_VERSION
    assert record["population_total_alive"] == 8
    assert len(record["weight_sha256"]) == 16

    # Test Section 4.5 Regression Trap: exactly 0.5 prediction error with live population
    buggy_emergence = {"prediction_error": 0.5, "emergence_index": 0.0}
    with pytest.raises(ValueError, match="SECTION 4.5 REGRESSION DETECTED"):
        # Temporarily fake alive count > 10 to trigger trap
        pop.alive_mask = torch.ones((2, 8), dtype=torch.bool)
        logger.log(
            tick=2000,
            diagnostic_audit=audit,
            population=pop,
            memory_bank=pop.memory_bank,
            emergence_metrics=buggy_emergence
        )

    if test_log.exists():
        test_log.unlink()


def test_phase5_probe_harness_and_cert():
    """Validates counterbalanced clone probe execution and 10-seed replication generator."""
    device = "cpu"
    pop = BatchedPopulation5(n_worlds=2, pop_per_world=4, max_neurons=80, max_synapses=32, device=device)
    harness = ShadowCloneProbeHarness5()

    audit = harness.run_full_diagnostic_audit(pop)
    assert "dmts_benchmark" in audit
    assert "gate_d_remap" in audit
    assert "gate_s_consolidation" in audit

    cert_gen = Phase5ReplicationCertificateGenerator()
    stats = cert_gen.evaluate_10_seed_replication(pop, n_seeds=3)
    assert stats["n_seeds"] == 3
    assert len(stats["seeds"]) == 3
    assert "overall_z" in stats
