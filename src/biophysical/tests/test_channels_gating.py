"""test_channels_gating.py — Unit tests for channels/gating.py.

Covers:
  vtrap         — L'Hôpital at singularity, normal path, sign correctness
  q10_factor    — numerical values, reference-temperature identity
  nata_*        — NaTa_t rate functions at singularity (V=−40, −66) and normal (V=−55)
  skv3_*        — SKv3.1 steady-state and tau at rest and near AP peak
  Gate          — open_fraction, step_alpha_beta, step_inf_tau, cnexp exactness
  CHAN          — singleton values: reversal potentials, density ordering, qt_* factors

No solver, morphology, or membrane dependencies.
"""

import math
import pytest
from biophysical.channels.gating import (
    vtrap,
    Gate,
    q10_factor,
    nata_alpha_m,
    nata_beta_m,
    nata_alpha_h,
    nata_beta_h,
    skv3_n_inf,
    skv3_tau_n_ms,
)
from biophysical.core.constants import CHAN, T_CELSIUS


# ===========================================================================
# vtrap
# ===========================================================================

class TestVtrap:
    """vtrap(x, y) = x/(exp(x/y)−1); L'Hôpital limit at x=0 is y."""

    # --- Singularity at x = 0 -----------------------------------------------

    def test_singularity_m_gate_y_neg9(self):
        """vtrap(0, −9) = −9: L'Hôpital limit for NaTa_t α_m at V=−40 mV."""
        assert abs(vtrap(0.0, -9.0) - (-9.0)) < 1e-10, \
            f'vtrap(0, -9) = {vtrap(0.0, -9.0)}, expected -9.0'

    def test_singularity_m_gate_y_pos9(self):
        """vtrap(0, +9) = +9: L'Hôpital limit for NaTa_t β_m at V=−40 mV."""
        assert abs(vtrap(0.0, 9.0) - 9.0) < 1e-10, \
            f'vtrap(0, +9) = {vtrap(0.0, 9.0)}, expected +9.0'

    def test_singularity_h_gate_y_neg6(self):
        """vtrap(0, −6) = −6: L'Hôpital limit for NaTa_t α_h at V=−66 mV."""
        assert abs(vtrap(0.0, -6.0) - (-6.0)) < 1e-10, \
            f'vtrap(0, -6) = {vtrap(0.0, -6.0)}, expected -6.0'

    def test_singularity_h_gate_y_pos6(self):
        """vtrap(0, +6) = +6: L'Hôpital limit for NaTa_t β_h at V=−66 mV."""
        assert abs(vtrap(0.0, 6.0) - 6.0) < 1e-10, \
            f'vtrap(0, +6) = {vtrap(0.0, 6.0)}, expected +6.0'

    # --- Normal path at V = −55 mV (no singularity) -------------------------

    def test_normal_path_alpha_m_at_minus55(self):
        """vtrap(−15, −9) at V=−55 mV: matches direct formula (no L'Hôpital)."""
        x, y = -15.0, -9.0
        expected = x / (math.exp(x / y) - 1.0)
        result   = vtrap(x, y)
        assert abs(result - expected) < 1e-10, \
            f'vtrap({x}, {y}) = {result:.8f}, expected {expected:.8f}'

    def test_normal_path_beta_m_at_minus55(self):
        """vtrap(−15, +9) at V=−55 mV: matches direct formula."""
        x, y = -15.0, 9.0
        expected = x / (math.exp(x / y) - 1.0)
        result   = vtrap(x, y)
        assert abs(result - expected) < 1e-10, \
            f'vtrap({x}, {y}) = {result:.8f}, expected {expected:.8f}'

    # --- Sign correctness ---------------------------------------------------

    def test_positive_x_positive_y_gives_positive(self):
        """vtrap(x>0, y>0) > 0: exp(x/y)>1 → denominator>0."""
        assert vtrap(5.0, 9.0) > 0.0

    def test_negative_x_negative_y_gives_positive(self):
        """vtrap(x<0, y<0) > 0: both numerator and denominator negative."""
        assert vtrap(-5.0, -9.0) < 0.0  # x/y > 0, exp > 1, denominator positive, x negative

    def test_positive_x_negative_y_gives_negative(self):
        """vtrap(x>0, y<0) < 0: numerator>0, exp(x/y)<1 → denominator<0."""
        assert vtrap(5.0, -9.0) < 0.0

    def test_negative_x_positive_y_gives_negative(self):
        """vtrap(x<0, y>0) < 0: numerator<0, exp(x/y)<1 → denominator<0."""
        assert vtrap(-5.0, 9.0) > 0.0  # x/y < 0, exp < 1, denominator negative, x negative

    def test_continuity_through_zero(self):
        """vtrap is continuous at x=0: values at ±ε should be close to the limit."""
        y   = 9.0
        eps = 1e-7
        lim = vtrap(0.0, y)   # = 9.0  (L'Hôpital)
        assert abs(vtrap( eps, y) - lim) < 1e-4
        assert abs(vtrap(-eps, y) - lim) < 1e-4

    def test_second_order_taylor_accuracy(self):
        """Near x=0 the result should match y−x/2 (second-order Taylor)."""
        y, x = 9.0, 1e-8
        expected = y - x / 2.0
        assert abs(vtrap(x, y) - expected) < 1e-10


# ===========================================================================
# q10_factor
# ===========================================================================

class TestQ10Factor:
    """q10_factor(Q10, T, T_ref) = Q10^((T−T_ref)/10)."""

    def test_nata_at_37c(self):
        """NaTa_t Q10=2.3 from 23°C to 37°C: factor = 2.3^1.4."""
        expected = 2.3 ** 1.4
        result   = q10_factor(2.3, 37.0, 23.0)
        assert abs(result - expected) < 1e-10, \
            f'q10_factor(2.3, 37, 23) = {result:.6f}, expected {expected:.6f}'

    def test_skv3_at_37c(self):
        """SKv3.1 Q10=3.0 from 23°C to 37°C: factor = 3.0^1.4."""
        expected = 3.0 ** 1.4
        result   = q10_factor(3.0, 37.0, 23.0)
        assert abs(result - expected) < 1e-10, \
            f'q10_factor(3.0, 37, 23) = {result:.6f}, expected {expected:.6f}'

    def test_identity_at_reference_temperature(self):
        """Factor must be exactly 1.0 when T = T_ref."""
        assert q10_factor(2.3, 23.0, 23.0) == 1.0
        assert q10_factor(3.0, 23.0, 23.0) == 1.0

    def test_factor_above_one_when_warmer(self):
        """Factor > 1.0 for T > T_ref (kinetics speed up)."""
        assert q10_factor(2.0, 37.0, 23.0) > 1.0

    def test_factor_below_one_when_cooler(self):
        """Factor < 1.0 for T < T_ref (kinetics slow down)."""
        assert q10_factor(2.0, 10.0, 23.0) < 1.0

    def test_chan_qt_na_matches_formula(self):
        """CHAN.qt_Na == q10_factor(CHAN.Q10_Na, T_CELSIUS, CHAN.T_ref_celsius)."""
        expected = q10_factor(CHAN.Q10_Na, T_CELSIUS, CHAN.T_ref_celsius)
        assert abs(CHAN.qt_Na - expected) < 1e-12, \
            f'CHAN.qt_Na = {CHAN.qt_Na:.8f}, expected {expected:.8f}'

    def test_chan_qt_k_matches_formula(self):
        """CHAN.qt_K == q10_factor(CHAN.Q10_K, T_CELSIUS, CHAN.T_ref_celsius)."""
        expected = q10_factor(CHAN.Q10_K, T_CELSIUS, CHAN.T_ref_celsius)
        assert abs(CHAN.qt_K - expected) < 1e-12, \
            f'CHAN.qt_K = {CHAN.qt_K:.8f}, expected {expected:.8f}'


# ===========================================================================
# NaTa_t rate functions
# ===========================================================================

class TestNataTRates:
    """NaTa_t α/β rates at T_ref = 23°C; analytical values verified."""

    # --- m gate at V = −40 mV (singularity) ---------------------------------

    def test_alpha_m_at_minus40(self):
        """alpha_m(−40 mV) = −0.182 × vtrap(0, −9) = 1.638 ms⁻¹."""
        result = nata_alpha_m(-40.0)
        assert abs(result - 1.638) < 1e-4, \
            f'α_m(−40) = {result:.4f} ms⁻¹, expected 1.638 ms⁻¹'

    def test_beta_m_at_minus40(self):
        """beta_m(−40 mV) = 0.124 × vtrap(0, +9) = 1.116 ms⁻¹."""
        result = nata_beta_m(-40.0)
        assert abs(result - 1.116) < 1e-4, \
            f'β_m(−40) = {result:.4f} ms⁻¹, expected 1.116 ms⁻¹'

    def test_m_inf_at_minus40(self):
        """m∞(−40 mV) = α/(α+β) = 1.638/2.754 ≈ 0.595."""
        a, b = nata_alpha_m(-40.0), nata_beta_m(-40.0)
        m_inf = a / (a + b)
        assert abs(m_inf - 1.638 / 2.754) < 1e-4, \
            f'm∞(−40) = {m_inf:.4f}, expected ≈0.595'

    def test_tau_m_at_minus40_ref_temp_23c(self):
        """tau_m(−40 mV, 23°C) = 1/(α+β) ≈ 0.363 ms."""
        a, b = nata_alpha_m(-40.0), nata_beta_m(-40.0)
        tau  = 1.0 / (a + b)
        assert abs(tau - 0.363) < 0.005, \
            f'τ_m(−40, 23°C) = {tau:.4f} ms, expected ≈0.363 ms'

    def test_tau_m_at_minus40_body_temp_37c(self):
        """tau_m(−40 mV, 37°C) ≈ 0.113 ms  (plan target: ≈0.11 ms)."""
        a, b   = nata_alpha_m(-40.0), nata_beta_m(-40.0)
        tau_37 = 1.0 / ((a + b) * CHAN.qt_Na)
        assert abs(tau_37 - 0.113) < 0.005, \
            f'τ_m(−40, 37°C) = {tau_37:.4f} ms, expected ≈0.113 ms'

    # --- m gate at V = −55 mV (normal path, no L'Hôpital) ------------------

    def test_alpha_m_at_minus55_positive(self):
        """alpha_m(−55 mV) must be positive."""
        assert nata_alpha_m(-55.0) > 0.0

    def test_beta_m_at_minus55_positive(self):
        """beta_m(−55 mV) must be positive."""
        assert nata_beta_m(-55.0) > 0.0

    def test_alpha_m_at_minus55_value(self):
        """alpha_m(−55 mV) matches direct formula: −0.182 × vtrap(−15, −9)."""
        x, y = -15.0, -9.0
        expected = -0.182 * (x / (math.exp(x / y) - 1.0))
        result   = nata_alpha_m(-55.0)
        assert abs(result - expected) < 1e-8, \
            f'α_m(−55) = {result:.8f}, expected {expected:.8f}'

    # --- h gate at V = −66 mV (singularity; half-activation point) ----------

    def test_alpha_h_at_minus66(self):
        """alpha_h(−66 mV) = −0.015 × vtrap(0, −6) = 0.090 ms⁻¹."""
        result = nata_alpha_h(-66.0)
        assert abs(result - 0.090) < 1e-8, \
            f'α_h(−66) = {result:.8f}, expected 0.090 ms⁻¹'

    def test_beta_h_at_minus66(self):
        """beta_h(−66 mV) = 0.015 × vtrap(0, +6) = 0.090 ms⁻¹."""
        result = nata_beta_h(-66.0)
        assert abs(result - 0.090) < 1e-8, \
            f'β_h(−66) = {result:.8f}, expected 0.090 ms⁻¹'

    def test_h_half_activation_at_minus66(self):
        """h∞(−66 mV) = 0.5: alpha_h = beta_h at the singularity → h∞ = 0.5."""
        a, b  = nata_alpha_h(-66.0), nata_beta_h(-66.0)
        h_inf = a / (a + b)
        assert abs(h_inf - 0.5) < 1e-10, \
            f'h∞(−66) = {h_inf:.10f}, expected 0.5'

    def test_tau_h_at_rest_body_temp_in_range(self):
        """tau_h(−70 mV, 37°C) must be in the plan target range 0.25–2.5 ms."""
        a, b   = nata_alpha_h(-70.0), nata_beta_h(-70.0)
        tau_37 = 1.0 / ((a + b) * CHAN.qt_Na)
        assert 0.25 <= tau_37 <= 2.5, \
            f'τ_h(−70, 37°C) = {tau_37:.4f} ms — outside target [0.25, 2.5] ms'

    # --- Monotonicity -------------------------------------------------------

    def test_alpha_m_increases_with_depolarisation(self):
        """alpha_m increases with V: V=−70 < V=−40 < V=−20."""
        assert nata_alpha_m(-70.0) < nata_alpha_m(-40.0) < nata_alpha_m(-20.0)

    def test_beta_m_decreases_with_depolarisation(self):
        """beta_m decreases with V: V=−70 > V=−40 > V=−20."""
        assert nata_beta_m(-70.0) > nata_beta_m(-40.0) > nata_beta_m(-20.0)

    def test_all_nata_rates_positive_across_voltage_range(self):
        """All four NaTa_t rate functions must be positive from −90 to +50 mV."""
        for V in range(-90, 51, 10):
            Vf = float(V)
            assert nata_alpha_m(Vf) > 0, f'α_m({V}) = {nata_alpha_m(Vf):.6f} ≤ 0'
            assert nata_beta_m(Vf)  > 0, f'β_m({V}) = {nata_beta_m(Vf):.6f}  ≤ 0'
            assert nata_alpha_h(Vf) > 0, f'α_h({V}) = {nata_alpha_h(Vf):.6f} ≤ 0'
            assert nata_beta_h(Vf)  > 0, f'β_h({V}) = {nata_beta_h(Vf):.6f}  ≤ 0'


# ===========================================================================
# SKv3.1 rate functions
# ===========================================================================

class TestSkv3Rates:
    """SKv3.1 Boltzmann kinetics: n_inf and tau_n at T_ref = 23°C."""

    def test_n_inf_essentially_zero_at_rest(self):
        """n∞(−70 mV) ≈ 0: channel must be essentially closed at resting V."""
        assert skv3_n_inf(-70.0) < 1e-3, \
            f'n∞(−70) = {skv3_n_inf(-70.0):.6f}, expected < 0.001'

    def test_n_inf_half_activation_at_187mV(self):
        """n∞(+18.7 mV) = 0.5: half-activation voltage of SKv3.1."""
        result = skv3_n_inf(18.7)
        assert abs(result - 0.5) < 1e-10, \
            f'n∞(+18.7) = {result:.10f}, expected 0.5'

    def test_n_inf_mostly_open_at_ap_peak(self):
        """n∞(+40 mV) > 0.8: channel must be largely open at AP peak."""
        assert skv3_n_inf(40.0) > 0.8, \
            f'n∞(+40) = {skv3_n_inf(40.0):.4f}, expected > 0.8'

    def test_n_inf_monotonically_increasing(self):
        """n∞ must increase monotonically with depolarisation."""
        voltages = [-70.0, -40.0, 0.0, 18.7, 40.0]
        values   = [skv3_n_inf(V) for V in voltages]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], (
                f'n∞ not monotone at ({voltages[i]}, {voltages[i+1]}): '
                f'{values[i]:.6f} ≥ {values[i+1]:.6f}'
            )

    def test_n_inf_bounded_in_unit_interval(self):
        """n∞ must lie strictly in (0, 1) for all finite voltages."""
        for V in range(-100, 101, 10):
            n = skv3_n_inf(float(V))
            assert 0.0 < n < 1.0, f'n∞({V}) = {n:.8f} outside (0, 1)'

    def test_tau_n_peak_at_4656mV_ref_temp(self):
        """Peak tau_n occurs at V = +46.56 mV with value 2.0 ms (23°C)."""
        tau = skv3_tau_n_ms(46.56)
        assert abs(tau - 2.0) < 0.01, \
            f'tau_n(+46.56, 23°C) = {tau:.4f} ms, expected 2.0 ms'

    def test_tau_n_positive_across_voltage_range(self):
        """tau_n must be > 0 for all finite voltages."""
        for V in range(-100, 101, 10):
            tau = skv3_tau_n_ms(float(V))
            assert tau > 0.0, f'tau_n({V}) = {tau:.6f} ms ≤ 0'


# ===========================================================================
# Gate dataclass
# ===========================================================================

class TestGate:
    """Gate: open_fraction power, step_alpha_beta (cnexp), step_inf_tau."""

    # --- open_fraction -------------------------------------------------------

    def test_open_fraction_power_1(self):
        """x=0.5, power=1 → open_fraction = 0.5."""
        g = Gate(x=0.5, power=1)
        assert abs(g.open_fraction() - 0.5) < 1e-15

    def test_open_fraction_power_3(self):
        """x=0.5, power=3 → open_fraction = 0.125 (m³ gate)."""
        g = Gate(x=0.5, power=3)
        assert abs(g.open_fraction() - 0.125) < 1e-15

    def test_open_fraction_power_4(self):
        """x=0.5, power=4 → open_fraction = 0.0625 (n⁴ gate)."""
        g = Gate(x=0.5, power=4)
        assert abs(g.open_fraction() - 0.0625) < 1e-15

    def test_open_fraction_at_zero(self):
        """x=0 → open_fraction = 0 for any power."""
        for power in (1, 2, 3, 4):
            g = Gate(x=0.0, power=power)
            assert g.open_fraction() == 0.0

    def test_open_fraction_at_one(self):
        """x=1 → open_fraction = 1 for any power."""
        for power in (1, 2, 3, 4):
            g = Gate(x=1.0, power=power)
            assert g.open_fraction() == 1.0

    # --- step_alpha_beta: cnexp exactness ------------------------------------

    def test_cnexp_ab_analytical_value(self):
        """After one step x matches x_inf + (x0−x_inf)·exp(−dt·(α+β))."""
        x0, alpha, beta, dt = 0.3, 2.0, 3.0, 0.025   # ms
        x_inf    = alpha / (alpha + beta)              # 0.4
        expected = x_inf + (x0 - x_inf) * math.exp(-dt * (alpha + beta))
        g = Gate(x=x0, power=1)
        g.step_alpha_beta(alpha, beta, dt)
        assert abs(g.x - expected) < 1e-14, \
            f'step_alpha_beta: x={g.x:.14f}, expected={expected:.14f}'

    def test_cnexp_ab_exactness_one_vs_two_halfsteps(self):
        """One step of dt = two steps of dt/2  (cnexp is EXACT for linear ODE)."""
        x0, alpha, beta, dt = 0.2, 2.0, 3.0, 0.025

        g1 = Gate(x=x0, power=1)
        g1.step_alpha_beta(alpha, beta, dt)

        g2 = Gate(x=x0, power=1)
        g2.step_alpha_beta(alpha, beta, dt / 2.0)
        g2.step_alpha_beta(alpha, beta, dt / 2.0)

        assert abs(g1.x - g2.x) < 1e-14, (
            f'cnexp not exact: 1×dt={g1.x:.14f}, 2×(dt/2)={g2.x:.14f}'
        )

    def test_cnexp_ab_converges_to_xinf(self):
        """Many steps must drive x toward x_inf."""
        alpha, beta = 3.0, 1.0   # x_inf = 0.75
        x_inf = alpha / (alpha + beta)
        g = Gate(x=0.0, power=1)
        for _ in range(2000):
            g.step_alpha_beta(alpha, beta, 0.05)
        assert abs(g.x - x_inf) < 1e-10, \
            f'Did not converge: x={g.x:.12f}, x_inf={x_inf}'

    def test_cnexp_ab_stable_large_dt(self):
        """dt = 1000 ms must not blow up (unconditional stability)."""
        g = Gate(x=0.2, power=1)
        g.step_alpha_beta(alpha_ms=1.0, beta_ms=1.0, dt_ms=1000.0)
        assert 0.0 <= g.x <= 1.0, f'Gate out of [0,1] after huge dt: x={g.x}'
        # exp(-2000) underflows to 0.0, so g.x = x_inf = 0.5 exactly
        assert abs(g.x - 0.5) < 1e-12

    # --- step_inf_tau: cnexp exactness --------------------------------------

    def test_cnexp_inf_tau_analytical_value(self):
        """After one step x matches x_inf + (x0−x_inf)·exp(−dt/τ)."""
        x0, x_inf, tau, dt = 0.2, 0.8, 1.5, 0.025
        expected = x_inf + (x0 - x_inf) * math.exp(-dt / tau)
        g = Gate(x=x0, power=1)
        g.step_inf_tau(x_inf, tau, dt)
        assert abs(g.x - expected) < 1e-14, \
            f'step_inf_tau: x={g.x:.14f}, expected={expected:.14f}'

    def test_cnexp_inf_tau_exactness_one_vs_two_halfsteps(self):
        """One step of dt = two steps of dt/2  (cnexp exact for linear ODE)."""
        x0, x_inf, tau, dt = 0.1, 0.9, 2.0, 0.025

        g1 = Gate(x=x0, power=1)
        g1.step_inf_tau(x_inf, tau, dt)

        g2 = Gate(x=x0, power=1)
        g2.step_inf_tau(x_inf, tau, dt / 2.0)
        g2.step_inf_tau(x_inf, tau, dt / 2.0)

        assert abs(g1.x - g2.x) < 1e-14, (
            f'cnexp inf/tau not exact: 1×dt={g1.x:.14f}, 2×(dt/2)={g2.x:.14f}'
        )

    def test_cnexp_inf_tau_stable_large_dt(self):
        """dt = 1000 ms must converge to x_inf (unconditional stability)."""
        x_inf = 0.7
        g = Gate(x=0.1, power=1)
        g.step_inf_tau(x_inf=x_inf, tau_ms=1.0, dt_ms=1000.0)
        assert abs(g.x - x_inf) < 1e-12, \
            f'Gate not at x_inf after huge dt: x={g.x}'

    def test_cnexp_inf_tau_zero_tau_snaps_to_xinf(self):
        """tau=0 (degenerate): gate must snap instantly to x_inf."""
        g = Gate(x=0.2, power=1)
        g.step_inf_tau(x_inf=0.9, tau_ms=0.0, dt_ms=0.025)
        assert g.x == 0.9, f'Expected snap to x_inf=0.9, got {g.x}'


# ===========================================================================
# CHAN singleton
# ===========================================================================

class TestChanSingleton:
    """CHAN singleton: reversal potentials, density ordering, Q10 multipliers."""

    def test_e_na_positive(self):
        """E_Na must be positive (Na Nernst, c_out >> c_in)."""
        assert CHAN.E_Na_V > 0.0, f'E_Na = {CHAN.E_Na_V:.4f} V, expected > 0'

    def test_e_k_negative(self):
        """E_K must be negative (K Nernst, c_in >> c_out)."""
        assert CHAN.E_K_V < 0.0, f'E_K = {CHAN.E_K_V:.4f} V, expected < 0'

    def test_ais_na_density_highest(self):
        """AIS Na density > soma > apical  (Hay 2011 gradient)."""
        assert CHAN.gbar_Na_AIS > CHAN.gbar_Na_soma > CHAN.gbar_Na_apical, (
            f'AIS={CHAN.gbar_Na_AIS}, soma={CHAN.gbar_Na_soma}, '
            f'apical={CHAN.gbar_Na_apical}'
        )

    def test_basal_densities_are_zero(self):
        """Basal dendrites: passive only — both gbar values must be 0."""
        assert CHAN.gbar_Na_basal == 0.0
        assert CHAN.gbar_K_basal  == 0.0

    def test_node_densities_equal_ais(self):
        """Nodes of Ranvier have the same density as AIS (saltatory conduction)."""
        assert CHAN.gbar_Na_node == CHAN.gbar_Na_AIS
        assert CHAN.gbar_K_node  == CHAN.gbar_K_AIS

    def test_qt_na_value(self):
        """qt_Na = 2.3^1.4 ≈ 3.21."""
        expected = 2.3 ** 1.4
        assert abs(CHAN.qt_Na - expected) < 1e-10, \
            f'CHAN.qt_Na = {CHAN.qt_Na:.6f}, expected {expected:.6f}'

    def test_qt_k_value(self):
        """qt_K = 3.0^1.4 ≈ 4.65."""
        expected = 3.0 ** 1.4
        assert abs(CHAN.qt_K - expected) < 1e-10, \
            f'CHAN.qt_K = {CHAN.qt_K:.6f}, expected {expected:.6f}'

    def test_t_ref_is_23c(self):
        """Reference temperature must be 23 °C (Mainen & Sejnowski 1996)."""
        assert CHAN.T_ref_celsius == 23.0
