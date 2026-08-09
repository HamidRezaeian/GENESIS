"""crank_nicolson.py — Implicit theta-method solver for the passive cable equation.

Cable equation:     C * dV/dt = G * V + b + I_ext

theta-method discretisation (theta = 0.5 is Crank-Nicolson):
    C * (V⁺ - V) / dt = theta * G * V⁺ + (1 - theta) * G * V + b + I_ext

Rearranged:
    A * V⁺ = M * V + b + I_ext

where:
    A = C_diag / dt - theta * G          (LHS — LU-factorised per (dt, theta))
    M = C_diag / dt + (1 - theta) * G    (RHS multiplier)

Rannacher startup (FIX#3)
-------------------------
Pure CN (theta = 0.5) is A-stable but NOT L-stable: the amplification factor
of a mode with time constant tau_k is
    (1 - dt / (2*tau_k)) / (1 + dt / (2*tau_k))   ->  -1  as dt/tau_k -> inf
so stiff modes are not damped, they alternate sign and decay very slowly.  A
dendritic tree is extremely stiff (equalizing modes of a few microseconds next
to tau_m = 30 ms), so every discontinuity in the state — an initial condition,
a perturbation, a current onset — left a ringing residual behind (the symptom
was a ~0.07 mV offset that never settled).

Rannacher (1984) smoothing fixes this without giving up second-order accuracy:
run the first `rannacher_steps` steps with theta = 1 (backward Euler, which is
L-stable and annihilates stiff modes in a single step), then switch to
theta = 0.5 for the rest of the run.  Startup is re-armed by reset_startup(),
by reset_dt(), by run(), and automatically whenever the state passed to step()
is not the state the solver last returned.

Unconditional stability: theta = 1 and theta = 0.5 are both A-stable, so any
positive dt is stable.  Accuracy still requires dt << tau_m; 0.025 ms is the
published target for L5PC passive models (Hines & Carnevale 1997).

References
----------
[1] Crank J, Nicolson P (1947) Proc Camb Phil Soc 43:50-67
[2] Koch C (1999) Biophysics of Computation. OUP Ch. 6
[3] Hines M, Carnevale NT (1997) Neural Comput 9:1179-1209
[4] Press WH et al. (2007) Numerical Recipes 3rd ed. Ch. 20
[5] Rall W (1969) Biophys J 9:1483-1508  (membrane time-constant protocol)
[6] Rannacher R (1984) Numer Math 43:309-327  (smoothing of stiff modes)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from biophysical.morphology.compartment import Compartment
from biophysical.simulation.cable_matrix import build_cable_matrix
from biophysical.core.constants import MEM


class CrankNicolsonSolver:
    """Implicit theta-method solver for the passive cable equation.

    Parameters
    ----------
    compartments : List[Compartment]
        With passive mechanisms (LeakChannel, optionally NaKPump) attached.
    dt_s  : float
        Simulation timestep in seconds.  Default 25 µs (0.025 ms).
    Ra_SI : float
        Specific axial resistance (Ohm m).  Default = MEM.Ra_SI = 2.0.
    theta : float
        Implicitness of the steady-state phase.  0.5 = Crank-Nicolson
        (second order), 1.0 = backward Euler (first order, L-stable).
    rannacher_steps : int
        Number of backward-Euler steps used at the start of each integration
        to damp stiff modes (Rannacher startup).  0 disables the startup.

    Notes
    -----
    Operators are LU-factorised per (dt, theta) pair and cached, so the
    backward-Euler startup costs one extra factorisation per timestep value.
    For time-varying dt, prefer calling reset_dt() once rather than passing a
    changing dt to step().
    """

    def __init__(
        self,
        compartments: List[Compartment],
        dt_s: float = 25e-6,
        Ra_SI: float = MEM.Ra_SI,
        theta: float = 0.5,
        rannacher_steps: int = 2,
    ) -> None:
        self.N = len(compartments)
        self.compartments = compartments
        self.dt_s = float(dt_s)
        self.theta = float(theta)
        self.rannacher_steps = int(rannacher_steps)

        # Build static matrices (C, G, b do not change for passive linear model)
        C_vec, G_mat, b_vec = build_cable_matrix(compartments, Ra_SI)
        self._C_vec = C_vec           # (N,) Farads
        self._G_mat = G_mat           # (N, N) sparse CSC, Siemens
        self._b_vec = b_vec           # (N,) Amperes

        # (dt, theta) -> (A, M, LU)
        self._cache: Dict[Tuple[float, float], Tuple[sp.csc_matrix, sp.csc_matrix, Any]] = {}

        # Rannacher startup bookkeeping
        self._steps_taken: int = 0
        self._last_V_out: Optional[np.ndarray] = None

        # Legacy attribute surface (theta-phase operators for current dt)
        self._A_mat: sp.csc_matrix = None
        self._M_mat: sp.csc_matrix = None
        self._lu = None
        self._dt_factorised: float = -1.0
        self._build_operators(self.dt_s)

    # ------------------------------------------------------------------
    # Operator assembly
    # ------------------------------------------------------------------

    def _make_operators(
        self,
        dt_s: float,
        theta: float,
    ) -> Tuple[sp.csc_matrix, sp.csc_matrix, Any]:
        """Assemble and SuperLU-factorise the operators for (dt, theta)."""
        dt = float(dt_s)
        th = float(theta)
        C_diag = sp.diags(self._C_vec / dt, format='csc')
        A_mat  = (C_diag - th * self._G_mat).tocsc()
        M_mat  = (C_diag + (1.0 - th) * self._G_mat).tocsc()
        lu     = spla.splu(A_mat)
        return A_mat, M_mat, lu

    def _get_operators(
        self,
        dt_s: float,
        theta: float,
    ) -> Tuple[sp.csc_matrix, sp.csc_matrix, Any]:
        """Return cached operators for (dt, theta), building them if needed."""
        key = (float(dt_s), float(theta))
        entry = self._cache.get(key)
        if entry is None:
            entry = self._make_operators(dt_s, theta)
            self._cache[key] = entry
        return entry

    def _build_operators(self, dt_s: float) -> None:
        """Factorise A = C/dt - theta*G for `dt_s` and re-arm the startup."""
        A_mat, M_mat, lu = self._get_operators(dt_s, self.theta)
        self._A_mat = A_mat
        self._M_mat = M_mat
        self._lu = lu
        self._dt_factorised = float(dt_s)
        self.reset_startup()

    def reset_dt(self, dt_s: float) -> None:
        """Rebuild operators / LU factorisation for a new timestep."""
        self.dt_s = float(dt_s)
        self._build_operators(self.dt_s)

    def reset_startup(self) -> None:
        """Re-arm the Rannacher startup (next steps use backward Euler).

        Call this whenever a new integration begins or the state jumps
        discontinuously, so that the stiff modes excited by the discontinuity
        are annihilated instead of ringing.  step() also re-arms it
        automatically when the state it receives is not the state it last
        returned.
        """
        self._steps_taken = 0
        self._last_V_out = None

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

        # A state that is not the one we last returned means the caller has
        # started a new integration (or perturbed the state): re-arm startup.
        if (
            self._last_V_out is None
            or self._last_V_out.shape != V.shape
            or not np.array_equal(V, self._last_V_out)
        ):
            self.reset_startup()

        theta = 1.0 if self._steps_taken < self.rannacher_steps else self.theta
        _, M_mat, lu = self._get_operators(self.dt_s, theta)

        rhs = M_mat.dot(V) + self._b_vec + I_ext
        V_new = lu.solve(rhs)

        self._steps_taken += 1
        self._last_V_out = V_new.copy()
        return V_new

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

        self.reset_startup()   # fresh initial condition -> damp stiff modes

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

    def measure_dc_attenuation(
        self,
        inject_idx: int,
        record_idx: int,
        I_amp: float = 1e-10,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
    ) -> float:
        """DC voltage attenuation for current injected at `inject_idx`.

        Returns dV(record_idx) / dV(inject_idx) at DC steady state.

        FIX#4 — attenuation in a dendritic tree is asymmetric.  The transfer
        resistance R_ij is symmetric (reciprocity), so
            att(i -> j) = R_ij / R_ii        att(j -> i) = R_ij / R_jj
        i.e. the two directions differ by the ratio of the local input
        resistances.  The soma is a large current sink (R_in ~ 70 MOhm) while a
        thin distal tuft compartment has a much larger input resistance, so
        somatic input spreads well into the tuft (weak attenuation) whereas
        distal input is heavily attenuated on the way to the soma.

        Parameters
        ----------
        inject_idx  : int    compartment receiving the DC current.
        record_idx  : int    compartment where the response is recorded.
        I_amp       : float  test current (A). Default 100 pA.
        dt_settle_s : float  coarse dt for settling (s).
        t_settle_s  : float  settling duration (s).
        """
        V_rest = self.steady_state(dt_settle_s=dt_settle_s, t_settle_s=t_settle_s)

        I_ext = np.zeros(self.N)
        I_ext[inject_idx] = I_amp
        saved_dt = self.dt_s
        self.reset_dt(dt_settle_s)

        V = V_rest.copy()
        n_steps = max(1, int(round(t_settle_s / dt_settle_s)))
        for _ in range(n_steps):
            V_new = self.step(V, 0.0, I_ext)
            if np.max(np.abs(V_new - V)) < 1e-15:
                V = V_new
                break
            V = V_new

        self.reset_dt(saved_dt)

        dV_inject = float(V[inject_idx]) - float(V_rest[inject_idx])
        dV_record = float(V[record_idx]) - float(V_rest[record_idx])

        if abs(dV_inject) < 1e-30:
            return 0.0
        return dV_record / dV_inject

    def measure_voltage_attenuation(
        self,
        soma_idx: int,
        distal_idx: int,
        I_amp: float = 1e-10,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
    ) -> float:
        """DC attenuation soma -> distal: inject at soma, record distal.

        Returns dV_distal / dV_soma.  This is the WEAK direction (~0.59 for a
        1.1 lambda apical path); see measure_voltage_attenuation_to_soma() for
        the > 10x direction used as the Phase 0a validation target.
        """
        return self.measure_dc_attenuation(
            inject_idx  = soma_idx,
            record_idx  = distal_idx,
            I_amp       = I_amp,
            dt_settle_s = dt_settle_s,
            t_settle_s  = t_settle_s,
        )

    def measure_voltage_attenuation_to_soma(
        self,
        soma_idx: int,
        distal_idx: int,
        I_amp: float = 1e-10,
        dt_settle_s: float = 5e-3,
        t_settle_s: float = 1.0,
    ) -> float:
        """DC attenuation distal -> soma: inject at distal, record soma.

        Returns dV_soma / dV_distal.  This is the strongly attenuating
        direction; for a human L5 pyramidal tuft it should be < 0.10
        (> 10x attenuation of distal input at the soma).
        """
        return self.measure_dc_attenuation(
            inject_idx  = distal_idx,
            record_idx  = soma_idx,
            I_amp       = I_amp,
            dt_settle_s = dt_settle_s,
            t_settle_s  = t_settle_s,
        )
