"""
Experiment 103 — Reservoir + Readout Probe
Pre-registration: 2026-08-05
Protocol: EXP103_RESERVOIR_READOUT_v1
Status: STUB — Phase 3 implementation pending (design approved at Phase 1)
"""

import os
import sys

# Pre-registration metadata
PROTOCOL = "EXP103_RESERVOIR_READOUT_v1"
PRE_REG_DATE = "2026-08-05"

# Environment setup (same frozen-cohort static probe as Exp 100–102)
os.environ["GENESIS_RAM_SIZE"] = str(2 * 1024 * 1024)
os.environ["GENESIS_MAX_ORGANISMS"] = "512"
os.environ["GENESIS_REMAP"] = "0"
os.environ["GENESIS_ECONOMY"] = "books"
os.environ["GENESIS_LIVE_WEB"] = "0"
os.environ["GENESIS_AUTO_REPRO"] = "0"
os.environ["GENESIS_RESUME"] = "0"

# Reservoir / readout feature flags
ARM = os.environ.get("EXP103_ARM", "learner")

if ARM == "nolearn":
    os.environ["GENESIS_RESERVOIR"] = "0"
else:
    os.environ["GENESIS_RESERVOIR"] = "1"

# STDP3 family OFF to isolate reservoir/readout contribution from Hebbian path
os.environ["GENESIS_STDP3C"] = "0"
os.environ["GENESIS_STDP3"] = "0"
os.environ["GENESIS_STDP_TARGET"] = "0"

# Do NOT import engine / genesis_lab until Phase 3 (avoids JIT cache pollution during design)
# Phase 3 will add:
#   from neuromorphic_engine import world_tick_numba, ...
#   gl.g_eligibility → replaced by reservoir_state + readout arrays
#   STDP3C eligibility tracking → replaced by LMS update on readout weights
#   RSTDP reward computation → replaced by direct supervised error

def build_patch():
    """Placeholder — will inject static text patch and spawn frozen cohort."""
    raise NotImplementedError("Phase 3: implement reservoir SNN + linear readout before running")

def run_arm(arm_name: str):
    """Placeholder — will run 20,000 ticks and collect accuracy samples."""
    raise NotImplementedError("Phase 3: implement reservoir dynamics + LMS in engine first")

def main():
    print(f"Exp 103 STUB — Protocol: {PROTOCOL}")
    print(f"Pre-registration: {PRE_REG_DATE}")
    print(f"Arm: {ARM}")
    print(f"Status: STUB — implementation pending in Phase 3.")
    print("Binding hypothesis: Reservoir + LMS readout produces Δ > +2pp on static text.")
    raise NotImplementedError("Phase 3: implement reservoir in engine first")

if __name__ == "__main__":
    main()
