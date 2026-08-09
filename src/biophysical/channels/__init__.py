"""channels/ — Voltage-gated ion channel package for Project GENESIS Phase 0b.

Provides
--------
KineticsSet         — enum selecting kinetic formulation (Step 1)
Gate                — gating variable with cnexp stepping (Step 1)
vtrap               — numerically stable x/(exp(x/y)−1) (Step 1)
q10_factor          — Q10 temperature-scaling multiplier (Step 1)
nata_alpha_m/beta_m — NaTa_t m-gate rate functions at T_ref (Step 1)
nata_alpha_h/beta_h — NaTa_t h-gate rate functions at T_ref (Step 1)
skv3_n_inf          — SKv3.1 n-gate steady-state (Step 1)
skv3_tau_n_ms       — SKv3.1 n-gate time constant at T_ref (Step 1)
VoltageGatedChannel — partial concrete ABC for all VGCs (Step 1)
NaV16Channel        — transient Na⁺ channel, m³h gates (Step 2)
KvChannel           — delayed-rectifier K⁺ channel (Step 2)
ChannelDistribution — region → compartment density map (Step 3)
"""

from biophysical.channels.kinetics import KineticsSet
from biophysical.channels.gating import (
    Gate,
    vtrap,
    q10_factor,
    nata_alpha_m,
    nata_beta_m,
    nata_alpha_h,
    nata_beta_h,
    skv3_n_inf,
    skv3_tau_n_ms,
)
from biophysical.channels.base_channel import VoltageGatedChannel

__all__ = [
    # Step 1 — Foundation
    'KineticsSet',
    'Gate',
    'vtrap',
    'q10_factor',
    'nata_alpha_m',
    'nata_beta_m',
    'nata_alpha_h',
    'nata_beta_h',
    'skv3_n_inf',
    'skv3_tau_n_ms',
    'VoltageGatedChannel',
    # Step 2 — Channels (added in next step)
    # 'NaV16Channel',
    # 'KvChannel',
    # Step 3 — Distributions (added in later step)
    # 'ChannelDistribution',
]
