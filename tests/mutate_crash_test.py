"""
Regression test for the Ark-reseed crash: `ValueError: empty range in randrange(8, 8)`
in mutate_dna (genesis_lab.py). Trigger = a genome of length exactly 8 (the floor the
deletion-mutation branch shrinks down to) hitting the duplication branch, which called
random.randint(8, l-1) == randint(8, 7) with no `l > 8` guard.

Hammer mutate_dna on length-8..12 genomes thousands of times; the 0.10-0.15 random band
(duplication) fires ~5% of calls, so a few thousand iterations exercises the crash path
hundreds of times. PASS = no exception; every result is a valid uint8 genome.
"""
import os, sys, tempfile
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(tempfile.gettempdir(), "genesis_numba_muttest"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import random
import numpy as np
import genesis_lab as gl

random.seed(0)
crashes = 0
checked = 0
for l in range(8, 13):                       # length 8 is the crash floor
    genome = bytes(random.randint(0, 255) for _ in range(l))
    for _ in range(4000):
        try:
            out = gl.mutate_dna(genome)
        except ValueError as e:
            crashes += 1
            print(f"CRASH at l={l}: {e}")
            break
        assert isinstance(out, np.ndarray) and out.dtype == np.uint8 and len(out) >= 8
        checked += 1

print(f"RESULT mutate_dna calls={checked} crashes={crashes} "
      f"-> {'PASS' if crashes == 0 else 'FAIL'}")
