"""units.py — Lightweight SI unit tracking for biophysical quantities.

All internal calculations use SI base units:
    voltage          V   (volts)
    current          A   (amperes)
    current density  A m⁻²
    conductance      S   (siemens)
    resistance       Ω   (ohms)
    capacitance      F   (farads)
    length           m   (metres)
    area             m²
    volume           m³
    time             s   (seconds)
    amount           mol

This module provides a ``Quantity`` wrapper that carries a unit label for
documentation and safety checks. It does NOT impose pint as a runtime dep.

Usage
-----
    from biophysical.core.units import Q, ureg
    cm = Q(2.0e-2, ureg.F_m2)    # 2.0 µF/cm² expressed in SI
    print(cm.to_uF_cm2().value)   # 2.0
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Union


def _assert_unit(actual: str, substrings: tuple, target: str) -> None:
    if not any(s in actual for s in substrings):
        raise TypeError(
            f"Cannot convert '{actual}' → '{target}': "
            f"unit must contain one of {substrings}"
        )


@dataclass(frozen=True)
class Quantity:
    """Scalar float with an attached SI unit label.

    Parameters
    ----------
    value : float  — numeric value in the stated unit
    unit  : str    — unit descriptor, e.g. 'V', 'F/m^2', 'Ohm*m'
    """

    value: float
    unit: str

    def __repr__(self) -> str:
        return f"Q({self.value!r}, '{self.unit}')"

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"

    def __float__(self) -> float:
        return float(self.value)

    def __mul__(self, other: Union[float, int]) -> "Quantity":
        return Quantity(self.value * float(other), self.unit)

    def __rmul__(self, other: Union[float, int]) -> "Quantity":
        return self.__mul__(other)

    def __truediv__(self, other: Union[float, int]) -> "Quantity":
        return Quantity(self.value / float(other), self.unit)

    # ------------------------------------------------------------------ #
    # Unit conversions (SI base → common display units)                  #
    # ------------------------------------------------------------------ #

    def to_mV(self) -> "Quantity":
        """V → mV."""
        _assert_unit(self.unit, ("V",), "mV")
        return Quantity(self.value * 1e3, "mV")

    def to_ms(self) -> "Quantity":
        """s → ms."""
        _assert_unit(self.unit, ("s",), "ms")
        return Quantity(self.value * 1e3, "ms")

    def to_uF_cm2(self) -> "Quantity":
        """F m⁻² → µF cm⁻²  (factor = 1e2, not 1e10 — see derivation below).

        1 F m⁻² = 1 F / (1e4 cm²) = 1e-4 F/cm² = 1e-4 × 1e6 µF/cm² = 100 µF/cm²
        ⇒ multiply SI value by 100  (= 1e2).
        """
        _assert_unit(self.unit, ("F",), "uF/cm^2")
        return Quantity(self.value * 1e2, "uF/cm^2")

    def to_MOhm(self) -> "Quantity":
        """Ω → MΩ."""
        _assert_unit(self.unit, ("Ohm", "ohm"), "MOhm")
        return Quantity(self.value * 1e-6, "MOhm")

    def to_GOhm(self) -> "Quantity":
        """Ω → GΩ."""
        _assert_unit(self.unit, ("Ohm", "ohm"), "GOhm")
        return Quantity(self.value * 1e-9, "GOhm")

    def to_nA(self) -> "Quantity":
        """A → nA."""
        _assert_unit(self.unit, ("A",), "nA")
        return Quantity(self.value * 1e9, "nA")

    def to_pA(self) -> "Quantity":
        """A → pA."""
        _assert_unit(self.unit, ("A",), "pA")
        return Quantity(self.value * 1e12, "pA")

    def to_um(self) -> "Quantity":
        """m → µm."""
        _assert_unit(self.unit, ("m",), "um")
        return Quantity(self.value * 1e6, "um")

    def to_um2(self) -> "Quantity":
        """m² → µm²."""
        _assert_unit(self.unit, ("m^2", "m2"), "um^2")
        return Quantity(self.value * 1e12, "um^2")

    def to_ms_from_s(self) -> "Quantity":
        """Alias for to_ms()."""
        return self.to_ms()


# Convenience constructor alias
Q = Quantity


class _UnitRegistry:
    """String-constant SI unit labels used as Quantity.unit values.

    These are purely documentary — no dimensional analysis is performed.
    """
    V      = "V"
    mV     = "mV"
    A      = "A"
    pA     = "pA"
    nA     = "nA"
    S      = "S"
    S_m2   = "S/m^2"
    F      = "F"
    F_m2   = "F/m^2"
    Ohm    = "Ohm"
    Ohm_m2 = "Ohm*m^2"
    Ohm_m  = "Ohm*m"
    MOhm   = "MOhm"
    m      = "m"
    m2     = "m^2"
    m3     = "m^3"
    um     = "um"
    um2    = "um^2"
    um3    = "um^3"
    s      = "s"
    ms     = "ms"
    mol    = "mol"
    A_m2   = "A/m^2"
    kg     = "kg"


ureg = _UnitRegistry()
