"""sodium_channel.py — NaV1.6 voltage-gated sodium channel (NaTa_t kinetics).

Kinetics: Mainen & Sejnowski (1996) NaTa_t at 37 °C.
Gates: m (power=3, activation), h (power=1, inactivation).
Open fraction: m³ × h.
Current: I_Na = −gbar × (m³ × h) × (V − E_Na)   [Amperes]

Sign convention: positive = inward = depolarising.
  V < E_Na → (V − E_Na) < 0 → I_Na > 0  (inward)  ✓
  V > E_Na → (V − E_Na) > 0 → I_Na < 0  (outward) ✓
  V = E_Na → I_Na = 0                               ✓

References
----------
[MS96] Mainen ZF, Sejnowski TJ (1996) J Neurophysiol 76:1329–1338
[H11]  Hay E et al. (2011) PLoS Comput Biol 7:e1002107; ModelDB #139653
"""

from __future__ import annotations

from typing import Any, Dict

from biophysical.channels.base_channel import VoltageGatedChannel
from biophysical.channels.gating import (
    Gate,
    nata_alpha_m,
    nata_beta_m,
    nata_alpha_h,
    nata_beta_h,
)
from biophysical.core.constants import CHAN

# Resting membrane potential for gate initialisation [V]
_V_REST_V: float = -0.070   # −70 mV


class NaV16Channel(VoltageGatedChannel):
    """NaV1.6 sodium channel with NaTa_t (Mainen & Sejnowski 1996) kinetics.

    Parameters
    ----------
    gbar_SI : float   maximum conductance density  [S m⁻²]
    area_m2 : float   compartment surface area     [m²]

    The constructor computes total_gbar = gbar_SI × area_m2 [S] and passes
    it to VoltageGatedChannel so that current() returns Amperes directly.
    """

    def __init__(self, gbar_SI: float, area_m2: float) -> None:
        self._gbar_density: float = float(gbar_SI)
        self._area_m2: float = float(area_m2)
        # Pass total conductance to parent so inherited current() returns [A]
        super().__init__(
            gbar_SI=self._gbar_density * self._area_m2,
            E_rev_V=CHAN.E_Na_V,
        )
        # Gates — m³h
        self._m_gate = Gate(x=0.0, power=3)
        self._h_gate = Gate(x=0.0, power=1)
        self.set_steady_state(_V_REST_V)

    # ------------------------------------------------------------------
    # AbstractVoltageGatedChannel — overrides
    # ------------------------------------------------------------------

    @property
    def gbar_SI(self) -> float:
        """Maximum conductance *density* [S m⁻²]."""
        return self._gbar_density

    @property
    def E_rev_V(self) -> float:
        """Reversal potential E_Na [V] (Nernst at 37 °C, ≈ +71.4 mV)."""
        return CHAN.E_Na_V

    @property
    def gate_state(self) -> Dict[str, float]:
        """{'m': <m gate>, 'h': <h gate>}."""
        return {'m': self._m_gate.x, 'h': self._h_gate.x}

    def set_steady_state(self, V: float) -> None:
        """Initialise m and h to their steady-state values at voltage V [V].

        Uses Q10-scaled rates (qt_Na ≈ 3.21) to evaluate α/β at 37 °C,
        then sets x = α / (α + β) for each gate.
        """
        V_mV = V * 1e3
        qt = CHAN.qt_Na
        alpha_m = nata_alpha_m(V_mV) * qt
        beta_m  = nata_beta_m(V_mV)  * qt
        alpha_h = nata_alpha_h(V_mV) * qt
        beta_h  = nata_beta_h(V_mV)  * qt

        sum_m = alpha_m + beta_m
        sum_h = alpha_h + beta_h
        self._m_gate.x = alpha_m / sum_m if sum_m > 0.0 else 0.0
        self._h_gate.x = alpha_h / sum_h if sum_h > 0.0 else 1.0

    # ------------------------------------------------------------------
    # AbstractMembraneMechanism
    # ------------------------------------------------------------------

    def update_state(self, V: float, t: float, dt: float) -> None:
        """Advance m and h gates one cnexp step.

        Parameters
        ----------
        V  : float   membrane voltage [V]
        t  : float   current time [s]   (unused; gates are updated here)
        dt : float   timestep [s]
        """
        V_mV  = V * 1e3
        dt_ms = dt * 1e3
        qt    = CHAN.qt_Na

        self._m_gate.step_alpha_beta(
            nata_alpha_m(V_mV) * qt,
            nata_beta_m(V_mV)  * qt,
            dt_ms,
        )
        self._h_gate.step_alpha_beta(
            nata_alpha_h(V_mV) * qt,
            nata_beta_h(V_mV)  * qt,
            dt_ms,
        )

    def reset(self) -> None:
        """Restore gates to steady-state at V_rest = −70 mV."""
        self.set_steady_state(_V_REST_V)

    # ------------------------------------------------------------------
    # VoltageGatedChannel — abstract gate method
    # ------------------------------------------------------------------

    def _open_fraction(self) -> float:
        """m³ × h."""
        return self._m_gate.open_fraction() * self._h_gate.open_fraction()

    # ------------------------------------------------------------------
    # BiophysComponent
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return 'NaV16Channel'

    def state_dict(self) -> Dict[str, Any]:
        return {
            'gbar_density_S_m2': self._gbar_density,
            'area_m2':           self._area_m2,
            'E_Na_V':            CHAN.E_Na_V,
            'm':                 self._m_gate.x,
            'h':                 self._h_gate.x,
        }
