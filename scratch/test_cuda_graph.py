import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_ecology import EcologyField
from genesis.server.phase_e_plus import PhaseEPlusInternetSensing

device = "cuda" if torch.cuda.is_available() else "cpu"
pop = BatchedPopulation(n_worlds=32, pop_per_world=128, device=device)
eco = EcologyField(n_worlds=32, grid_size=32, device=device)
sensing = PhaseEPlusInternetSensing(population=pop, ecology=eco, device=device)

# Initialize CUDA Graph on population
sample_sensory = torch.zeros(32, 128, 20, dtype=torch.float16, device=device)
sample_harvest = torch.zeros(32, 128, dtype=torch.float16, device=device)

print("[TEST] Capturing CUDA Graph on BatchedPopulation...")
pop.capture_tick_graph(sample_sensory, sample_harvest)
print("✅ CUDA Graph captured successfully!")

# Benchmark 2000 ticks with CUDA Graph active
print("Executing 2000 benchmark ticks with CUDA Graph...")
t0 = time.perf_counter()
for t in range(2000):
    sensing.step_tick(t)

torch.cuda.synchronize()
t1 = time.perf_counter()
elapsed = t1 - t0
tps = 2000.0 / elapsed

print("=" * 70)
print(f"🔥 Speed with CUDA Graph: {tps:.1f} Ticks/Second (2000 ticks in {elapsed:.2f}s)")
print(f"⚡ Time per 1000 Ticks : {1000.0 / tps:.2f} seconds (was 60.0s baseline)")
print("=" * 70)
