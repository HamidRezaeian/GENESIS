"""cable_matrix.py — Conductance matrix for the passive cable neuron.

Builds the matrices needed for the Crank-Nicolson solver:

    C * dV/dt = G * V + b + I_ext

where:
    C   diagonal capacitance (N,)      F
    G   sparse conductance  (N, N)     S   (negative diagonal, positive off-diag)
    b   constant RHS        (N,)       A   from leak reversal potentials
    I_ext external current  (N,)       A   time-varying (updated each step)

G entries
---------
    G[i, i] = -(g_mem_i + sum_j g_ax_{ij})   (net leak + coupling loss)
    G[i, j] = g_ax_{ij}                        (axial coupling)

Axial conductance between adjacent compartments i and j
--------------------------------------------------------
    g_ax_{ij} = 1 / (R_half_i + R_half_j)   [S]
    R_half_k  = Ra_SI * (L_k / 2) / (pi * (d_k/2)^2)  [Ohm]

References
----------
[1] Koch C (1999) Biophysics of Computation. OUP  Ch. 6
[2] Hines M (1984) Efficient computation of branched nerve equations.
    Int J Biomed Comput 15:69-76.
[3] Rall W (1977) Core conductor theory.  In Handbook of Physiology Sect 1.
"""

from __future__ import annotations
import math
from typing import List, Tuple

import numpy as np
import scipy.sparse as sp

from biophysical.morphology.compartment import Compartment
from biophysical.core.constants import MEM


def r_half_ohm(comp: Compartment, Ra_SI: float) -> float:
    """Half-compartment axial resistance (Ohm, SI).

    R_half = Ra_SI * (L/2) / A_cross
           = Ra_SI * (L/2) / (pi * r^2)
           = Ra_SI * L / (2 * pi * r^2)    where r = d/2

    Parameters
    ----------
    comp   : Compartment
    Ra_SI  : float  specific axial resistance (Ohm m). E.g. 1.0 for 100 Ohm.cm.

    Returns
    -------
    float  half-compartment axial resistance in Ohm.
    """
    r = comp.diameter_m / 2.0
    if r < 1e-30:
        return 1e30   # degenerate guard
    return Ra_SI * comp.length_m / (2.0 * math.pi * r * r)


def build_cable_matrix(
    compartments: List[Compartment],
    Ra_SI: float = MEM.Ra_SI,
) -> Tuple[np.ndarray, sp.csc_matrix, np.ndarray]:
    """Build C_vec, G_mat, b_vec for the cable equation.

    Parameters
    ----------
    compartments : List[Compartment]  with passive mechanisms already attached.
    Ra_SI        : float  specific axial resistance (Ohm m).

    Returns
    -------
    C_vec : np.ndarray (N,)        capacitance per compartment (F).
    G_mat : sp.csc_matrix (N, N)   conductance matrix (Siemens).
    b_vec : np.ndarray (N,)        constant RHS (A), from gL * EL terms.
    """
    N = len(compartments)
    C_vec = np.zeros(N, dtype=np.float64)
    b_vec = np.zeros(N, dtype=np.float64)
    G = sp.lil_matrix((N, N), dtype=np.float64)

    # ---- Capacitance and linear membrane conductances ----
    for i, comp in enumerate(compartments):
        C_vec[i] = comp.total_capacitance_F
        A = comp.surface_area_m2
        for mech in comp.mechanisms:
            if mech.is_linear:
                g = mech.conductance_density * A   # S
                G[i, i] -= g
                b_vec[i] += g * mech.reversal_potential   # A (= S * V)
            # Non-linear (e.g. NaKPump with I=0): contributes 0 in Phase 0a.
            # Phase 0b+ will add non-linear I to the RHS at each step.

    # ---- Axial coupling (parent-child only; tree topology) ----
    # Each parent-child pair is processed exactly once when iterating over
    # the child compartment.  The parent's coupling entry is updated here too.
    for i, comp in enumerate(compartments):
        p = comp.parent_idx
        if p is None:
            continue
        R_i = r_half_ohm(comp, Ra_SI)
        R_p = r_half_ohm(compartments[p], Ra_SI)
        g_ax = 1.0 / (R_i + R_p)   # S

        G[i, i] -= g_ax
        G[p, p] -= g_ax
        G[i, p] += g_ax
        G[p, i] += g_ax

    return C_vec, G.tocsc(), b_vec
