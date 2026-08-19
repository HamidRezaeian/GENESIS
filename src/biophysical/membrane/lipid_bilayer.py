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
from biophysical.core.constants import MEM


class LipidBilayer:
    """Manages Cm and Rm for a compartment tree. Configuration object only.

    Actual transmembrane current is injected by LeakChannel and NaKPump.
    Call apply_to_compartments() to attach LeakChannel to every compartment.

    Parameters
    ----------
    Rm_SI : float  specific membrane resistance (Ohm m^2).
                   Default = MEM.Rm_SI = 3.0 Ohm.m^2 (30 000 Ohm.cm^2).
    """

    def __init__(self, Rm_SI: float = MEM.Rm_SI) -> None:
        self.Rm_SI = float(Rm_SI)

    def get_Cm(self, comp: Compartment) -> float:
        """Specific membrane capacitance F/m^2 for this compartment type."""
        return comp.Cm_SI

    def get_Rm(self, comp: Compartment) -> float:
        """Specific membrane resistance Ohm.m^2 (same for all regions)."""
        return self.Rm_SI

    def get_leak_conductance_density(self, comp: Compartment) -> float:
        """Passive leak conductance density gL = 1/Rm (S/m^2)."""
        return 1.0 / self.Rm_SI

    def get_tau_m_s(self, comp: Compartment) -> float:
        """Local membrane time constant tau_m = Rm * Cm (seconds)."""
        return self.Rm_SI * comp.Cm_SI

    def get_tau_m_ms(self, comp: Compartment) -> float:
        """Local membrane time constant (ms)."""
        return self.get_tau_m_s(comp) * 1e3

    def apply_to_compartments(
        self,
        compartments: Sequence[Compartment],
        add_pump: bool = False,
    ) -> None:
        """Attach LeakChannel (and optionally NaKPump) to every compartment.

        Parameters
        ----------
        compartments : all compartments of the neuron tree.
        add_pump     : if True, also attach a NaKPump (I=0 in Phase 0a).
        """
        from biophysical.membrane.leak_channel import LeakChannel
        from biophysical.membrane.nak_pump import NaKPump

        gL = 1.0 / self.Rm_SI
        EL = MEM.E_leak_V

        for comp in compartments:
            comp.add_mechanism(LeakChannel(gL_SI=gL, EL_V=EL))
            if add_pump:
                comp.add_mechanism(NaKPump(I_pump_SI=MEM.I_pump_SI))

    def summary(self) -> Dict[str, Any]:
        """Human-readable summary of bilayer parameters."""
        return {
            'Rm_ohm_cm2':      self.Rm_SI * 1e4,
            'gL_mS_cm2':       (1.0 / self.Rm_SI) * 1e-3 * 1e-4,
            'Cm_soma_uF_cm2':  MEM.Cm_soma_SI * 1e2,
            'Cm_dend_uF_cm2':  MEM.Cm_dend_SI * 1e2,
            'tau_m_soma_ms':   self.Rm_SI * MEM.Cm_soma_SI * 1e3,
            'tau_m_dend_ms':   self.Rm_SI * MEM.Cm_dend_SI * 1e3,
            'EL_mV':           MEM.E_leak_V * 1e3,
        }
