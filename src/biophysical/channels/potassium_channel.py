"""potassium_channel.py — Kv (SKv3.1) voltage-gated potassium channel.

Kinetics: SKv3.1 (Hay et al. 2011, ModelDB #139653) at 37 °C.
Gate: n (power=1, activation — Boltzmann inf/tau form).
Open fraction: n¹ = n  (NOT n⁴).
Current: I_K = −gbar × n × (V − E_K)   [Amperes]

Sign convention: positive = inward = depolarising.
  V > E_K → (V − E_K) > 0 → I_K < 0  (outward, hyperpolarising) ✓
  V < E_K → (V − E_K) < 0 → I_K > 0  (inward)                   ✓
  V = E_K → I_K = 0                                               ✓

At rest (V = −70 mV): n∞ ≈ 9.5 × 10⁻⁵  (channel essentially closed) ✓

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

# Resting membrane potential for gate initialisation [V]
_V_REST_V: float = -0.070   # −70 mV


class KvChannel(VoltageGatedChannel):
    """SKv3.1 potassium channel (Hay et al. 2011) with n¹ activation.

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
        super().__init__(
            gbar_SI=self._gbar_density * self._area_m2,
            E_rev_V=CHAN.E_K_V,
        )
        self._n_gate = Gate(x=0.0, power=1)
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
        """Reversal potential E_K [V] (Nernst at 37 °C, ≈ −98.5 mV)."""
        return CHAN.E_K_V

    @property
    def gate_state(self) -> Dict[str, float]:
        """{'n': <n gate>}."""
        return {'n': self._n_gate.x}

    def set_steady_state(self, V: float) -> None:
        """Initialise n to its Boltzmann steady-state at voltage V [V].

        n∞(V) is temperature-independent (equilibrium ratio).
        """
        self._n_gate.x = skv3_n_inf(V * 1e3)

    # ------------------------------------------------------------------
    # AbstractMembraneMechanism
    # ------------------------------------------------------------------

    def update_state(self, V: float, t: float, dt: float) -> None:
        """Advance n gate one cnexp step using Q10-scaled τ.

        Parameters
        ----------
        V  : float   membrane voltage [V]
        t  : float   current time [s]   (unused)
        dt : float   timestep [s]
        """
        V_mV  = V * 1e3
        dt_ms = dt * 1e3
        qt    = CHAN.qt_K
        tau_ms = skv3_tau_n_ms(V_mV) / qt   # τ at 37 °C

        self._n_gate.step_inf_tau(
            x_inf=skv3_n_inf(V_mV),
            tau_ms=tau_ms,
            dt_ms=dt_ms,
        )

    def reset(self) -> None:
        """Restore gate to steady-state at V_rest = −70 mV."""
        self.set_steady_state(_V_REST_V)

    # ------------------------------------------------------------------
    # VoltageGatedChannel — abstract gate method
    # ------------------------------------------------------------------

    def _open_fraction(self) -> float:
        """n¹ = n."""
        return self._n_gate.open_fraction()

    # ------------------------------------------------------------------
    # BiophysComponent
    # ------------------------------------------------------------------

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
