"""
Book-reading economy test (Result.md / Rules 9-10). Do organisms gain energy by SOLVING books
(land on an ASCII symbol + vocalize it correctly) rather than eating 0x55 food ("weeds")?

Injects the English Alphabet curriculum as ASCII into RAM, runs Ark-OFF, and counts correct vs
wrong reads from read_log (type 1 = correct symbol solved, type 2 = wrong output penalized).

    py -3.13 tests/book_read_test.py <read_scale> <eat_gain> <horizon>

Env: GENESIS_READ_SCALE flips the read reward; GENESIS_EAT_GAIN sets mindless-food value (lower =
subsistence food, forcing reading). NUMBA_CACHE_DIR keyed by (eat_gain, read_scale) since both bake
into the njit hot path.
"""
import os, sys, tempfile, importlib

READ_SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
EAT_GAIN   = float(sys.argv[2]) if len(sys.argv) > 2 else 1024.0
HORIZON    = int(sys.argv[3])   if len(sys.argv) > 3 else 400
FILL_FRAC  = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0   # fraction of RAM flooded with A-Z text
BOOK       = sys.argv[5] if len(sys.argv) > 5 else "alpha"      # "alpha" (echo A-Z) or "math" (Addition)

os.environ["GENESIS_READ_SCALE"] = str(READ_SCALE)
os.environ["GENESIS_EAT_GAIN"]   = str(EAT_GAIN)
os.environ["NUMBA_CACHE_DIR"] = os.path.join(
    tempfile.gettempdir(), f"genesis_numba_e{int(EAT_GAIN)}_r{READ_SCALE}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import self_sustain_test as sst
import numpy as np, random
gl = sst.gl
import books_of_genesis as bog


def run():
    importlib.reload(gl)
    random.seed(1234); np.random.seed(1234)
    if BOOK == "math":
        # Addition curriculum: contiguous equations "1+1=2" (answer included). Walking across
        # "1+1=" and stepping onto "2" scores a PREDICTION (type 3) only if the organism computed it.
        for _ in range(60):
            bog.inject_curriculum_file(gl.g_ram, gl.RAM_SIZE, "Math", "02_Addition")
    elif FILL_FRAC > 0.0:
        # Flood mode: fill a fraction of RAM with random A-Z so organisms are almost always on a
        # symbol — isolates "can reading pay as an economy?" from symbol-density/seeking.
        gl.g_ram[:] = 0
        n_fill = int(gl.RAM_SIZE * FILL_FRAC)
        for _ in range(n_fill):
            gl.g_ram[random.randint(0, gl.RAM_SIZE - 1)] = random.randint(65, 90)
    else:
        # Inject the Alphabet curriculum repeatedly so symbols are dense enough to encounter.
        for _ in range(8):
            bog.inject_curriculum_file(gl.g_ram, gl.RAM_SIZE, "English", "01_Alphabet")
    n_symbols = int(np.sum((gl.g_ram >= 32) & (gl.g_ram <= 126) & (gl.g_ram != 0x55)))
    gl.seed_universe(300, initial_energy=10000.0)

    correct = wrong = predictions = 0
    for t in range(HORIZON):
        alive = int(np.sum(gl.g_alive))
        if alive == 0:
            break
        # Re-inject curriculum so it is not exhausted. NO 0x55 food added (reading is the economy).
        if t % 20 == 0:
            if BOOK == "math":
                bog.inject_curriculum_file(gl.g_ram, gl.RAM_SIZE, "Math", "02_Addition")
            elif FILL_FRAC <= 0.0:
                bog.inject_curriculum_file(gl.g_ram, gl.RAM_SIZE, "English", "01_Alphabet")
        gl.g_read_log[0] = 1  # reset read-log write head
        steps = max(1, int(3000 / max(1, alive)))
        sst._world_tick(steps)
        # Tally logged events: 1 = correct echo read, 3 = correct PREDICTION (computed next symbol),
        # 2 = wrong echo read.
        idx = 1
        rl = gl.g_read_log
        while idx < rl[0] and idx + 2 < len(rl):
            typ = rl[idx]
            if typ == 1: correct += 1; idx += 3
            elif typ == 3: predictions += 1; idx += 3
            elif typ == 2: wrong += 1; idx += 4
            else: idx += 1
        gl.global_time += steps

    final = int(np.sum(gl.g_alive))
    print(f"RESULT book={BOOK} read_scale={READ_SCALE} eat_gain={EAT_GAIN:.0f} symbols={n_symbols} "
          f"survived_to={t} final_pop={final} correct_reads={correct} "
          f"correct_predictions={predictions} wrong_reads={wrong}")


run()
