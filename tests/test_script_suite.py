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
    "fabrication_scan_test.py",  # Exp 95: anti-fabrication guard (replaces the quarantined
    # capability_protocol_test.py / task_generalization_protocol_test.py, which guarded
    # fabricated numbers — see experiments/legacy_fabricated/README.md)
    "reproducibility_smoke_test.py",
    "compile_fingerprint_test.py",
    "mutate_crash_test.py",
    "auto_capacity_probe.py",
]

SLOW_SCRIPTS = [
    "smoke_test.py",
    "engine_defaultpath_regression_test.py",
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


@pytest.mark.slow
def test_tf1_leaderboard_runner():
    """Small-budget certification: the pre-registered TF1 runner must publish a row with
    gates evaluated, the Exp-94 paired-permutation stats block, and full provenance fields
    (Exp 92-TF1 / Exp 94). Uses 2 seeds for CI wall-time; the certified dashboard row is
    produced by the full n=8 driver."""
    env = os.environ.copy()
    env.update({
        "GENESIS_LIVE_WEB": "0",
        "EXP92_TF1_SEEDS": "0,1",
        "EXP92_TF1_TICKS": "8000",  # >= 4 windows needed for SWAP-era measurement (G2b gate)
        "EXP92_TF1_TIMEOUT": "600",
    })
    lb_path = os.path.join(ROOT, "experiments", "leaderboard", "latest.json")
    backup = None
    if os.path.exists(lb_path):
        with open(lb_path, "rb") as f:
            backup = f.read()
    try:
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "experiments", "exp92_tf1_leaderboard_runner.py")],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800,
        )
        tail = (proc.stdout or "") + (proc.stderr or "")
        assert proc.returncode == 0, f"tf1 runner exited {proc.returncode}:\n{tail[-3000:]}"
        import json
        with open(lb_path) as f:
            d = json.load(f)
    finally:
        # The dashboard's published certified row belongs to the FULL n=8 driver; never let a
        # CI-budget run overwrite it.
        if backup is not None:
            with open(lb_path, "wb") as f:
                f.write(backup)
    assert d["protocol_id"] == "REMAP_SANDBOX_TF1_v1"
    assert "certified" in d and "gates" in d and "runs_manifest_hash" in d
    assert d["metrics"]["swap_delta_learner_minus_ablation"] is not None
    st = d["metrics"]["stats"]
    assert st["n_pairs"] == 2 and st["p_two_sided"] is not None
    assert st["tail"].startswith("two-sided")
    assert len(st["per_seed_deltas"]) == 2
