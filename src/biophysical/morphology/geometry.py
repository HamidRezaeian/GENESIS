"""geometry.py — Cable geometry calculations for the compartment tree.

All functions work in SI units (metres, Ohms, Siemens).

Functions
---------
axial_resistance_ohm(a, b)          full coupling resistance  (Ohm)
axial_conductance_S(a, b)           coupling conductance      (S)
lambda_dc_m(diameter_m)             DC electrotonic length    (m)
lambda_dc_um(diameter_m)            DC electrotonic length    (um)
check_morphology_stats(compartments) morphometric statistics dict
build_coupling_map(compartments)    adjacency map for solver

References
----------
[1] Koch C (1999) Biophysics of Computation. OUP  Ch. 2
[2] Hay E et al. (2011) PLoS Comput Biol 7:e1002107
[3] Stuart GJ, Spruston N (1998) J Neurosci 18:3501-3510
"""

from __future__ import annotations
import math
from typing import Dict, List, Sequence, Tuple

from biophysical.core.constants import MEM
from biophysical.morphology.compartment import Compartment, CompartmentType


def axial_resistance_ohm(comp_a: Compartment, comp_b: Compartment) -> float:
    """Full axial coupling resistance between adjacent compartments (Ohm).

    R_ij = Ra*L_a/(2*A_a) + Ra*L_b/(2*A_b)    [Koch 1999 eq 2.6]

    Uses the half-compartment convention: each compartment contributes half
    its length to the coupling resistance at each of its endpoints.
    """
    return comp_a.half_axial_resistance() + comp_b.half_axial_resistance()


def axial_conductance_S(comp_a: Compartment, comp_b: Compartment) -> float:
    """Axial coupling conductance between adjacent compartments (S).

    g_ij = 1 / R_ij
    """
    return 1.0 / axial_resistance_ohm(comp_a, comp_b)


def lambda_dc_m(diameter_m: float) -> float:
    """DC electrotonic length constant lambda (metres).

    lambda = sqrt(Rm * d / (4 * Ra))     [Koch 1999 eq 2.17]

    For a typical apical trunk segment (d = 5 um):
        lambda = sqrt(1.5 * 5e-6 / 4.0) = 1369 um

    For a thin distal tuft (d = 1 um):
        lambda = sqrt(1.5 * 1e-6 / 4.0) = 612 um

    Parameters
    ----------
    diameter_m : float  compartment diameter in metres
    """
    return math.sqrt(MEM.Rm_SI * diameter_m / (4.0 * MEM.Ra_SI))


def lambda_dc_um(diameter_m: float) -> float:
    """DC electrotonic length constant in micrometres (display convenience)."""
    return lambda_dc_m(diameter_m) * 1e6


def check_morphology_stats(compartments: Sequence[Compartment]) -> Dict[str, float]:
    """Compute morphometric statistics for a full compartment list.

    Returns a dict with compartment counts, surface areas, and cable lengths
    per region and in total.

    All areas in um^2, all lengths in um.
    """
    counts:  Dict[str, int]   = {t.name: 0   for t in CompartmentType}
    areas:   Dict[str, float] = {t.name: 0.0 for t in CompartmentType}
    lengths: Dict[str, float] = {t.name: 0.0 for t in CompartmentType}

    for c in compartments:
        tn = c.comp_type.name
        counts[tn]  += 1
        areas[tn]   += c.surface_area_m2 * 1e12   # m^2  -> um^2
        lengths[tn] += c.length_m        * 1e6    # m    -> um

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


def build_coupling_map(
    compartments: Sequence[Compartment],
) -> Dict[int, List[Tuple[int, float]]]:
    """Build adjacency map: idx -> [(neighbour_idx, g_S), ...] for solver.

    Each undirected edge appears once in each direction.
    Used by simulation.cable_matrix to assemble the sparse G matrix.
    """
    by_idx = {c.idx: c for c in compartments}
    adj: Dict[int, List[Tuple[int, float]]] = {c.idx: [] for c in compartments}

    for comp in compartments:
        if comp.parent_idx is not None:
            parent = by_idx[comp.parent_idx]
            g = axial_conductance_S(comp, parent)
            adj[comp.idx].append((parent.idx, g))
            adj[parent.idx].append((comp.idx, g))

    return adj


def electrotonic_distance_from_soma(
    compartments: Sequence[Compartment],
    target_idx: int,
) -> float:
    """Electrotonic distance (X = L / lambda) from soma to compartment target_idx.

    Computed by summing L_i/lambda_i along the path from soma to target.
    Uses DC lambda (voltage-independent; AC lambda used for AC impedance analysis).

    Returns
    -------
    float  dimensionless electrotonic distance X
    """
    by_idx = {c.idx: c for c in compartments}
    target = by_idx[target_idx]
    X = 0.0
    comp = target
    while comp.parent_idx is not None:
        lam = lambda_dc_m(comp.diameter_m)
        X  += comp.length_m / lam
        comp = by_idx[comp.parent_idx]
    return X
