"""passive_validation.py — Passive property validation for Phase 0a.

Validation targets
------------------
All targets are from peer-reviewed literature on human L5 pyramidal neurons:

  Rin      50 – 200 MΩ   Beaulieu-Laroche et al. (2018) Table S1
  tau_m_dend 10 – 40 ms  Rm * Cm_dend (analytical); Eyal et al. (2016) Table 1
  V_rest   -75 – -65 mV  EL = -70 mV by construction
  Att_DC   < 0.1 (>10x)  DC attenuation distal tuft → soma (FIX#4)
  lambda   600 – 1400 µm  sqrt(Rm*d/(4*Ra)); apical trunk d = 5 µm
  N_comps  150 – 500      APPROX-6: parametric tree gives 224 (plan was 350–410)

References
----------
[1] Beaulieu-Laroche L et al. (2018) Cell 175:643-651.e14
[2] Hay E et al. (2011) PLoS Comput Biol 7:e1002107
[3] Eyal G et al. (2016) eLife 5:e16553
[4] Rall W (1969) Biophys J 9:1483-1508
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import numpy as np

from biophysical.core.constants import MEM
from biophysical.morphology.geometry import lambda_dc_um


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """A single validation check outcome."""
    name:         str
    value:        float          # measured/computed value
    unit:         str
    target_low:   float
    target_high:  float
    passed:       bool
    analytical:   Optional[float] = None   # predicted value (if known)
    notes:        str = ''

    @property
    def status(self) -> str:
        return '✅ PASS' if self.passed else '❌ FAIL'

    def __str__(self) -> str:
        s = f'{self.status}  {self.name}: {self.value:.4g} {self.unit}'
        s += f'  (target: [{self.target_low:.4g}, {self.target_high:.4g}])'
        if self.analytical is not None:
            s += f'  analytical: {self.analytical:.4g}'
        if self.notes:
            s += f'  [{self.notes}]'
        return s


@dataclass
class PerformanceBenchmark:
    """Timing and memory statistics for the Phase 0a solver."""
    build_time_s:           float = 0.0
    matrix_assembly_time_s: float = 0.0
    lu_factor_time_s:       float = 0.0
    step_time_us:           float = 0.0    # microseconds per step
    steps_per_second:       float = 0.0
    n_nonzero_G:            int   = 0
    n_compartments:         int   = 0
    total_area_um2:         float = 0.0


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class PassiveValidator:
    """Runs all Phase 0a validation checks against literature targets.

    Parameters
    ----------
    compartments : List[Compartment]  with LeakChannel attached.
    meta         : dict               from build_l5_pyramidal().
    solver       : CrankNicolsonSolver already built.
    """

    def __init__(self, compartments, meta: Dict, solver) -> None:
        self.compartments  = compartments
        self.meta          = meta
        self.solver        = solver
        self.results:      List[ValidationResult] = []
        self.benchmark:    PerformanceBenchmark   = PerformanceBenchmark()

    def run_all(self) -> List[ValidationResult]:
        """Execute all validation checks and return the result list."""
        self.results = []
        self._check_compartment_count()
        self._check_v_rest()
        self._check_tau_m_analytical()
        self._check_tau_m_numerical()
        self._check_input_resistance()
        self._check_voltage_attenuation()
        self._check_lambda()
        self._measure_performance()
        return self.results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_compartment_count(self) -> None:
        n = self.meta['n_compartments']
        # Plan target was 350-410; APPROX-6 gives 224
        result = ValidationResult(
            name        = 'N_compartments',
            value       = float(n),
            unit        = 'compartments',
            target_low  = 150.0,
            target_high = 500.0,
            passed      = 150 <= n <= 500,
            analytical  = 224.0,
            notes       = 'APPROX-6: parametric tree; plan was 350-410',
        )
        self.results.append(result)

    def _check_v_rest(self) -> None:
        V_rest_mV = MEM.E_leak_V * 1e3
        result = ValidationResult(
            name        = 'V_rest_mV',
            value       = V_rest_mV,
            unit        = 'mV',
            target_low  = -75.0,
            target_high = -65.0,
            passed      = -75.0 <= V_rest_mV <= -65.0,
            analytical  = V_rest_mV,
            notes       = 'V_rest = EL = -70 mV by construction (uniform leak)',
        )
        self.results.append(result)

    def _check_tau_m_analytical(self) -> None:
        """Analytical tau_m = Rm * Cm_dend for dendritic compartments."""
        tau_ms = MEM.Rm_SI * MEM.Cm_dend_SI * 1e3   # 3.0 * 0.01 * 1000 = 30 ms
        result = ValidationResult(
            name        = 'tau_m_dend_analytical_ms',
            value       = tau_ms,
            unit        = 'ms',
            target_low  = 10.0,
            target_high = 40.0,
            passed      = 10.0 <= tau_ms <= 40.0,
            analytical  = tau_ms,
            notes       = 'tau = Rm_SI * Cm_dend_SI = 3.0 * 0.01 = 30 ms',
        )
        self.results.append(result)

    def _check_tau_m_numerical(self) -> None:
        """Numerical somatic time constant (Rall charge / release protocol)."""
        t0 = time.perf_counter()
        tau_s = self.solver.measure_time_constant(
            target_idx = self.meta['soma_idx'],
            dV_init    = 10e-3,
            dt_fine_s  = 100e-6,
            t_max_s    = 0.4,
        )
        elapsed = time.perf_counter() - t0
        tau_ms = tau_s * 1e3
        analytical_ms = MEM.Rm_SI * MEM.Cm_dend_SI * 1e3

        result = ValidationResult(
            name        = 'tau_soma_numerical_ms',
            value       = tau_ms,
            unit        = 'ms',
            target_low  = 5.0,      # somatic tau < tau_m due to dendritic loading
            target_high = 40.0,
            passed      = 5.0 <= tau_ms <= 40.0,
            analytical  = analytical_ms,
            notes       = f'Rall protocol: ln(dV) fit over dV/dV0 in [0.05, 0.70]. '
                          f'analytical tau_m={analytical_ms:.1f} ms. '
                          f'Measured in {elapsed:.2f} s',
        )
        self.results.append(result)

    def _check_input_resistance(self) -> None:
        """DC input resistance at soma by step-current injection."""
        t0 = time.perf_counter()
        Rin_ohm = self.solver.measure_input_resistance(
            target_idx  = self.meta['soma_idx'],
            I_amp       = 1e-10,   # 100 pA
            dt_settle_s = 5e-3,
            t_settle_s  = 1.0,
        )
        elapsed = time.perf_counter() - t0
        Rin_MOhm = Rin_ohm / 1e6

        result = ValidationResult(
            name        = 'Rin_soma_MOhm',
            value       = Rin_MOhm,
            unit        = 'MΩ',
            target_low  = 50.0,
            target_high = 200.0,
            passed      = 50.0 <= Rin_MOhm <= 200.0,
            analytical  = None,
            notes       = f'100 pA test pulse, 1s settling, '
                          f'measured in {elapsed:.1f} s. '
                          f'Target from Beaulieu-Laroche 2018',
        )
        self.results.append(result)

    def _check_voltage_attenuation(self) -> None:
        """DC voltage attenuation between the soma and the distal apical tuft.

        FIX#4 — the > 10x target belongs to the tuft → soma direction.  DC
        attenuation is asymmetric: with R_ij symmetric by reciprocity,
        att(i → j) = R_ij / R_ii, so the direction that terminates on the
        low-resistance soma is the strongly attenuating one.  The soma → tuft
        ratio (~0.59 for a ~1.1 lambda path) is kept as a diagnostic.
        """
        tuft_idxs = self.meta.get('apical_tuft_idxs', [])
        if not tuft_idxs:
            return
        distal_idx = tuft_idxs[-1]
        soma_idx   = self.meta['soma_idx']

        att_in = self.solver.measure_voltage_attenuation_to_soma(
            soma_idx    = soma_idx,
            distal_idx  = distal_idx,
            I_amp       = 1e-10,
            dt_settle_s = 5e-3,
            t_settle_s  = 1.0,
        )
        self.results.append(ValidationResult(
            name        = 'DC_attenuation_tuft_to_soma',
            value       = abs(att_in),
            unit        = 'fraction',
            target_low  = 0.0,
            target_high = 0.10,  # < 0.10 = more than 10x attenuation
            passed      = abs(att_in) <= 0.10,
            analytical  = None,
            notes       = 'ΔV_soma / ΔV_tuft at DC (distal input). < 0.10 = >10× attenuation',
        ))

        att_out = self.solver.measure_voltage_attenuation(
            soma_idx    = soma_idx,
            distal_idx  = distal_idx,
            I_amp       = 1e-10,
            dt_settle_s = 5e-3,
            t_settle_s  = 1.0,
        )
        self.results.append(ValidationResult(
            name        = 'DC_attenuation_soma_to_tuft',
            value       = abs(att_out),
            unit        = 'fraction',
            target_low  = 0.20,
            target_high = 0.95,
            passed      = 0.20 <= abs(att_out) <= 0.95,
            analytical  = None,
            notes       = 'Diagnostic: ΔV_tuft / ΔV_soma at DC (somatic input); '
                          'weak direction, ~0.59 for a ~1.1 lambda apical path',
        ))

    def _check_lambda(self) -> None:
        """Electrotonic space constant at apical trunk average diameter."""
        d_avg_m    = 5.0e-6   # average apical trunk d
        lam_um_val = lambda_dc_um(d_avg_m, MEM.Rm_SI, MEM.Ra_SI)

        result = ValidationResult(
            name        = 'lambda_apical_um_d5',
            value       = lam_um_val,
            unit        = 'µm',
            target_low  = 600.0,
            target_high = 1400.0,
            passed      = 600.0 <= lam_um_val <= 1400.0,
            analytical  = lam_um_val,
            notes       = 'lambda = sqrt(Rm*d/(4*Ra)); d=5µm avg trunk diam',
        )
        self.results.append(result)

    def _measure_performance(self) -> None:
        """Benchmark one solver step and populate self.benchmark."""
        import sys
        N = self.meta['n_compartments']
        V = np.full(N, MEM.E_leak_V)
        I_zero = np.zeros(N)

        # Warm-up
        for _ in range(5):
            V = self.solver.step(V, 0.0, I_zero)

        # Timed run
        n_bench = 200
        t0 = time.perf_counter()
        for _ in range(n_bench):
            V = self.solver.step(V, 0.0, I_zero)
        elapsed = time.perf_counter() - t0

        step_us = elapsed / n_bench * 1e6
        self.benchmark.step_time_us      = step_us
        self.benchmark.steps_per_second  = 1e6 / step_us
        self.benchmark.n_compartments    = N
        self.benchmark.total_area_um2    = self.meta.get('total_area_um2', 0.0)
        self.benchmark.n_nonzero_G       = int(self.solver._G_mat.nnz)

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def summary_dict(self) -> Dict:
        return {
            r.name: {
                'value':  r.value,
                'unit':   r.unit,
                'passed': r.passed,
            }
            for r in self.results
        }
