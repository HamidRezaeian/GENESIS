"""current_clamp.py — Current clamp stimulation protocol.

Represents a square-wave current pulse injected into a target compartment.

Usage
-----
    from biophysical.simulation.current_clamp import CurrentClampProtocol

    proto = CurrentClampProtocol(
        amp_A      = 1e-10,   # 100 pA
        onset_s    = 0.1,     # 100 ms delay
        dur_s      = 0.5,     # 500 ms pulse
        target_idx = 0,       # soma
    )
    I_ext = proto.get_I_ext(t=0.15, N=224)   # active at 150 ms
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import numpy as np


@dataclass
class CurrentClampProtocol:
    """Square-wave current clamp pulse.

    Parameters
    ----------
    amp_A      : float   pulse amplitude (Amperes, positive = depolarising).
    onset_s    : float   start time (s).
    dur_s      : float   pulse duration (s).
    target_idx : int     compartment index to stimulate.
    """
    amp_A:      float
    onset_s:    float
    dur_s:      float
    target_idx: int

    @property
    def offset_s(self) -> float:
        return self.onset_s + self.dur_s

    def is_active(self, t: float) -> bool:
        """True if the pulse is active at time t."""
        return self.onset_s <= t < self.offset_s

    def get_I_ext(self, t: float, N: int) -> np.ndarray:
        """External current vector (A) at time t.

        Returns
        -------
        I : np.ndarray (N,)  current in Amperes.  Zero everywhere except
            target_idx when pulse is active.
        """
        I = np.zeros(N, dtype=np.float64)
        if self.is_active(t):
            I[self.target_idx] = self.amp_A
        return I

    def amp_pA(self) -> float:
        return self.amp_A * 1e12

    def amp_nA(self) -> float:
        return self.amp_A * 1e9


@dataclass
class MultiProtocol:
    """Superposition of multiple CurrentClampProtocol pulses.

    Parameters
    ----------
    protocols : list of CurrentClampProtocol.
    """
    protocols: List[CurrentClampProtocol] = field(default_factory=list)

    def add(self, proto: CurrentClampProtocol) -> 'MultiProtocol':
        """Add a protocol and return self (for chaining)."""
        self.protocols.append(proto)
        return self

    def get_I_ext(self, t: float, N: int) -> np.ndarray:
        """Sum of all active protocol currents (A)."""
        I = np.zeros(N, dtype=np.float64)
        for p in self.protocols:
            if p.is_active(t):
                I[p.target_idx] += p.amp_A
        return I

    def is_any_active(self, t: float) -> bool:
        return any(p.is_active(t) for p in self.protocols)
