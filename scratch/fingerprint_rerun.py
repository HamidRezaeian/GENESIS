"""Clean re-run of compile_fingerprint_test check [4] with a NON-DEFAULT RAM_SIZE arm.
Diagnosis (user): the committed test uses GENESIS_RAM_SIZE=65536, which IS the host default,
so base and ram arms produce the same fingerprint -> 3 dirs instead of 4. Test bug."""
import subprocess
import sys
import os

SRC = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "src")

_CHILD = (
    "import sys, os; sys.path.insert(0, %r); "
    "import numpy as np; "
    "import neuromorphic_engine as ne; "
    "m = np.zeros(8, np.bool_); "
    "ne.malloc_block(2, m); "
    "import numba; print(numba.config.CACHE_DIR or 'UNSET')"
)


def child(extra):
    env = dict(os.environ)
    env.pop("NUMBA_CACHE_DIR", None)
    env.update(extra)
    out = subprocess.run([sys.executable, "-c", _CHILD % SRC],
                         capture_output=True, text=True, env=env, timeout=600)
    assert out.returncode == 0, out.stderr[-1500:]
    return out.stdout.strip().splitlines()[-1]


d_base = child({})
d_base2 = child({})
d_dale = child({"GENESIS_DALE": "1"})
# NON-DEFAULT (host default is 65536)
d_ram = child({"GENESIS_RAM_SIZE": "131072"})
d_ec = child({"GENESIS_EVOLVABLE_CONSTANTS": "1"})

assert d_base == d_base2, "identical rerun must reuse same dir"
dirs = {d_base, d_dale, d_ram, d_ec}
for k, v in [("base", d_base), ("dale", d_dale), ("ram131072", d_ram), ("ec", d_ec)]:
    print(f"{k:10s} -> {v}")
print(f"DISTINCT_DIRS = {len(dirs)} (expect 4)")
assert len(dirs) == 4, f"STILL FAILING: {dirs}"
print("CLEAN_RERUN_WITH_NONDEFAULT_RAM: PASS")
