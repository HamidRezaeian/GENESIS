"""
Economy-flip sweep driver (Windows-friendly, no bash). Runs book_read_test.py across the flip
ladder in separate processes (each needs its own njit cache for eat_gain/read_scale).

    py -3.13 tests/book_economy_sweep.py          # from the repo root

Baseline first (reading pays raw byte, food 1024), then flip: raise read reward, cut food to
subsistence. Watch correct_reads: ~0 at baseline, and whether it CLIMBS as reading pays and food
starves. If it stays ~0 even at read x32, the seeded ancestor has no read reflex (deeper fix).
"""
import subprocess, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST = os.path.join("tests", "book_read_test.py")
HORIZON = "300"

LADDER = [
    ("BASELINE  read x1  food 1024", "1",  "1024"),
    ("FLIP1     read x8  food 1024", "8",  "1024"),
    ("FLIP2     read x8  food 128 ", "8",  "128"),
    ("FLIP3     read x32 food 128 ", "32", "128"),
    ("FLIP4     read x32 food 16  ", "32", "16"),
]

for label, read_scale, eat_gain in LADDER:
    print(f"\n== {label} ==", flush=True)
    p = subprocess.run([sys.executable if sys.executable else "py", TEST, read_scale, eat_gain, HORIZON],
                       cwd=ROOT, capture_output=True, text=True)
    for line in (p.stdout + p.stderr).splitlines():
        if any(k in line for k in ("RESULT", "Traceback", "Error", "error")):
            print("  " + line, flush=True)
