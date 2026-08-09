"""base_channel.py — Partial concrete ABC for all voltage-gated ion channels.

VoltageGatedChannel inherits from AbstractVoltageGatedChannel and provides:
  - Storage for gbar_SI and E_rev_V
  - Concrete current() formula:  I = −gbar × open_fraction × (V − E_rev)
  - is_linear = False  (non-linear → not folded into G matrix)
  - conductance_density = 0.0  (non-linear channels not in G assembly)
  - reversal_potential from E_rev_V

Subclasses (NaV16Channel, KvChannel, ...) must implement:
  _open_fraction()      product of all gate contributions
  update_state()        advance gating variables one timestep
  gate_state            property: {gate_name: current_value}
  set_steady_state()    initialise gates to V steady-state values
  name                  str identifier
  state_dict()          JSON-serialisable state snapshot
  reset()               restore to t=0 initial conditions

Phase 0e hook
-------------
Subclasses receive gbar_SI at construction time.  In Phase 0e, a
DensityProvider (mRNA → protein → gbar) will compute gbar per compartment
and inject it at build time.  No changes to VoltageGatedChannel needed.

Sign convention
---------------
Positive current density = inward = depolarising  (same as LeakChannel).

    I = −gbar × open_fraction × (V − E_rev)

Sign checks:
  Na at rest (V ≈ −70 mV, E_Na ≈ +72 mV):  V − E_Na = −0.142 V
    I = −gbar × p × (−0.142) > 0  (inward, depolarising) ✓
  K repolarisation (V ≈ +30 mV, E_K ≈ −95 mV): V − E_K = +0.125 V
    I = −gbar × p × (+0.125) < 0  (outward, repolarising) ✓
  At Nernst: V = E_rev → I = 0 ✓

References
----------
[MS96] Mainen ZF, Sejnowski TJ (1996) J Neurophysiol 76:1329–1338
[H11]  Hay E et al. (2011) PLoS Comput Biol 7:e1002107
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict

from biophysical.core.interfaces import AbstractVoltageGatedChannel


class VoltageGatedChannel(AbstractVoltageGatedChannel):
    """Partial concrete ABC for voltage-gated ion channels.

    Provides the universal current formula and property storage.
    Subclasses must implement the gate-specific methods listed below.

    Parameters
    ----------
    gbar_SI : float   maximum conductance density  [S m⁻²]
    E_rev_V : float   reversal (Nernst) potential  [V]
    """

    def __init__(self, gbar_SI: float, E_rev_V: float) -> None:
        self._gbar_SI = float(gbar_SI)
        self._E_rev_V = float(E_rev_V)

    # ------------------------------------------------------------------
    # AbstractVoltageGatedChannel — storage and gate introspection
    # ------------------------------------------------------------------

    @property
    def gbar_SI(self) -> float:
        """Maximum conductance density [S m⁻²]."""
        return self._gbar_SI

    @property
    def E_rev_V(self) -> float:
        """Reversal (Nernst) potential [V]."""
        return self._E_rev_V

    # ------------------------------------------------------------------
    # AbstractMembraneMechanism — linearity and conductance
    # ------------------------------------------------------------------

    @property
    def is_linear(self) -> bool:
        """False: non-linear gate kinetics → operator-split, not in G matrix."""
        return False

    @property
    def conductance_density(self) -> float:
        """0.0: non-linear channel; solver uses current() directly, not G."""
        return 0.0

    @property
    def reversal_potential(self) -> float:
        """E_rev [V] — available for diagnostics; not used in G assembly."""
        return self._E_rev_V

    # ------------------------------------------------------------------
    # Transmembrane current  (concrete implementation)
    # ------------------------------------------------------------------

    def current(self, V: float, t: float) -> float:
        """Transmembrane current density [A m⁻²].  Inward-positive.

        I = −gbar × _open_fraction() × (V − E_rev)

        Parameters
        ----------
        V : float   membrane voltage [V]
        t : float   simulation time [s]  (not used; gates updated separately
                    via update_state() before this call)
        """
        return -self._gbar_SI * self._open_fraction() * (V - self._E_rev_V)

    # ------------------------------------------------------------------
    # Abstract gate methods — subclass responsibility
    # ------------------------------------------------------------------

    @abstractmethod
    def _open_fraction(self) -> float:
        """Product of all gate open fractions (scalar in [0, 1]).

        For a m³h channel:
            return m_gate.open_fraction() * h_gate.open_fraction()
                 = m.x**3 * h.x**1
        """

    @abstractmethod
    def update_state(self, V: float, t: float, dt: float) -> None:
        """Advance all gating variables by one timestep using cnexp.

        Called BEFORE current() in the Hines (1984) staggered scheme:
          gates at V^n → current at V^{n+1}

        Parameters
        ----------
        V  : float   membrane voltage [V] at the current timestep
        t  : float   current time [s]
        dt : float   timestep [s]
        """

    @property
    @abstractmethod
    def gate_state(self) -> Dict[str, float]:
        """Current gating variable values keyed by gate name.

        Example: {'m': 0.050, 'h': 0.600} for NaV16Channel.
        Used by state_dict() and for debugging.
        """

    @abstractmethod
    def set_steady_state(self, V: float) -> None:
        """Initialise all gates to steady-state values at voltage V [V].

        Must be called once before the first simulation step.  Initialising
        to steady state avoids an initial transient from arbitrary gate
        starting conditions.
        """

    @abstractmethod
    def state_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the channel state."""

    @abstractmethod
    def reset(self) -> None:
        """Restore to t=0 initial conditions."""

    @property
    @