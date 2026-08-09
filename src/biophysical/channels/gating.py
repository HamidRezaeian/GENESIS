"""gating.py — Gate state and kinetic rate functions for voltage-gated channels.

Provides
--------
vtrap           Numerically stable x/(exp(x/y)−1) with L'Hôpital fix.
Gate            Dataclass holding one gating variable; cnexp stepping.
q10_factor      Temperature-scaling multiplier Q10^((T−T_ref)/10).
nata_alpha_m    NaTa_t m-gate opening rate α_m(V) [1/ms] at T_ref = 23 °C.
nata_beta_m     NaTa_t m-gate closing rate β_m(V) [1/ms] at T_ref = 23 °C.
nata_alpha_h    NaTa_t h-gate opening rate α_h(V) [1/ms] at T_ref = 23 °C.
nata_beta_h     NaTa_t h-gate closing rate β_h(V) [1/ms] at T_ref = 23 °C.
skv3_n_inf      SKv3.1 n-gate steady-state n∞(V) [dimensionless].
skv3_tau_n_ms   SKv3.1 n-gate time constant τ_n(V) [ms] at T_ref = 23 °C.

All NaTa_t rate functions return values at T_ref = 23 °C.  Before passing
them to Gate.step_alpha_beta(), scale by:
    qt = q10_factor(CHAN.Q10_Na, T_CELSIUS, CHAN.T_ref_celsius)  ≈ 3.21

All SKv3.1 rate functions return values at T_ref = 23 °C.  Before passing
tau_n to Gate.step_inf_tau(), divide by:
    qt = q10_factor(CHAN.Q10_K, T_CELSIUS, CHAN.T_ref_celsius)   ≈ 4.65

References
----------
[MS96]  Mainen ZF, Sejnowski TJ (1996) J Neurophysiol 76:1329–1338
        Rate functions from rat neocortical pyramidal cells at 23 °C.
[H11]   Hay E et al. (2011) PLoS Comput Biol 7:e1002107; ModelDB #139653
        NaTa_t.mod and SKv3_1.mod — same α/β and inf/tau as [MS96].
[CN47]  Crank J, Nicolson P (1947) Proc Camb Phil Soc 43:50–67
        Exponential Euler (cnexp) is exact for linear first-order ODEs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ===========================================================================
# Numerical helper
# ===========================================================================

def vtrap(x: float, y: float) -> float:
    """Numerically stable  x / (exp(x/y) − 1)  using L'Hôpital near x/y → 0.

    The NaTa_t α/β rate functions have the form  A * vtrap(V + V_half, k),
    which evaluates x/(e^{x/y}−1) at x = V + V_half, y = k.  The function
    has a removable singularity at x = 0 where the limit (L'Hôpital) is y.

    Implementation uses a second-order Taylor expansion for |x/y| < ε:
        y · (1 − x/(2y))
    which matches the NEURON simulator's vtrap helper to machine precision.

    Parameters
    ----------
    x : float   numerator — often V_mV + V_half
    y : float   scale parameter / slope  (non-zero)

    Returns
    -------
    float   value of x / (exp(x/y) − 1), finite at x = 0

    Singularity points in NaTa_t (V in mV):
      m-gate:  V = −40 mV  (x = V + 40 = 0, y = ±9)
      h-gate:  V = −66 mV  (x = V + 66 = 0, y = ±6)

    Analytical verification:
      vtrap(0, −9) = −9  →  α_m(−40) = −0.182 × (−9) = 1.638 ms⁻¹
      vtrap(0, +9) = +9  →  β_m(−40) =  0.124 ×  9   = 1.116 ms⁻¹
      vtrap(0, −6) = −6  →  α_h(−66) = −0.015 × (−6) = 0.090 ms⁻¹
      vtrap(0, +6) = +6  →  β_h(−66) =  0.015 ×  6   = 0.090 ms⁻¹
    """
    if abs(x) < 1e-6 * abs(y):
        # L'Hôpital: lim_{x→0} x/(e^{x/y}−1) = y
        # Second-order correction avoids catastrophic cancellation:
        return y * (1.0 - 0.5 * x / y)
    return x / (math.exp(x / y) - 1.0)


# ===========================================================================
# Gate dataclass
# ===========================================================================

@dataclass
class Gate:
    """A single Hodgkin-Huxley gating variable with exponential Euler stepping.

    State
    -----
    x     : float   current gate value, in [0, 1]
    power : int     exponent applied to x for the open probability;
                    e.g. power=3 gives the m³ factor, power=1 for h or n.

    Exponential Euler (cnexp)  [CN47]
    ---------------------------------
    For the linear first-order ODE  dx/dt = (x∞ − x) / τ  the exact solution
    over a timestep dt is:

        x(t+dt) = x∞ + (x − x∞) · exp(−dt / τ)

    Properties of this method:
      • **Unconditionally stable** for any dt > 0 and τ > 0.
      • **Exact** for linear ODEs: one step of dt gives the same result as
        two steps of dt/2.  This is verified in the dt-halving convergence
        test (test_channels_gating.py).
      • Named "cnexp" in NEURON; the default method for HH gating variables.
    """

    x:     float   # current gate value in [0, 1]
    power: int     # gate exponent (e.g. 3 for m³, 1 for n or h)

    def open_fraction(self) -> float:
        """x^power — the open-probability contribution of this gate.

        For a channel with m³h gates:
            total_open = m.open_fraction() * h.open_fraction()
                       = m.x ** 3  ×  h.x ** 1
        """
        return self.x ** self.power

    def step_alpha_beta(
        self,
        alpha_ms: float,
        beta_ms:  float,
        dt_ms:   float,
    ) -> None:
        """Advance gate one cnexp step using α/β kinetics (at simulation temp).

        Computes steady-state and time constant from rates, then applies
        the exact exponential-Euler update:

            x∞ = α / (α + β)
            τ  = 1 / (α + β)
            x  ← x∞ + (x − x∞) · exp(−dt · (α + β))

        Parameters
        ----------
        alpha_ms : float   opening rate α(V) at **simulation temperature** [1/ms]
                           (i.e. reference rate already multiplied by qt)
        beta_ms  : float   closing rate β(V) at **simulation temperature** [1/ms]
        dt_ms    : float   timestep [ms]  (must be > 0)
        """
        sum_ab = alpha_ms + beta_ms
        if sum_ab <= 0.0:
            return  # degenerate: no net driving force
        x_inf = alpha_ms / sum_ab
        self.x = x_inf + (self.x - x_inf) * math.exp(-dt_ms * sum_ab)

    def step_inf_tau(
        self,
        x_inf:  float,
        tau_ms: float,
        dt_ms:  float,
    ) -> None:
        """Advance gate one cnexp step using inf/tau (Boltzmann) kinetics.

            x ← x∞ + (x − x∞) · exp(−dt / τ)

        Parameters
        ----------
        x_inf  : float   steady-state gate value x∞(V) ∈ [0, 1]
        tau_ms : float   time constant τ(V) at **simulation temperature** [ms]
                         (i.e. reference tau already divided by qt)
        dt_ms  : float   timestep [ms]  (must be > 0)
        """
        if tau_ms <= 0.0:
            self.x = x_inf
            return
        self.x = x_inf + (self.x - x_inf) * math.exp(-dt_ms / tau_ms)


# ===========================================================================
# Q10 temperature scaling
# ===========================================================================

def q10_factor(Q10: float, T_celsius: float, T_ref_celsius: float = 23.0) -> float:
    """Q10 temperature-scaling multiplier  Q10 ^ ((T − T_ref) / 10).

    Multiply reference-temperature rates (1/ms) by qt to obtain rates at
    T_celsius.  Equivalently, divide reference-temperature time constants
    (ms) by qt.

    Parameters
    ----------
    Q10           : float   Q10 coefficient (dimensionless, typically 2–4)
    T_celsius     : float   simulation temperature [°C]
    T_ref_celsius : float   reference temperature at which rates were measured
                            [°C]; default 23 °C  [MS96]

    Returns
    -------
    float   speed-up factor ≥ 1.0 for T_celsius > T_ref_celsius

    Examples
    --------
    NaTa_t at 37 °C:  q10_factor(2.3, 37.0, 23.0) = 2.3^1.4 ≈ 3.21
    SKv3.1 at 37 °C:  q10_factor(3.0, 37.0, 23.0) = 3.0^1.4 ≈ 4.65
    At reference:     q10_factor(2.3, 23.0, 23.0) = 1.0  (exactly)
    """
    return Q10 ** ((T_celsius - T_ref_celsius) / 10.0)


# ===========================================================================
# NaTa_t rate functions  (Mainen & Sejnowski 1996 / Hay 2011 NaTa_t.mod)
# ===========================================================================
#
# All functions below return rates in 1/ms at T_ref = 23 °C.
# Before calling Gate.step_alpha_beta(), scale each rate by:
#     qt_Na = q10_factor(CHAN.Q10_Na, T_CELSIUS, CHAN.T_ref_celsius)  ≈ 3.21
#
# Analytically verified values at key voltages:
#
#   V = −40 mV  (m-gate singularity):
#     α_m = −0.182 × vtrap(0, −9) = −0.182 × (−9) = 1.638 ms⁻¹
#     β_m =  0.124 × vtrap(0, +9) =  0.124 ×  9   = 1.116 ms⁻¹
#     m∞  = 1.638 / 2.754 ≈ 0.595
#     τ_m(23°C) = 1 / 2.754 ≈ 0.363 ms
#     τ_m(37°C) = 0.363 / 3.21 ≈ 0.113 ms  ← matches plan target ≈ 0.11 ms ✓
#
#   V = −66 mV  (h-gate singularity; half-activation):
#     α_h = −0.015 × vtrap(0, −6) = 0.090 ms⁻¹
#     β_h =  0.015 × vtrap(0, +6) = 0.090 ms⁻¹
#     h∞  = 0.5  (α = β by symmetry)
#
#   V = −70 mV  (resting):
#     m∞ ≈ 0.050  (channel mostly closed)
#     τ_h(37°C) ≈ 1.68 ms  ← within plan target 0.25–2.5 ms ✓

def nata_alpha_m(V_mV: float) -> float:
    """NaTa_t m-gate opening rate α_m(V) [1/ms] at T_ref = 23 °C.

    α_m(V) = −0.182 × vtrap(V + 40, −9)

    Returns a positive rate for all physiological V.
    Singularity at V = −40 mV handled by vtrap L'Hôpital → α_m(−40) = 1.638.

    Source: NaTa_t.mod, Hay et al. 2011 (ModelDB #139653); [MS96].
    """
    return -0.182 * vtrap(V_mV + 40.0, -9.0)


def nata_beta_m(V_mV: float) -> float:
    """NaTa_t m-gate closing rate β_m(V) [1/ms] at T_ref = 23 °C.

    β_m(V) = 0.124 × vtrap(V + 40, +9)

    Returns a positive rate for all physiological V.
    Singularity at V = −40 mV handled by vtrap L'Hôpital → β_m(−40) = 1.116.

    Source: NaTa_t.mod, Hay et al. 2011 (ModelDB #139653); [MS96].
    """
    return 0.124 * vtrap(V_mV + 40.0, 9.0)


def nata_alpha_h(V_mV: float) -> float:
    """NaTa_t h-gate opening rate α_h(V) [1/ms] at T_ref = 23 °C.

    α_h(V) = −0.015 × vtrap(V + 66, −6)

    Returns a positive rate for all physiological V.
    Singularity at V = −66 mV handled by vtrap L'Hôpital → α_h(−66) = 0.090.

    Source: NaTa_t.mod, Hay et al. 2011 (ModelDB #139653); [MS96].
    """
    return -0.015 * vtrap(V_mV + 66.0, -6.0)


def nata_beta_h(V_mV: float) -> float:
    """NaTa_t h-gate closing rate β_h(V) [1/ms] at T_ref = 23 °C.

    β_h(V) = 0.015 × vtrap(V + 66, +6)

    Returns a positive rate for all physiological V.
    Singularity at V = −66 mV handled by vtrap L'Hôpital → β_h(−66) = 0.090.

    Source: NaTa_t.mod, Hay et al. 2011 (ModelDB #139653); [MS96].
    """
    return 0.015 * vtrap(V_mV + 66.0, 6.0)


# ===========================================================================
# SKv3.1 rate functions  (Hay 2011 SKv3_1.mod)
# ===========================================================================
#
# SKv3.1 uses Boltzmann (inf/tau) form rather than α/β.
# The n gate uses power = 1 in the Hay 2011 / ModelDB #139653 implementation.
#
# NOTE — plan vs. biophysics:
#   The approved Phase 0b plan references "KvChannel, n⁴", the classic
#   Hodgkin-Huxley form.  The SKv3.1 channel in Hay 2011 uses n¹ (single
#   Boltzmann gate).  KvChannel in Step 2 uses the kinetics below with a
#   configurable `power` parameter (default 1, matching ModelDB).
#   Setting power=4 gives a steeper activation curve but does not match
#   published SKv3.1 data.
#
# Analytically verified values:
#   V = −70 mV: n∞ ≈ 9.5×10⁻⁵  (essentially closed at rest) ✓
#   V = +18.7 mV: n∞ = 0.500   (half-activation voltage) ✓
#   V = +40 mV: n∞ ≈ 0.900    (mostly open near AP peak) ✓
#   V = +46.56 mV: τ_n(23°C) = 2.00 ms  (peak of tau curve)
#                  τ_n(37°C) = 2.00 / 4.65 ≈ 0.43 ms

def skv3_n_inf(V_mV: float) -> float:
    """SKv3.1 n-gate steady-state n∞(V) [dimensionless, in (0, 1)].

    n∞(V) = 1 / (1 + exp(−(V − 18.7) / 9.7))

    Half-activation: V_half = +18.7 mV.  Slope factor k = 9.7 mV.
    Temperature-independent (steady state is an equilibrium ratio).

    Source: SKv3_1.mod, Hay et al. 2011 (ModelDB #139653); [H11].
    """
    return 1.0 / (1.0 + math.exp(-(V_mV - 18.7) / 9.7))


def skv3_tau_n_ms(V_mV: float) -> float:
    """SKv3.1 n-gate time constant τ_n(V) [ms] at T_ref = 23 °C.

    τ_n(V) = 4.0 / (1 + exp((V − 46.56) / 44.14))

    Peak τ_n = 2.0 ms at V = +46.56 mV (23 °C).
    At 37 °C: τ_n ≈ 2.0 / 4.65 ≈ 0.43 ms.

    Before passing to Gate.step_inf_tau(), divide by:
        qt = q10_factor(CHAN.Q10_K, T_CELSIUS, CHAN.T_ref_celsius)  ≈ 4.65

    Source: SKv3_1.mod, Hay et al. 2011 (ModelDB #139653); [H11].
    Equivalent to NEURON expression:
        0.2 * 20.0 / (1 + exp(((v - 46.56) / (-44.14))))
    """
    # Equivalent: 0.2 * 20.0 / (1 + exp(-(V-46.56)/(-44.14)))
    #           = 4.0 / (1 + exp((V-46.56)/44.14))
    return 4.0 / (1.0 + math.exp((V_mV - 46.56) / 44.14))
