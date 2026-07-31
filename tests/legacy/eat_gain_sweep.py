"""
Economy-rebalance sweep — Result.md Exp 4 follow-up / Roadmap P4.

Even on a 100% food carpet, organisms starve: one meal (+CYCLES_PER_EAT_GAIN = 1024) is worth
less than the honest per-cycle burn of a brain. This sweep raises the meal value and asks: is
there a value at which a foraging population self-sustains (energy flattens > 0, survives the
horizon) with the Ark OFF?

`CYCLES_PER_EAT_GAIN` is baked into the njit hot path at COMPILE time, so each meal value must run
in its OWN process with a distinct NUMBA_CACHE_DIR — otherwise numba reuses a stale cached kernel
compiled with the old value. This script handles ONE meal value; a shell loop runs it per value:

    for g in 1024 4096 16384 65536; do py -3.13 tests/eat_gain_sweep.py $g 500; done

It probes two food densities (moderate + ~100% carpet) at a fixed small buffer, Ark OFF.
"""
import os, sys, tempfile

EAT_GAIN = float(sys.argv[1]) if len(sys.argv) > 1 else 1024.0
HORIZON = int(sys.argv[2]) if len(sys.argv) > 2 else 500

# MUST be set before numba / the engine are imported (import self_sustain_test triggers that).
os.environ["GENESIS_EAT_GAIN"] = str(EAT_GAIN)
os.environ["NUMBA_CACHE_DIR"] = os.path.join(tempfile.gettempdir(), f"genesis_numba_eat_{int(EAT_GAIN)}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tests/  (for self_sustain_test)
import self_sustain_test as sst                                  # its import chain pulls in numba
import neuromorphic_engine as ne

# Sanity: confirm the override actually reached the engine constant.
assert abs(float(ne.CYCLES_PER_EAT_GAIN) - EAT_GAIN) < 1e-6, (
    f"GENESIS_EAT_GAIN not applied: engine has {float(ne.CYCLES_PER_EAT_GAIN)}, expected {EAT_GAIN}")

print(f"{'eat_gain':>9} {'food':>7} {'survived':>8} {'extinct':>7} "
      f"{'e_early':>8} {'e_mid':>8} {'e_late':>8} {'min_tail':>8} {'SUSTAIN':>7}")
for fr in (100.0, 5000.0):   # moderate density, then ~100% carpet
    r = sst.run_config(10000.0, fr, ark_enabled=False, n_ticks=HORIZON)
    print(f"{EAT_GAIN:>9.0f} {fr:>7.0f} {r['survived_ticks']:>8} {str(r['went_extinct']):>7} "
          f"{r['e_early']:>8.0f} {r['e_mid']:>8.0f} {r['e_late']:>8.0f} "
          f"{r['min_pop_tail']:>8} {str(r['sustained']):>7}")
