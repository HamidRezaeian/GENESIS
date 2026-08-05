"""Rule 21.8 compile-fingerprint coverage + behaviour suite (2026-07-31 audit).

Guards the invariant that EVERY GENESIS_* env read in neuromorphic_engine.py is covered by the
numba cache fingerprint (compile_fingerprint.ENV_NAME_MAP), so a future flag cannot silently
reintroduce the stale-kernel bug class, and verifies the fingerprint actually changes when the
physics state changes (fresh subprocess per arm — compile-time flags are process-bound).

Run: python tests/compile_fingerprint_test.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "src"))

import compile_fingerprint as cfp
import subprocess


ENGINE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "src", "neuromorphic_engine.py")

_CHILD = (
    "import sys, os; sys.path.insert(0, %r); "
    "import numpy as np; "
    "import neuromorphic_engine as ne; "
    # force ONE kernel compilation so the
    "m = np.zeros(8, np.bool_); "
    # cache locator must bind somewhere
    "ne.malloc_block(2, m); "
    "import numba; print(numba.config.CACHE_DIR or 'UNSET')"
)


def _child_cache_dir(extra_env):
    env = dict(os.environ)
    env.pop("NUMBA_CACHE_DIR", None)
    env.update(extra_env)
    src_dir = os.path.dirname(ENGINE_PATH)
    out = subprocess.run(
        [sys.executable, "-c", _CHILD % src_dir],
        capture_output=True, text=True, env=env, timeout=600)
    assert out.returncode == 0, f"child failed: {out.stderr[-2000:]}"
    return out.stdout.strip().splitlines()[-1]


def main():
    print("Initializing Compile-Fingerprint Test Suite...")

    # [1] Coverage: every GENESIS_* env read in the engine is fingerprint-mapped.
    uncovered, covered = cfp.coverage_report(ENGINE_PATH)
    assert not uncovered, (
        f"Uncovered engine env reads (add to ENV_NAME_MAP or HOST_SIDE_EXEMPT): {uncovered}")
    print(
        f"[1] Engine Env-Read Coverage OK: {len(covered)} GENESIS_* reads mapped, 0 uncovered")

    # [2] Mapping sanity: every mapped engine global is actually fingerprinted, and every
    # exempt name carries a documented reason.
    for env_name, glob in cfp.ENV_NAME_MAP.items():
        assert env_name not in cfp.HOST_SIDE_EXEMPT, f"{env_name} both mapped and exempt"
        assert glob in cfp.KERNEL_STATE_VARS, f"{env_name} -> {glob} not in KERNEL_STATE_VARS"
    for env_name, reason in cfp.HOST_SIDE_EXEMPT.items():
        assert isinstance(reason, str) and len(
            reason) > 10, f"{env_name} exempt without a reason"
    print(f"[2] Env->Global Mapping Complete OK ({len(cfp.ENV_NAME_MAP)} mapped, "
          f"{len(cfp.HOST_SIDE_EXEMPT)} documented host-side exemptions)")

    # [3] Fingerprint reads engine globals faithfully + raises on a missing global.
    fake = {name: 1 for name in cfp.KERNEL_STATE_VARS}
    fp1, canon1 = cfp.fingerprint(fake)
    fake2 = dict(fake)
    fake2["RAM_SIZE"] = 2
    fp2, _ = cfp.fingerprint(fake2)
    assert fp1 != fp2, "fingerprint insensitive to a physics change"
    assert "=" in canon1 and "RAM_SIZE=1" in canon1
    try:
        cfp.fingerprint({})
        raise AssertionError("fingerprint did not raise on missing globals")
    except KeyError:
        pass
    print("[3] Fingerprint Sensitivity + Strictness OK")

    # [4] Behavioural: distinct physics -> distinct cache dirs (the stale-kernel guard), an
    # identical rerun reuses the SAME dir (cache stays useful), AND — the critical regression
    # for the "cache keying was theatre" finding — the child COMPILED a kernel and its artifacts
    # really landed in the keyed dir (numba honours config.CACHE_DIR, not a late env set).
    d_base = _child_cache_dir({})
    d_base2 = _child_cache_dir({})
    assert d_base == d_base2 and "genesis_numba" in d_base, (d_base, d_base2)
    _artifacts = []
    for _root, _dirs, _files in os.walk(d_base):
        _artifacts += [f for f in _files if f.endswith((".nbi", ".nbc"))]
    assert os.path.isdir(d_base) and _artifacts, (
        f"no cache artifacts under keyed dir {d_base}: "
        f"{os.listdir(d_base) if os.path.isdir(d_base) else 'missing'}")
    # ... and NOT in source-adjacent __pycache__ (fresh artifacts only).
    fresh_pycache = [f for f in os.listdir(os.path.join(os.path.dirname(ENGINE_PATH), "__pycache__"))
                     if f.endswith((".nbi", ".nbc"))] \
        if os.path.isdir(os.path.join(os.path.dirname(ENGINE_PATH), "__pycache__")) else []
    assert not fresh_pycache, \
        f"kernel artifacts leaked to source __pycache__: {fresh_pycache[:3]}"
    d_dale = _child_cache_dir({"GENESIS_DALE": "1"})
    # NON-DEFAULT value required: 65536 IS the host-derived default on the floor machine, so it
    # would produce the SAME fingerprint as base and collapse the distinct-dir count (audit 2026-08-01).
    d_ram = _child_cache_dir({"GENESIS_RAM_SIZE": "131072"})
    d_ec = _child_cache_dir({"GENESIS_EVOLVABLE_CONSTANTS": "1"})
    dirs = {d_base, d_dale, d_ram, d_ec}
    assert len(dirs) == 4, f"cache dirs did not isolate physics arms: {dirs}"
    print(f"[4] Cache-Key Isolation + Artifact Placement OK: 4 distinct dirs, "
          f"artifacts verified inside keyed dir (base={d_base.rsplit('/', 1)[-1]})")

    # [5] User-supplied NUMBA_CACHE_DIR is never overridden.
    env = dict(os.environ)
    env["NUMBA_CACHE_DIR"] = "/tmp/genesis_user_explicit_cache"
    src_dir = os.path.dirname(ENGINE_PATH)
    out = subprocess.run([sys.executable, "-c", _CHILD % src_dir],
                         capture_output=True, text=True, env=env, timeout=600)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().splitlines(
    )[-1] == "/tmp/genesis_user_explicit_cache"
    print("[5] User NUMBA_CACHE_DIR Respected OK")

    print("ALL_COMPILE_FINGERPRINT_TESTS_PASSED")


if __name__ == "__main__":
    main()
