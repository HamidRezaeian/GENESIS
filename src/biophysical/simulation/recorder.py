"""recorder.py — Voltage recorder for biophysical simulation runs.

Records voltage traces at a specified set of compartment indices.  After each
call to solver.run(), the caller passes V and t to recorder.record(); traces
can then be retrieved as NumPy arrays.

Usage
-----
    from biophysical.simulation.recorder import Recorder

    rec = Recorder(
        idxs   = [0, 50, 100],
        labels = ['soma', 'apical_trunk_mid', 'tuft_tip'],
    )
    for step in range(n_steps):
        V = solver.step(V, t, I_ext)
        rec.record(V, t)

    soma_mV = rec.traces_mV()['soma']   # shape (n_recorded,)
    time_ms = rec.get_time_ms()          # shape (n_recorded,)
"""

from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np


class Recorder:
    """Records voltage traces at a set of compartment indices.

    Parameters
    ----------
    idxs   : List[int]           compartment indices to record from.
    labels : List[str] or None   human-readable names; defaults to 'comp_i'.
    """

    def __init__(
        self,
        idxs:   List[int],
        labels: Optional[List[str]] = None,
    ) -> None:
        self.idxs   = list(idxs)
        self.labels = (labels if labels is not None
                       else [f'comp_{i}' for i in idxs])
        if len(self.labels) != len(self.idxs):
            raise ValueError('labels length must match idxs length')

        self._times:  List[float]              = []
        self._traces: Dict[int, List[float]]   = {i: [] for i in idxs}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, V: np.ndarray, t: float) -> None:
        """Append current voltages and time.

        Parameters
        ----------
        V : np.ndarray (N,)  current voltage vector (Volts).
        t : float            current simulation time (seconds).
        """
        self._times.append(float(t))
        for i in self.idxs:
            self._traces[i].append(float(V[i]))

    def reset(self) -> None:
        """Discard all recorded data."""
        self._times = []
        for k in self._traces:
            self._traces[k] = []

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_time(self) -> np.ndarray:
        """Recorded times in seconds, shape (n_samples,)."""
        return np.array(self._times, dtype=np.float64)

    def get_time_ms(self) -> np.ndarray:
        """Recorded times in milliseconds."""
        return self.get_time() * 1e3

    def get_trace(self, idx: int) -> np.ndarray:
        """Voltage trace for compartment idx (Volts)."""
        return np.array(self._traces[idx], dtype=np.float64)

    def get_trace_mV(self, idx: int) -> np.ndarray:
        """Voltage trace for compartment idx (milliVolts)."""
        return self.get_trace(idx) * 1e3

    def traces_V(self) -> Dict[str, np.ndarray]:
        """All traces in Volts, keyed by label."""
        return {
            lbl: np.array(self._traces[idx], dtype=np.float64)
            for lbl, idx in zip(self.labels, self.idxs)
        }

    def traces_mV(self) -> Dict[str, np.ndarray]:
        """All traces in milliVolts, keyed by label."""
        return {k: v * 1e3 for k, v in self.traces_V().items()}

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def n_samples(self) -> int:
        return len(self._times)

    @property
    def n_channels(self) -> int:
        return len(self.idxs)

    def __repr__(self) -> str:
        return (f'Recorder(channels={self.n_channels}, '
                f'n_samples={self.n_samples}, '
                f'labels={self.labels})')
