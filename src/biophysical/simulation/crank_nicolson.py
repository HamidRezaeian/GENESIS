"""crank_nicolson.py — Implicit Crank-Nicolson solver for the passive cable equation.

Cable equation:     C * dV/dt = G * V + b + I_ext

CN discretisation (theta = 0.5, fully second-order in time):
    C * (V⁺ - V) / dt = 0.5 * [G * (V⁺ + V)] + b + I_ext

Rearranged:
    A * V⁺ = M * V + b + I_ext

where:
    A = C_diag / dt - G / 2     (LHS — factorised once per (tree, dt))
    M = C_diag / dt + G / 2     (RHS multiplier)

Unconditional stability: CN is A-stable, so any positive dt is stable.
Accuracy breaks down for dt >> tau_m; use dt ≤ lambda/100 ms (0.025 ms is
the published target for L5PC passive models; Hines & Carnevale 1997).

References
----------
[1] Crank J, Nicolson P (1947) Proc Camb Phil Soc 43:50-67
[2] Koch C (1999) Biophysics of Computation. OUP Ch. 6
[3] Hines M, Carnevale NT (1997) Neural Comput 9:1179-1209
[4] Press WH et al. (2007) Numerical Recipes 3rd ed. Ch. 20
[5] Rall W (1969) Biophys J 9:1483-1508  (membrane time-constant protocol)
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from biophysical.morphology.compartment import Compartment
from biophysical.simulation.cable_matrix import build_cable_matrix
from biophysical.core.constants import MEM


class CrankNicolsonSolver:
    """Fully implicit CN solver for the passive cable equation.

    Parameters
    ----------
    compartments : List[Compartment]
        With passive mechanisms (LeakChannel, optionally NaKPump) attached.
    dt_s  : float
        Simulation timestep in seconds.  Default 25 µs (0.025 ms).
    Ra_SI : float
        Specific axial resistance (Ohm m).  Default = MEM.Ra_SI = 2.0.

    Notes
    -----
    Each time dt changes, the LHS matrix A must be re-factorised (O(N^1.5)
    for sparse tree structure).  For time-varying dt, prefer calling
    reset_dt() once rather than passing changing dt to step().
    """

    def __init__(
        self,
        compartments: List[Compartment],
        dt_s: float = 25e-6,
        Ra_SI: float = MEM.Ra_SI,
    ) -> None:
        self.N = len(compartments)
        self.compartments = compartments
        self.dt_s = float(dt_s)

        # Build static matrices (C, G, b do not change for passive linear model)
        C_vec, G_mat, b_vec = build_cable_matrix(compartments, Ra_SI)
        self._C_vec = C_vec           # (N,) Farads
        self._G_mat = G_mat           # (N, N) sparse CSC, Siemens
        self._b_vec = b_vec           # (N,) Amperes

        # Build and factorize operators
        self._A_mat: sp.csc_matrix = None
        self._M_mat: sp.csc_matrix = None
        self._lu = None
        self._dt_factorised: float = -1.0
        self._build_operators(self.dt_s)

    # ------------------------------------------------------------------
    # Operator assembly
    # ------------------------------------------------------------------

    def _build_operators(self, dt_s: float) -> None:
        """Assemble and SuperLU-factorise A = C/dt - G/2."""
        dt = float(dt_s)
        C_diag  = sp.diags(self._C_vec / dt, format='csc')
        half_G  = 0.5 * self._G_mat
        self._A_mat = (C_diag - half_G).tocsc()
        self._M_mat = (C_diag + half_G).tocsc()
        self._lu    = spla.splu(self._A_mat)
        self._dt_factorised = dt

    def reset_dt(self, dt_s: float) -> None:
        """Rebuild operators and LU factorisation for new timestep."""
        self.dt_s = float(dt_s)
        self._build_operators(self.dt_s)

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------

    def step(
        self,
        V: np.ndarray,
        t: float,
        I_ext: np.ndarray,
        dt_s: Optional[float] = None,
    ) -> np.ndarray:
        """Advance state by one timestep.

        Parameters
        ----------
        V     : np.ndarray (N,)  current voltages (V).
        t     : float            current simulation time (s).
        I_ext : np.ndarray (N,)  external current injected per compartment (A).
        dt_s  : float or None    override timestep; triggers refactorisation if
                                 different from self.dt_s.

        Returns
        -------
        V_new : np.ndarray (N,)  updated voltages at t + dt_s (V).
        """
        if dt_s is not None and abs(dt_s - self._dt_factorised) > self._dt_factorised * 1e-6:
            self.reset_dt(dt_s)

        rhs = self._M_mat.dot(V) + self._b_vec + I_ext
        return self._lu.solve(rhs)

    # ------------------------------------------------------------------
    # Measurement helpers (used by passive_validation.py)
    # ------------------------------------------------------------------

    def run(
        self,
        V0: np.ndarray,
        t_max_s: float,
        I_ext_fn,
        recorder=None,
        record_every: int = 1,
    ) -> np.ndarray:
        """Run simulation from t=0 to t_max_s.

        Parameters
        ----------
        V0          : np.ndarray (N,)  initial voltages.
        t_max_s     : float            total time (s).
        I_ext_fn    : callable(t, N) -> np.ndarray (N,)  external current (A).
        recorder    : Recorder or None
        record_every: int  record every N-th step.

        Returns
        -------
        V_final : np.ndarray (N,)  final voltages.
        """
        V = V0.copy()
        dt = self.dt_s
        n_steps = max(1, int(round(t_max_s / dt)))
        t = 0.0

        if recorder is not None:
            recorder.record(V, t)

        for step_n in range(n_steps):
            I = I_ext_fn(t, self.N)
            V = self.step(V, t, I)
            t += dt
            if recorder is not None and (step_n + 1) % record_every == 0:
                recorder.record(V, t)

        return V

    def steady_state(
        self,
        V0: Optional[np.ndarray] = None,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
        tol_V: float = 1e-12,
    ) -> np.ndarray:
        """Integrate to steady state with zero external current.

        Uses a coarse timestep for speed; rebuilds operators temporarily.

        Returns
        -------
        V_rest : np.ndarray (N,)  resting voltages (V).
        """
        saved_dt = self.dt_s
        self.reset_dt(dt_settle_s)

        N = self.N
        V = np.full(N, MEM.E_leak_V) if V0 is None else V0.copy()
        I_zero = np.zeros(N)
        n_steps = int(round(t_settle_s / dt_settle_s))

        for _ in range(n_steps):
            V_new = self.step(V, 0.0, I_zero)
            if np.max(np.abs(V_new - V)) < tol_V:
                V = V_new
                break
            V = V_new

        self.reset_dt(saved_dt)
        return V

    def measure_input_resistance(
        self,
        target_idx: int,
        I_amp: float = 1e-10,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
    ) -> float:
        """Measure DC input resistance at target compartment (Ohm).

        Procedure:
        1. Settle to V_rest with I_ext = 0.
        2. Inject I_amp at target_idx, settle again.
        3. Rin = (V_ss - V_rest) / I_amp.

        Parameters
        ----------
        target_idx  : int    compartment to stimulate and record from.
        I_amp       : float  test current (A). Default 100 pA.
        dt_settle_s : float  coarse dt for settling (s).
        t_settle_s  : float  settling duration (s).

        Returns
        -------
        float  input resistance in Ohm (positive = depolarising).
        """
        V_rest = self.steady_state(dt_settle_s=dt_settle_s, t_settle_s=t_settle_s)

        I_ext = np.zeros(self.N)
        I_ext[target_idx] = I_amp
        saved_dt = self.dt_s
        self.reset_dt(dt_settle_s)

        V = V_rest.copy()
        n_steps = int(round(t_settle_s / dt_settle_s))
        for _ in range(n_steps):
            V_new = self.step(V, 0.0, I_ext)
            if np.max(np.abs(V_new - V)) < 1e-15:
                V = V_new
                break
            V = V_new

        self.reset_dt(saved_dt)
        dV = float(V[target_idx]) - float(V_rest[target_idx])
        return dV / I_amp

    def measure_time_constant(
        self,
        target_idx: int,
        dV_init: float = 10e-3,
        dt_fine_s: float = 100e-6,
        t_max_s: float = 0.3,
        fit_lo: float = 0.05,
        fit_hi: float = 0.70,
        I_amp: Optional[float] = None,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
    ) -> float:
        """Measure the membrane time constant tau_m in seconds (Rall protocol).

        FIX#2 — measurement-protocol bug
        --------------------------------
        The previous implementation displaced a single compartment by dV_init
        and returned the first 1/e crossing of that displacement.  A local
        voltage step excites the fast *equalizing* eigenmodes of the cable
        (tau_1, tau_2, ... << tau_0), so the value it returned (~0.1 ms) was
        an equalizing time constant and not the membrane time constant.

        Rall (1969) protocol — what electrophysiologists actually do:
          1. Inject a constant current at target_idx until the whole tree is
             at DC steady state (all equalizing modes have died out).
          2. Switch the current off and record the relaxation to V_rest.
          3. Regress ln(dV) on t over the window dV/dV0 in [fit_lo, fit_hi].
             The tail is dominated by the slowest eigenmode tau_0, which for a
             sealed-end tree with uniform Rm and Cm equals tau_m = Rm * Cm.

        Parameters
        ----------
        target_idx  : int    compartment to stimulate and record from.
        dV_init     : float  desired DC displacement at t=0 (V), default 10 mV.
                             Only used to choose I_amp when I_amp is None.
        dt_fine_s   : float  timestep for the relaxation trace (s).
        t_max_s     : float  maximum relaxation time simulated (s).
        fit_lo      : float  lower edge of the fit window, as dV/dV0.
        fit_hi      : float  upper edge of the fit window, as dV/dV0.
        I_amp       : float  explicit charging current (A); overrides dV_init.
        dt_settle_s : float  coarse timestep used while charging to DC (s).
        t_settle_s  : float  charging duration (s).

        Returns
        -------
        float  membrane time constant tau_m in seconds.
        """
        V_rest = self.steady_state(dt_settle_s=dt_settle_s, t_settle_s=t_settle_s)

        # --- 1. pick a charging current giving ~dV_init at DC --------------
        if I_amp is None:
            Rin = self.measure_input_resistance(
                target_idx  = target_idx,
                I_amp       = 1e-10,
                dt_settle_s = dt_settle_s,
                t_settle_s  = t_settle_s,
            )
            I_amp = (dV_init / Rin) if abs(Rin) > 1e-30 else 1e-10

        # --- 2. charge the tree to DC steady state -------------------------
        I_ext = np.zeros(self.N)
        I_ext[target_idx] = I_amp

        saved_dt = self.dt_s
        self.reset_dt(dt_settle_s)

        V = V_rest.copy()
        n_settle = max(1, int(round(t_settle_s / dt_settle_s)))
        for _ in range(n_settle):
            V_new = self.step(V, 0.0, I_ext)
            if np.max(np.abs(V_new - V)) < 1e-15:
                V = V_new
                break
            V = V_new

        V_inf = float(V_rest[target_idx])
        dV0   = float(V[target_idx]) - V_inf
        if abs(dV0) < 1e-12:
            self.reset_dt(saved_dt)
            return float(t_max_s)

        # --- 3. release the current, record the normalised relaxation ------
        self.reset_dt(dt_fine_s)
        I_zero  = np.zeros(self.N)
        n_steps = max(1, int(round(t_max_s / dt_fine_s)))
        t_rel:  List[float] = []
        y_rel:  List[float] = []      # dV(t) / dV0, decays 1 -> 0

        for k in range(n_steps):
            V = self.step(V, k * dt_fine_s, I_zero)
            y = (float(V[target_idx]) - V_inf) / dV0
            t_rel.append((k + 1) * dt_fine_s)
            y_rel.append(y)
            if y < 0.5 * fit_lo:      # decayed well past the fit window
                break

        self.reset_dt(saved_dt)

        # --- 4. log-linear regression over the fit window ------------------
        t_arr = np.asarray(t_rel, dtype=np.float64)
        y_arr = np.asarray(y_rel, dtype=np.float64)

        mask = (y_arr >= fit_lo) & (y_arr <= fit_hi)
        if int(np.count_nonzero(mask)) < 2:
            mask = y_arr > 0.0        # fallback: fit the whole decay
        if int(np.count_nonzero(mask)) < 2:
            return float(t_max_s)

        slope = float(np.polyfit(t_arr[mask], np.log(y_arr[mask]), 1)[0])
        if slope >= 0.0:
            return float(t_max_s)
        return -1.0 / slope

    def measure_voltage_attenuation(
        self,
        soma_idx: int,
        distal_idx: int,
        I_amp: float = 1e-10,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
    ) -> float:
        """DC voltage attenuation from soma to distal compartment.

        Returns V_distal / V_soma (DC, with I_amp injected at soma).
        For the Hay L5PC model, attenuation to apical tuft > 10x expected.
        """
        V_rest = self.steady_state(dt_settle_s=dt_settle_s, t_settle_s=t_settle_s)

        I_ext = np.zeros(self.N)
        I_ext[soma_idx] = I_amp
        saved_dt = self.dt_s
        self.reset_dt(dt_settle_s)

        V = V_rest.copy()
        n_steps = int(round(t_settle_s / dt_settle_s))
        for _ in range(n_steps):
            V = self.step(V, 0.0, I_ext)

        self.reset_dt(saved_dt)

        dV_soma    = float(V[soma_idx])    - float(V_rest[soma_idx])
        dV_distal  = float(V[distal_idx]) - float(V_rest[distal_idx])

        if abs(dV_soma) < 1e-30:
            return 0.0
        return dV_distal / dV_soma
