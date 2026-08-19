"""test_resting_potential.py — Tests for resting-state computation.

Covers:
  analytical_resting_potential_V()  — must equal EL = -70 mV
  set_resting_state(compartments)   — sets V = EL on all compartments
  compute_resting_potential()        — analytical and numerical paths
  CrankNicolsonSolver.steady_state() — must converge to EL within 1 µV
"""

import numpy as np
import pytest
from biophysical.membrane.resting_state import (
    analytical_resting_potential_V,
    set_resting_state,
    compute_resting_potential,
)
from biophysical.core.constants import MEM


# ---- Shared fixtures -------------------------------------------------------

@pytest.fixture(scope='module')
def passive_compartments():
    from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
    comps, meta = build_l5_pyramidal(apply_bilayer=True)
    return comps, meta


@pytest.fixture(scope='module')
def solver(passive_compartments):
    from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
    comps, _ = passive_compartments
    return CrankNicolsonSolver(comps, dt_s=1e-3)


# ---- Analytical resting potential ------------------------------------------

class TestAnalyticalRestingPotential:
    """analytical_resting_potential_V() -> float."""

    def test_equals_MEM_EL(self):
        V = analytical_resting_potential_V()
        assert abs(V - MEM.E_leak_V) < 1e-20, (
            f'V_rest = {V*1e3:.4f} mV, expected {MEM.E_leak_V*1e3:.4f} mV'
        )

    def test_is_minus_70mV(self):
        V_mV = analytical_resting_potential_V() * 1e3
        assert abs(V_mV + 70.0) < 1e-10, (
            f'V_rest = {V_mV:.4f} mV, expected -70.0 mV'
        )

    def test_type_is_float(self):
        V = analytical_resting_potential_V()
        assert isinstance(V, float)

    def test_within_physiological_range(self):
        V_mV = analytical_resting_potential_V() * 1e3
        assert -90 <= V_mV <= -55, (
            f'V_rest = {V_mV:.1f} mV outside physiological range [-90, -55] mV'
        )


# ---- set_resting_state -----------------------------------------------------

class TestSetRestingState:
    """set_resting_state(compartments) should set V = EL on all."""

    def test_overwrites_nonzero_voltages(self):
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=False)
        # Disturb all voltages
        for c in comps:
            c.V = 0.0
        # Restore resting state
        set_resting_state(comps)
        # Verify
        for c in comps:
            assert abs(c.V - MEM.E_leak_V) < 1e-20, (
                f'comp {c.idx}: V = {c.V*1e3:.4f} mV after set_resting_state(), '
                f'expected {MEM.E_leak_V*1e3:.4f} mV'
            )

    def test_idempotent(self):
        """Calling twice gives same result."""
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=False)
        set_resting_state(comps)
        V1 = [c.V for c in comps]
        set_resting_state(comps)
        V2 = [c.V for c in comps]
        assert V1 == V2


# ---- compute_resting_potential ---------------------------------------------

class TestComputeRestingPotential:
    """compute_resting_potential(compartments, solver=None) -> np.ndarray."""

    def test_analytical_path_returns_EL_everywhere(self, passive_compartments):
        comps, _ = passive_compartments
        V = compute_resting_potential(comps, solver=None)
        assert V.shape == (len(comps),)
        assert np.allclose(V, MEM.E_leak_V, atol=1e-20), (
            f'Max deviation from EL = {np.max(np.abs(V - MEM.E_leak_V))*1e3:.4f} mV'
        )

    def test_returns_ndarray(self, passive_compartments):
        comps, _ = passive_compartments
        V = compute_resting_potential(comps, solver=None)
        assert isinstance(V, np.ndarray)

    def test_length_equals_n_compartments(self, passive_compartments):
        comps, _ = passive_compartments
        V = compute_resting_potential(comps, solver=None)
        assert len(V) == len(comps)


# ---- Numerical convergence -------------------------------------------------

class TestNumericalSteadyState:
    """CN solver steady_state() must converge to EL within 1 µV."""

    def test_steady_state_converges_to_EL(self, solver, passive_compartments):
        comps, _ = passive_compartments
        V_ss = solver.steady_state(dt_settle_s=5e-3, t_settle_s=1.0)
        max_err_V  = float(np.max(np.abs(V_ss - MEM.E_leak_V)))
        max_err_uV = max_err_V * 1e6
        assert max_err_uV < 1.0, (
            f'Max deviation from EL after steady-state = {max_err_uV:.3f} µV '
            f'(tolerance: 1 µV)'
        )

    def test_steady_state_uniform_across_all_compartments(self, solver, passive_compartments):
        comps, _ = passive_compartments
        V_ss = solver.steady_state(dt_settle_s=5e-3, t_settle_s=1.0)
        # At rest with no current, all compartments should be at EL
        V_range_uV = (V_ss.max() - V_ss.min()) * 1e6
        assert V_range_uV < 1.0, (
            f'Voltage spread across compartments at rest = {V_range_uV:.3f} µV '
            f'(all should be identical at EL)'
        )

    def test_step_from_perturbation_returns_to_EL(self, solver, passive_compartments):
        """Single +10 mV perturbation decays back to EL."""
        comps, meta = passive_compartments
        N = len(comps)
        V = np.full(N, MEM.E_leak_V)
        V[meta['soma_idx']] += 10e-3   # perturb soma
        I_zero = np.zeros(N)
        # Run 500 ms (500 steps at dt=1ms)
        for _ in range(500):
            V = solver.step(V, 0.0, I_zero)
        V_final_mV = V[meta['soma_idx']] * 1e3
        V_rest_mV  = MEM.E_leak_V * 1e3
        assert abs(V_final_mV - V_rest_mV) < 0.01, (
            f'Soma V after 500 ms = {V_final_mV:.4f} mV, '
            f'expected {V_rest_mV:.4f} mV'
        )
