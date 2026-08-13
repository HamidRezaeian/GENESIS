"""test_potassium_channel.py — 15 unit tests for KvChannel (SKv3.1).

All expected values derived analytically from SKv3_1.mod (Hay 2011)
kinetics at 37 °C (qt_K ≈ 4.65).

Key steady-state values:
  n∞(−70 mV)  ≈ 9.5 × 10⁻⁵  (essentially closed at rest)        ✓
  n∞(+18.7 mV) = 0.500       (half-activation voltage)            ✓
  n∞(+40 mV)  ≈ 0.900        (mostly open near AP peak)           ✓
"""

import pytest

from biophysical.channels.potassium_channel import KvChannel
from biophysical.channels.gating import skv3_n_inf
from biophysical.core.constants import CHAN


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_channel(gbar_SI: float = 1000.0, area_m2: float = 1e-9) -> KvChannel:
    return KvChannel(gbar_SI=gbar_SI, area_m2=area_m2)


# ---------------------------------------------------------------------------
# 1. Construction — n initialised at rest ≈ 9.5 × 10⁻⁵
# ---------------------------------------------------------------------------

def test_construction_initializes_n_at_rest():
    """n gate must equal n∞(−70 mV) ≈ 9.5 × 10⁻⁵ after __init__."""
    ch = _make_channel()
    n_expected = skv3_n_inf(-70.0)
    assert abs(ch.gate_state['n'] - n_expected) < 1e-9
    assert n_expected < 1e-3  # n_inf at -70mV is very


# ---------------------------------------------------------------------------
# 2. Open fraction at rest is essentially zero
# ---------------------------------------------------------------------------

def test_open_fraction_at_rest_is_zero():
    """n∞(−70 mV) ≈ 9.5 × 10⁻⁵ → open fraction < 1 × 10⁻³."""
    ch = _make_channel()
    n = ch.gate_state['n']
    assert n < 1e-3


# ---------------------------------------------------------------------------
# 3. Open fraction at half-activation voltage (+18.7 mV) ≈ 0.5
# ---------------------------------------------------------------------------

def test_open_fraction_half_activation():
    """n∞(+18.7 mV) = 0.5 by definition of V_half for Boltzmann n gate."""
    ch = _make_channel()
    ch.set_steady_state(+0.0187)   # +18.7 mV
    n = ch.gate_state['n']
    assert abs(n - 0.5) < 1e-4


# ---------------------------------------------------------------------------
# 4. Open fraction mostly open at AP peak (+40 mV)
# ---------------------------------------------------------------------------

def test_open_fraction_mostly_open_at_peak():
    """n∞(+40 mV) ≈ 0.900 — channel mostly open at action potential peak."""
    ch = _make_channel()
    ch.set_steady_state(+0.040)
    n = ch.gate_state['n']
    assert n > 0.8


# ---------------------------------------------------------------------------
# 5. Current is zero at reversal potential E_K
# ---------------------------------------------------------------------------

def test_current_zero_at_reversal():
    """I_K = 0 when V = E_K, regardless of gating."""
    ch = _make_channel()
    E_K = CHAN.E_K_V
    I = ch.current(V=E_K, t=0.0)
    assert abs(I) < 1e-20


# ---------------------------------------------------------------------------
# 6. Current is negative (outward) above reversal (V > E_K)
# ---------------------------------------------------------------------------

def test_current_negative_above_reversal():
    """At V = −70 mV > E_K ≈ −98.5 mV: I_K < 0 (outward, hyperpolarising)."""
    ch = _make_channel()
    ch.set_steady_state(-0.040)   # open channel enough for measurable current
    I = ch.current(V=-0.070, t=0.0)
    assert I < 0.0


# ---------------------------------------------------------------------------
# 7. Current is positive (inward) below reversal (V < E_K)
# ---------------------------------------------------------------------------

def test_current_positive_below_reversal():
    """At V = −100 mV < E_K ≈ −98.5 mV: I_K > 0 (inward)."""
    ch = _make_channel()
    ch.set_steady_state(-0.040)   # ensure n is meaningfully open
    I = ch.current(V=-0.100, t=0.0)
    assert I > 0.0


# ---------------------------------------------------------------------------
# 8. Current magnitude is physiologically reasonable at AP peak
# ---------------------------------------------------------------------------

def test_current_magnitude_reasonable():
    """At V = +40 mV, gbar = 19 000 S m⁻², area = 1e-9 m²:

    E_K ≈ −98.5 mV (Nernst). V = +40 mV > E_K.
    I_K = −(19 000 × 1e-9) × n∞(+40) × (0.040 − (−0.0985))
        ≈ −1.9e-5 × 0.900 × 0.1385
        ≈ −2.37 × 10⁻⁶ A  (outward, negative)

    Current density ≈ −2370 A m⁻² (outward).
    """
    area = 1e-9
    ch = KvChannel(gbar_SI=19_000.0, area_m2=area)
    ch.set_steady_state(+0.040)
    I = ch.current(V=+0.040, t=0.0)
    density = I / area   # A m⁻²  (negative = outward)
    assert density < -100.0
    assert density > -5_000.0


# ---------------------------------------------------------------------------
# 9. update_state advances n toward n∞ at +40 mV
# ---------------------------------------------------------------------------

def test_update_state_advances_n():
    """After 5 ms at V = +40 mV, n should approach n∞(+40) ≈ 0.90."""
    ch = _make_channel()
    n0 = ch.gate_state['n']
    for _ in range(5):
        ch.update_state(V=+0.040, t=0.0, dt=1e-3)
    n1 = ch.gate_state['n']
    n_target = skv3_n_inf(+40.0)
    assert n1 > n0
    assert n1 <= n_target + 1e-9


# ---------------------------------------------------------------------------
# 10. reset() restores n to n∞(−70 mV)
# ---------------------------------------------------------------------------

def test_reset_restores_steady_state():
    """After perturbing n and calling reset(), n returns to n∞(−70 mV)."""
    ch = _make_channel()
    for _ in range(10):
        ch.update_state(V=+0.040, t=0.0, dt=1e-3)   # perturb
    ch.reset()
    n_rest = skv3_n_inf(-70.0)
    assert abs(ch.gate_state['n'] - n_rest) < 1e-9


# ---------------------------------------------------------------------------
# 11. state_dict round-trip
# ---------------------------------------------------------------------------

def test_state_dict_roundtrip():
    """state_dict() correctly reports gate value and channel parameters."""
    ch = _make_channel(gbar_SI=800.0, area_m2=3e-9)
    ch.update_state(V=+0.020, t=0.0, dt=1e-3)
    sd = ch.state_dict()
    assert abs(sd['n'] - ch.gate_state['n']) < 1e-15
    assert sd['gbar_density_S_m2'] == pytest.approx(800.0)
    assert sd['area_m2'] == pytest.approx(3e-9)


# ---------------------------------------------------------------------------
# 12. is_linear returns False
# ---------------------------------------------------------------------------

def test_is_linear_returns_false():
    ch = _make_channel()
    assert ch.is_linear is False


# ---------------------------------------------------------------------------
# 13. Current scales linearly with gbar_SI
# ---------------------------------------------------------------------------

def test_current_scales_with_gbar():
    """Doubling gbar_SI should double the current."""
    area = 1e-9
    ch1 = KvChannel(gbar_SI=1000.0, area_m2=area)
    ch2 = KvChannel(gbar_SI=2000.0, area_m2=area)
    V = -0.050
    I1 = ch1.current(V=V, t=0.0)
    I2 = ch2.current(V=V, t=0.0)
    assert I2 == pytest.approx(2.0 * I1, rel=1e-9)


# ---------------------------------------------------------------------------
# 14. Current scales linearly with area_m2
# ---------------------------------------------------------------------------

def test_current_scales_with_area():
    """Doubling area_m2 should double the current."""
    gbar = 1000.0
    ch1 = KvChannel(gbar_SI=gbar, area_m2=1e-9)
    ch2 = KvChannel(gbar_SI=gbar, area_m2=2e-9)
    V = -0.050
    I1 = ch1.current(V=V, t=0.0)
    I2 = ch2.current(V=V, t=0.0)
    assert I2 == pytest.approx(2.0 * I1, rel=1e-9)


# ---------------------------------------------------------------------------
# 15. Open fraction uses n¹, not n⁴
# ---------------------------------------------------------------------------

def test_power_1_for_n_gate():
    """open_fraction must equal n^1, clearly different from n^4."""
    ch = _make_channel()
    ch.set_steady_state(+0.0187)   # n ≈ 0.5
    n = ch.gate_state['n']
    expected_n1 = n ** 1
    expected_n4 = n ** 4
    actual = ch._open_fraction()
    assert actual == pytest.approx(expected_n1, rel=1e-12)
    assert abs(actual - expected_n4) > 0.05   # n^1=0.5 vs n^4=0.0625
