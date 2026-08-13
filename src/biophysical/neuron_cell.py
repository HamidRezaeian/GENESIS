"""neuron_cell.py — NeuronCell: top-level facade for the biophysical neuron.

This is the PRIMARY ENTRY POINT for the biophysical package.  It orchestrates:
    morphology building  →  mechanism attachment  →  solver construction
    →  simulation  →  recording  →  validation

Quick-start
-----------
    from biophysical.neuron_cell import NeuronCell

    cell = NeuronCell().build()
    print(cell)   # NeuronCell(n=224, dt=25.0µs, build=83ms)

    # Passive recording (no current)
    rec = cell.run(t_max_s=0.5)
    soma_mV = rec.traces_mV()['soma']

    # Somatic current injection
    rec = cell.run(t_max_s=1.0, soma_amp_A=100e-12, onset_s=0.1, dur_s=0.5)

    # Validation
    summary = cell.validate()
    summary.print_report()

Phase 0a scope
--------------
    Passive cable model only.  Membrane: LeakChannel + NaKPump (I=0).
    Solver: Crank-Nicolson with SuperLU factorisation.
    No voltage-gated channels; these appear in Phase 0b+.

DNA → RNA → Protein NOTE
--------------------------
    Phase 0e (Gene Expression) is CRITICAL to PROJECT GENESIS.
    The channel densities, transporter concentrations, and pump rates
    introduced in phases 0b–0h will be derived from gene-expression
    outputs (mRNA abundances → protein copy numbers → channel densities).
    Placeholder hooks are provided in NaKPump (Phase 0a) and will be
    wired in Phase 0e.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import time
import numpy as np

from biophysical.core.constants import MEM
from biophysical.morphology.compartment import Compartment
from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.recorder import Recorder
from biophysical.simulation.current_clamp import CurrentClampProtocol as CurrentClamp, MultiProtocol


class NeuronCell:
    """Human L5 pyramidal neuron passive cable model — Phase 0a.

    Parameters
    ----------
    dt_s : float
        Simulation timestep (seconds).  Default: 25 µs (0.025 ms).
        Must satisfy dt_s << tau_m (30 ms) for accuracy.
    """

    def __init__(self, dt_s: float = 25e-6) -> None:
        self.dt_s             = float(dt_s)
        self.compartments:    Optional[List[Compartment]]   = None
        self.meta:            Optional[Dict]                = None
        self.solver:          Optional[CrankNicolsonSolver] = None
        self._built:          bool                          = False
        self._build_time_s:   float                        = 0.0

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, apply_bilayer: bool = True) -> 'NeuronCell':
        """Build compartment tree, attach mechanisms, and factorize solver.

        Parameters
        ----------
        apply_bilayer : bool
            If True (default), attach LeakChannel + NaKPump to every
            compartment via LipidBilayer.apply_to_compartments().

        Returns
        -------
        self  (for chaining: ``cell = NeuronCell().build()``)
        """
        t0 = time.perf_counter()

        self.compartments, self.meta = build_l5_pyramidal(
            apply_bilayer=apply_bilayer,
        )
        self.solver = CrankNicolsonSolver(
            compartments=self.compartments,
            dt_s=self.dt_s,
        )

        self._built        = True
        self._build_time_s = time.perf_counter() - t0
        return self

    def _require_built(self) -> None:
        if not self._built:
            raise RuntimeError(
                'Call NeuronCell.build() before running simulations.'
            )

    # ------------------------------------------------------------------
    # Initial state
    # ------------------------------------------------------------------

    def resting_state(self) -> np.ndarray:
        """Return the analytical resting potential vector (Volts).

        For Phase 0a (leak-only model), V_rest = EL everywhere by
        construction.  Returns np.ndarray (N,) of shape (n_compartments,).
        """
        self._require_built()
        return np.full(len(self.compartments), MEM.E_leak_V)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def run(
        self,
        t_max_s:     float,
        soma_amp_A:  float = 0.0,
        onset_s:     float = 0.0,
        dur_s:       Optional[float] = None,
        protocols:   Optional[MultiProtocol] = None,
        V0:          Optional[np.ndarray] = None,
        record_idxs: Optional[List[int]] = None,
        record_every: int = 10,
    ) -> Recorder:
        """Run the passive cable simulation and return a voltage Recorder.

        Parameters
        ----------
        t_max_s      : float  total simulation time (s).
        soma_amp_A   : float  current amplitude at soma (A).  0 = passive.
        onset_s      : float  onset time for soma current (s).
        dur_s        : float  duration of soma current (s); defaults to t_max_s.
        protocols    : MultiProtocol  custom multi-site stimulation.
                       If provided, overrides soma_amp_A.
        V0           : np.ndarray (N,) or None  initial voltages (V).
                       Default: resting_state().
        record_idxs  : List[int] or None  compartments to record from.
                       Default: soma + last trunk + last tuft + first basal.
        record_every : int  record every N-th timestep (controls output size).
                       Default 10 (record every 0.25 ms at dt=25 µs).

        Returns
        -------
        Recorder  containing voltage traces; access via rec.traces_mV().
        """
        self._require_built()
        N = len(self.compartments)

        # ---- Recording sites ----
        if record_idxs is None:
            idxs   = [self.meta['soma_idx']]
            labels = ['soma']
            if self.meta['apical_trunk_idxs']:
                idxs.append(self.meta['apical_trunk_idxs'][-1])
                labels.append('apical_trunk_distal')
            if self.meta['apical_tuft_idxs']:
                idxs.append(self.meta['apical_tuft_idxs'][-1])
                labels.append('apical_tuft_distal')
            if self.meta['basal_idxs']:
                idxs.append(self.meta['basal_idxs'][0])
                labels.append('basal_proximal')
        else:
            idxs   = list(record_idxs)
            labels = [f'comp_{i}' for i in idxs]

        rec = Recorder(idxs, labels)
        V   = self.resting_state() if V0 is None else V0.copy()
        dt  = self.dt_s
        n_steps = max(1, int(round(t_max_s / dt)))

        # ---- Stimulus ----
        if protocols is not None:
            proto: Optional[MultiProtocol] = protocols
        elif abs(soma_amp_A) > 1e-30:
            d = dur_s if dur_s is not None else t_max_s
            proto = MultiProtocol([
                CurrentClampProtocol(
                    amp_A      = soma_amp_A,
                    onset_s    = onset_s,
                    dur_s      = d,
                    target_idx = self.meta['soma_idx'],
                )
            ])
        else:
            proto = None

        I_zero = np.zeros(N)
        rec.record(V, 0.0)

        for step_n in range(n_steps):
            t = step_n * dt
            I = proto.get_I_ext(t, N) if proto else I_zero
            V = self.solver.step(V, t, I)
            if (step_n + 1) % record_every == 0:
                rec.record(V, t + dt)

        return rec

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> 'ValidationSummary':
        """Run all Phase 0a passive validation checks.

        Returns
        -------
        ValidationSummary  with .all_passed(), .results, and .print_report().
        """
        self._require_built()
        from biophysical.validation.passive_validation import PassiveValidator
        validator = PassiveValidator(self.compartments, self.meta, self.solver)
        results   = validator.run_all()
        return ValidationSummary(results, validator.benchmark, self.meta)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def soma_idx(self) -> int:
        self._require_built()
        return int(self.meta['soma_idx'])

    @property
    def n_compartments(self) -> int:
        self._require_built()
        return int(self.meta['n_compartments'])

    @property
    def total_area_um2(self) -> float:
        self._require_built()
        return float(self.meta['total_area_um2'])

    @property
    def build_time_ms(self) -> float:
        return self._build_time_s * 1e3

    def __repr__(self) -> str:
        if self._built:
            return (f'NeuronCell('
                    f'n={self.n_compartments}, '
                    f'dt={self.dt_s*1e6:.1f}µs, '
                    f'build={self._build_time_s*1e3:.0f}ms)')
        return 'NeuronCell(not built)'


# ---------------------------------------------------------------------------
# ValidationSummary
# ---------------------------------------------------------------------------

class ValidationSummary:
    """Thin wrapper around PassiveValidator results.

    Attributes
    ----------
    results   : list of ValidationResult
    benchmark : PerformanceBenchmark
    meta      : dict
    """

    def __init__(self, results, benchmark, meta: Dict) -> None:
        self.results   = results
        self.benchmark = benchmark
        self.meta      = meta

    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def n_total(self) -> int:
        return len(self.results)

    def print_report(self) -> None:
        print(str(self))

    def __str__(self) -> str:
        from biophysical.validation.report import generate_text_report
        return generate_text_report(self.results, self.benchmark, self.meta)

    def __repr__(self) -> str:
        return (f'ValidationSummary('
                f'{self.n_passed()}/{self.n_total()} passed, '
                f'all_ok={self.all_passed()})')
