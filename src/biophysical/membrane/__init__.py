"""membrane — Passive membrane components for the human L5 pyramidal neuron.

Phase 0a components (all passive)
----------------------------------
    LipidBilayer   — assigns Cm_SI and Rm_SI per CompartmentType
    LeakChannel    — ohmic leak: I = gL * (V - EL)   [linear, folds into G]
    NaKPump        — constant background pump current  [linear in Phase 0a]

Phase 0g replacement
---------------------
    NaKPump will be replaced by a full Post-Albers kinetic model of the
    Na+/K+ ATPase (3 Na+ out / 2 K+ in per ATP), coupled to the metabolic
    engine and ATP concentration.

References
----------
Hay E et al. (2011) PLoS Comput Biol 7:e1002107
Eyal G et al. (2016) eLife 5:e16553
Beaulieu-Laroche L et al. (2018) Cell 175:643-651.e14
"""

from biophysical.membrane.lipid_bilayer import LipidBilayer
from biophysical.membrane.leak_channel import LeakChannel
from biophysical.membrane.nak_pump import NaKPump
from biophysical.membrane.resting_state import compute_resting_potential

__all__ = ["LipidBilayer", "LeakChannel", "NaKPump", "compute_resting_potential"]
