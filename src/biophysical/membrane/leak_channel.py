"""leak_channel.py — Ohmic leak: background membrane conductance.

Current formula  (inward-positive sign convention)
---------------------------------------------------
    I_leak = -gL * (V - EL)     [A m^-2]

where:
    gL = 1 / Rm_SI     specific conductance  S m^-2
    EL = -70 mV        reversal potential    V

Sign check:
    V > EL  (depolarised)   -> I < 0  outward, repolarising  (correct)
    V < EL  (hyperpolarised)-> I > 0  inward,  depolarising  (correct)
    V = EL                  -> I = 0  steady state            (correct)

Linearity: is_linear = True.  The solver folds gL*V into the G-matrix
diagonal and gL*EL into the RHS vector b, giving a fully implicit CN scheme.

References
----------
[1] Koch C (1999) Biophysics of Computation. OUP  Ch. 2
[2] Eyal G et al. (2016) eLife 5:e16553  gL from Rm = 15 000 Ohm.cm^2
[3] Beaulieu-Laroche et al. (2018) Cell 175:643-651
"""

from __future__ import annotations
from typing import Any, Dict
from biophysical.core.interfaces import AbstractMembraneMechanism
from biophysical.core.constants import MEM


class LeakChannel(AbstractMembraneMechanism):
    """Ohmic leak: I_leak = -gL * (V - EL)  [A m^-2].

    Parameters
    ----------
    gL_SI : float  specific conductance  S m^-2.   Default = 1/Rm_SI.
    EL_V  : float  reversal potential    V.         Default = E_leak_V (-70 mV).
    """

    def __init__(
        self,
        gL_SI: float = 1.0 / MEM.Rm_SI,
        EL_V:  float = MEM.E_leak_V,
    ) -> None:
        self.gL_SI = float(gL_SI)
        self.EL_V  = float(EL_V)

    # ------------------------------------------------------------------ #
    # AbstractMembraneMechanism
    # ------------------------------------------------------------------ #

    def current(self, V: float, t: float) -> float:
        """I_leak = -gL * (V - EL)  [A m^-2].  Inward-positive."""
        return -self.gL_SI * (V - self.EL_V)

    def update_state(self, V: float, t: float, dt: float) -> None:
        """No-op: passive leak has no gating variables."""

    @property
    def is_linear(self) -> bool:
        """True: current is linear in V -> folds into conductance matrix G."""
        return True

    @property
    def conductance_density(self) -> float:
        """gL in S m^-2."""
        return self.gL_SI

    @property
    def reversal_potential(self) -> float:
        """EL in V."""
        return self.EL_V

    # ------------------------------------------------------------------ #
    # BiophysComponent
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return 'LeakChannel'

    def state_dict(self) -> Dict[str, Any]:
        return {
            'gL_S_m2':   self.gL_SI,
            'EL_mV':     self.EL_V * 1e3,
            'Rm_ohm_m2': 1.0 / self.gL_SI,
        }

    def reset(self) -> None:
        """No internal state to reset."""
