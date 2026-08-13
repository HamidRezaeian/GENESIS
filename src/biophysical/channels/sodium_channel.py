"""sodium_channel.py — NaV1.6 voltage-gated sodium channel (NaTa_t kinetics).

Kinetics: Mainen & Sejnowski (1996) NaTa_t at 37 °C.
Gates: m (power=3, activation), h (power=1, inactivation).
Open fraction: m³ × h.
Current: I_Na = −gbar × (m³ × h) × (V − E_Na)   [Amperes]

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
    """NaV1.6 sodium channel with NaTa_t (Mainen & Sejnowski 1996) kinetics."""

    def __init__(self, gbar_SI: float, area_m2: float) -> None:
        self._gbar_density: float = float(gbar_SI)
        self._area_m2: float = float(area_m2)
        super().__init__(
            gbar_SI=self._gbar_density * self._area_m2,
            E_rev_V=CHAN.E_Na_V,
        )
        self._m_gate = Gate(x=0.0, power=3)
        self._h_gate = Gate(x=0.0, power=1)
        self.set_steady_state(_V_REST_V)

    @property
    def gbar_SI(self) -> float:
        return self._gbar_density

    @property
    def E_rev_V(self) -> float:
        return CHAN.E_Na_V

    @property
    def gate_state(self) -> Dict[str, float]:
        return {'m': self._m_gate.x, 'h': self._h_gate.x}

    def set_steady_state(self, V: float) -> None:
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

    def update_state(self, V: float, t: float, dt: float) -> None:
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
        self.set_steady_state(_V_REST_V)

    def _open_fraction(self) -> float:
        return self._m_gate.open_fraction() * self._h_gate.open_fraction()

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