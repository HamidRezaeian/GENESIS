"""potassium_channel.py — Kv (SKv3.1) voltage-gated potassium channel.

Kinetics: SKv3.1 (Hay et al. 2011) at 37 °C.
Gate: n (power=1, activation — Boltzmann).
Open fraction: n¹ = n  (NOT n⁴).
Current: I_K = −gbar × n × (V − E_K)   [Amperes]

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
    skv3_n_inf,
    skv3_tau_n_ms,
)
from biophysical.core.constants import CHAN

_V_REST_V: float = -0.070


class KvChannel(VoltageGatedChannel):
    """SKv3.1 potassium channel (Hay et al. 2011) with n¹ activation."""

    def __init__(self, gbar_SI: float, area_m2: float) -> None:
        self._gbar_density: float = float(gbar_SI)
        self._area_m2: float = float(area_m2)
        super().__init__(
            gbar_SI=self._gbar_density * self._area_m2,
            E_rev_V=CHAN.E_K_V,
        )
        self._n_gate = Gate(x=0.0, power=1)
        self.set_steady_state(_V_REST_V)

    @property
    def gbar_SI(self) -> float:
        return self._gbar_density

    @property
    def E_rev_V(self) -> float:
        return CHAN.E_K_V

    @property
    def gate_state(self) -> Dict[str, float]:
        return {'n': self._n_gate.x}

    def set_steady_state(self, V: float) -> None:
        self._n_gate.x = skv3_n_inf(V * 1e3)

    def update_state(self, V: float, t: float, dt: float) -> None:
        V_mV  = V * 1e3
        dt_ms = dt * 1e3
        qt    = CHAN.qt_K
        tau_ms = skv3_tau_n_ms(V_mV) / qt

        self._n_gate.step_inf_tau(
            x_inf=skv3_n_inf(V_mV),
            tau_ms=tau_ms,
            dt_ms=dt_ms,
        )

    def reset(self) -> None:
        self.set_steady_state(_V_REST_V)

    def _open_fraction(self) -> float:
        return self._n_gate.open_fraction()

    @property
    def name(self) -> str:
        return 'KvChannel'

    def state_dict(self) -> Dict[str, Any]:
        return {
            'gbar_density_S_m2': self._gbar_density,
            'area_m2':           self._area_m2,
            'E_K_V':             CHAN.E_K_V,
            'n':                 self._n_gate.x,
        }