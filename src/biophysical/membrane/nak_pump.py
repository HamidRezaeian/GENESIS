"""nak_pump.py — Na+/K+ ATPase pump  (Phase 0a: constant current model).

Stoichiometry:  3 Na+ out  /  2 K+ in  per ATP  -> net outward current

Phase 0a approximation
-----------------------
I_pump = 0 A m^-2.  The pump's steady-state contribution to V_rest is
absorbed into E_leak = -70 mV.  This is valid for Phase 0a because we only
need passive cable properties; V_rest is set by EL directly.

Phase 0g replacement  (full kinetic Post-Albers model)
-------------------------------------------------------
The 6-state Post-Albers cycle:
    E1   + 3 Na+_i + ATP  ->  E1-3Na (phosphorylation)
    E1-3Na              ->  E2P-3Na (conformational change)
    E2P-3Na             ->  E2P + 3 Na+_o (Na+ release)
    E2P  + 2 K+_o       ->  E2P-2K (K+ binding)
    E2P-2K              ->  E2-2K  (dephosphorylation)
    E2-2K               ->  E1 + 2 K+_i (K+ release)

Current = 1 * (net charge moved per cycle) * cycling_rate * F
Accounts for ~50% of neuronal ATP consumption (Attwell & Laughlin 2001).

References
----------
[1] De Weer P et al. (1988) Annu Rev Physiol 50:225-241
[2] Attwell D, Laughlin SB (2001) J Cereb Blood Flow Metab 21:1133-1145
[3] Bhalla US (2004) Neural Comput 16:2211-2241
[4] Hille B (2001) Ion Channels of Excitable Membranes. 3rd ed. Sinauer
"""

from __future__ import annotations
from typing import Any, Dict
from biophysical.core.interfaces import AbstractMembraneMechanism


class NaKPump(AbstractMembraneMechanism):
    """Na+/K+ ATPase: constant outward current density (Phase 0a model).

    Parameters
    ----------
    I_pump_SI : float  pump current density A m^-2.
                       Outward (hyperpolarising) -> I_pump_SI <= 0.
                       Default = 0.0 (Phase 0a: effect absorbed into EL).
    """

    def __init__(self, I_pump_SI: float = 0.0) -> None:
        self._I0 = float(I_pump_SI)
        self.I_pump_SI = float(I_pump_SI)

    def current(self, V: float, t: float) -> float:
        """Constant pump current density A m^-2. Inward-positive convention.

        Phase 0a: voltage-independent, ATP-independent constant.
        Phase 0g: will depend on V, [Na+]_i, [K+]_o, [ATP].
        """
        return self.I_pump_SI

    def update_state(self, V: float, t: float, dt: float) -> None:
        """No state variables in the Phase 0a constant model."""

    @property
    def is_linear(self) -> bool:
        """False: constant current is not linear in V.

        With I_pump_SI = 0 (Phase 0a), this mechanism contributes nothing.
        When non-zero it is added as a constant term in the RHS vector b.
        """
        return False

    @property
    def name(self) -> str:
        return 'NaKPump'

    def state_dict(self) -> Dict[str, Any]:
        return {
            'I_pump_A_m2':   self.I_pump_SI,
            'I_pump_pA_um2': self.I_pump_SI * 1e-12 / 1e-12,
            'model':         'Phase-0a-constant',
        }

    def reset(self) -> None:
        """Restore pump current to initial value."""
        self.I_pump_SI = self._I0
