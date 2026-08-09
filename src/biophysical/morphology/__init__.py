"""morphology — Compartment tree for the human L5 pyramidal neuron.

Builder entry point::

    from biophysical.morphology import build_l5_pyramidal
    compartments = build_l5_pyramidal()   # list[Compartment], ~406 items

Morphology source
-----------------
Hay E et al. (2011) PLoS Comput Biol 7:e1002107  — L5PC NEURON model
    Morphometric parameters (diameters, lengths, branching).
Eyal G et al. (2016) eLife 5:e16553  — human-specific corrections
    Cm_dend = 2.0 uF/cm2, Rm = 15000 ohm.cm2.
"""

from biophysical.morphology.compartment import Compartment, CompartmentType
from biophysical.morphology.l5_pyramidal import build_l5_pyramidal

__all__ = ["Compartment", "CompartmentType", "build_l5_pyramidal"]
