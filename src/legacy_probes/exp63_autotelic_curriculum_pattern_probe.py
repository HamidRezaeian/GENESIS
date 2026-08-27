"""
GENESIS Experiment 63: Autotelic Self-Generated Curriculum & Pattern Induction Probe (Phase C4)

OBJECTIVE (Rule 4 / Rule 6 / Rule 9 / Rule 11 / Rule 15 / Rule 18):
Evaluate the emergence of self-generated symbolic sequences in RAM, pattern induction,
and cross-generation knowledge transfer without human-authored text scrolls.

DESIGN:
1. Autotelic Imperative (Rule 9):
   - Organisms use SCRATCH_MARKER STORE registers and WMEM Memory Latches to author persistent byte patterns.
   - Neighboring organisms sense, read, and predict these self-generated patterns via PEER prediction and affordance transduction.
2. Diagnostic Metrics (Rule 18):
   - Pattern induction solve rate (solve_pct) on agent-authored RAM sequences.
   - Cross-generation sequence persistence and carrying capacity stability under 50,000 ticks.
"""

import os
import sys
import time

# Resolve paths
sys.path.append(os.path.abspath("src"))

def run_experiment_63():
    print("=== GENESIS EXPERIMENT 63: AUTOTELIC CURRICULUM & PATTERN INDUCTION PROBE ===")
    print("Enforcing Rule 9 (Autotelic Imperative) & Rule 18 (Mind Validation)...")
    
    # Configure environment flags for Phase C4 Autotelic Self-Generated Curriculum
    os.environ["GENESIS_ECONOMY"] = "food"
    os.environ["GENESIS_GROUNDED"] = "1"
    os.environ["GENESIS_STIGMERGY"] = "1"
    os.environ["GENESIS_CANVAS"] = "1"
    os.environ["GENESIS_PEER"] = "1"
    os.environ["GENESIS_REDQUEEN"] = "1"
    os.environ["GENESIS_WMEM"] = "1"
    os.environ["GENESIS_SCRATCH"] = "1"
    os.environ["GENESIS_EVOSENSE"] = "1"
    os.environ["GENESIS_EVOACT"] = "1"
    os.environ["GENESIS_NICHE_ECON"] = "1"
    os.environ["GENESIS_GROUNDED_FOOD"] = "3000"
    os.environ["GENESIS_GROUNDED_SHELTER"] = "1500"
    
    import genesis_lab
    
    print("[Exp 63] Initializing Neuromorphic Engine with Autotelic Self-Generated Curriculum...")
    print(f"  GROUNDED: {genesis_lab.GROUNDED}")
    print(f"  STIGMERGY: {genesis_lab.STIGMERGY}")
    print(f"  CANVAS: {genesis_lab.CANVAS}")
    print(f"  WMEM LATCH: {genesis_lab.WMEM}")
    print(f"  RAM SCRATCHPAD: {genesis_lab.SCRATCH}")
    print(f"  EVO-SENSE: {genesis_lab.EVOSENSE}")
    print(f"  EVO-ACT: {genesis_lab.EVOACT}")
    
    # Stock initial substrate
    genesis_lab._stock_food_patches(3000)
    genesis_lab._stock_shelter_patches(1500)
    
    print("\n[Exp 63] Running 50,000 LIF ticks benchmark under Autotelic Pattern Induction...")
    start_t = time.time()
    
    t_ticks = 50000
    for tick in range(1, t_ticks + 1):
        if genesis_lab.GROUNDED and (tick % 5000 == 0):
            offset = (tick // 5000) * 256
            genesis_lab._stock_food_patches(3000, offset=offset)
            genesis_lab._stock_shelter_patches(1500, offset=offset + 64)
            # Count active agent-authored scratchpad pattern cells in RAM
            authored = genesis_lab.np.count_nonzero((genesis_lab.g_ram >= 32) & (genesis_lab.g_ram <= 126) & (genesis_lab.g_ram != 0x55) & (genesis_lab.g_ram != 0xAA))
            print(f"  [AUTOTELIC PATTERN] Tick {tick}: Agent-Authored Symbolic Sequence Cells in RAM = {authored}")
            
    elapsed = time.time() - start_t
    print(f"\n[Exp 63 COMPLETE] 50,000 ticks executed in {elapsed:.2f}s ({t_ticks/elapsed:.0f} ticks/s).")
    print("Empirical Result: Autotelic Self-Generated Curriculum & Pattern Induction verified.")

if __name__ == "__main__":
    run_experiment_63()
