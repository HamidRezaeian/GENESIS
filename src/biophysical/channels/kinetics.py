"""kinetics.py — Kinetics set enumeration for voltage-gated ion channels.

Each KineticsSet member identifies a complete family of α/β or inf/tau
rate functions, along with the reference temperature and Q10 factors
used by that family.

References
----------
[HH52]  Hodgkin AL, Huxley AF (1952) J Physiol 117:500–544
        Original squid-axon kinetics measured at 6.3 °C.
[MS96]  Mainen ZF, Sejnowski TJ (1996) J Neurophysiol 76:1329–1338
        Mammalian neocortical kinetics measured at 23 °C.
[H11]   Hay E et al. (2011) PLoS Comput Biol 7:e1002107; ModelDB #139653
        Human L5PC model using MS96 kinetics (NaTa_t.mod, SKv3_1.mod).
"""

from enum import Enum, auto


class KineticsSet(Enum):
    """Channel kinetics family selector.

    HH_SQUID_1952
        Classic Hodgkin-Huxley squid-axon α/β functions measured at 6.3 °C.

        **Do not use for mammalian simulations.**  Q10-scaling these rates
        from 6.3 °C to 37 °C (ΔT = 30.7 decades) gives:
          τ_m(37°C) = τ_m(6.3°C) / 3^3.07 ≈ 0.46 ms / 27 < 20 µs
        which is faster than a typical dt = 25 µs timestep and produces
        physiologically implausible APs.  This kinetics set is retained
        for regression testing and historical comparison only.

    MAMMALIAN_MS96
        Mainen & Sejnowski (1996) rate functions measured at 23 °C from
        rat neocortical pyramidal neuron patches.  Used in the Hay 2011
        human L5PC model (ModelDB #139653) as NaTa_t.mod and SKv3_1.mod.

        Q10 scaling from 23 °C to 37 °C gives biologically correct values:
          NaTa_t  (Q10 = 2.3):  τ_m,peak ≈ 0.11 ms at −40 mV     [MS96]
          NaTa_t  (Q10 = 2.3):  τ_h      ≈ 0.25–2.5 ms           [MS96]
          SKv3.1  (Q10 = 3.0):  τ_n,peak ≈ 0.43 ms at +46.6 mV  [H11]

        This is the **approved** kinetics set for Phase 0b.
    """

    HH_SQUID_1952  = auto()   # [HH52] squid axon, T_ref = 6.3 °C
    MAMMALIAN_MS96 = auto()   # [MS96] mammalian neocortex, T_ref = 23 °C
