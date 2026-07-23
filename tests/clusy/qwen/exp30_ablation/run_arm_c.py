"""
Exp 30 Arm C: STDP_COSTONLY — Energy-cost isolation.

Runs one arm where STDP energy cost is charged but weight updates are zeroed.
Compares against existing Arm A (STDP ON) and Arm B (STDP OFF) results.

Usage:
    python run_arm_c.py
"""
import subprocess, os, json, time, textwrap, sys

DRIVER = "/tmp/exp30_driver.py"
N_TICKS = 200_000; SAMPLE_EVERY = 1_000; SEED = 42; BOOK_TARGET_BYTES = 6000

env = os.environ.copy()
env.update(GENESIS_NOLEARN="0", GENESIS_STDP_COSTONLY="1",
           SEED=str(SEED), N_TICKS=str(N_TICKS), SAMPLE_EVERY=str(SAMPLE_EVERY),
           OUTPUT_FILE="results/arm_C.json", BOOK_TARGET_BYTES=str(BOOK_TARGET_BYTES),
           NUMBA_CACHE_DIR="/tmp/numba_cache_C_COSTONLY")

print(f"\n{'='*70}")
print(f"  ARM C: STDP_COSTONLY (energy charged, weights frozen)")
print(f"{'='*70}", flush=True)

t0 = time.time()
result = subprocess.run([sys.executable, DRIVER], env=env, timeout=5400)
dt = time.time() - t0
print(f"  Finished in {dt:.1f}s (exit {result.returncode})")

for label, path in [("A", "results/arm_A.json"), ("B", "results/arm_B.json"), ("C", "results/arm_C.json")]:
    with open(path) as f: d = json.load(f)
    print(f"  Arm {label}: {d['ticks_per_sec']:.0f} t/s, pop={np.mean(d['population'][-50:]):.0f}, ext={d['extinctions']}")
