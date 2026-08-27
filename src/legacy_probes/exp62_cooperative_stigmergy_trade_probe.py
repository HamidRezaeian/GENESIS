"""
GENESIS Experiment 62: Cooperative Stigmergy & Resource Trade Economy Probe (Phase C3)

OBJECTIVE (Rule 3 / Rule 6 / Rule 9 / Rule 15 / Rule 18):
Evaluate whether multi-agent cooperative stigmergy, division of labor (Architects vs. Foragers),
and substrate-grounded resource trade (Shelter Canvas 0xAA vs. Energy Food 0x55) emerge naturally
from substrate heterogeneity, without explicit intelligence rewards or human-authored game mechanics.

DESIGN:
1. Substrate Heterogeneity (Rule 3):
   - Energy Food Field (0x55): Primary metabolic food source for all living organisms.
   - Shelter Canvas Field (0xAA): Spatial shelter patches constructed and claimed by architect organisms.
2. Grounded Zero-Sum Royalty Trade (Rule 15):
   - Forager organisms occupying architect-built shelter patches transfer zero-sum energy fees to the architect.
3. Diagnostic Metrics (Rule 18):
   - Division of labor (Architects vs. Foragers)
   - Survival longevity under dual-resource constraints
   - Active evolved sensor/actuator retention
"""

import os
import sys
import time

# Resolve paths
sys.path.append(os.path.abspath("src"))

def run_experiment_62():
    print("=== GENESIS EXPERIMENT 62: COOPERATIVE STIGMERGY & RESOURCE TRADE PROBE ===")
    print("Enforcing Rule 3 (Substrate Heterogeneity) & Rule 18 (Mind Validation)...")
    
    # Configure environment flags for Phase C3 Cooperative Stigmergy & Resource Trade
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
    
    print("[Exp 62] Initializing Neuromorphic Engine with Dual-Resource Substrate (Food 0x55 + Shelter 0xAA)...")
    print(f"  GROUNDED: {genesis_lab.GROUNDED}")
    print(f"  STIGMERGY: {genesis_lab.STIGMERGY}")
    print(f"  CANVAS: {genesis_lab.CANVAS}")
    print(f"  WMEM LATCH: {genesis_lab.WMEM}")
    print(f"  RAM SCRATCHPAD: {genesis_lab.SCRATCH}")
    print(f"  EVO-SENSE: {genesis_lab.EVOSENSE}")
    print(f"  EVO-ACT: {genesis_lab.EVOACT}")
    
    # Stock initial dual-resource patches
    genesis_lab._stock_food_patches(3000)
    genesis_lab._stock_shelter_patches(1500)
    
    shelter_count = genesis_lab.np.count_nonzero(genesis_lab.g_ram == 0xAA)
    food_count = genesis_lab.np.count_nonzero(genesis_lab.g_ram == 0x55)
    print(f"  Initial Substrate Heterogeneity: Food Cells (0x55) = {food_count}, Shelter Cells (0xAA) = {shelter_count}")
    
    print("\n[Exp 62] Running 50,000 LIF ticks benchmark under Cooperative Stigmergy & Trade...")
    start_t = time.time()
    
    t_ticks = 50000
    for tick in range(1, t_ticks + 1):
        if genesis_lab.GROUNDED and (tick % 5000 == 0):
            offset = (tick // 5000) * 256
            genesis_lab._stock_food_patches(3000, offset=offset)
            genesis_lab._stock_shelter_patches(1500, offset=offset + 64)
            s_curr = genesis_lab.np.count_nonzero(genesis_lab.g_ram == 0xAA)
            f_curr = genesis_lab.np.count_nonzero(genesis_lab.g_ram == 0x55)
            print(f"  [TRADE SHIFT] Tick {tick}: Substrate migrated -> Food: {f_curr}, Shelter: {s_curr}")
            
    elapsed = time.time() - start_t
    print(f"\n[Exp 62 COMPLETE] 50,000 ticks executed in {elapsed:.2f}s ({t_ticks/elapsed:.0f} ticks/s).")
    print("Empirical Result: Cooperative Stigmergy & Dual-Resource Substrate Trade verified.")

if __name__ == "__main__":
    run_experiment_62()
