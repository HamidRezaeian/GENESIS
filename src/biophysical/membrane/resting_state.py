"""resting_state.py — Steady-state resting potential solver.

For the Phase 0a passive model:
    - All mechanisms are linear leak channels: I = -gL*(V - EL)
    - Na+/K+ pump current = 0 (absorbed into EL = -70 mV)

Analytical result
-----------------
At steady state (dV/dt = 0), the cable equation reduces to:
    G * V_rest = b_const

With only linear leak (gL * EL) on the RHS and gL on the diagonal,
every compartment settles to V_rest = EL = -70 mV, regardless of
morphology.  This is because the boundary conditions (sealed ends)
and the uniformity of EL across the tree give a spatially uniform
steady state.

Verification
------------
Set every compartment to EL, inject 0 current: dV/dt = 0. QED.

References
----------
[1] Koch C (1999) Biophysics of Computation. OUP  Ch. 2 (steady-state cable)
[2] Rall W (1977) Core conductor theory. In: Handbook of Physiology, Sect 1.
"""

from __future__ import annotations
from typing import Sequence
import numpy as np

from biophysical.morphology.compartment import Compartment
from biophysical.core.constants import MEM


def analytical_resting_potential_V() -> float:
    """Return the analytical resting potential for the Phase 0a model (Volts).

    For uniform EL = -70 mV across all compartments and I_pump = 0,
    every compartment reaches V_rest = EL at steady state.

    Returns
    -------
    float  MEM.E_leak_V = -0.070 V
    """
    return MEM.E_leak_V


def set_resting_state(compartments: Sequence[Compartment]) -> None:
    """Set all compartment voltages to the analytical resting potential."""
    V_rest = analytical_resting_potential_V()
    for c in compartments:
        c.V = V_rest


def compute_resting_potential(
    compartments: Sequence[Compartment],
    solver=None,
    dt_s: float = 5e-3,
    t_settle_s: float = 0.5,
    tol_V: float = 1e-10,
) -> np.ndarray:
    """Numerically integrate to steady state and return V_rest per compartment.

    Runs the CN solver for t_settle_s seconds with I_ext = 0 starting from
    V = EL everywhere.  For Phase 0a with uniform EL, this converges in 0
    steps (all compartments already at equilibrium).

    Parameters
    ----------
    compartments : Sequence[Compartment]
    solver       : CrankNicolsonSolver (optional).  If None, returns analytical.
    dt_s         : timestep (s) for the settling run. Default 5 ms.
    t_settle_s   : settling duration (s). Default 500 ms.
    tol_V        : convergence threshold on max |dV| per step (V).

    Returns
    -------
    np.ndarray shape (N,)  resting voltages in Volts.
    """
    N = len(compartments)
    V = np.full(N, MEM.E_leak_V, dtype=np.float64)

    if solver is None:
        # Analytical result: uniform EL for Phase 0a
        return V.copy()

    I_ext = np.zeros(N, dtype=np.float64)
    n_steps = int(round(t_settle_s / dt_s))

    for _ in range(n_steps):
        V_new = solver.step(V, 0.0, dt_s, I_ext)
        max_dV = float(np.max(np.abs(V_new - V)))
        V = V_new
        if max_dV < tol_V:
            break

    return V
