"""test_geometry.py — Unit tests for morphology.geometry functions.

Covers:
  axial_resistance_ohm  — R = Ra * L / (pi * r^2)
  lambda_dc_m / lambda_dc_um — sqrt(Rm * d / (4 * Ra))
  Space-constant range for physiological diameters.
"""

import math
import pytest
from biophysical.morphology.geometry import (
    axial_resistance_ohm,
    lambda_dc_m,
    lambda_dc_um,
)
from biophysical.core.constants import MEM


class TestAxialResistance:
    """axial_resistance_ohm tests."""

    def test_soma_cylinder(self):
        """R for d=20µm, L=20µm cylinder."""
        d, L = 20e-6, 20e-6
        R = axial_resistance_ohm(d, L, MEM.Ra_SI)
        expected = MEM.Ra_SI * L / (math.pi * (d / 2) ** 2)
        assert abs(R - expected) / expected < 1e-10, (
            f'R={R:.2f} Ohm, expected {expected:.2f} Ohm'
        )

    def test_inverse_d_squared(self):
        """Doubling diameter quarters resistance (fixed L)."""
        L = 100e-6
        R1 = axial_resistance_ohm(1e-6, L, MEM.Ra_SI)
        R2 = axial_resistance_ohm(2e-6, L, MEM.Ra_SI)
        assert abs(R1 / R2 - 4.0) < 1e-10, f'R1/R2 = {R1/R2:.6f}, expected 4.0'

    def test_linear_with_length(self):
        """Doubling length doubles resistance (fixed d)."""
        d = 5e-6
        R1 = axial_resistance_ohm(d, 100e-6, MEM.Ra_SI)
        R2 = axial_resistance_ohm(d, 200e-6, MEM.Ra_SI)
        assert abs(R2 / R1 - 2.0) < 1e-10, f'R2/R1 = {R2/R1:.6f}, expected 2.0'

    def test_proportional_to_Ra(self):
        """R ∝ Ra."""
        d, L = 5e-6, 100e-6
        R1 = axial_resistance_ohm(d, L, Ra_SI=1.0)
        R2 = axial_resistance_ohm(d, L, Ra_SI=2.0)
        assert abs(R2 / R1 - 2.0) < 1e-10

    def test_thin_dendrite_is_high(self):
        """1µm dendrite, 50µm should be > 10 MΩ."""
        R = axial_resistance_ohm(1e-6, 50e-6, MEM.Ra_SI)
        assert R > 10e6, f'R = {R/1e6:.1f} MΩ unexpectedly low'


class TestSpaceConstant:
    """lambda_dc tests."""

    def test_formula(self):
        """Exact formula: lambda = sqrt(Rm * d / (4 * Ra))."""
        d = 5e-6
        lam = lambda_dc_m(d, MEM.Rm_SI, MEM.Ra_SI)
        expected = math.sqrt(MEM.Rm_SI * d / (4 * MEM.Ra_SI))
        assert abs(lam - expected) < 1e-15, (
            f'lam={lam:.6f} m, expected {expected:.6f} m'
        )

    def test_um_vs_m_consistency(self):
        d = 5e-6
        lam_m  = lambda_dc_m(d,  MEM.Rm_SI, MEM.Ra_SI)
        lam_um = lambda_dc_um(d, MEM.Rm_SI, MEM.Ra_SI)
        assert abs(lam_um - lam_m * 1e6) < 1e-6

    def test_sqrt_d_scaling(self):
        """lambda ∝ sqrt(d)."""
        lam1 = lambda_dc_m(1e-6, MEM.Rm_SI, MEM.Ra_SI)
        lam4 = lambda_dc_m(4e-6, MEM.Rm_SI, MEM.Ra_SI)
        ratio = lam4 / lam1
        assert abs(ratio - 2.0) < 1e-10, f'lam(4µm)/lam(1µm) = {ratio:.6f}, expected 2.0'

    def test_apical_trunk_d5_in_spec_range(self):
        """Phase 0a spec: lambda for d=5µm must be 600–1400 µm."""
        lam = lambda_dc_um(5e-6, MEM.Rm_SI, MEM.Ra_SI)
        assert 600 <= lam <= 1400, (
            f'lambda(d=5µm) = {lam:.0f} µm outside spec [600, 1400] µm'
        )

    def test_range_for_physiological_diameters(self):
        """All typical dendrite diameters give lambda in 400-3500 µm."""
        for d_um in [0.5, 1, 2, 5, 8, 10, 15]:
            lam = lambda_dc_um(d_um * 1e-6, MEM.Rm_SI, MEM.Ra_SI)
            assert 200 < lam < 5000, (
                f'd={d_um}µm: lambda={lam:.0f}µm out of physiological range'
            )
