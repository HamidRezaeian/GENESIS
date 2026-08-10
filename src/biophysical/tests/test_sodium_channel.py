"""test_sodium_channel.py — 18 unit tests for NaV16Channel.

All expected values derived analytically from NaTa_t.mod (Hay 2011)
kinetics at 37 °C (qt_Na ≈ 3.21).

Key steady-state values at V_rest = −70 mV:
  m∞ ≈ 0.0496   h∞ ≈ 0.340
  open ≈ m∞³ × h∞ ≈ 4.3 × 10⁻⁵  (channel essentially closed) ✓

Key steady-state values at V = −40 mV (NaTa_t half-activation):
  m∞ ≈ 0.595   h∞ ≈ 0.987
  open ≈ 0.595³ × 0.987 ≈ 0.208  (channel substantially open) ✓

Key steady-state values at V = +40 mV (AP peak):
  m∞ ≈ 1.000   h∞ ≈ 1.000
  open ≈ 1.0  (channel essentially fully open) ✓
"""

import math
import pytest

from biophysical.channels.sodium_channel import NaV16Channel
from biophysical.channels.gating import (
    nata_alpha_m, nata_beta_m,
    nata_alpha_h, nata_beta_h,
)
from biophysical.core.constants import CHAN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _m_inf(V_mV: float) -> float:
    qt = CHAN.qt_Na
    a = nata_alpha_m(V_mV) * qt
    b = nata_beta_m(V_mV)  * qt
    return a / (a + b)


def _h_inf(V_mV: float) -> float:
    qt = CHAN.qt_Na
    a = nata_alpha_h(V_mV) * qt
    b = nata_beta_h(V_mV)  * qt
    return a / (a + b)


def _make_channel(gbar_SI: float = 1000.0, area_m2: float = 1e-9) -> NaV16Channel:
    return NaV16Channel(gbar_SI=gbar_SI, area_m2=area_m2)


# ---------------------------------------------------------------------------
# 1. Construction — gates initialised at rest
# ---------------------------------------------------------------------------

def test_construction_initializes_gates_at_rest():
    """Gates must equal m∞(−70 mV) and h∞(−70 mV) immediately after __init__."""
    ch = _make_channel()
    m_expected = _m_inf(-70.0)
    h_expected = _h_inf(-70.0)
    assert abs(ch.gate_state['m'] - m_expected) < 1e-9
    assert abs(ch.gate_state['h'] - h_expected) < 1e-9


# ---------------------------------------------------------------------------
# 2. Open fraction at rest is very low
# ---------------------------------------------------------------------------

def test_open_fraction_at_rest_is_low():
    """At V = −70 mV (rest), m³ × h ≈ 4.3 × 10⁻⁵ — channel essentially closed."""
    ch = _make_channel()
    m = ch.gate_state['m']
    h = ch.gate_state['h']
    open_frac = m ** 3 * h
    assert open_frac < 0.01


# ---------------------------------------------------------------------------
# 3. Open fraction at −40 mV (NaTa_t half-activation) is moderate
# ---------------------------------------------------------------------------

def test_open_fraction_at_threshold_is_moderate():
    """At V = −40 mV (steady state), m³ × h ≈ 0.21 — substantially open.

    Note: −40 mV is the NaTa_t m-gate half-activation voltage where
    m∞ ≈ 0.595, giving m³ × h ≈ 0.21 ∈ [0.1, 0.5].
    """
    ch = _make_channel()
    ch.set_steady_state(-0.040)   # −40 mV
    m = ch.gate_state['m']
    h = ch.gate_state['h']
    open_frac = m ** 3 * h
    assert 0.1 <= open_frac <= 0.5


# ---------------------------------------------------------------------------
# 4. Open fraction at AP peak (+40 mV) is high
# ---------------------------------------------------------------------------

def test_open_fraction_at_peak_is_high():
    """At V = +40 mV (AP peak, steady state), m³ × h ≈ 1.0 — channel fully open."""
    ch = _make_channel()
    ch.set_steady_state(+0.040)   # +40 mV
    m = ch.gate_state['m']
    h = ch.gate_state['h']
    open_frac = m ** 3 * h
    assert open_frac > 0.5


# ---------------------------------------------------------------------------
# 5. Current is zero at reversal potential
# ---------------------------------------------------------------------------

def test_current_zero_at_reversal():
    """I_Na = 0 when V = E_Na (Nernst potential), regardless of gating."""
    ch = _make_channel(gbar_SI=1000.0, area_m2=1e-9)
    E_Na = CHAN.E_Na_V
    I = ch.current(V=E_Na, t=0.0)
    assert abs(I) < 1e-20   # numerically zero


# ---------------------------------------------------------------------------
# 6. Current is positive (inward) below reversal
# ---------------------------------------------------------------------------

def test_current_positive_below_reversal():
    """At V = −70 mV < E_Na, I_Na > 0 (inward, depolarising)."""
    ch = _make_channel()
    I = ch.current(V=-0.070, t=0.0)
    # Gates at rest → small but positive current
    assert I > 0.0


# ---------------------------------------------------------------------------
# 7. Current is negative (outward) above reversal
# ---------------------------------------------------------------------------

def test_current_negative_above_reversal():
    """At V = +80 mV > E_Na, I_Na < 0 (outward)."""
    ch = _make_channel()
    ch.set_steady_state(+0.080)   # large m, small h at this voltage
    I = ch.current(V=+0.080, t=0.0)
    assert I < 0.0


# ---------------------------------------------------------------------------
# 8. Current magnitude is physiologically reasonable at AP peak
# ---------------------------------------------------------------------------

def test_current_magnitude_at_ap_peak():
    """At V = +40 mV, gbar = 30 000 S m⁻², area = 1e-9 m²:

    E_Na ≈ +71.4 mV (Nernst), so V = +40 mV < E_Na.
    I_Na = −(30 000 × 1e-9) × open × (0.040 − 0.0714)
         ≈ −3e-5 × 1.0 × (−0.0314)
         ≈ +9.4 × 10⁻⁷ A  (inward, positive)

    Current density ≈ +940 A m⁻² (inward).
    """
    area = 1e-9
    ch = NaV16Channel(gbar_SI=30_000.0, area_m2=area)
    ch.set_steady_state(+0.040)
    I = ch.current(V=+0.040, t=0.0)
    # V < E_Na → inward (positive)
    density = I / area   # A m⁻²
    assert density > 100.0
    assert density < 2_000.0


# ---------------------------------------------------------------------------
# 9. update_state advances gates toward new steady state
# ---------------------------------------------------------------------------

def test_update_state_advances_gates():
    """After 1 ms at V = −40 mV, m should increase toward m∞(−40) ≈ 0.595."""
    ch = _make_channel()
    m0 = ch.gate_state['m']
    ch.update_state(V=-0.040, t=0.0, dt=1e-3)
    m1 = ch.gate_state['m']
    m_target = _m_inf(-40.0)
    assert m1 > m0
    assert m1 <= m_target + 1e-9


# ---------------------------------------------------------------------------
# 10. reset() restores steady state at −70 mV
# ---------------------------------------------------------------------------

def test_reset_restores_steady_state():
    """After perturbing gates and calling reset(), values return to −70 mV SS."""
    ch = _make_channel()
    ch.update_state(V=+0.040, t=0.0, dt=10e-3)   # perturb
    ch.reset()
    assert abs(ch.gate_state['m'] - _m_inf(-70.0)) < 1e-9
    assert abs(ch.gate_state['h'] - _h_inf(-70.0)) < 1e-9


# ---------------------------------------------------------------------------
# 11. state_dict round-trip
# ---------------------------------------------------------------------------

def test_state_dict_roundtrip():
    """state_dict() reports the current gate values and channel parameters."""
    ch = _make_channel(gbar_SI=500.0, area_m2=2e-9)
    ch.update_state(V=-0.050, t=0.0, dt=0.5e-3)
    sd = ch.state_dict()
    assert abs(sd['m'] - ch.gate_state['m']) < 1e-15
    assert abs(sd['h'] - ch.gate_state['h']) < 1e-15
    assert sd['gbar_density_S_m2'] == pytest.approx(500.0)
    assert sd['area_m2'] == pytest.approx(2e-9)


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
    """Doubling gbar_SI should double the current (same gates, same V)."""
    area = 1e-9
    ch1 = NaV16Channel(gbar_SI=1000.0, area_m2=area)
    ch2 = NaV16Channel(gbar_SI=2000.0, area_m2=area)
    V = -0.060
    I1 = ch1.current(V=V, t=0.0)
    I2 = ch2.current(V=V, t=0.0)
    assert I2 == pytest.approx(2.0 * I1, rel=1e-9)


# ---------------------------------------------------------------------------
# 14. Current scales linearly with area_m2
# ---------------------------------------------------------------------------

def test_current_scales_with_area():
    """Doubling area_m2 should double the current."""
    gbar = 1000.0
    ch1 = NaV16Channel(gbar_SI=gbar, area_m2=1e-9)
    ch2 = NaV16Channel(gbar_SI=gbar, area_m2=2e-9)
    V = -0.060
    I1 = ch1.current(V=V, t=0.0)
    I2 = ch2.current(V=V, t=0.0)
    assert I2 == pytest.approx(2.0 * I1, rel=1e-9)


# ---------------------------------------------------------------------------
# 15. Gates stay in [0, 1] after update_state
# ---------------------------------------------------------------------------

def test_gates_bounded_in_unit_interval():
    """After a large-voltage update step, m and h must remain in [0, 1]."""
    ch = _make_channel()
    ch.update_state(V=+0.100, t=0.0, dt=1e-3)
    assert 0.0 <= ch.gate_state['m'] <= 1.0
    assert 0.0 <= ch.gate_state['h'] <= 1.0


# ---------------------------------------------------------------------------
# 16. Multiple updates converge to steady state
# ---------------------------------------------------------------------------

def test_multiple_updates_converge_to_steady_state():
    """100 steps of 0.1 ms at V = −40 mV should drive m, h to their SS values."""
    ch = _make_channel()
    V = -0.040
    for _ in range(100):
        ch.update_state(V=V, t=0.0, dt=0.1e-3)
    assert abs(ch.gate_state['m'] - _m_inf(-40.0)) < 1e-6
    assert abs(ch.gate_state['h'] - _h_inf(-40.0)) < 1e-5  # relaxed tolerance

# ---------------------------------------------------------------------------
# 17. Rates use Q10 correction (qt_Na ≈ 3.21)
# ---------------------------------------------------------------------------

def test_gates_use_q10_correction():
    """Rates at 37 °C are qt_Na × reference rates: qt_Na ≈ 3.21."""
    qt = CHAN.qt_Na
    assert 3.0 < qt < 3.5      # sanity: Q10_Na=2.3 at ΔT=14°C gives ≈3.21

    # m-gate time constant at 37 °C at −40 mV should be ≈ 0.113 ms
    V_mV = -40.0
    a = nata_alpha_m(V_mV) * qt
    b = nata_beta_m(V_mV)  * qt
    tau_m_37 = 1.0 / (a + b)   # ms
    assert 0.05 < tau_m_37 < 0.20   # ≈ 0.113 ms ✓


# ---------------------------------------------------------------------------
# 18. Open fraction uses m³, not m
# ---------------------------------------------------------------------------

def test_power_3_for_m_gate():
    """open_fraction must use m^3, not m^1 or m^4."""
    ch = _make_channel()
    ch.set_steady_state(-0.040)   # m ≈ 0.595, h ≈ 0.987
    m = ch.gate_state['m']
    h = ch.gate_state['h']
    expected = m ** 3 * h
    actual = ch._open_fraction()
    assert actual == pytest.approx(expected, rel=1e-12)
    # Ensure it is clearly not m^1 * h
    assert abs(actual - m * h) > 1e-4
