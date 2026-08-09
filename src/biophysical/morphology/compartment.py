"""compartment.py — Compartment dataclass: one cable segment of the neuron.

Geometry (SI, right-circular cylinder)
---------------------------------------
    surface_area_m2 = pi * d * L
    volume_m3       = pi * (d/2)^2 * L
    cross_section   = pi * (d/2)^2

Axial coupling  (half-compartment convention)
---------------------------------------------
    Ra_half_i = Ra * L_i / (2 * A_cross_i)    [Koch 1999 eq 2.6]
    R_ij      = Ra_half_i + Ra_half_j

References
----------
[1] Koch C (1999) Biophysics of Computation. OUP  Ch. 2
[2] Hay E et al. (2011) PLoS Comput Biol 7:e1002107
[3] Eyal G et al. (2016) eLife 5:e16553
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from biophysical.core.interfaces import AbstractCompartment, AbstractMembraneMechanism
from biophysical.core.constants import MEM


class CompartmentType(Enum):
    """Biological region of a compartment, used to select Cm and properties."""
    SOMA           = auto()   # cell body
    APICAL_TRUNK   = auto()   # main apical dendrite shaft
    APICAL_TUFT    = auto()   # distal apical tuft branches
    APICAL_OBLIQUE = auto()   # oblique branches from apical trunk
    BASAL          = auto()   # basal dendrites
    AIS            = auto()   # axon initial segment
    MYELIN         = auto()   # myelinated internodal axon
    NODE           = auto()   # node of Ranvier
    AXON_TERMINAL  = auto()   # axon bouton / terminal


# Specific membrane capacitance by region (F m^-2)
# Soma / axon : 1.0 uF/cm^2 = 1e-2 F/m^2  [Hodgkin & Katz 1949]
# Dendrites   : 2.0 uF/cm^2 = 2e-2 F/m^2  [Eyal et al. 2016, Table 1, Human]
_CM_BY_TYPE: Dict[CompartmentType, float] = {
    CompartmentType.SOMA:           MEM.Cm_soma_SI,
    CompartmentType.APICAL_TRUNK:   MEM.Cm_dend_SI,
    CompartmentType.APICAL_TUFT:    MEM.Cm_dend_SI,
    CompartmentType.APICAL_OBLIQUE: MEM.Cm_dend_SI,
    CompartmentType.BASAL:          MEM.Cm_dend_SI,
    CompartmentType.AIS:            MEM.Cm_axon_SI,
    CompartmentType.MYELIN:         MEM.Cm_axon_SI,
    CompartmentType.NODE:           MEM.Cm_axon_SI,
    CompartmentType.AXON_TERMINAL:  MEM.Cm_axon_SI,
}


@dataclass
class Compartment(AbstractCompartment):
    """Single cylindrical compartment of the multi-compartment cable model.

    All geometric values in SI (metres, Farads, Ohms, Volts).

    Parameters
    ----------
    _idx           : unique 0-based integer index assigned by builder
    comp_type      : CompartmentType  biological region
    diameter_m     : cylinder diameter in metres
    length_m       : cylinder length in metres
    x, y, z        : 3-D centre position in metres
    _parent_idx    : index of parent; None for the root (soma)
    _children_idxs : indices of direct child compartments
    _V             : membrane voltage in Volts (initialised to E_leak)
    _mechanisms    : attached AbstractMembraneMechanism objects
    """

    _idx:           int                              = field(repr=True)
    comp_type:      CompartmentType                  = field(repr=True)
    diameter_m:     float                            = field(repr=True)
    length_m:       float                            = field(repr=True)
    x:              float                            = field(default=0.0,  repr=False)
    y:              float                            = field(default=0.0,  repr=False)
    z:              float                            = field(default=0.0,  repr=False)
    _parent_idx:    Optional[int]                    = field(default=None, repr=False)
    _children_idxs: List[int]                        = field(default_factory=list, repr=False)
    _V:             float                            = field(default=MEM.E_leak_V, repr=False)
    _mechanisms:    List[AbstractMembraneMechanism]  = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ #
    # BiophysComponent
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return f'Compartment[{self._idx}:{self.comp_type.name}]'

    def state_dict(self) -> Dict[str, Any]:
        return {
            'idx':         self._idx,
            'type':        self.comp_type.name,
            'V_mV':        self._V * 1e3,
            'diameter_um': self.diameter_m * 1e6,
            'length_um':   self.length_m   * 1e6,
            'area_um2':    self.surface_area_m2 * 1e12,
            'n_mechs':     len(self._mechanisms),
        }

    def reset(self) -> None:
        """Reset voltage to E_leak and reset all attached mechanisms."""
        self._V = MEM.E_leak_V
        for m in self._mechanisms:
            m.reset()

    # ------------------------------------------------------------------ #
    # AbstractCompartment geometry
    # ------------------------------------------------------------------ #

    @property
    def idx(self) -> int:
        return self._idx

    @property
    def V(self) -> float:
        return self._V

    @V.setter
    def V(self, value: float) -> None:
        self._V = float(value)

    @property
    def surface_area_m2(self) -> float:
        """Lateral cylinder surface area pi*d*L (m^2)."""
        return math.pi * self.diameter_m * self.length_m

    @property
    def volume_m3(self) -> float:
        """Cylinder volume pi*(d/2)^2*L (m^3)."""
        r = self.diameter_m * 0.5
        return math.pi * r * r * self.length_m

    @property
    def cross_section_m2(self) -> float:
        """Axial cross-sectional area pi*(d/2)^2 (m^2)."""
        r = self.diameter_m * 0.5
        return math.pi * r * r

    @property
    def Cm_SI(self) -> float:
        """Specific membrane capacitance F/m^2 for this compartment type."""
        return _CM_BY_TYPE[self.comp_type]

    @property
    def capacitance_F(self) -> float:
        """Total capacitance Cm*A (Farads)."""
        return self.Cm_SI * self.surface_area_m2

    # ------------------------------------------------------------------ #
    # Tree connectivity
    # ------------------------------------------------------------------ #

    @property
    def parent_idx(self) -> Optional[int]:
        return self._parent_idx

    @property
    def children_idxs(self) -> List[int]:
        return self._children_idxs

    # ------------------------------------------------------------------ #
    # Mechanisms
    # ------------------------------------------------------------------ #

    @property
    def mechanisms(self) -> List[AbstractMembraneMechanism]:
        return self._mechanisms

    def add_mechanism(self, mech: AbstractMembraneMechanism) -> None:
        """Attach a membrane mechanism."""
        self._mechanisms.append(mech)

    def total_mechanism_current_density(self, t: float) -> float:
        """Sum of all mechanism current densities A/m^2 at time t."""
        return sum(m.current(self._V, t) for m in self._mechanisms)

    # ------------------------------------------------------------------ #
    # Axial resistance
    # ------------------------------------------------------------------ #

    def half_axial_resistance(self) -> float:
        """Ra * L / (2 * A_cross)  [Ohms].  Koch (1999) eq 2.6.

        This is the resistance contribution from the proximal half of this
        compartment's axial path to its coupling point with the parent.
        Full coupling resistance = self.half_axial_resistance() + parent.half_axial_resistance()
        """
        return MEM.Ra_SI * self.length_m / (2.0 * self.cross_section_m2)

    def __repr__(self) -> str:
        return (
            f'Compartment(idx={self._idx}, type={self.comp_type.name}, '
            f'd={self.diameter_m*1e6:.2f}um, L={self.length_m*1e6:.2f}um, '
            f'V={self._V*1e3:.1f}mV)'
        )
