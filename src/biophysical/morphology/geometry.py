"""geometry.py — Cable geometry calculations for the compartment tree.

All public functions accept SCALAR SI values (metres, Ohms, Siemens) and
explicit membrane/axial resistance parameters (Rm_SI, Ra_SI).  This ensures
functions are fully testable without relying on module-level constants.

Public API
----------
axial_resistance_ohm(d_m, L_m, Ra_SI)           full cylinder resistance (Ohm)
axial_conductance_S(d_m, L_m, Ra_SI)            coupling conductance     (S)
lambda_dc_m(diameter_m, Rm_SI, Ra_SI)           DC space constant        (m)
lambda_dc_um(diameter_m, Rm_SI, Ra_SI)          DC space constant        (um)
check_morphology_stats(compartments)             morphometric stats dict
build_coupling_map(compartments, Ra_SI)          adjacency map for solver
electrotonic_distance_from_soma(compartments, target_idx, Rm_SI, Ra_SI)

BUG#2 fix: axial_resistance_ohm now takes (d_m, L_m, Ra_SI) not (comp_a, comp_b).
BUG#3 fix: lambda_dc_m / lambda_dc_um now take (diameter_m, Rm_SI, Ra_SI).

References
----------
[1] Koch C (1999) Biophysics of Computation. OUP  Ch. 2
[2] Hay E et al. (2011) PLoS Comput Biol 7:e1002107
[3] Stuart GJ, Spruston N (1998) J Neurosci 18:3501-3510
[4] Rall W (1977) Core conductor theory. Handbook of Physiology Sect 1.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Sequence, Tuple

from biophysical.core.constants import MEM
from biophysical.morphology.compartment import Compartment, CompartmentType


# ---------------------------------------------------------------------------
# Scalar geometry functions  (BUG#2 + BUG#3 fixes)
# ---------------------------------------------------------------------------

def axial_resistance_ohm(d_m: float, L_m: float, Ra_SI: float) -> float:
    """Full axial resistance of a uniform cylinder segment (Ohm, SI).

    R = Ra_SI * L / (pi * r^2)    where r = d / 2

    BUG#2 FIX: was axial_resistance_ohm(comp_a, comp_b) taking two Compartment
    objects.  Changed to scalar (d_m, L_m, Ra_SI) so tests and geometry code
    can call it without constructing Compartment instances.

    Parameters
    ----------
    d_m   : float  cylinder diameter in metres.
    L_m   : float  cylinder length in metres.
    Ra_SI : float  specific axial resistance (Ohm m).  E.g. 1.0 for 100 Ohm.cm.

    Returns
    -------
    float  axial resistance in Ohms.

    Notes
    -----
    For the half-compartment convention used by the cable solver, pass
    L_m = comp.length_m / 2.  The coupling conductance between compartments
    i and j is then  1 / (axial_resistance_ohm(d_i, L_i/2, Ra) +
                           axial_resistance_ohm(d_j, L_j/2, Ra)).
    """
    r = d_m / 2.0
    if r < 1e-30:
        return 1e30   # degenerate guard
    return Ra_SI * L_m / (math.pi * r * r)


def axial_conductance_S(d_m: float, L_m: float, Ra_SI: float) -> float:
    """Axial conductance of a uniform cylinder segment (Siemens, SI).

    g = 1 / axial_resistance_ohm(d_m, L_m, Ra_SI)

    Parameters
    ----------
    d_m   : float  cylinder diameter in metres.
    L_m   : float  cylinder length in metres.
    Ra_SI : float  specific axial resistance (Ohm m).
    """
    return 1.0 / axial_resistance_ohm(d_m, L_m, Ra_SI)


def lambda_dc_m(diameter_m: float, Rm_SI: float, Ra_SI: float) -> float:
    """DC electrotonic length constant lambda (metres).

    lambda = sqrt(Rm_SI * d / (4 * Ra_SI))     [Koch 1999 eq 2.17]

    BUG#3 FIX: was lambda_dc_m(diameter_m) with Rm_SI/Ra_SI hardcoded from
    MEM singleton.  Changed to explicit parameters for testability.

    Typical values (Rm=1.5 Ohm m^2, Ra=1.0 Ohm m — Eyal 2016 human L5):
        d = 1 um  ->  lambda =  612 um
        d = 5 um  ->  lambda = 1369 um
        d = 8 um  ->  lambda = 1732 um

    Parameters
    ----------
    diameter_m : float  compartment diameter in metres.
    Rm_SI      : float  specific membrane resistance (Ohm m^2).
    Ra_SI      : float  specific axial resistance (Ohm m).

    Returns
    -------
    float  DC space constant in metres.
    """
    return math.sqrt(Rm_SI * diameter_m / (4.0 * Ra_SI))


def lambda_dc_um(diameter_m: float, Rm_SI: float, Ra_SI: float) -> float:
    """DC electrotonic length constant in micrometres (display convenience).

    BUG#3 FIX: was lambda_dc_um(diameter_m) with Rm_SI/Ra_SI hardcoded.

    Parameters
    ----------
    diameter_m : float  compartment diameter in metres.
    Rm_SI      : float  specific membrane resistance (Ohm m^2).
    Ra_SI      : float  specific axial resistance (Ohm m).

    Returns
    -------
    float  DC space constant in micrometres.
    """
    return lambda_dc_m(diameter_m, Rm_SI, Ra_SI) * 1e6


# ---------------------------------------------------------------------------
# Morphometric statistics
# ---------------------------------------------------------------------------

def check_morphology_stats(compartments: Sequence[Compartment]) -> Dict[str, float]:
    """Compute morphometric statistics for a full compartment list.

    Returns a dict with compartment counts, surface areas, and cable lengths
    per region and in total.  All areas in um^2, all lengths in um.
    """
    counts:  Dict[str, int]   = {t.name: 0   for t in CompartmentType}
    areas:   Dict[str, float] = {t.name: 0.0 for t in CompartmentType}
    lengths: Dict[str, float] = {t.name: 0.0 for t in CompartmentType}

    for c in compartments:
        tn = c.comp_type.name
        counts[tn]  += 1
        areas[tn]   += c.surface_area_m2 * 1e12   # m^2 → um^2
        lengths[tn] += c.length_m        * 1e6    # m   → um

    apical_names = {
        CompartmentType.APICAL_TRUNK.name,
        CompartmentType.APICAL_TUFT.name,
        CompartmentType.APICAL_OBLIQUE.name,
    }
    axonal_names = {
        CompartmentType.AIS.name,
        CompartmentType.MYELIN.name,
        CompartmentType.NODE.name,
        CompartmentType.AXON_TERMINAL.name,
    }

    total_area    = sum(areas.values())
    apical_area   = sum(areas[t]   for t in apical_names)
    basal_area    = areas[CompartmentType.BASAL.name]
    axon_area     = sum(areas[t]   for t in axonal_names)
    apical_length = sum(lengths[t] for t in apical_names)
    basal_length  = lengths[CompartmentType.BASAL.name]

    return {
        'n_total':          len(compartments),
        'n_soma':           counts[CompartmentType.SOMA.name],
        'n_apical_trunk':   counts[CompartmentType.APICAL_TRUNK.name],
        'n_apical_tuft':    counts[CompartmentType.APICAL_TUFT.name],
        'n_apical_oblique': counts[CompartmentType.APICAL_OBLIQUE.name],
        'n_basal':          counts[CompartmentType.BASAL.name],
        'n_ais':            counts[CompartmentType.AIS.name],
        'n_myelin':         counts[CompartmentType.MYELIN.name],
        'n_node':           counts[CompartmentType.NODE.name],
        'n_axon_terminal':  counts[CompartmentType.AXON_TERMINAL.name],
        'total_area_um2':   total_area,
        'soma_area_um2':    areas[CompartmentType.SOMA.name],
        'apical_area_um2':  apical_area,
        'basal_area_um2':   basal_area,
        'axon_area_um2':    axon_area,
        'total_length_um':  sum(lengths.values()),
        'apical_length_um': apical_length,
        'basal_length_um':  basal_length,
    }


# ---------------------------------------------------------------------------
# Solver helpers
# ---------------------------------------------------------------------------

def build_coupling_map(
    compartments: Sequence[Compartment],
    Ra_SI: float = MEM.Ra_SI,
) -> Dict[int, List[Tuple[int, float]]]:
    """Build adjacency map {idx: [(neighbour_idx, g_S), ...]} for the solver.

    Uses the half-compartment convention:

        g_ij = 1 / (R_half_i + R_half_j)
        R_half_k = axial_resistance_ohm(d_k, L_k / 2, Ra_SI)

    Each undirected edge appears once in both directions.

    Parameters
    ----------
    compartments : Sequence[Compartment]
    Ra_SI        : float  specific axial resistance (Ohm m). Defaults to MEM.Ra_SI.

    Returns
    -------
    Dict[int, List[Tuple[int, float]]]
        Adjacency: compartment index -> list of (neighbour_idx, conductance_S).
    """
    by_idx: Dict[int, Compartment] = {c.idx: c for c in compartments}
    adj: Dict[int, List[Tuple[int, float]]] = {c.idx: [] for c in compartments}

    for comp in compartments:
        if comp.parent_idx is None:
            continue
        parent = by_idx[comp.parent_idx]
        R_half_comp   = axial_resistance_ohm(comp.diameter_m,   comp.length_m   / 2.0, Ra_SI)
        R_half_parent = axial_resistance_ohm(parent.diameter_m, parent.length_m / 2.0, Ra_SI)
        g = 1.0 / (R_half_comp + R_half_parent)
        adj[comp.idx].append((parent.idx, g))
        adj[parent.idx].append((comp.idx, g))

    return adj


def electrotonic_distance_from_soma(
    compartments: Sequence[Compartment],
    target_idx:   int,
    Rm_SI: float  = MEM.Rm_SI,
    Ra_SI: float  = MEM.Ra_SI,
) -> float:
    """Electrotonic distance X = sum(L_i / lambda_i) from soma to target.

    Walks from target_idx up to the root (soma), summing L/lambda at each
    compartment.  Uses DC lambda (voltage-independent steady-state value).

    Parameters
    ----------
    compartments : Sequence[Compartment]
    target_idx   : int    index of the distal target compartment.
    Rm_SI        : float  specific membrane resistance (Ohm m^2). Default = MEM.Rm_SI.
    Ra_SI        : float  specific axial resistance (Ohm m).       Default = MEM.Ra_SI.

    Returns
    -------
    float  dimensionless electrotonic distance X (0.0 at soma).
    """
    by_idx: Dict[int, Compartment] = {c.idx: c for c in compartments}
    comp = by_idx[target_idx]
    X = 0.0
    while comp.parent_idx is not None:
        lam = lambda_dc_m(comp.diameter_m, Rm_SI, Ra_SI)
        X  += comp.length_m / lam
        comp = by_idx[comp.parent_idx]
    return X
