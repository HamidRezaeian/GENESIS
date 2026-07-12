"""
LIVE book-economy verification (Roadmap P0) — does the reading economy, as wired into the LIVE
sim_loop (genesis_lab.py, GENESIS_ECONOMY=books), actually SUSTAIN a population on reading income
instead of collapsing like the legacy 0x55-food economy?

This mirrors the live loop's book logic EXACTLY:
  - contiguous curriculum passages injected with inject_passage() (a real library, not confetti),
  - the library restocked to BOOK_TARGET_BYTES whenever it depletes,
  - a MODEST seed buffer (reading must pay the bills; no 250k coast),
  - NO 0x55 food added (reading is the only real income),
  - Ark OFF so extinction is TERMINAL and survival is an honest measurement.

It sweeps the standing library size (BOOK_TARGET_BYTES) and reports, per config, how long the
population survives, its final size, and — decisively — how many CORRECT reads (read_log type 1)
occurred. Survival WITHOUT reads would just be buffer-coasting; survival WITH many reads is the
Prime-Directive win. Prints one RESULT line per config.

    py -3.13 tests/live_book_economy_test.py [horizon]

Runs under GENESIS_ECONOMY=books so the njit hot path bakes READ_SCALE=64 / EAT_GAIN=16 (the live
book defaults); NUMBA_CACHE_DIR is keyed to those by genesis_lab itself.
"""
import os, sys, importlib

os.environ["GENESIS_ECONOMY"] = "books"          # bake the reading economy into the hot path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import self_sustain_test as sst                  # reuses _world_tick / _process_births / gl
import numpy as np, random
gl = sst.gl
import books_of_genesis as bog

HORIZON = int(sys.argv[1]) if len(sys.argv) > 1 else 400
CATEGORY = os.environ.get("GENESIS_BOOK_CATEGORY", "English")
NAME = os.environ.get("GENESIS_BOOK_NAME", "01_Alphabet")


def _library_bytes():
    r = gl.g_ram
    return int(np.count_nonzero((r >= 32) & (r <= 126) & (r != 0x55)))


def run_config(target_bytes, seed_energy, rng_seed=1234):
    importlib.reload(gl)                          # pristine universe
    # reload resets module globals; re-assert the economy knobs the loop reads
    gl.GENESIS_ECONOMY = "books"
    random.seed(rng_seed); np.random.seed(rng_seed)

    # Pre-stock the library (mirror sim_loop prestock).
    while _library_bytes() < target_bytes:
        if bog.inject_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME) is None:
            print(f"[WARN] cannot inject {CATEGORY}/{NAME}"); break
    start_lib = _library_bytes()

    gl.seed_universe(300, initial_energy=seed_energy)

    correct = wrong = predictions = 0
    survived_to = 0
    for t in range(HORIZON):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            break
        survived_to = t
        # Restock the library when depleted — same cadence shape as the live loop. NO 0x55 food.
        if _library_bytes() < target_bytes:
            bog.inject_passage(gl.g_ram, gl.RAM_SIZE, CATEGORY, NAME)

        gl.g_read_log[0] = 1
        steps = max(1, int(3000 / max(1, alive)))
        _, n_births = sst._world_tick(steps)
        sst._process_births(n_births)

        rl = gl.g_read_log; idx = 1
        while idx < rl[0] and idx + 2 < len(rl):
            typ = rl[idx]
            if typ == 1: correct += 1; idx += 3
            elif typ == 3: predictions += 1; idx += 3
            elif typ == 2: wrong += 1; idx += 4
            else: idx += 1
        gl.global_time += steps

    final = int(np.sum(gl.g_alive))
    sustained = (final > 0 and survived_to >= HORIZON - 1)
    print(f"RESULT target_bytes={target_bytes:>6} start_lib={start_lib:>6} seed_E={seed_energy:>7.0f} "
          f"survived_to={survived_to:>4} final_pop={final:>3} correct_reads={correct:>6} "
          f"predictions={predictions:>5} wrong_reads={wrong:>6} SUSTAIN={sustained}")
    return sustained, correct, final


def main():
    print(f"=== LIVE BOOK-ECONOMY VERIFICATION (horizon={HORIZON}, book={CATEGORY}/{NAME}, Ark OFF) ===")
    print(f"    READ_SCALE={os.environ.get('GENESIS_READ_SCALE')} EAT_GAIN={os.environ.get('GENESIS_EAT_GAIN')} "
          f"(no 0x55 food injected; reading is the only income)")
    # Optional single-config override (isolate "can the live wiring sustain?" from default tuning):
    #   TARGET=<bytes> SEED_E=<energy>  (GENESIS_READ_SCALE/EAT_GAIN via the usual env, pre-import)
    if os.environ.get("TARGET"):
        run_config(int(os.environ["TARGET"]), seed_energy=float(os.environ.get("SEED_E", "20000")))
        return
    # Sweep standing library size. Denser library -> organisms land on symbols more often -> more
    # reading income. Finds the coverage where reading alone sustains life.
    for target in (3000, 6000, 12000, 24000):
        run_config(target, seed_energy=20000.0)


if __name__ == "__main__":
    main()
