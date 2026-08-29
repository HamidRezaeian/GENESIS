import os
import sys
import time
import pytest
import torch
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from genesis.server.phase_e_substrate import CPPNGenome, BatchedPopulation
from genesis.server.phase_e_ecology import EcologyField
from genesis.server.phase_e_metrics import PhaseEEmergenceTracker


def test_cppn_genome_expression_and_mutation():
    """Verify CPPN genome creates valid phenotypic connectivity and mutates without NaN."""
    genome = CPPNGenome(seed=123)
    pre, post, w, active = genome.express_phenotype(
        max_neurons=64,
        max_synapses=512,
        input_neurons=16,
        output_neurons=4
    )
    
    assert len(pre) == 512
    assert len(post) == 512
    assert len(w) == 512
    assert len(active) == 512
    assert active.sum() > 0, "CPPN must generate active synaptic connections"
    assert np.all(np.abs(w) <= 3.0), "Weights must respect bounds"
    
    # Mutation verification
    mutated = genome.mutate()
    pre_m, post_m, w_m, active_m = mutated.express_phenotype(64, 512, 16, 4)
    assert not np.array_equal(w, w_m) or mutated.eta_stdp != genome.eta_stdp, "Mutation must alter genome traits"


def test_batched_population_step_and_stdp():
    """Verify batched neural propagation, 3-factor STDP, and finite energy consumption."""
    pop = BatchedPopulation(pop_size=64, max_neurons=64, max_synapses=512, seed=42)
    eco = EcologyField(grid_size=32, seed=42)
    
    # Process initial sensory state
    sensory, harvested = eco.process_interactions(
        pop.positions, pop.orientations, pop.actions, pop.alive_mask, pop.energy, pop.dev
    )
    
    initial_energy = pop.energy[0].item()
    w_before = pop.weights.clone()
    
    # Execute 10 simulation ticks
    for _ in range(10):
        actions, telem = pop.step_tick(sensory, harvested)
        sensory, harvested = eco.process_interactions(
            pop.positions, pop.orientations, pop.actions, pop.alive_mask, pop.energy, pop.dev
        )
        
    assert telem["population_size"] > 0
    assert torch.all(torch.isfinite(pop.states)), "States must remain finite (no NaN/Inf)"
    assert torch.all(torch.isfinite(pop.weights)), "Weights must remain finite"
    assert torch.all(torch.abs(pop.weights) <= 4.0), "Weights must respect synaptic homeostasis bounds"
    assert not torch.equal(w_before, pop.weights), "3-Factor STDP must adapt synaptic weights locally"


def test_landauer_thermodynamics_and_lifecycle():
    """Verify apoptosis on zero energy and reproduction on energy surplus."""
    pop = BatchedPopulation(pop_size=32, max_neurons=64, max_synapses=512, seed=42)
    
    # Force low energy on organism 0 and high energy on organism 1
    pop.energy[0] = 0.001
    pop.energy[1] = 250.0  # Above E_threshold (~160.0)
    
    sensory = torch.zeros((32, 16), dtype=pop.dtype, device=pop.dev)
    harvested = torch.zeros(32, dtype=pop.dtype, device=pop.dev)
    
    actions, telem = pop.step_tick(sensory, harvested)
    
    # Organism 0 perishes (registered in total_deaths), slot 0 is colonized by offspring
    assert telem["deaths_total"] >= 1, "Organism with exhausted energy must die (Apoptosis)"
    assert telem["births_total"] >= 1, "Organism with energy surplus must trigger auto-reproduction"


def test_emergence_tracker_mann_kendall():
    """Verify Mann-Kendall trend computation and non-parametric emergence index."""
    tracker = PhaseEEmergenceTracker(history_len=100)
    
    positions = torch.rand(32, 2)
    actions = torch.randint(0, 4, (32,))
    states = torch.randn(32, 64)
    alive_mask = torch.ones(32, dtype=torch.bool)
    
    for t in range(50):
        # Monotonically expanding positions
        positions += torch.randn(32, 2) * 0.01
        telem = tracker.observe_step(positions, actions, states, alive_mask)
        
    assert telem["traj_entropy"] > 0.0
    assert telem["behavioral_diversity"] >= 0.0
    assert "mann_kendall_z" in telem


def test_high_throughput_performance():
    """Verify throughput exceeds 50 ticks/second on batched HPC execution."""
    pop_size = 128
    pop = BatchedPopulation(pop_size=pop_size, max_neurons=64, max_synapses=512, seed=42)
    eco = EcologyField(grid_size=32, seed=42)
    
    sensory, harvested = eco.process_interactions(
        pop.positions, pop.orientations, pop.actions, pop.alive_mask, pop.energy, pop.dev
    )
    
    # Warmup
    for _ in range(10):
        pop.step_tick(sensory, harvested)
        
    n_ticks = 100
    t0 = time.perf_counter()
    for _ in range(n_ticks):
        actions, telem = pop.step_tick(sensory, harvested)
        sensory, harvested = eco.process_interactions(
            pop.positions, pop.orientations, pop.actions, pop.alive_mask, pop.energy, pop.dev
        )
    t1 = time.perf_counter()
    
    elapsed = t1 - t0
    rate = n_ticks / elapsed
    print(f"\n[PHASE-E PERFORMANCE] {n_ticks} population ticks completed in {elapsed:.3f}s -> Rate: {rate:.1f} ticks/s (Pop: {pop_size})")
    assert rate >= 50.0, f"Throughput must be at least 50 ticks/s, got {rate:.1f}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
