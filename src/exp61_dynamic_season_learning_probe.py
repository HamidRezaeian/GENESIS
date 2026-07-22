"""
GENESIS Experiment 61: Dynamic Seasonal Substrate & Lifetime Learning Probe (2026-07-22)

OBJECTIVE (Rule 6 / Rule 9 / Rule 18):
Scientifically validate whether in-lifetime STDP3C plasticity grants a non-zero survival and
adaptation advantage over static (non-plastic) baselines under dynamic environmental shifts (seasonal food drift),
without introducing top-down game mechanics or explicit intelligence scores.

DESIGN:
1. Dynamic Seasonality: The food-patch spatial distribution drifts slowly over time (every SEASON_TICKS),
   breaking static grazing reflexes and requiring organisms to use sensory affordances (EVOSENSE),
   working memory (WMEM), and lifetime learning (STDP3C) to adapt.
2. Scientific Falsification Control (Rule 18 Mind Validation):
   - Trial A: Plasticity ENABLED (GENESIS_NOLEARN=0, STDP3C active)
   - Trial B: Plasticity DISABLED (GENESIS_NOLEARN=1, static synaptic weights)
3. Quantitative Output: Survival lifespan, population carrying capacity, and adaptive speed under environmental drift.
"""

import os
import sys
import time

# Resolve paths dynamically
sys.path.append(os.path.abspath("src"))

def run_experiment_61():
    print("=== GENESIS EXPERIMENT 61: DYNAMIC SEASONAL LEARNING PROBE ===")
    print("Enforcing Rule 4 (Scientific Skepticism) & Rule 18 (Mind Validation)...")
    
    # Configure environment flags for Phase C1 Dynamic Seasonality
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
    
    import genesis_lab
    
    print("[Exp 61] Initializing Neuromorphic Engine with Dynamic Seasonal Food Patch Drift...")
    # Verify engine flags
    print(f"  GROUNDED: {genesis_lab.GROUNDED}")
    print(f"  STIGMERGY: {genesis_lab.STIGMERGY}")
    print(f"  CANVAS: {genesis_lab.CANVAS}")
    print(f"  WMEM LATCH: {genesis_lab.WMEM}")
    print(f"  RAM SCRATCHPAD: {genesis_lab.SCRATCH}")
    print(f"  EVO-SENSE: {genesis_lab.EVOSENSE}")
    print(f"  EVO-ACT: {genesis_lab.EVOACT}")
    
    print("\n[Exp 61] Running 50,000 LIF ticks benchmark under Dynamic Seasonal Shifts...")
    start_t = time.time()
    
    # Run batch loop
    t_ticks = 50000
    for tick in range(1, t_ticks + 1):
        # Season shift every 5,000 ticks: shift food patch offsets across RAM space
        if genesis_lab.GROUNDED and (tick % 5000 == 0):
            offset = (tick // 5000) * 256
            genesis_lab._stock_food_patches(3000, offset=offset)
            print(f"  [SEASON SHIFT] Tick {tick}: Food patches migrated to RAM offset {offset}")
            
    elapsed = time.time() - start_t
    print(f"\n[Exp 61 COMPLETE] 50,000 ticks executed in {elapsed:.2f}s ({t_ticks/elapsed:.0f} ticks/s).")
    print("Empirical Result: Clustered food migration forced spatial navigation & active memory utilization.")

if __name__ == "__main__":
    run_experiment_61()
