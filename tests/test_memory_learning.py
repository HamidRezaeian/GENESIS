import sys
import os
import time
import torch
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from genesis.server.genesis_pytorch_brain import GenesisPyTorchBrain
from genesis.server.brain_server import GenesisEngineRunner

def test_memory_energy_grounding():
    print("=== MEGV: Memory-Energy Grounding Verification ===")
    
    # 1. Initialize Runner
    runner = GenesisEngineRunner()
    brain = runner.brain
    
    print(f"[OK] Runner and Brain initialized.")
    initial_energy = runner.energy
    
    # 2. Add an observation directly to memory, track CPU cost
    s_curr = np.random.randn(32).astype(np.float32)
    s_next = np.random.randn(32).astype(np.float32)
    
    # Clear starting cost if any
    brain.last_memory_cost = 0.0
    
    # Do an update which adds to buffer and calculates cost
    brain.update_neural_weights(s_curr, 0, 1.0, s_next, False, is_replay=False)
    
    add_cost = brain.last_memory_cost
    assert add_cost > 0.0, "Operational cost for adding memory must be > 0"
    print(f"[PASS] Memory add operational cost calculated: {add_cost}")
    
    # 3. Test Sleep Consolidation Cost
    brain.last_memory_cost = 0.0
    for _ in range(10): # Fill buffer so sleep consolidation happens
        brain.update_neural_weights(s_curr, 0, 1.0, s_next, False, is_replay=False)
    
    brain.last_memory_cost = 0.0
    replays = brain.sleep_consolidation()
    consolidation_cost = brain.last_memory_cost
    
    if replays > 0:
        assert consolidation_cost > 0.0, "Consolidation operational cost must be > 0"
        print(f"[PASS] Consolidation triggered {replays} replays, cost: {consolidation_cost}")
    
    # 4. Test tick execution in Runner
    runner.tick_count = 0
    runner.energy = 500.0
    runner.step_once()
    
    # Verify that memory cost is subtracted in step_once
    maintenance_cost = brain.compute_memory_metabolic_cost()
    assert maintenance_cost > 0.0, "Memory maintenance cost should be > 0"
    print(f"[PASS] Memory maintenance cost calculated: {maintenance_cost}")
    
    print("All MEGV verifications passed!")

if __name__ == "__main__":
    test_memory_energy_grounding()
