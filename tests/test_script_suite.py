"""Pytest wrapper for the script-style test suite (2026-07-31, deep-review CI hygiene).

The project's canonical tests are executable scripts under tests/ (they print PASS lines
and sys.exit(non-zero) on failure). They CANNOT be imported by pytest directly — most run
work at module scope and exit at import. This wrapper runs each as a subprocess so the whole
suite is reachable through `pytest` (and CI) with per-test reporting:

    pytest -m "not slow"   # fast suite (default CI)
    pytest -m slow         # adds kernel-driving probes (numba JIT; minutes on cold cache)
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAST_SCRIPTS = [
    "telemetry_honesty_test.py",
    "ast_duplicate_test.py",
    "capacity_resolver_test.py",
    "brain_io_test.py",
    "birth_provenance_test.py",
    "capability_protocol_test.py",
    "reproducibility_smoke_test.py",
    "task_generalization_protocol_test.py",
    "compile_fingerprint_test.py",
    "mutate_crash_test.py",
    "auto_capacity_probe.py",
]

SLOW_SCRIPTS = [
    "smoke_test.py",
]


def _run_script(script):
    env = os.environ.copy()
    env.setdefault("GENESIS_LIVE_WEB", "0")  # deterministic benchmark mode in CI
    env.setdefault("NUMBA_CACHE_DIR", "/tmp/genesis_pytest_numba")
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", script)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800,
    )
    tail = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, f"{script} exited {proc.returncode}:\n{tail[-4000:]}"


@pytest.mark.parametrize("script", FAST_SCRIPTS)
def test_fast_script(script):
    _run_script(script)


@pytest.mark.slow
@pytest.mark.parametrize("script", SLOW_SCRIPTS)
def test_slow_script(script):
    _run_script(script)
