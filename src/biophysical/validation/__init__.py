"""validation — Passive electrophysiology validation protocols.

All measurements use current-clamp electrode protocols matching standard
experimental practice (Beaulieu-Laroche et al. 2018; Eyal et al. 2016).

Protocols
---------
PassiveValidator.measure_resting_potential(cell)
    Zero-current steady state at soma.
    Target: -70 +/- 5 mV  [Beaulieu-Laroche et al. 2018, Table 1]

PassiveValidator.measure_input_resistance(cell, I_pA=-100.0)
    Hyperpolarising step 500 ms; steady-state deltaV / I_inj.
    Target: 50-200 MOhm   [Eyal et al. 2016; human L2/3 & L5]

PassiveValidator.measure_time_constant(cell, I_pA=-100.0)
    Single-exponential fit to voltage decay after step removal.
    Target: 10-30 ms      [Beaulieu-Laroche et al. 2018]

PassiveValidator.measure_voltage_attenuation(cell)
    Soma deltaV / distal apical tuft deltaV.
    Target: ratio < 0.10  (> 10x attenuation, Hay et al. 2011 Fig 4)

ValidationReport
    Collects results and renders a PASS/FAIL table.
"""

from biophysical.validation.passive_validation import PassiveValidator
from biophysical.validation.report import ValidationReport

__all__ = ["PassiveValidator", "ValidationReport"]
