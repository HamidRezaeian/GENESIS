"""simulation — Crank-Nicolson cable solver and support infrastructure.

Components
----------
CrankNicolsonSolver
    Assembles the sparse G matrix + C vector from compartment geometry.
    Solves (C/dt - G/2) V^{n+1} = (C/dt + G/2) V^n + b each step.
    Phase 0a: fully implicit (all mechanisms are linear leak).
    Phase 0b+: operator-split for nonlinear HH channels.

StateRecorder
    Stores V(t) for all compartments. Supports soma-only and full-neuron
    recording modes. Provides exponential-fit utilities for tau_m extraction.

CurrentClamp
    Models a patch-clamp electrode: constant or step current injection
    at a specified compartment. Used for Rin and tau_m measurements.
"""

from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.recorder import StateRecorder
from biophysical.simulation.current_clamp import CurrentClamp

__all__ = ["CrankNicolsonSolver", "StateRecorder", "CurrentClamp"]
