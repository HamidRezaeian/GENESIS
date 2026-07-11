"""
Foraging race — does food-SEEKING beat blind drift under PATCHY food? (Result.md Exp 4 / Rule 10)

Uniform-random food gives no gradient to climb, so seeking showed no benefit. Real "pristine memory
blocks" (Rule 15) are contiguous regions, so this harness seeds food in a few contiguous PATCHES,
creating the spatial gradients a food-seeking sense can exploit. It runs ONE fully-parameterised
config (Ark OFF) and prints a single structured RESULT line.

    py -3.13 tests/forage_race.py <seeking 0|1> <eat_gain> <food_per_tick> <horizon>

GENESIS_SEEKING toggles only the ancestor's food-seeking WIRING (both arms still pay the scan cost,
isolating the behavioural value of using food-direction info). NUMBA_CACHE_DIR is keyed by eat_gain
(the only thing the njit hot path bakes) so parallel runs at the same eat_gain share a warm cache.
Extra knobs via env: FORAGE_PATCHES, FORAGE_PATCH_RADIUS, FORAGE_BUFFER, FORAGE_SEED, FORAGE_SCAN.
"""
import os, sys, tempfile, importlib

SEEKING = sys.argv[1] if len(sys.argv) > 1 else "1"
EAT_GAIN = float(sys.argv[2]) if len(sys.argv) > 2 else 1024.0
FOOD_PER_TICK = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
HORIZON = int(sys.argv[4]) if len(sys.argv) > 4 else 500

N_PATCHES = int(os.environ.get("FORAGE_PATCHES", "6"))
PATCH_RADIUS = int(os.environ.get("FORAGE_PATCH_RADIUS", "64"))
BUFFER = float(os.environ.get("FORAGE_BUFFER", "10000"))
SEED = int(os.environ.get("FORAGE_SEED", "1234"))

os.environ["GENESIS_SEEKING"] = SEEKING
os.environ["GENESIS_EAT_GAIN"] = str(EAT_GAIN)
# njit bakes only CYCLES_PER_EAT_GAIN, so cache is safe to share across seeking/food/seed at a
# fixed eat_gain. A stray FORAGE_SCAN (food-scan radius) override would also change the kernel;
# fold it into the cache key so a perturbed scan radius recompiles instead of reusing a stale one.
_scan = os.environ.get("FORAGE_SCAN", "")
os.environ["NUMBA_CACHE_DIR"] = os.path.join(
    tempfile.gettempdir(), f"genesis_numba_eat_{int(EAT_GAIN)}{('_scan' + _scan) if _scan else ''}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tests/
import self_sustain_test as sst        # pulls in numba / genesis_lab (env already set above)
import numpy as np
import random
gl = sst.gl


def seed_patch_food(n, centers):
    """Place n food bytes into contiguous patches around the given centers (empty cells only)."""
    for _ in range(int(n)):
        c = centers[random.randint(0, len(centers) - 1)]
        idx = (c + random.randint(-PATCH_RADIUS, PATCH_RADIUS)) % gl.RAM_SIZE
        if gl.g_ram[idx] == 0x00:
            gl.g_ram[idx] = 0x55


def run():
    importlib.reload(gl)                 # fresh universe; ancestor reads GENESIS_SEEKING at seed time
    random.seed(SEED)
    np.random.seed(SEED)
    gl.g_ram[:] = 0                       # clear the module's default uniform food; patches only
    centers = [int((i + 0.5) * gl.RAM_SIZE / N_PATCHES) for i in range(N_PATCHES)]
    gl.seed_universe(300, initial_energy=BUFFER)
    seed_patch_food(N_PATCHES * PATCH_RADIUS, centers)   # initial standing food in the patches

    energy_trace, pop_trace = [], []
    extinct_tick = None
    for t in range(HORIZON):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            extinct_tick = t
            break
        whole = int(FOOD_PER_TICK)
        seed_patch_food(whole, centers)
        if random.random() < (FOOD_PER_TICK - whole):
            seed_patch_food(1, centers)
        steps = max(1, int(3000 / max(1, alive)))
        _, n_births = sst._world_tick(steps)
        sst._process_births(n_births)
        gl.global_time += steps
        e = gl.g_energy[gl.g_alive]
        energy_trace.append(float(np.mean(e)) if len(e) else 0.0)
        pop_trace.append(int(np.sum(gl.g_alive)))

    def e_at(f):
        return energy_trace[min(len(energy_trace) - 1, int(f * len(energy_trace)))] if energy_trace else 0.0

    tail = pop_trace[len(pop_trace) // 2:] if len(pop_trace) > 2 else pop_trace
    late_ok = (len(energy_trace) > 4 and energy_trace[-1] > 0.0
               and energy_trace[-1] >= 0.85 * max(1.0, energy_trace[len(energy_trace) // 2]))
    sustained = late_ok and extinct_tick is None
    survived = extinct_tick if extinct_tick is not None else HORIZON
    print(f"RESULT seeking={SEEKING} eat_gain={EAT_GAIN:.0f} food={FOOD_PER_TICK:.0f} "
          f"patches={N_PATCHES}x{PATCH_RADIUS} seed={SEED} survived={survived} "
          f"extinct={extinct_tick is not None} e_early={e_at(0.1):.0f} e_mid={e_at(0.5):.0f} "
          f"e_late={e_at(0.9):.0f} peak={max(pop_trace) if pop_trace else 0} "
          f"min_tail={min(tail) if tail else 0} SUSTAIN={sustained}")


run()
