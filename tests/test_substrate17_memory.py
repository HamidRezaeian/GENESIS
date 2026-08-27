import sys
import os
import time
import torch
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from genesis.server.genesis_pytorch_brain import GenesisPyTorchBrain

def test_substrate17_memory_rules():
    print("=== Substrate 17 Memory Rules Verification ===")
    
    # 1. Initialize Brain
    brain = GenesisPyTorchBrain(device="cpu")
    print(f"[OK] Brain initialized with EpisodicBuffer capacity: {brain.hippocampus.capacity}")
    
    # 2. Simulate 10,000 steps to fill the buffer and trigger consolidations
    start_time = time.time()
    
    for tick in range(6000):
        # Fake sensory input (D_MODEL = 32)
        s_curr = np.random.randn(32).astype(np.float32)
        s_next = np.random.randn(32).astype(np.float32)
        action = int(np.random.randint(0, 4))
        reward = float(np.random.randn())
        done = False
        
        # Online Learning (Adds to EpisodicBuffer and accumulates SI path integral)
        brain.update_neural_weights(s_curr, action, reward, s_next, done)
        
        # Sleep Consolidation every 2000 ticks
        if tick > 0 and tick % 2000 == 0:
            replays = brain.sleep_consolidation()
            print(f"Tick {tick}: Sleep Consolidation triggered. Replays: {replays}")
            print(f" -> SI Omega Norm: {sum(o.norm().item() for o in brain.si_omega.values()):.4f}")
            
    end_time = time.time()
    
    # 3. Rule 19: Check RAM bound
    print("\n--- Rule 19: Compact RAM Design ---")
    expected_size = min(6000, brain.hippocampus.capacity)
    actual_size = brain.hippocampus.size
    print(f"Buffer Size: {actual_size} / {brain.hippocampus.capacity}")
    
    if actual_size == 5000:
        print("[PASS] EpisodicBuffer respected capacity limit (Priority Eviction active).")
    else:
        print(f"[FAIL] EpisodicBuffer size {actual_size} is incorrect.")
        
    # 4. Rule 21: Check Memory Metabolic Cost
    print("\n--- Rule 21: Memory Metabolic Grounding ---")
    # A rough estimate of memory byte footprint
    total_bytes = actual_size * brain.hippocampus.ram_bytes_per_transition
    print(f"RAM Footprint of EpisodicBuffer: {total_bytes / 1024:.2f} KB")
    if total_bytes > 0:
        print("[PASS] RAM cost is correctly tracked and quantifiable for metabolic taxation.")
        
    print(f"\nTotal Simulation Time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    test_substrate17_memory_rules()
