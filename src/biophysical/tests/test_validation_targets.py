"""test_validation_targets.py — Integration tests for Phase 0a validation targets.

These tests mirror the PassiveValidator checks exactly.  They MUST all pass
before Phase 0b begins (per user requirement #1).

All numerical targets are from peer-reviewed literature:
  Rin      : 50–200 MΩ    Beaulieu-Laroche et al. (2018) Cell 175:643
  tau_m    : 10–40 ms      Eyal et al. (2016) eLife 5:e16553
  V_rest   : −75 – −65 mV  Construction target
  DC_att   : < 0.10        Hay et al. (2011) PLoS Comput Biol 7:e1002107
  lambda   : 600–1400 µm   Koch (1999) Biophysics of Computation Ch. 6
  N_comps  : 150–500       APPROX-6 accepted range
"""

import numpy as np
import pytest
from biophysical.core.constants import MEM
from biophysical.morphology.l5_pyramidal_data import EXPECTED_N_COMPS


# ---- Shared module-scope fixture -------------------------------------------
# (Scope = module so the cell is built only once; build+factorize takes ~100 ms)

@pytest.fixture(scope='module')
def cell():
    from biophysical.neuron_cell import NeuronCell
    c = NeuronCell(dt_s=25e-6)
    c.build()
    return c


@pytest.fixture(scope='module')
def validation_summary(cell):
    return cell.validate()


# ---- Morphology targets ---------------------------------------------------

class TestMorphologyTargets:
    def test_compartment_count_lower_bound(self, cell):
        assert cell.n_compartments >= 150, (
            f'N={cell.n_compartments} < 150 (lower bound)'
        )

    def test_compartment_count_upper_bound(self, cell):
        assert cell.n_compartments <= 500, (
            f'N={cell.n_compartments} > 500 (upper bound)'
        )

    def test_compartment_count_matches_expected(self, cell):
        assert cell.n_compartments == EXPECTED_N_COMPS, (
            f'N={cell.n_compartments}, EXPECTED_N_COMPS={EXPECTED_N_COMPS}'
        )

    def test_total_area_plausible(self, cell):
        area_um2 = cell.total_area_um2
        assert 5_000 < area_um2 < 50_000, (
            f'Total area = {area_um2:.0f} µm² outside [5000, 50000]'
        )


# ---- Analytical targets (no simulation needed) ----------------------------

class TestAnalyticalTargets:
    def test_v_rest_equals_minus_70mV(self):
        V_mV = MEM.E_leak_V * 1e3
        assert -75.0 <= V_mV <= -65.0, (
            f'EL = {V_mV:.2f} mV, must be in [−75, −65] mV'
        )

    def test_tau_m_dend_in_range(self):
        tau_ms = MEM.Rm_SI * MEM.Cm_dend_SI * 1e3
        assert 10.0 <= tau_ms <= 40.0, (
            f'tau_m = {tau_ms:.1f} ms outside [10, 40] ms'
        )

    def test_tau_m_dend_is_30ms(self):
        tau_ms = MEM.Rm_SI * MEM.Cm_dend_SI * 1e3
        # Rm=1.5 Om^2, Cm=0.02 F/m^2 => 30 ms
        assert abs(tau_ms - 30.0) < 0.01, (
            f'tau_m = {tau_ms:.3f} ms, expected 30.0 ms'
        )

    def test_lambda_apical_trunk_d5um(self):
        from biophysical.morphology.geometry import lambda_dc_um
        lam = lambda_dc_um(5e-6, MEM.Rm_SI, MEM.Ra_SI)
        assert 600.0 <= lam <= 1400.0, (
            f'lambda(d=5µm) = {lam:.0f} µm outside [600, 1400] µm'
        )

    def test_lambda_apical_trunk_all_diameters(self):
        from biophysical.morphology.geometry import lambda_dc_um
        # Apical trunk d tapers 8 -> 2 µm; all values should be in range
        for d_um in [2, 3, 4, 5, 6, 7, 8]:
            lam = lambda_dc_um(d_um * 1e-6, MEM.Rm_SI, MEM.Ra_SI)
            assert lam > 400, (
                f'd={d_um}µm: lambda={lam:.0f}µm too short (expected > 400 µm)'
            )


# ---- Numerical targets (require simulation) --------------------------------

class TestNumericalTargets:
    def test_resting_voltage_uniform(self, cell):
        """All compartments at EL after steady-state."""
        V_ss = cell.solver.steady_state(dt_settle_s=5e-3, t_settle_s=1.0)
        max_err_mV = float(np.max(np.abs(V_ss - MEM.E_leak_V))) * 1e3
        assert max_err_mV < 0.01, (
            f'Resting V spread = {max_err_mV:.4f} mV (tolerance 0.01 mV)'
        )

    def test_input_resistance_lower_bound(self, cell):
        Rin_ohm = cell.solver.measure_input_resistance(
            target_idx  = cell.soma_idx,
            I_amp       = 1e-10,
            dt_settle_s = 5e-3,
            t_settle_s  = 1.0,
        )
        Rin_MOhm = Rin_ohm / 1e6
        assert Rin_MOhm >= 50.0, (
            f'Rin = {Rin_MOhm:.1f} MΩ < 50 MΩ lower bound'
        )

    def test_input_resistance_upper_bound(self, cell):
        Rin_ohm = cell.solver.measure_input_resistance(
            target_idx  = cell.soma_idx,
            I_amp       = 1e-10,
            dt_settle_s = 5e-3,
            t_settle_s  = 1.0,
        )
        Rin_MOhm = Rin_ohm / 1e6
        assert Rin_MOhm <= 200.0, (
            f'Rin = {Rin_MOhm:.1f} MΩ > 200 MΩ upper bound'
        )

    def test_somatic_time_constant_in_range(self, cell):
        tau_s = cell.solver.measure_time_constant(
            target_idx = cell.soma_idx,
            dV_init    = 10e-3,
            dt_fine_s  = 100e-6,
            t_max_s    = 0.3,
        )
        tau_ms = tau_s * 1e3
        assert 5.0 <= tau_ms <= 40.0, (
            f'Somatic tau = {tau_ms:.1f} ms outside [5, 40] ms'
        )

    def test_dc_voltage_attenuation_soma_to_tuft(self, cell):
        tuft_idxs = cell.meta.get('apical_tuft_idxs', [])
        if not tuft_idxs:
            pytest.skip('No apical tuft compartments in this build')
        att = cell.solver.measure_voltage_attenuation(
            soma_idx   = cell.soma_idx,
            distal_idx = tuft_idxs[-1],
            I_amp      = 1e-10,
        )
        assert abs(att) <= 0.10, (
            f'DC attenuation (soma → tuft) = {att:.4f} '
            f'(need ≤ 0.10, i.e. ≥ 10× attenuation)'
        )


# ---- Passive recording sanity check ----------------------------------------

class TestPassiveSimulation:
    def test_passive_run_returns_recorder(self, cell):
        from biophysical.simulation.recorder import Recorder
        rec = cell.run(t_max_s=0.1, soma_amp_A=0.0, record_every=100)
        assert isinstance(rec, Recorder)
        assert rec.n_samples > 0

    def test_passive_soma_voltage_stays_at_rest(self, cell):
        rec = cell.run(t_max_s=0.1, soma_amp_A=0.0, record_every=100)
        soma_mV = rec.traces_mV().get('soma', None)
        if soma_mV is None:
            pytest.skip('soma label not in recorder')
        assert np.all(np.abs(soma_mV + 70.0) < 0.1), (
            f'Soma V during passive run: max dev = '
            f'{np.max(np.abs(soma_mV + 70.0)):.4f} mV'
        )


# ---- Full validation suite pass ------------------------------------------

class TestFullValidationSuite:
    def test_all_validation_checks_pass(self, validation_summary):
        """Master test: ALL Phase 0a validation checks must pass."""
        failed = [
            f'{r.name}: {r.value:.4g} {r.unit} '
            f'(target [{r.target_low:.4g}, {r.target_high:.4g}])'
            for r in validation_summary.results
            if not r.passed
        ]
        assert not failed, (
            f'The following {len(failed)} validation checks FAILED:\n' +
            '\n'.join(f'  ❌ {f}' for f in failed)
        )

    def test_report_is_non_empty_string(self, validation_summary):
        report = str(validation_summary)
        assert isinstance(report, str)
        assert len(report) > 500, 'Validation report is suspiciously short'

    def test_n_passed_equals_n_total(self, validation_summary):
        assert validation_summary.n_passed() == validation_summary.n_total(), (
            f'Only {validation_summary.n_passed()}/{validation_summary.n_total()} '
            f'checks passed'
        )
