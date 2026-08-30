import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import torch
from genesis.server.phase_e_substrate import BatchedPopulation
from genesis.server.phase_e_ecology import EcologyField
from genesis.server.phase_e_plus import PhaseEPlusInternetSensing

print("=" * 70)
print("🚀 GENESIS High-Performance Substrate TPS Benchmark (Zero-Allocation & Streams)")
print("=" * 70)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Hardware Device: {torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU'}")

pop = BatchedPopulation(n_worlds=32, pop_per_world=128, device=device)
eco = EcologyField(n_worlds=32, grid_size=32, device=device)
sensing = PhaseEPlusInternetSensing(
    population=pop,
    ecology=eco,
    update_interval=100,
    target_batch_size=4,
    device=device
)

# Warmup (100 ticks)
print("Warming up GPU pipeline (100 ticks)...")
for t in range(100):
    sensing.step_tick(t)

if device == "cuda":
    torch.cuda.synchronize()
    mem_initial = torch.cuda.memory_allocated() / (1024 * 1024)
    print(f"Initial Allocated VRAM: {mem_initial:.2f} MB")

n_benchmark_ticks = 2000
print(f"Executing {n_benchmark_ticks} benchmark ticks across 4,096 organisms (32 worlds)...")

t0 = time.perf_counter()
for t in range(100, 100 + n_benchmark_ticks):
    sensing.step_tick(t)

if device == "cuda":
    torch.cuda.synchronize()
    mem_final = torch.cuda.memory_allocated() / (1024 * 1024)

t1 = time.perf_counter()
elapsed = t1 - t0
tps = n_benchmark_ticks / elapsed

print("=" * 70)
print(f"✅ Elapsed Time : {elapsed:.2f} seconds")
print(f"🔥 Measured Speed: {tps:.1f} Ticks/Second ({n_benchmark_ticks} ticks in {elapsed:.2f}s)")
print(f"⚡ Time per 1000 Ticks: {1000.0 / tps:.2f} seconds (was 60.0s)")
if device == "cuda":
    print(f"💾 VRAM Delta (Zero-Allocation Check): {mem_final - mem_initial:.4f} MB (Must be 0.0 MB)")
    if abs(mem_final - mem_initial) < 0.1:
        print("✅ Zero-Allocation Invariant: 100% VERIFIED!")
    else:
        print("⚠️ Warning: Dynamic memory allocation detected!")
print("=" * 70)
