"""l5_pyramidal.py — Compartment tree builder for the human L5 pyramidal neuron.

Consumes SectionSpec parametric data from l5_pyramidal_data.py and produces a
flat, topologically ordered list of Compartment objects with parent-child
connectivity set.  All compartments are initialised at V = EL = -70 mV.

Usage
-----
    from biophysical.morphology.l5_pyramidal import build_l5_pyramidal

    compartments, meta = build_l5_pyramidal()
    # compartments: List[Compartment], length 224
    # meta['soma_idx']           -> 0
    # meta['apical_trunk_idxs']  -> [1, 2, ..., 15]
    # meta['n_compartments']     -> 224
    # meta['total_area_um2']     -> float  (~15 000-20 000 µm²)
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple

from biophysical.morphology.compartment import Compartment, CompartmentType
from biophysical.morphology.l5_pyramidal_data import get_section_specs
from biophysical.core.constants import MEM


def _normalise(dx: float, dy: float, dz: float) -> Tuple[float, float, float]:
    """Normalise direction vector; return (0, 1, 0) for zero vectors."""
    mag = math.sqrt(dx * dx + dy * dy + dz * dz)
    if mag < 1e-15:
        return 0.0, 1.0, 0.0
    return dx / mag, dy / mag, dz / mag


# Maps SectionSpec comp_type string to the appropriate meta-dict key.
_TYPE_KEY: Dict[str, str] = {
    'SOMA':           'soma_idx',
    'APICAL_TRUNK':   'apical_trunk_idxs',
    'APICAL_OBLIQUE': 'apical_oblique_idxs',
    'APICAL_TUFT':    'apical_tuft_idxs',
    'BASAL':          'basal_idxs',
    'AIS':            'ais_idxs',
    'MYELIN':         'myelin_idxs',
    'NODE':           'node_idxs',
    'AXON_TERMINAL':  'terminal_idxs',
}


def build_l5_pyramidal(
    apply_bilayer: bool = True,
) -> Tuple[List[Compartment], Dict]:
    """Build and return the compartment tree for the human L5 pyramidal neuron.

    Iterates through the ordered SectionSpec list and creates Compartment
    objects, linking each to its parent and recording children_idxs.

    Parameters
    ----------
    apply_bilayer : bool
        If True (default), attach a LeakChannel to every compartment via
        LipidBilayer.apply_to_compartments().  Set False only if you are
        building the tree for inspection without any mechanisms.

    Returns
    -------
    compartments : List[Compartment]
        Flat list of 224 Compartment objects in tree order.
        compartments[0] is always the soma.
    meta : dict with keys:
        'soma_idx'             : int
        'apical_trunk_idxs'    : List[int]
        'apical_oblique_idxs'  : List[int]
        'apical_tuft_idxs'     : List[int]
        'basal_idxs'           : List[int]
        'ais_idxs'             : List[int]
        'myelin_idxs'          : List[int]
        'node_idxs'            : List[int]
        'terminal_idxs'        : List[int]
        'n_compartments'       : int
        'total_area_m2'        : float
        'total_area_um2'       : float
    """
    specs = get_section_specs()
    compartments: List[Compartment] = []

    # section_label -> index of last compartment in that section
    last_of_section: Dict[str, int] = {}
    # section_label -> 3-D position (m) of distal (far) end of section
    end_pos: Dict[str, Tuple[float, float, float]] = {}

    meta: Dict = {
        'soma_idx':            -1,
        'apical_trunk_idxs':   [],
        'apical_oblique_idxs': [],
        'apical_tuft_idxs':    [],
        'basal_idxs':          [],
        'ais_idxs':            [],
        'myelin_idxs':         [],
        'node_idxs':           [],
        'terminal_idxs':       [],
    }

    for spec in specs:
        # ---- Determine proximal start position and parent compartment idx ----
        if spec.parent_label is None:
            parent_idx: Optional[int] = None
            px, py, pz = 0.0, 0.0, 0.0
        else:
            parent_idx = last_of_section[spec.parent_label]
            px, py, pz = end_pos[spec.parent_label]

        # ---- Section geometry ----
        ux, uy, uz = _normalise(spec.dir_x, spec.dir_y, spec.dir_z)
        L_m    = spec.length_um * 1e-6          # total section length (m)
        L_comp = L_m / spec.n_comps             # per-compartment length (m)
        comp_type = CompartmentType[spec.comp_type]

        # ---- Create compartments sequentially within this section ----
        for i in range(spec.n_comps):
            # Midpoint fraction along section (for diameter interpolation)
            frac = (i + 0.5) / spec.n_comps
            d_m  = ((spec.diam_start_um +
                     (spec.diam_end_um - spec.diam_start_um) * frac) * 1e-6)

            # Compartment centre position
            offset = (i + 0.5) * L_comp
            cx = px + ux * offset
            cy = py + uy * offset
            cz = pz + uz * offset

            this_idx   = len(compartments)
            comp_parent = parent_idx if i == 0 else this_idx - 1

            # FIX BUG#1: Compartment dataclass uses private field names _idx
            # and _parent_idx in __init__.  Pass them with the underscore prefix.
            comp = Compartment(
                _idx        = this_idx,
                comp_type   = comp_type,
                diameter_m  = d_m,
                length_m    = L_comp,
                x           = cx,
                y           = cy,
                z           = cz,
                _parent_idx = comp_parent,
            )
            comp.V = MEM.E_leak_V

            # Register this compartment as a child of its parent.
            if comp_parent is not None:
                compartments[comp_parent].children_idxs.append(this_idx)

            compartments.append(comp)

            # Accumulate into meta lists.
            key = _TYPE_KEY.get(spec.comp_type)
            if key:
                if key == 'soma_idx':
                    meta['soma_idx'] = this_idx
                else:
                    meta[key].append(this_idx)

        # Record the distal-end index and position for child sections.
        last_of_section[spec.label] = len(compartments) - 1
        end_pos[spec.label] = (
            px + ux * L_m,
            py + uy * L_m,
            pz + uz * L_m,
        )

    # ---- Attach passive mechanisms ----
    if apply_bilayer:
        from biophysical.membrane.lipid_bilayer import LipidBilayer
        LipidBilayer().apply_to_compartments(compartments)

    # ---- Summary statistics ----
    total_area_m2 = sum(c.surface_area_m2 for c in compartments)
    meta['n_compartments'] = len(compartments)
    meta['total_area_m2']  = total_area_m2
    meta['total_area_um2'] = total_area_m2 * 1e12

    return compartments, meta
