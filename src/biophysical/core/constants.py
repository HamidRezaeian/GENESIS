"""constants.py — All biophysical constants for Project GENESIS.

Every constant is annotated with its SI unit and primary literature reference.
All internal calculations are in SI (V, A, S, F, Ω, m, s, mol, kg).
Convenience properties expose CGS values (µF/cm², Ω·cm, mV …) where common.

References
----------
[1]  Hodgkin AL, Huxley AF (1952) J Physiol 117:500–544
[2]  Hay E et al. (2011) PLoS Comput Biol 7:e1002107          (L5PC model)
[3]  Eyal G et al. (2016) eLife 5:e16553                      (human L2/3 & L5)
[4]  Beaulieu-Laroche L et al. (2018) Cell 175:643–651.e14    (human cortex)
[5]  Stuart GJ, Spruston N (1998) J Neurosci 18:3501–3510
[6]  Koch C (1999) Biophysics of Computation. OUP
[7]  Hille B (2001) Ion Channels of Excitable Membranes. 3rd ed. Sinauer
[8]  CODATA 2018 recommended values
"""

from __future__ import annotations
import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Fundamental physical constants  [CODATA 2018, ref 8]
# ---------------------------------------------------------------------------

F_FARADAY: float = 96_485.332_12    # C mol⁻¹  — Faraday constant
R_GAS: float = 8.314_462_618        # J mol⁻¹ K⁻¹ — universal gas constant
K_BOLTZMANN: float = 1.380_649e-23  # J K⁻¹   — Boltzmann constant
N_AVOGADRO: float = 6.022_140_76e23 # mol⁻¹   — Avogadro number


# ---------------------------------------------------------------------------
# Physiological temperature  [ref 4 — human body]
# ---------------------------------------------------------------------------

T_CELSIUS: float = 37.0              # °C
T_KELVIN: float = T_CELSIUS + 273.15  # K  = 310.15 K

# Thermal voltage at 37 °C: RT/F ≈ 0.026_71 V
RT_OVER_F: float = R_GAS * T_KELVIN / F_FARADAY


# ---------------------------------------------------------------------------
# Ionic concentrations  (intracellular / extracellular, mM)
# [ref 7] Table 1.1; [ref 4] for human neocortex specifics
# ---------------------------------------------------------------------------

NA_IN_MM:  float = 10.0    # [Na⁺]ᵢ  — intracellular sodium  (mM)
NA_OUT_MM: float = 145.0   # [Na⁺]ₒ  — extracellular sodium  (mM)
K_IN_MM:   float = 140.0   # [K⁺]ᵢ   — intracellular potassium  (mM)
K_OUT_MM:  float = 3.5     # [K⁺]ₒ   — extracellular potassium  (mM)
CA_IN_MM:  float = 1.0e-4  # [Ca²⁺]ᵢ — resting intracellular calcium (100 nM)
CA_OUT_MM: float = 2.0     # [Ca²⁺]ₒ — extracellular calcium  (mM)
CL_IN_MM:  float = 7.0     # [Cl⁻]ᵢ  — intracellular chloride  (mM)
CL_OUT_MM: float = 110.0   # [Cl⁻]ₒ  — extracellular chloride  (mM)
MG_IN_MM:  float = 0.6     # [Mg²⁺]ᵢ — intracellular magnesium (mM)
MG_OUT_MM: float = 1.0     # [Mg²⁺]ₒ — extracellular magnesium (mM)


def nernst_mV(c_in: float, c_out: float, z: int) -> float:
    """Nernst equilibrium potential in mV.

    E = (RT / zF) * ln(c_out / c_in)   [ref 7, eq 1.8]

    Parameters
    ----------
    c_in, c_out : float  — concentrations in any consistent unit (e.g. mM)
    z           : int    — ionic valence (signed: Na⁺ → +1, Cl⁻ → -1, Ca²⁺ → +2)

    Returns
    -------
    float — equilibrium potential in mV
    """
    return (RT_OVER_F / z) * math.log(c_out / c_in) * 1e3  # V → mV


# Pre-computed Nernst potentials at 37 °C
E_NA_MV: float = nernst_mV(NA_IN_MM,  NA_OUT_MM,  z=+1)   # ≈ +72 mV
E_K_MV:  float = nernst_mV(K_IN_MM,   K_OUT_MM,   z=+1)   # ≈ −95 mV
E_CA_MV: float = nernst_mV(CA_IN_MM,  CA_OUT_MM,  z=+2)   # ≈ +136 mV
E_CL_MV: float = nernst_mV(CL_IN_MM,  CL_OUT_MM,  z=-1)   # ≈ −68 mV


@dataclass(frozen=True)
class PhysicalConstants:
    """Immutable container for fundamental physical constants."""
    faraday:   float = F_FARADAY
    R:         float = R_GAS
    kB:        float = K_BOLTZMANN
    NA:        float = N_AVOGADRO
    T_kelvin:  float = T_KELVIN
    T_celsius: float = T_CELSIUS
    RToverF:   float = RT_OVER_F  # V


@dataclass(frozen=True)
class MembraneConstants:
    """Passive membrane parameters for a human L5 pyramidal neuron.

    Phase 0a parameter set  (FIX#1)
    -------------------------------
    Cm = 1.0 µF/cm² in every region            [ref 1, ref 3]
        The canonical Hodgkin/Katz specific capacitance.  Earlier revisions of
        this file used Cm_dend = 2.0 µF/cm²; that value compensates for an
        under-estimated dendritic membrane area and is not needed once Rm and
        Ra are set from the human recordings below.  A uniform Cm also makes
        the slowest cable eigenmode exactly tau_m = Rm * Cm, which is the
        quantity the Rall relaxation protocol measures.
    Rm = 30 000 Ω·cm²  (3.0 Ω·m²)              [ref 3, ref 4]
        High-Rm end of the range fitted to human pyramidal recordings.  With
        the Phase 0a morphology it gives R_in(soma) ≈ 72 MΩ, inside the
        50–200 MΩ measured range [ref 4]; 15 000 Ω·cm² gave ≈ 36 MΩ.
    Ra = 200 Ω·cm  (2.0 Ω·m)                   [ref 2, ref 5]
        Axial resistivity used by the Hay L5PC model.  Doubling Rm and Ra
        together leaves λ = sqrt(Rm·d / 4Ra) unchanged (1369 µm at d = 5 µm)
        while doubling R_in ∝ sqrt(Rm·Ra).
    E_leak = −70 mV                            [ref 4]
        Human neocortical resting membrane potential (whole-cell patch clamp).

    Resulting targets: tau_m = 30 ms, λ(d = 5 µm) = 1369 µm, V_rest = −70 mV.

    All SI values (units: F m⁻², Ω m², Ω m, V)
    """
    # Specific capacitance  [F m⁻²]
    Cm_soma_SI:  float = 1.0e-2   # 1.0 µF/cm²  soma                  [ref 1]
    Cm_dend_SI:  float = 1.0e-2   # 1.0 µF/cm²  dendrites (FIX#1)     [ref 1, 3]
    Cm_axon_SI:  float = 1.0e-2   # 1.0 µF/cm²  axon                  [ref 1]

    # Specific membrane resistance  [omega m²]  (= 30 000 Ω·cm²)
    Rm_SI:       float = 3.0      # 30 000 Ω·cm²  (FIX#1)          [ref 3, 4]

    # Cytoplasmic axial resistivity  [Ω m]  (= 200 Ω·cm)
    Ra_SI:       float = 2.0      # 200 Ω·cm      (FIX#1)          [ref 2, 5]

    # Leak / resting reversal potential  [V]
    E_leak_V:    float = -0.070   # −70 mV                         [ref 4]

    # Na⁺/K⁺ ATPase pump: equivalent constant outward current density  [A m⁻²]
    # Chosen so that V_rest = E_leak + I_pump * Rm = −70 mV (self-consistent).
    # Pump contribution is small (< 5 mV shift from E_leak).
    # Full kinetic model deferred to Phase 0g (Metabolism).
    I_pump_SI: float = 0.0        # A m⁻²  (zero for Phase 0a passive model)

    # --- CGS convenience properties -----------------------------------------

    @property
    def Cm_soma_uF_cm2(self) -> float:
        """Somatic specific capacitance in µF/cm²."""
        return self.Cm_soma_SI * 1e2

    @property
    def Cm_dend_uF_cm2(self) -> float:
        """Dendritic specific capacitance in µF/cm² (1.0 after FIX#1)."""
        return self.Cm_dend_SI * 1e2

    @property
    def Rm_ohm_cm2(self) -> float:
        """Specific membrane resistance in Ω·cm²."""
        return self.Rm_SI * 1e4

    @property
    def Ra_ohm_cm(self) -> float:
        """Axial resistivity in Ω·cm."""
        return self.Ra_SI * 1e2

    @property
    def tau_m_dend_ms(self) -> float:
        """Dendritic membrane time constant τ_m = R_m * C_m (ms).

        τ_m = 3.0 Ω·m² x 1e-2 F/m² = 0.030 s = 30 ms
        Target range: 10–30 ms (Beaulieu-Laroche 2018, Table 1).
        """
        return self.Rm_SI * self.Cm_dend_SI * 1e3  # s → ms

    @property
    def tau_m_soma_ms(self) -> float:
        """Somatic membrane time constant (ms)."""
        return self.Rm_SI * self.Cm_soma_SI * 1e3

    def lambda_um(self, diameter_m: float) -> float:
        """Electrotonic length constant λ = sqrt(Rm*d / 4*Ra) in micrometres.

        [ref 6, Koch 1999, eq 2.17]
        Parameters
        ----------
        diameter_m : float — compartment diameter in metres
        """
        lam_m = math.sqrt(self.Rm_SI * diameter_m / (4.0 * self.Ra_SI))
        return lam_m * 1e6  # m → µm


# Module-level singleton instances
PHYS = PhysicalConstants()
MEM  = MembraneConstants()
