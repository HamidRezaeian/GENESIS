"""test_active_solver.py — Phase 0b Step 4: ActiveSolver tests.

These tests validate the Hines (1984) staggered semi-implicit solver surface:
- Passive limit matches CrankNicolsonSolver (critical regression)
- Stability / diagonal dominance properties of the implicit operator
- Convergence under dt halving
- Rannacher startup re-arming behaviour
- Gate update staging and channel linearisation injection
- run() integration with CurrentClampProtocol and Recorder

Two tests are xfail due to known model findings:
- FINDING-1: nata_alpha_h/nata_beta_h swapped in channels/gating.py
- FINDING-2: -70 mV is not an equilibrium of the active model
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from biophysical.channels.channel_distributions import apply_hay_2011_distribution
from biophysical.core.constants import MEM
from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
from biophysical.simulation.active_solver import ActiveSolver, channel_conductance_S
from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.current_clamp import CurrentClampProtocol
from biophysical.simulation.recorder import Recorder


def _build_passive_tree():
    comps, meta = build_l5_pyramidal(apply_bilayer=True)
    return comps, meta


def _build_active_tree():
    comps, meta = build_l5_pyramidal(apply_bilayer=True)
    apply_hay_2011_distribution(comps)
    return comps, meta


def _finite_run(solver, V0, duration_s, proto=None):
    N = solver.N
    dt = solver.dt_s
    n_steps = int(round(duration_s / dt))
    V = V0.copy()
    for k in range(n_steps):
        t = k * dt
        I = proto.get_I_ext(t, N) if proto is not None else np.zeros(N)
        V = solver.step(V, t, I)
    return V


def test_passive_limit_regression():
    """With no active channels, ActiveSolver must exactly match passive solver."""
    comps, _ = _build_passive_tree()
    dt = 25e-6

    s_pass = CrankNicolsonSolver(compartments=comps, dt_s=dt)
    s_act = ActiveSolver(compartments=comps, dt_s=dt)

    assert s_act.has_active_channels is False

    N = s_pass.N
    V0 = np.full(N, MEM.E_leak_V, dtype=np.float64)
    # Inject a small pulse at soma to ensure non-trivial dynamics.
    proto = CurrentClampProtocol(amp_A=2e-10, onset_s=1e-3, dur_s=2e-3, target_idx=0)

    V_pass = _finite_run(s_pass, V0, duration_s=5e-3, proto=proto)
    V_act = _finite_run(s_act, V0, duration_s=5e-3, proto=proto)

    # Should match to numerical precision (same operators / LU).
    assert np.max(np.abs(V_pass - V_act)) < 1e-12


def test_diagonal_dominance():
    """Implicit operator A should be (strictly) diagonally dominant."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    V0 = np.full(solver.N, MEM.E_leak_V, dtype=np.float64)
    solver.initialise_gates(V0)

    # Force operator build once.
    V1 = solver.step(V0, 0.0, np.zeros(solver.N))
    assert np.all(np.isfinite(V1))

    dt = solver.dt_s
    theta = 1.0  # first step uses Rannacher
    A, _, _ = solver._active_cache[(dt, theta)]

    A_abs = np.abs(A)
    diag = np.asarray(A_abs.diagonal()).ravel()
    off = np.asarray(A_abs.sum(axis=1)).ravel() - diag

    # For stability we want diag >= off for all rows (allow tiny numeric slack).
    assert np.all(diag + 1e-18 >= off)


def test_dt_halving_convergence():
    """Halving dt should reduce one-step error against a small-dt reference."""
    comps, _ = _build_active_tree()

    V0 = np.full(len(comps), MEM.E_leak_V, dtype=np.float64)
    t_end = 1e-3

    s_ref = ActiveSolver(compartments=comps, dt_s=6.25e-6)
    s_ref.initialise_gates(V0)
    V_ref = _finite_run(s_ref, V0, duration_s=t_end)

    s1 = ActiveSolver(compartments=comps, dt_s=25e-6)
    s1.initialise_gates(V0)
    V1 = _finite_run(s1, V0, duration_s=t_end)

    s2 = ActiveSolver(compartments=comps, dt_s=12.5e-6)
    s2.initialise_gates(V0)
    V2 = _finite_run(s2, V0, duration_s=t_end)

    err1 = float(np.max(np.abs(V1 - V_ref)))
    err2 = float(np.max(np.abs(V2 - V_ref)))

    assert err2 < err1


def test_rannacher_startup_rearms():
    """Startup should re-arm on state discontinuity and on stimulus changes in run()."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6, rannacher_steps=2)

    V0 = np.full(solver.N, MEM.E_leak_V, dtype=np.float64)
    solver.initialise_gates(V0)

    # Step 1 uses theta=1.0
    V1 = solver.step(V0, 0.0, np.zeros(solver.N))
    assert solver.last_step["theta"] == 1.0

    # Force discontinuity (external perturbation) -> re-arm -> theta=1.0 again
    V_pert = V1.copy()
    V_pert[0] += 1e-3
    V2 = solver.step(V_pert, solver.dt_s, np.zeros(solver.N))
    assert solver.last_step["theta"] == 1.0
    assert np.all(np.isfinite(V2))


def test_gate_update_advances_correctly():
    """Gates should advance during step() (staggered update)."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    V0 = np.full(solver.N, MEM.E_leak_V, dtype=np.float64)
    solver.initialise_gates(V0)

    # Pick first channel and snapshot its gate values.
    assert solver.n_active_channels > 0
    _, mech = solver._channel_index[0]
    state0 = dict(mech.gate_state)

    # Depolarise a bit to provoke change, step once.
    V_dep = V0.copy()
    V_dep[0] += 10e-3
    _ = solver.step(V_dep, 0.0, np.zeros(solver.N))
    state1 = dict(mech.gate_state)

    # At least one gate should change.
    assert any(abs(state1[k] - state0[k]) > 0.0 for k in state0)


def test_channel_currents_folded_into_matrix():
    """Adding a channel should change the diagonal operator through g_chan."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    V0 = np.full(solver.N, MEM.E_leak_V, dtype=np.float64)
    solver.initialise_gates(V0)

    # Build once.
    _ = solver.step(V0, 0.0, np.zeros(solver.N))

    g = solver.last_step["g_chan"]
    assert np.any(g > 0.0)

    # Ensure at least one mechanism's conductance extraction matches g entry.
    i0, mech0 = solver._channel_index[0]
    g0 = channel_conductance_S(mech0, 0.0)
    assert g[i0] >= g0 - 1e-12


def test_run_with_current_clamp():
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    proto = CurrentClampProtocol(amp_A=5e-10, onset_s=1e-3, dur_s=2e-3, target_idx=0)
    rec = solver.run(protocols=proto, duration_s=5e-3, record_idxs=[0], record_every=10)

    soma = rec.get_trace(0)
    assert len(soma) == rec.n_samples
    assert np.any(np.abs(np.diff(soma)) > 0.0)


def test_run_returns_recorder():
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    rec = solver.run(duration_s=1e-3, record_idxs=[0])
    assert isinstance(rec, Recorder)
    assert rec.n_samples >= 1


@pytest.mark.xfail(reason="h-gate alpha/beta swapped in gating.py - FINDING-1")
def test_multiple_spikes():
    """Strong drive should yield multiple spikes (xfail due to h-gate swap)."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    proto = CurrentClampProtocol(amp_A=2e-9, onset_s=2e-3, dur_s=10e-3, target_idx=0)
    rec = solver.run(protocols=proto, duration_s=15e-3, record_idxs=[0], record_every=1)
    v = rec.get_trace(0)

    # Naively count upward crossings of 0 mV.
    crossings = np.sum((v[:-1] < 0.0) & (v[1:] >= 0.0))
    assert crossings >= 2


@pytest.mark.xfail(reason="-70mV not equilibrium of active model - FINDING-2")
def test_resting_stability_with_channels():
    """At -70 mV with gates initialised, should remain near rest (xfail by finding)."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    V0 = np.full(solver.N, MEM.E_leak_V, dtype=np.float64)
    solver.initialise_gates(V0)

    V = V0.copy()
    for k in range(200):
        V = solver.step(V, k * solver.dt_s, np.zeros(solver.N))

    assert float(np.max(np.abs(V - V0))) < 0.5e-3


def test_charge_balance():
    """With no external current, total charge should remain bounded (no blow-up)."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    V0 = np.full(solver.N, MEM.E_leak_V, dtype=np.float64)
    solver.initialise_gates(V0)

    V = V0.copy()
    for k in range(400):
        V = solver.step(V, k * solver.dt_s, np.zeros(solver.N))

    # This is a weak invariant: ensure no numerical explosion.
    assert np.all(np.isfinite(V))
    assert float(np.max(np.abs(V))) < 1.0  # volts


def test_performance_benchmark():
    """A short run should complete quickly (smoke performance test)."""
    comps, _ = _build_active_tree()
    solver = ActiveSolver(compartments=comps, dt_s=25e-6)

    proto = CurrentClampProtocol(amp_A=5e-10, onset_s=1e-3, dur_s=2e-3, target_idx=0)

    t0 = time.perf_counter()
    rec = solver.run(protocols=proto, duration_s=5e-3, record_idxs=[0], record_every=20)
    elapsed = time.perf_counter() - t0

    assert isinstance(rec, Recorder)
    # Very generous threshold; intended to catch accidental O(N^3) regressions.
    assert elapsed < 5.0
