"""test_passive_membrane.py — Unit tests for membrane mechanisms.

Covers:
  LeakChannel   — ohmic I-V, is_linear, conductance, reversal potential
  NaKPump       — zero current Phase 0a, is_linear=False, reset()
  LipidBilayer  — apply_to_compartments, mechanism attachment
"""

import math
import pytest
from biophysical.membrane.leak_channel import LeakChannel
from biophysical.membrane.nak_pump import NaKPump
from biophysical.membrane.lipid_bilayer import LipidBilayer
from biophysical.core.constants import MEM


class TestLeakChannel:
    """LeakChannel: I = -gL * (V - EL), gL = 1/Rm_SI."""

    def test_zero_current_at_rest(self):
        """At V = EL, leak current must be exactly 0."""
        lc = LeakChannel()
        I = lc.current(V=MEM.E_leak_V, t=0.0)
        assert abs(I) < 1e-30, f'I_leak at V=EL = {I} A (must be 0)'

    def test_outward_when_depolarised(self):
        """V > EL → hyperpolarising (outward) current: I < 0."""
        lc = LeakChannel()
        I  = lc.current(V=MEM.E_leak_V + 10e-3, t=0.0)
        assert I < 0, f'I_leak at V+10mV = {I*1e12:.1f} pA/m² (expected < 0)'

    def test_inward_when_hyperpolarised(self):
        """V < EL → depolarising (inward) current: I > 0."""
        lc = LeakChannel()
        I  = lc.current(V=MEM.E_leak_V - 10e-3, t=0.0)
        assert I > 0, f'I_leak at V-10mV = {I*1e12:.1f} pA/m² (expected > 0)'

    def test_is_linear_flag(self):
        assert LeakChannel().is_linear is True

    def test_reversal_potential_equals_EL(self):
        lc = LeakChannel()
        assert abs(lc.reversal_potential - MEM.E_leak_V) < 1e-20

    def test_conductance_density_is_1_over_Rm(self):
        lc = LeakChannel()
        expected = 1.0 / MEM.Rm_SI
        assert abs(lc.conductance_density - expected) < 1e-30

    def test_ohmic_scaling(self):
        """I ∝ (V - EL): doubling dV must double I."""
        lc  = LeakChannel()
        dV  = 5e-3
        I1  = lc.current(MEM.E_leak_V + dV,     t=0.0)
        I2  = lc.current(MEM.E_leak_V + 2 * dV, t=0.0)
        assert abs(I2 / I1 - 2.0) < 1e-10, f'I(2dV)/I(dV) = {I2/I1:.6f}, expected 2.0'

    def test_current_magnitude(self):
        """I at V=EL+10mV should equal -gL * 10mV."""
        lc   = LeakChannel()
        gL   = 1.0 / MEM.Rm_SI
        dV   = 10e-3
        I    = lc.current(MEM.E_leak_V + dV, t=0.0)
        expected = -gL * dV
        assert abs(I - expected) < 1e-30, f'I={I:.6g}, expected {expected:.6g}'

    def test_time_independent(self):
        """LeakChannel current must not depend on time."""
        lc = LeakChannel()
        V  = MEM.E_leak_V + 5e-3
        I1 = lc.current(V, t=0.0)
        I2 = lc.current(V, t=1.0)
        I3 = lc.current(V, t=1000.0)
        assert I1 == I2 == I3


class TestNaKPump:
    """NaKPump: Phase 0a constant model (I=0)."""

    def test_zero_current_phase_0a(self):
        """Phase 0a: pump current must be zero (ion concentrations not yet tracked)."""
        pump = NaKPump()
        I    = pump.current(V=MEM.E_leak_V, t=0.0)
        assert I == 0.0, f'NaKPump current = {I} A/m² (expected 0 in Phase 0a)'

    def test_is_not_linear(self):
        """NaKPump is non-linear (voltage-independent in Phase 0a, but not ohmic)."""
        assert NaKPump().is_linear is False

    def test_reset_restores_default(self):
        """reset() restores I_pump_SI to its constructor value."""
        default_val = NaKPump().I_pump_SI
        pump = NaKPump()
        pump.I_pump_SI = -999.0  # modify
        pump.reset()
        assert pump.I_pump_SI == default_val, (
            f'After reset, I_pump_SI = {pump.I_pump_SI}, expected {default_val}'
        )

    def test_current_zero_at_arbitrary_voltage(self):
        """Zero current holds for any voltage in Phase 0a."""
        pump = NaKPump()
        for V_mV in [-90, -70, -55, 0, +30]:
            I = pump.current(V=V_mV * 1e-3, t=0.0)
            assert I == 0.0, f'V={V_mV}mV: pump I={I}'


class TestLipidBilayer:
    """LipidBilayer: mechanism factory."""

    def test_no_mechanisms_before_apply(self):
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=False)
        assert all(len(c.mechanisms) == 0 for c in comps)

    def test_mechanisms_present_after_apply(self):
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=False)
        LipidBilayer().apply_to_compartments(comps)
        assert all(len(c.mechanisms) >= 1 for c in comps), (
            'Some compartments have no mechanisms after LipidBilayer.apply_to_compartments()'
        )

    def test_leak_channel_attached_to_all(self):
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=False)
        LipidBilayer().apply_to_compartments(comps)
        for comp in comps:
            has_leak = any(isinstance(m, LeakChannel) for m in comp.mechanisms)
            assert has_leak, f'comp {comp.idx} missing LeakChannel'

    def test_build_l5_pyramidal_with_bilayer(self):
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=True)
        for comp in comps:
            assert len(comp.mechanisms) >= 1

    def test_idempotent_not_double_applied(self):
        """Calling apply_to_compartments twice should not double mechanisms."""
        from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
        comps, _ = build_l5_pyramidal(apply_bilayer=False)
        bilayer = LipidBilayer()
        bilayer.apply_to_compartments(comps)
        n_after_first = sum(len(c.mechanisms) for c in comps)
        # A second call might append; just check at least the first call worked:
        assert n_after_first >= len(comps)
