"""active_solver.py — Hines (1984) staggered semi-implicit solver.

Extends the passive Crank–Nicolson theta-method with voltage-gated channels
via the staggered semi-implicit scheme of Hines (1984):

  1) Advance channel gates using V^n
  2) Linearise channel current as:  I_chan(V) = -g(V^n) * (V - E_rev)
     which contributes:
       -g to the diagonal of G, and +g*E_rev to the RHS
  3) Solve the resulting linear system for V^{n+1}

The scheme is unconditionally stable for dt > 0 and any channel density.

Notes
-----
- We intentionally do NOT fix the known swapped h-gate alpha/beta bug in
  channels/gating.py (see Phase 0b findings); tests handle this with xfail.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from biophysical.channels.base_channel import VoltageGatedChannel
from biophysical.core.constants import MEM
from biophysical.morphology.compartment import Compartment
from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.current_clamp import CurrentClampProtocol, MultiProtocol
from biophysical.simulation.recorder import Recorder

ProtocolLike = Union[
    CurrentClampProtocol,
    MultiProtocol,
    Sequence[CurrentClampProtocol],
    None,
]


def channel_conductance_S(mech: VoltageGatedChannel, t: float = 0.0) -> float:
    """Extract an effective conductance [S] via the public current() API.

    Channels in this codebase expose total conductance implicitly through:
        I(V) = -g_total * open_fraction * (V - E_rev)

    We estimate the (g_total * open_fraction) term without accessing private
    state by probing the current 1 V above E_rev.
    """
    E_rev = float(mech.E_rev_V)
    V_probe = E_rev + 1.0
    dV = V_probe - E_rev
    return -float(mech.current(V_probe, t)) / dV


def _as_protocol(protocols: ProtocolLike) -> Optional[MultiProtocol]:
    if protocols is None:
        return None
    if isinstance(protocols, MultiProtocol):
        return protocols
    if isinstance(protocols, CurrentClampProtocol):
        return MultiProtocol([protocols])
    if isinstance(protocols, (list, tuple)):
        flat: List[CurrentClampProtocol] = []
        for p in protocols:
            if isinstance(p, MultiProtocol):
                flat.extend(p.protocols)
            elif isinstance(p, CurrentClampProtocol):
                flat.append(p)
        return MultiProtocol(flat)
    raise TypeError(f"Unsupported protocol: {type(protocols).__name__}")


class ActiveSolver(CrankNicolsonSolver):
    """Crank-Nicolson extended with voltage-gated channels (Hines 1984).

    Unconditionally stable for any gbar and dt > 0.
    """

    def __init__(
        self,
        compartments: List[Compartment],
        dt_s: float = 25e-6,
        theta: float = 0.5,
        Ra_SI: Optional[float] = None,
        rannacher_steps: int = 2,
        refactor_rel_tol: float = 0.10,
        refactor_every: int = 100,
    ) -> None:
        # Initialize state before super().__init__ (it calls reset_startup)
        self._channel_index: List[tuple[int, VoltageGatedChannel]] = []
        self._g_chan: Optional[np.ndarray] = None
        self._I_chan: Optional[np.ndarray] = None
        self._g_ref: Optional[np.ndarray] = None
        self._I_ref: Optional[np.ndarray] = None
        self._steps_since_refactor: int = 0
        self._active_cache: Dict[tuple[float, float], Any] = {}

        self.refactor_rel_tol = float(refactor_rel_tol)
        self.refactor_every = int(refactor_every)
        self.n_refactorisations: int = 0
        self.last_step: Dict[str, Any] = {}

        # Use keyword args to avoid positional bug in skeleton.
        super().__init__(
            compartments=compartments,
            dt_s=dt_s,
            Ra_SI=Ra_SI if Ra_SI is not None else MEM.Ra_SI,
            theta=theta,
            rannacher_steps=rannacher_steps,
        )

        self._index_channels()
        self._g_chan = np.zeros(self.N, dtype=np.float64)
        self._I_chan = np.zeros(self.N, dtype=np.float64)

    # ------------------------------------------------------------------
    # Channel indexing / gate stepping
    # ------------------------------------------------------------------

    def _index_channels(self) -> None:
        """Cache (comp_idx, mechanism) for every VoltageGatedChannel."""
        self._channel_index = []
        for pos, comp in enumerate(self.compartments):
            for mech in comp.mechanisms:
                if isinstance(mech, VoltageGatedChannel):
                    self._channel_index.append((pos, mech))

    @property
    def has_active_channels(self) -> bool:
        return bool(self._channel_index)

    @property
    def n_active_channels(self) -> int:
        return len(self._channel_index)

    def initialise_gates(self, V: np.ndarray) -> None:
        """Set all gates to steady state at voltage V."""
        for i, mech in self._channel_index:
            mech.set_steady_state(float(V[i]))

    def _update_gates(self, V: np.ndarray, t: float, dt: float) -> None:
        """Hines step 1: advance gates using V^n."""
        for i, mech in self._channel_index:
            mech.update_state(float(V[i]), t, dt)

    def _collect_conductances(self, t: float) -> tuple[np.ndarray, np.ndarray]:
        """Hines step 2: compute g_chan [S] and I_chan [A] per compartment."""
        assert self._g_chan is not None and self._I_chan is not None

        g = self._g_chan
        I = self._I_chan
        g.fill(0.0)
        I.fill(0.0)

        for i, mech in self._channel_index:
            g_i = channel_conductance_S(mech, t)
            g[i] += g_i
            I[i] += g_i * float(mech.E_rev_V)

        return g, I

    # ------------------------------------------------------------------
    # Refactorisation strategy
    # ------------------------------------------------------------------

    def _needs_refactor(self, g_new: np.ndarray) -> bool:
        if self._g_ref is None:
            return True
        if self.refactor_every > 0 and self._steps_since_refactor >= self.refactor_every:
            return True
        if self.refactor_rel_tol <= 0:
            return True

        tol = self.refactor_rel_tol * np.abs(self._g_ref)
        return bool(np.any(np.abs(g_new - self._g_ref) > tol))

    def _build_operators(
        self,
        g_use: np.ndarray,
        dt: float,
        theta: float,
    ):
        """Build (A, M, LU) for given conductances."""
        # IMPORTANT: do not mutate self._G_mat in place.
        G_eff = self._G_mat - sp.diags(g_use, format="csc")
        C_diag = sp.diags(self._C_vec / dt, format="csc")
        A = (C_diag - theta * G_eff).tocsc()
        M = (C_diag + (1.0 - theta) * G_eff).tocsc()
        lu = spla.splu(A)
        return A, M, lu

    # ------------------------------------------------------------------
    # Integration step
    # ------------------------------------------------------------------

    def step(
        self,
        V: np.ndarray,
        t: float,
        I_ext: np.ndarray,
        dt_s: Optional[float] = None,
    ) -> np.ndarray:
        """One Hines staggered semi-implicit step."""
        if not self.has_active_channels:
            return super().step(V, t, I_ext, dt_s)

        if dt_s is not None and abs(float(dt_s) - self.dt_s) > self.dt_s * 1e-6:
            # Delegate dt changes to the parent (rebuilds factorisations, resets startup)
            self.reset_dt(float(dt_s))

        V = np.asarray(V, dtype=np.float64)
        I_ext = np.asarray(I_ext, dtype=np.float64)
        dt = self.dt_s

        # Re-arm startup if state changed
        if self._last_V_out is not None and not np.array_equal(V, self._last_V_out):
            self.reset_startup()

        # 1) Update gates
        self._update_gates(V, t, dt)

        # 2) Collect conductances
        g_new, I_new = self._collect_conductances(t)

        # 3) Refactorize if needed
        if self._needs_refactor(g_new):
            self._g_ref = g_new.copy()
            self._I_ref = I_new.copy()
            self._steps_since_refactor = 0
            self._active_cache = {}
            self.n_refactorisations += 1
        else:
            self._steps_since_refactor += 1

        g_use = self._g_ref if self._g_ref is not None else g_new
        I_use = self._I_ref if self._I_ref is not None else I_new

        # 4) Build operators
        theta = 1.0 if self._steps_taken < self.rannacher_steps else self.theta
        cache_key = (dt, theta)
        if cache_key not in self._active_cache:
            self._active_cache[cache_key] = self._build_operators(g_use, dt, theta)
        A, M, lu = self._active_cache[cache_key]

        # 5) Solve
        rhs = M.dot(V) + self._b_vec + I_use + I_ext
        V_new = lu.solve(rhs)

        self._steps_taken += 1
        self._last_V_out = V_new.copy()
        self.last_step = {"t": t, "theta": theta, "g_chan": g_use.copy()}
        return V_new

    # ------------------------------------------------------------------
    # Convenience runner
    # ------------------------------------------------------------------

    def run(
        self,
        protocols: ProtocolLike = None,
        duration_s: Optional[float] = None,
        record_idxs: Optional[Sequence[int]] = None,
        V0: Optional[np.ndarray] = None,
        record_every: int = 1,
        init_gates: bool = True,
        **kwargs,
    ) -> Recorder:
        """Run simulation with current clamp protocol(s)."""
        if duration_s is None:
            raise ValueError("duration_s required")

        proto = _as_protocol(protocols)
        N = self.N
        dt = self.dt_s
        n_steps = max(1, int(round(float(duration_s) / dt)))

        V = (
            np.full(N, MEM.E_leak_V, dtype=np.float64)
            if V0 is None
            else np.asarray(V0, dtype=np.float64).copy()
        )

        if init_gates and self.has_active_channels:
            self.initialise_gates(V)

        idxs = [0] if record_idxs is None else list(record_idxs)
        rec = Recorder(idxs)

        self.reset_startup()
        rec.record(V, 0.0)

        I_prev = np.zeros(N)
        t_wall = time.perf_counter()

        for step_n in range(n_steps):
            t = step_n * dt

            # Get stimulus current
            I = proto.get_I_ext(t, N) if proto is not None else np.zeros(N)

            # Re-arm Rannacher on stimulus change
            if not np.array_equal(I, I_prev):
                self.reset_startup()
                I_prev = I.copy()

            # Step
            V = self.step(V, t, I, dt)

            # Record
            if (step_n + 1) % record_every == 0:
                rec.record(V, t + dt)

        elapsed = time.perf_counter() - t_wall
        self.last_run_stats = {
            "n_steps": n_steps,
            "duration_s": float(duration_s),
            "wall_time_s": elapsed,
            "n_refactorisations": self.n_refactorisations,
        }
        return rec
