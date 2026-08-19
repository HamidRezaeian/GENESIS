"""simulation — Cable solvers and support infrastructure.

Components
----------
CrankNicolsonSolver
    Assembles the sparse G matrix + C vector from compartment geometry.
    Solves (C/dt - G/2) V^{n+1} = (C/dt + G/2) V^n + b each step.
    Phase 0a: fully implicit (all mechanisms are linear leak).

ActiveSolver
    Phase 0b.  CrankNicolsonSolver extended with voltage-gated channels via
    the Hines (1984) staggered semi-implicit scheme: gates advance on V^n,
    channel currents are linearised into the matrix diagonal / RHS, and the
    system is solved implicitly.  Unconditionally stable for any gbar, dt > 0.

Recorder
    Stores V(t) for all compartments. Supports soma-only and full-neuron
    recording modes. Provides exponential-fit utilities for tau_m extraction.

CurrentClamp
    Models a patch-clamp electrode: constant or step current injection
    at a specified compartment. Used for Rin and tau_m measurements.
"""

from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.active_solver import ActiveSolver
from biophysical.simulation.recorder import Recorder
from biophysical.simulation.current_clamp import (
    CurrentClampProtocol as CurrentClamp,
    MultiProtocol,
)

__all__ = [
    "CrankNicolsonSolver",
    "ActiveSolver",
    "Recorder",
    "CurrentClamp",
    "MultiProtocol",
]
