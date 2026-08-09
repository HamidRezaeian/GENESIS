"""interfaces.py — Abstract base classes for all biophysical components.

Phase 0a concrete implementations
----------------------------------
    AbstractCompartment       -> morphology.compartment.Compartment
    AbstractMembraneMechanism -> membrane.leak_channel.LeakChannel
                              -> membrane.nak_pump.NaKPump
    AbstractSolver            -> simulation.crank_nicolson.CrankNicolsonSolver

Future phase implementations (ABCs are already defined here)
-------------------------------------------------------------
    Phase 0b : HHNaChannel, HHKChannel, Kv1Channel, CaLChannel, HCNChannel
    Phase 0c : AMPAReceptor, NMDAReceptor, GABAaReceptor, GABAbReceptor
    Phase 0d : CaMKII, Calcineurin, IP3Receptor, SERCA, PMCA
    Phase 0e : GeneExpressionEngine (DNA->mRNA->Protein)
    Phase 0f : Mitochondrion, EndoplasmicReticulum, Cytoskeleton
    Phase 0g : MetabolicEngine (ATP budget, glycolysis, TCA, OxPhos)
    Phase 0h : CellCycleController (mitosis, apoptosis)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING
import numpy as np


# ===========================================================================
# Root abstract class
# ===========================================================================

class BiophysComponent(ABC):
    """Root ABC for every simulated biological component.

    Every component must:
      - expose a unique human-readable name
      - serialise its state to a plain dict (logging / checkpointing)
      - reset to t=0 initial conditions
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable component identifier."""

    @abstractmethod
    def state_dict(self) -> Dict[str, Any]:
        """Return current internal state as a JSON-serialisable dict."""

    @abstractmethod
    def reset(self) -> None:
        """Restore to t=0 initial conditions."""


# ===========================================================================
# Compartment
# ===========================================================================

class AbstractCompartment(BiophysComponent):
    """A single cable compartment of the neuron morphology.

    Geometry
    --------
    Each compartment is modelled as a right-circular cylinder:
        surface_area_m2  = pi * diameter_m * length_m
        volume_m3        = pi * (diameter_m/2)^2 * length_m

    For the soma (modelled as a sphere-equivalent):
        surface_area_m2  = pi * diameter_m * length_m   (oblate spheroid approx)

    Indexing
    --------
    idx           : unique integer (0-based) assigned by the morphology builder
    parent_idx    : idx of parent compartment; None for the soma (root)
    children_idxs : list of idxs of direct child compartments

    Parent-child relationships are stored as *index references* so that the
    sparse solver can build the conductance matrix without circular refs.
    """

    @property
    @abstractmethod
    def idx(self) -> int:
        """Global compartment index (0-based)."""

    @property
    @abstractmethod
    def V(self) -> float:
        """Membrane voltage in Volts (SI). At rest: approx -0.070 V."""

    @V.setter
    @abstractmethod
    def V(self, value: float) -> None:
        """Set membrane voltage in Volts."""

    @property
    @abstractmethod
    def surface_area_m2(self) -> float:
        """Membrane surface area in m^2 (SI)."""

    @property
    @abstractmethod
    def volume_m3(self) -> float:
        """Compartment volume in m^3 (SI)."""

    @property
    @abstractmethod
    def Cm_SI(self) -> float:
        """Specific membrane capacitance for this compartment type (F m^-2)."""

    @property
    def capacitance_F(self) -> float:
        """Total compartment capacitance: Cm_SI * surface_area_m2 (Farads)."""
        return self.Cm_SI * self.surface_area_m2

    @property
    @abstractmethod
    def parent_idx(self) -> Optional[int]:
        """Index of parent compartment; None if this is the root (soma)."""

    @property
    @abstractmethod
    def children_idxs(self) -> List[int]:
        """Indices of all direct child compartments."""

    @property
    @abstractmethod
    def mechanisms(self) -> List["AbstractMembraneMechanism"]:
        """All membrane mechanisms active on this compartment."""

    @abstractmethod
    def add_mechanism(self, mech: "AbstractMembraneMechanism") -> None:
        """Attach a membrane mechanism to this compartment."""

    @abstractmethod
    def total_mechanism_current_density(self, t: float) -> float:
        """Sum of all mechanism current densities at time t (A m^-2)."""


# ===========================================================================
# Membrane mechanism
# ===========================================================================

class AbstractMembraneMechanism(BiophysComponent):
    """A source of transmembrane current acting on a compartment.

    Sign convention
    ---------------
    Positive current density (A m^-2) is *inward* (depolarising).
    Outward currents (e.g. K+ efflux, Na+/K+ pump) are negative.

    Linearity and matrix incorporation
    -----------------------------------
    Linear mechanisms (is_linear = True) define I = g*(V - E).  These can be
    folded into the conductance matrix G, making the Crank-Nicolson solve
    fully implicit and unconditionally stable.

    Non-linear mechanisms (Phase 0b+ HH channels) use operator splitting:
    the mechanism current is evaluated at V^n and added to the RHS.
    """

    @abstractmethod
    def current(self, V: float, t: float) -> float:
        """Transmembrane current density (A m^-2) at voltage V and time t.

        Parameters
        ----------
        V : float  membrane voltage in Volts
        t : float  simulation time in seconds

        Returns
        -------
        float  current density A m^-2  (positive = inward = depolarising)
        """

    @abstractmethod
    def update_state(self, V: float, t: float, dt: float) -> None:
        """Advance any gating variables by one timestep dt.

        For purely passive mechanisms (Phase 0a) this is a no-op.
        Phase 0b channels integrate HH-style ODEs here.

        Parameters
        ----------
        V  : float  membrane voltage in Volts
        t  : float  current simulation time in seconds
        dt : float  timestep in seconds
        """

    @property
    def is_linear(self) -> bool:
        """True if current is linear in V: I = g*(V - E).

        When True the mechanism can be folded into G for full implicitness.
        Phase 0a mechanisms (LeakChannel, NaKPump in Phase 0a mode) are linear.
        """
        return False

    @property
    def conductance_density(self) -> float:
        """Membrane conductance density g (S m^-2) for linear mechanisms.

        Returns 0.0 for non-linear mechanisms (not used by solver).
        """
        return 0.0

    @property
    def reversal_potential(self) -> float:
        """Reversal potential E (V) for linear mechanisms. 0.0 otherwise."""
        return 0.0


# ===========================================================================
# Solver
# ===========================================================================

class AbstractSolver(ABC):
    """Time-integration engine for the multi-compartment cable equation.

    Cable equation per compartment i
    ---------------------------------
      C_i * dV_i/dt = sum_j G_ij*(V_j - V_i)  +  sum_k I_k(V_i, t)  +  I_ext_i

    where:
      C_i     = Cm_i * A_i           total membrane capacitance (F)
      G_ij    = 1/Ri_j               axial conductance to neighbour j (S)
      I_k     = mechanism currents   A m^-2 (integrated over area gives A)
      I_ext_i = external electrode   A m^-2

    Crank-Nicolson discretisation
    ------------------------------
      (C/dt - G/2) * V^{n+1} = (C/dt + G/2) * V^n + b^{n+1/2}

    Phase 0a: all mechanisms are linear, so G includes leak conductances.
    The matrix is built once and LU-factorised; each step is one solve.

    Phase 0b+: non-linear HH channels are operator-split and added to RHS.
    """

    @abstractmethod
    def build(self, compartments: Sequence[AbstractCompartment]) -> None:
        """Pre-compute G matrix and C vector from compartment geometry.

        Must be called once before any call to step().
        """

    @abstractmethod
    def step(
        self,
        V: np.ndarray,
        t: float,
        dt: float,
        I_ext: np.ndarray,
    ) -> np.ndarray:
        """Advance voltage by one Crank-Nicolson step.

        Parameters
        ----------
        V     : ndarray (N,)  membrane voltages in V at time t
        t     : float         current simulation time in seconds
        dt    : float         timestep in seconds
        I_ext : ndarray (N,)  external current density in A m^-2

        Returns
        -------
        ndarray (N,)  membrane voltages in V at time t + dt
        """
