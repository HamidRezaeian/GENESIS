"""lipid_bilayer.py — Plasma membrane passive electrical properties.

Phase 0a passive parameter set (see core/constants.py, FIX#1)
------------------------------------------------------------
    Cm      = 1.0 uF/cm^2    (= 1e-2 F/m^2)   soma, dendrites, AIS, axon
    Rm      = 30000 Ohm.cm^2 (= 3.0 Ohm.m^2)  all regions
    Ra      = 200 Ohm.cm     (= 2.0 Ohm.m)    axial resistivity

    tau_m   = Rm * Cm                   = 30 ms
    lambda  = sqrt(Rm*d/(4*Ra))         = 1369 um at d = 5 um

The first draft used Cm_dend = 2.0 uF/cm^2 with Rm = 15000 Ohm.cm^2 and
Ra = 100 Ohm.cm.  That combination gives the same tau_m and the same lambda,
but only half the somatic input resistance (~36 MOhm instead of the 50-200
MOhm measured in human L5 neurons), so Rm and Ra were doubled and Cm_dend
returned to the canonical 1.0 uF/cm^2.

References
----------
[1] Hodgkin AL, Katz B (1949) J Physiol 108:37-77   Cm = 1 uF/cm^2 (canonical)
[2] Eyal G et al. (2016) eLife 5:e16553             human L2/3 + L5 passive fits
[3] Beaulieu-Laroche et al. (2018) Cell 175:643     human L5 Rin and V_rest
"""

from __future__ import annotations
from typing import Any, Dict, Sequence

from biophysical.morphology.compartment import Compartment
