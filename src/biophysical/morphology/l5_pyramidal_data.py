"""l5_pyramidal_data.py — Morphometric parameters for the human L5 pyramidal neuron.

Sources
-------
Primary morphology:
    Hay E et al. (2011) PLoS Comput Biol 7:e1002107.
    ModelDB accession #139653.  L5b thick-tufted pyramidal cell.

Human corrections:
    Eyal G et al. (2016) eLife 5:e16553.
    Cm_dend = 2.0 uF/cm^2, Rm = 15000 Ohm.cm^2.
    Morphometric scaling from their supplementary human reconstructions.

Experimental validation targets:
    Beaulieu-Laroche L et al. (2018) Cell 175:643-651.e14.
    Human L5 Rin = 74 ± 10 MOhm, tau_m ≈ 23 ms (Table S1).


Documented approximations (APPROX tags referenced in validation/report.py)
---------------------------------------------------------------------------
APPROX-1: Soma modelled as cylinder d = 20 µm, L = 20 µm.
           Published: Hay et al. measured soma 22.27 µm × 15 µm.
           Area ours = 1257 µm²; published ≈ 1050 µm² (+20%).
           Justification: Eyal et al. (2016) use a similar simplified
           soma cylinder; exact shape has minimal effect on passive
           cable dynamics (soma dominates at DC, not AC).

APPROX-2: Apical trunk tapering modelled as 5 equal sections of 180 µm each
           (total 900 µm), with linear diameter taper from 8.0 → 2.0 µm.
           Published Hay SWC: piecewise constant taper from SWC 3-D coords.
           Max diameter error: ≈ 0.5 µm per 180 µm section.

APPROX-3: Branch angles from published figures (Hay 2011 Fig. 1, Eyal 2016
           Fig. 2), not from raw 3-D SWC coordinates.  X,Y,Z coordinates
           are approximate; electrotonic distances are correct because they
           depend on diameter and length, which are faithfully reproduced.

APPROX-4: Basal dendritic trees: 6 trees, 4 orders, evenly spaced at 60°.
           Published: Hay et al. report 5–7 primary basal trees of varying
           branching order.  Choice of 6 is the midpoint of this range.
           Branching symmetry (identical sister branches) approximates the
           average of asymmetric real trees.

APPROX-5: Apical obliques: 5 primaries (2 from trunk_0, 2 from trunk_2,
           1 from trunk_3).  Published: Hay et al. report 4–6 obliques.
           5 is the midpoint.

APPROX-6: Compartment count = 224 (vs. ~400 in Hay et al. after Rall
           equivalent-cylinder optimisation of the full SWC).  The present
           count arises from the parametric design; each compartment is
           well below lambda/10 in electrotonic length, so spatial accuracy
           is preserved.  Phase 0b will optionally import the raw SWC.

APPROX-7: Axonal myelination: 5 identical internode-node pairs, internode
           length 100 µm, node length 1.5 µm.  From Rushton (1951) scaling
           laws for d = 1.5 µm axon: internode length ≈ 100 × d = 150 µm
           (we use 100 µm, slightly conservative).  Phase 0c will add
           voltage-gated Na+ channels at nodes.
"""

from __future__ import annotations
import math
from typing import List, NamedTuple, Optional


# ---------------------------------------------------------------------------
# Morphometric constants  (from Hay 2011 + Eyal 2016)
# ---------------------------------------------------------------------------
SECTION_COUNTS = {
    'n_basal_trees':       6,      # APPROX-4
    'n_apical_obliques':   5,      # APPROX-5
    'n_tuft_primaries':    2,
    'n_axon_nodes':        5,      # APPROX-7
}

SOMATIC_PARAMS = {
    'soma_d_um':   20.0,   # APPROX-1 (published: 22.27 µm)
    'soma_L_um':   20.0,   # APPROX-1 (published: 15.0 µm)
    'soma_area_um2': math.pi * 20.0 * 20.0,  # 1257 µm²
}

APICAL_PARAMS = {
    'trunk_prox_d_um':   8.0,    # at soma junction
    'trunk_distal_d_um': 2.0,    # at tuft bifurcation
    'trunk_length_um':   900.0,  # total trunk length
    'trunk_n_sections':  5,      # 5 × 180 µm sections
    'n_comps_per_trunk_section': 3,
}


# ---------------------------------------------------------------------------
# SectionSpec: parametric description of one dendritic branch section
# ---------------------------------------------------------------------------
class SectionSpec(NamedTuple):
    """Morphometric specification for a single cylindrical branch section.

    The builder (l5_pyramidal.py) divides each section into n_comps equal
    compartments with linearly interpolated diameter.  Direction vectors
    define the 3-D orientation of the section from its proximal endpoint;
    they need not be normalised (the builder normalises them).
    """
    label:          str             # unique section identifier
    comp_type:      str             # CompartmentType enum member name
    diam_start_um:  float           # proximal diameter (µm)
    diam_end_um:    float           # distal diameter (µm)
    length_um:      float           # total section length (µm)
    n_comps:        int             # compartments in this section
    parent_label:   Optional[str]   # parent section label (None for soma)
    dir_x:          float = 0.0    # direction vector x-component
    dir_y:          float = 1.0    # direction vector y-component  (+y = apical)
    dir_z:          float = 0.0    # direction vector z-component


# ---------------------------------------------------------------------------
# Soma + apical trunk
# ---------------------------------------------------------------------------
_SOMA_AND_TRUNK: List[SectionSpec] = [
    # Soma
    SectionSpec('soma', 'SOMA', 20.0, 20.0, 20.0, 1, None, 0.0, 1.0, 0.0),
    # Apical trunk — 5 sections, 180 µm each, linear taper 8→2 µm
    SectionSpec('at0', 'APICAL_TRUNK', 8.0, 6.5, 180.0, 3, 'soma',  0.0, 1.0, 0.0),
    SectionSpec('at1', 'APICAL_TRUNK', 6.5, 5.0, 180.0, 3, 'at0',   0.0, 1.0, 0.0),
    SectionSpec('at2', 'APICAL_TRUNK', 5.0, 3.5, 180.0, 3, 'at1',   0.0, 1.0, 0.0),
    SectionSpec('at3', 'APICAL_TRUNK', 3.5, 2.5, 180.0, 3, 'at2',   0.0, 1.0, 0.0),
    SectionSpec('at4', 'APICAL_TRUNK', 2.5, 2.0, 180.0, 3, 'at3',   0.0, 1.0, 0.0),
]

# ---------------------------------------------------------------------------
# Apical obliques — 5 primaries + 10 secondaries = 28 compartments total
# Attached at: at0 (2 obliques), at2 (2 obliques), at3 (1 oblique)
# ---------------------------------------------------------------------------
_OBLIQUES: List[SectionSpec] = [
    # at0 obliques (180 µm from soma)
    SectionSpec('ob_0a',    'APICAL_OBLIQUE', 2.5, 1.5, 120.0, 2, 'at0',  1.0,  0.2,  0.0),
    SectionSpec('ob_0a_s1', 'APICAL_OBLIQUE', 1.5, 1.0,  80.0, 2, 'ob_0a',  1.0,  0.1,  0.4),
    SectionSpec('ob_0a_s2', 'APICAL_OBLIQUE', 1.5, 1.0,  80.0, 2, 'ob_0a',  0.7,  0.1, -0.4),

    SectionSpec('ob_0b',    'APICAL_OBLIQUE', 2.5, 1.5, 120.0, 2, 'at0', -1.0,  0.2,  0.0),
    SectionSpec('ob_0b_s1', 'APICAL_OBLIQUE', 1.5, 1.0,  80.0, 2, 'ob_0b', -1.0,  0.1,  0.4),
    SectionSpec('ob_0b_s2', 'APICAL_OBLIQUE', 1.5, 1.0,  80.0, 2, 'ob_0b', -0.7,  0.1, -0.4),

    # at2 obliques (540 µm from soma)
    SectionSpec('ob_2a',    'APICAL_OBLIQUE', 2.0, 1.3, 120.0, 2, 'at2',  1.0,  0.2,  0.0),
    SectionSpec('ob_2a_s1', 'APICAL_OBLIQUE', 1.3, 0.8,  80.0, 2, 'ob_2a',  1.0,  0.1,  0.3),
    SectionSpec('ob_2a_s2', 'APICAL_OBLIQUE', 1.3, 0.8,  80.0, 2, 'ob_2a',  0.8,  0.1, -0.3),

    SectionSpec('ob_2b',    'APICAL_OBLIQUE', 2.0, 1.3, 120.0, 2, 'at2', -1.0,  0.2,  0.0),
    SectionSpec('ob_2b_s1', 'APICAL_OBLIQUE', 1.3, 0.8,  80.0, 2, 'ob_2b', -1.0,  0.1,  0.3),
    SectionSpec('ob_2b_s2', 'APICAL_OBLIQUE', 1.3, 0.8,  80.0, 2, 'ob_2b', -0.8,  0.1, -0.3),

    # at3 oblique (720 µm from soma)
    SectionSpec('ob_3a',    'APICAL_OBLIQUE', 1.8, 1.2, 100.0, 2, 'at3',  0.0,  0.2,  1.0),
    SectionSpec('ob_3a_s1', 'APICAL_OBLIQUE', 1.2, 0.8,  60.0, 1, 'ob_3a',  0.0,  0.1,  1.0),
    SectionSpec('ob_3a_s2', 'APICAL_OBLIQUE', 1.2, 0.8,  60.0, 1, 'ob_3a',  0.0,  0.1, -1.0),
]

# ---------------------------------------------------------------------------
# Apical tuft — 2 primary trunks × (1 primary + 2 secondary + 4 tertiary)
# = 14 sections, 30 compartments total
# ---------------------------------------------------------------------------
_TUFT: List[SectionSpec] = [
    # Left tuft
    SectionSpec('tf_L',        'APICAL_TUFT', 2.0, 1.5, 150.0, 3, 'at4', -0.4,  1.0,  0.0),
    SectionSpec('tf_L_s1',     'APICAL_TUFT', 1.5, 1.0, 100.0, 2, 'tf_L',   -0.3,  1.0,  0.4),
    SectionSpec('tf_L_s1_t1',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_L_s1',  -0.2,  1.0,  0.3),
    SectionSpec('tf_L_s1_t2',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_L_s1',  -0.5,  1.0,  0.6),
    SectionSpec('tf_L_s2',     'APICAL_TUFT', 1.5, 1.0, 100.0, 2, 'tf_L',   -0.3,  1.0, -0.4),
    SectionSpec('tf_L_s2_t1',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_L_s2',  -0.2,  1.0, -0.3),
    SectionSpec('tf_L_s2_t2',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_L_s2',  -0.5,  1.0, -0.6),
    # Right tuft
    SectionSpec('tf_R',        'APICAL_TUFT', 2.0, 1.5, 150.0, 3, 'at4',  0.4,  1.0,  0.0),
    SectionSpec('tf_R_s1',     'APICAL_TUFT', 1.5, 1.0, 100.0, 2, 'tf_R',    0.3,  1.0,  0.4),
    SectionSpec('tf_R_s1_t1',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_R_s1',   0.2,  1.0,  0.3),
    SectionSpec('tf_R_s1_t2',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_R_s1',   0.5,  1.0,  0.6),
    SectionSpec('tf_R_s2',     'APICAL_TUFT', 1.5, 1.0, 100.0, 2, 'tf_R',    0.3,  1.0, -0.4),
    SectionSpec('tf_R_s2_t1',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_R_s2',   0.2,  1.0, -0.3),
    SectionSpec('tf_R_s2_t2',  'APICAL_TUFT', 1.0, 0.6,  80.0, 2, 'tf_R_s2',   0.5,  1.0, -0.6),
]


def _make_basal_tree(tree_id: int) -> List[SectionSpec]:
    """Generate SectionSpecs for one basal dendritic tree (4 branching orders).

    Trees are distributed at 60° intervals in the horizontal (x-z) plane with a
    slight downward tilt (dy_frac = -0.3). Each tree has the same topology:
      primary -> 2 secondaries -> 4 tertiaries -> 8 quaternaries
    = 15 sections, 18 compartments (2+4+4+8).

    Parameters
    ----------
    tree_id : int  0..5.  Controls azimuthal angle = tree_id * 60 degrees.
    """
    angle = tree_id * math.pi / 3.0
    cx = math.cos(angle)
    cz = math.sin(angle)
    dy = -0.3   # slight downward angle for basal dendrites
    T = str(tree_id)

    def spread(ax: float, az: float) -> tuple:
        """Return (x, y, z) direction with lateral spread."""
        return cx * ax + cz * az, dy, cz * ax - cx * az

    p = f'bas{T}'   # primary section label

    specs: List[SectionSpec] = [
        # --- Primary (2 compartments) ---
        SectionSpec(p, 'BASAL', 3.5, 2.0, 100.0, 2, 'soma', cx, dy, cz),
        # --- Secondary A (2 compartments) ---
        SectionSpec(f'{p}_sA', 'BASAL', 2.0, 1.2, 80.0, 2, p,
                    *spread(0.9, +0.4)),
        # --- Tertiary A1 (1 compartment) ---
        SectionSpec(f'{p}_sA_t1', 'BASAL', 1.2, 0.8, 60.0, 1, f'{p}_sA',
                    *spread(0.9, +0.7)),
        SectionSpec(f'{p}_sA_t1_q1', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sA_t1',
                    *spread(0.8, +1.0)),
        SectionSpec(f'{p}_sA_t1_q2', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sA_t1',
                    *spread(1.0, +0.4)),
        # --- Tertiary A2 (1 compartment) ---
        SectionSpec(f'{p}_sA_t2', 'BASAL', 1.2, 0.8, 60.0, 1, f'{p}_sA',
                    *spread(1.0, +0.1)),
        SectionSpec(f'{p}_sA_t2_q1', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sA_t2',
                    *spread(1.0, +0.3)),
        SectionSpec(f'{p}_sA_t2_q2', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sA_t2',
                    *spread(0.8, -0.1)),
        # --- Secondary B (2 compartments) ---
        SectionSpec(f'{p}_sB', 'BASAL', 2.0, 1.2, 80.0, 2, p,
                    *spread(0.9, -0.4)),
        # --- Tertiary B1 (1 compartment) ---
        SectionSpec(f'{p}_sB_t1', 'BASAL', 1.2, 0.8, 60.0, 1, f'{p}_sB',
                    *spread(0.9, -0.7)),
        SectionSpec(f'{p}_sB_t1_q1', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sB_t1',
                    *spread(0.8, -1.0)),
        SectionSpec(f'{p}_sB_t1_q2', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sB_t1',
                    *spread(1.0, -0.4)),
        # --- Tertiary B2 (1 compartment) ---
        SectionSpec(f'{p}_sB_t2', 'BASAL', 1.2, 0.8, 60.0, 1, f'{p}_sB',
                    *spread(1.0, -0.1)),
        SectionSpec(f'{p}_sB_t2_q1', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sB_t2',
                    *spread(1.0, -0.3)),
        SectionSpec(f'{p}_sB_t2_q2', 'BASAL', 0.8, 0.5, 50.0, 1, f'{p}_sB_t2',
                    *spread(0.8, +0.1)),
    ]
    # Total: 15 sections -> 2+2+1+1+1+1+1+1+2+1+1+1+1+1+1 = 18 compartments
    return specs


def _make_ais_and_axon() -> List[SectionSpec]:
    """Generate AIS (7 comps) + 5 myelin-node pairs (30 comps) + 5 terminals."""
    specs: List[SectionSpec] = []

    # --- Axon initial segment: 7 × 5 µm = 35 µm total ---
    parent = 'soma'
    for i in range(7):
        label = f'ais_{i}'
        specs.append(SectionSpec(label, 'AIS', 1.2, 1.2, 5.0, 1, parent,
                                  0.0, -1.0, 0.0))
        parent = label

    # --- Myelinated internodes + nodes: 5 pairs ---
    for n in range(5):
        myelin_label = f'myelin_{n}'
        node_label   = f'node_{n}'
        specs.append(SectionSpec(myelin_label, 'MYELIN', 1.5, 1.5, 100.0, 5,
                                  parent, 0.0, -1.0, 0.0))
        specs.append(SectionSpec(node_label, 'NODE', 1.5, 1.5, 1.5, 1,
                                  myelin_label, 0.0, -1.0, 0.0))
        parent = node_label

    # --- Axon terminals: one small bouton per node (APPROX-7) ---
    for n in range(5):
        specs.append(SectionSpec(f'terminal_{n}', 'AXON_TERMINAL',
                                  1.0, 1.0, 3.0, 1, f'node_{n}',
                                  0.3, -1.0, 0.0))
    return specs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_section_specs() -> List[SectionSpec]:
    """Return the complete ordered list of SectionSpec for the human L5PC.

    Order matters: a section's parent must appear before it in the list.
    The builder (l5_pyramidal.py) processes sections in order.

    Compartment count summary
    -------------------------
    Soma          :   1
    Apical trunk  :  15  (5 sections x 3 comps)
    Apical oblique:  28  (15 sections x 1-2 comps)
    Apical tuft   :  30  (14 sections x 2-3 comps)
    Basal         : 108  (6 trees x 15 sections/tree x 1-2 comps = 18 comps/tree)
    AIS           :   7  (7 x 1 comp)
    Myelin        :  25  (5 x 5 comps)
    Nodes         :   5  (5 x 1 comp)
    Terminals     :   5  (5 x 1 comp)
    TOTAL         : 224
    """
    specs: List[SectionSpec] = []
    specs.extend(_SOMA_AND_TRUNK)
    specs.extend(_OBLIQUES)
    specs.extend(_TUFT)
    for tree_id in range(SECTION_COUNTS['n_basal_trees']):
        specs.extend(_make_basal_tree(tree_id))
    specs.extend(_make_ais_and_axon())
    return specs


# Module-level cached list for convenience
SECTION_SPECS: List[SectionSpec] = get_section_specs()

# Expected compartment count (for assertion in tests)
EXPECTED_N_COMPS: int = sum(s.n_comps for s in SECTION_SPECS)
