"""neuron_cell.py — NeuronCell: top-level facade for the biophysical neuron.

This is the PRIMARY ENTRY POINT for the biophysical package.  It orchestrates:
    morphology building  →  mechanism attachment  →  solver construction
    →  simulation  →  recording  →  validation

Quick-start
-----------
    from biophysical.neuron_cell import NeuronCell
    from biophysical.simulation.current_clamp import CurrentClampProtocol

    # Phase 0a — passive cable (default, behaviour unchanged)
    cell = NeuronCell().build()
    print(cell)   # NeuronCell(n=224, dt=25.0µs, mode=passive, build=83ms)

    # Passive recording (no current)
    rec = cell.run(t_max_s=0.5)
    soma_mV = rec.traces_mV()['soma']

    # Somatic current injection (passive)
    rec = cell.run(t_max_s=1.0, soma_amp_A=100e-12, onset_s=0.1, dur_s=0.5)

    # Phase 0b — active membrane (NaV1.6 + SKv3.1, Hines staggered solver)
    cell = NeuronCell().build(active=True)
    proto = CurrentClampProtocol(
        amp_A=1e-9, onset_s=1e-3, dur_s=5e-3, target_idx=cell.soma_idx,
    )
    rec = cell.run_active(protocol=proto, duration_s=10e-3)
    soma_mV = rec.traces_mV()['soma']

    # Validation
    summary = cell.validate()          # passive Phase 0a checks
    report  = cell.validate_active()   # 6 action-potential protocols (Phase 0b)

Phase 0a scope
--------------
    Passive cable model only.  Membrane: LeakChannel + NaKPump (I=0).
    Solver: Crank-Nicolson with SuperLU factorisation.
    No voltage-gated channels; these appear in Phase 0b.

Phase 0b scope
--------------
    build(active=True) attaches the Hay et al. (2011) NaV1.6 / SKv3.1 channel
    distribution (channels/channel_distributions.py) on top of the passive
    bilayer and switches the solver to ActiveSolver (Hines 1984 staggered
    semi-implicit scheme; unconditionally stable for any gbar, dt > 0).

    Known findings carried over from Step 4 (documented, deliberately NOT
    fixed here):
      FINDING-1: nata_alpha_h / nata_beta_h are swapped in channels/gating.py
                 (h∞ is inverted), so spikes do not repolarise correctly.
      FINDING-2: −70 mV is not an equilibrium of the active model
                 (Na window conductance exceeds leak at rest).
    validate_active() reports these honestly as failing checks instead of
    hiding them.

DNA → RNA → Protein NOTE
--------------------------
    Phase 0e (Gene Expression) is CRITICAL to PROJECT GENESIS.
    The channel densities, transporter concentrations, and pump rates
    introduced in phases 0b–0h will be derived from gene-expression
    outputs (mRNA abundances → protein copy numbers → channel densities).
    Placeholder hooks are provided in NaKPump (Phase 0a) and in
    ChannelDistribution (the Phase 0e DensityProvider protocol).
"""

from __future__ import annotations
from typing import Dict, List, Optional
import time
import numpy as np

from biophysical.core.constants import MEM
from biophysical.morphology.compartment import Compartment
from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
from biophysical.channels.channel_distributions import apply_hay_2011_distribution
from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.active_solver import ActiveSolver, ProtocolLike
from biophysical.simulation.recorder import Recorder
from biophysical.simulation.current_clamp import CurrentClampProtocol as CurrentClamp, MultiProtocol


class NeuronCell:
    """Human L5 pyramidal neuron — passive (Phase 0a) and active (Phase 0b).

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
        self.active:          bool                          = False
        self._built:          bool                          = False
        self._build_time_s:   float                         = 0.0

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, apply_bilayer: bool = True, active: bool = False) -> 'NeuronCell':
        """Build compartment tree, attach mechanisms, and factorize solver.

        Parameters
        ----------
        apply_bilayer : bool
            If True (default), attach LeakChannel + NaKPump to every
            compartment via LipidBilayer.apply_to_compartments().
        active : bool
            Phase 0b switch.  If True, additionally attach the Hay et al.
            (2011) NaV1.6 / SKv3.1 channel distribution and construct an
            ActiveSolver (Hines 1984 staggered semi-implicit scheme).
            If False (default), Phase 0a passive behaviour is preserved
            exactly (plain CrankNicolsonSolver, leak only).

        Returns
        -------
        self  (for chaining: ``cell = NeuronCell().build(active=True)``)
        """
        t0 = time.perf_counter()

        self.compartments, self.meta = build_l5_pyramidal(
            apply_bilayer=apply_bilayer,
        )

        if active:
            # Attach NaV16Channel / KvChannel to excitable regions (Step 3).
            # Zero-density regions (BASAL, MYELIN, AXON_TERMINAL) are skipped
            # by the distribution and stay purely passive.
            apply_hay_2011_distribution(self.compartments)
            self.solver = ActiveSolver(
                compartments=self.compartments,
                dt_s=self.dt_s,
            )
        else:
            self.solver = CrankNicolsonSolver(
                compartments=self.compartments,
                dt_s=self.dt_s,
            )

        self.active        = bool(active)
        self._built        = True
        self._build_time_s = time.perf_counter() - t0
        return self

    def _require_built(self) -> None:
        if not self._built:
            raise RuntimeError(
                'Call NeuronCell.build() before running simulations.'
            )

    def _require_active(self) -> None:
        self._require_built()
        if not isinstance(self.solver, ActiveSolver):
            raise RuntimeError(
                'This method requires build(active=True); the passive build '
                'has no voltage-gated channels.'
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
    # Simulation — passive (Phase 0a, unchanged)
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
                CurrentClamp(
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
    # Simulation — active (Phase 0b)
    # ------------------------------------------------------------------

    def run_active(
        self,
        protocol:     ProtocolLike = None,
        duration_s:   Optional[float] = None,
        record_idxs:  Optional[List[int]] = None,
        V0:           Optional[np.ndarray] = None,
        record_every: int = 1,
        init_gates:   bool = True,
    ) -> Recorder:
        """Run an active-membrane simulation (Hines staggered scheme).

        Parameters
        ----------
        protocol     : CurrentClampProtocol | MultiProtocol | list | None
                       Stimulus.  None = zero external current.
        duration_s   : float  total simulation time (s).  Required.
        record_idxs  : List[int] or None  compartments to record from.
                       Default: soma + first AIS compartment.
        V0           : np.ndarray (N,) or None  initial voltages (V).
                       Default: resting_state().
        record_every : int  record every N-th timestep.  Default 1.
        init_gates   : bool  initialise all channel gates to their steady
                       state at V0 before the run (default True).

        Returns
        -------
        Recorder  with labels 'soma', 'ais_proximal' for the default sites
        (or 'comp_i' for custom record_idxs).
        """
        self._require_active()
        if duration_s is None:
            raise ValueError('duration_s is required')

        # ---- Recording sites ----
        if record_idxs is None:
            idxs   = [self.soma_idx]
            labels = ['soma']
            if self.meta.get('ais_idxs'):
                idxs.append(int(self.meta['ais_idxs'][0]))
                labels.append('ais_proximal')
        else:
            idxs   = list(record_idxs)
            labels = [f'comp_{i}' for i in idxs]

        rec = self.solver.run(
            protocols=protocol,
            duration_s=duration_s,
            record_idxs=idxs,
            V0=V0,
            record_every=record_every,
            init_gates=init_gates,
        )
        rec.labels = labels
        return rec

    # ------------------------------------------------------------------
    # Validation — passive (Phase 0a, unchanged)
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
    # Validation — active (Phase 0b)
    # ------------------------------------------------------------------

    def validate_active(self, spike_V: float = 0.0) -> 'ValidationReport':
        """Run the 6 Phase 0b action-potential validation protocols.

        Protocols (somatic current clamp, somatic recording):
          1. resting_potential_active — zero-current soma voltage after 10 ms.
          2. ap_threshold             — bisection estimate of the minimum
                                        pulse amplitude eliciting a spike (pA).
          3. ap_amplitude             — spike peak above baseline (mV).
          4. ap_half_width            — spike width at half amplitude (ms).
          5. repetitive_firing        — spike count during a sustained 2 nA
                                        pulse.
          6. ahp_depth                — post-pulse undershoot depth (mV).

        Known findings from Step 4 (FINDING-1 h-gate swap, FINDING-2 rest
        is not an equilibrium) will mark some checks as failed; this is
        reported honestly rather than masked.

        Returns
        -------
        ValidationReport  with one ValidationResult per protocol.
        """
        self._require_active()
        from biophysical.validation.report import ValidationReport

        report = ValidationReport(title='Phase 0b Active Validation')
        soma   = self.soma_idx

        def _trace(rec: Recorder):
            return rec.get_time(), rec.get_trace(soma)

        def _baseline(t: np.ndarray, v: np.ndarray, onset_s: float) -> float:
            mask = t < onset_s
            return float(np.mean(v[mask])) if np.any(mask) else float(v[0])

        # ---- 1. Resting potential with active channels ---------------------
        rec = self.run_active(protocol=None, duration_s=10e-3, record_idxs=[soma])
        _, v = _trace(rec)
        v_rest = float(v[-1])
        report.add_check(
            name='resting_potential_active',
            passed=bool(-0.075 <= v_rest <= -0.060),
            actual=round(v_rest * 1e3, 3),
            expected='-75 to -60 (FINDING-2: -70 mV is not an equilibrium)',
            unit='mV',
            message='Soma voltage after 10 ms of zero-current settling.',
        )

        # ---- 2. AP threshold (bisection on pulse amplitude) ----------------
        lo, hi = 0.0, 2e-9
        for _ in range(6):
            mid   = 0.5 * (lo + hi)
            proto = CurrentClamp(amp_A=mid, onset_s=1e-3, dur_s=6e-3, target_idx=soma)
            rec   = self.run_active(protocol=proto, duration_s=9e-3, record_idxs=[soma])
            _, v  = _trace(rec)
            if float(np.max(v)) > spike_V:
                hi = mid
            else:
                lo = mid
        threshold_A = float(hi)
        report.add_check(
            name='ap_threshold',
            passed=bool(threshold_A < 2e-9),
            actual=round(threshold_A * 1e12, 1),
            expected='< 2000',
            unit='pA',
            message='Minimum somatic pulse amplitude eliciting a spike.',
        )

        # ---- 3+4. AP amplitude and half-width (shared trace) ---------------
        I_strong     = max(1e-9, 1.5 * threshold_A)
        onset, dur   = 1e-3, 8e-3
        proto        = CurrentClamp(amp_A=I_strong, onset_s=onset, dur_s=dur,
                                    target_idx=soma)
        rec          = self.run_active(protocol=proto, duration_s=12e-3,
                                       record_idxs=[soma])
        t_arr, v     = _trace(rec)
        v_base       = _baseline(t_arr, v, onset)
        v_peak       = float(np.max(v))
        amp_mV       = (v_peak - v_base) * 1e3
        report.add_check(
            name='ap_amplitude',
            passed=bool(amp_mV > 60.0),
            actual=round(amp_mV, 2),
            expected='> 60',
            unit='mV',
            message='Spike peak height above the pre-pulse baseline.',
        )

        v_half = v_base + 0.5 * (v_peak - v_base)
        above  = np.flatnonzero(v >= v_half)
        if above.size >= 2 and amp_mV > 0.0:
            hw_ms    = float(t_arr[above[-1]] - t_arr[above[0]]) * 1e3
            hw_pass  = 0.5 <= hw_ms <= 3.0
            hw_value = round(hw_ms, 3)
        else:
            hw_pass  = False
            hw_value = None
        report.add_check(
            name='ap_half_width',
            passed=bool(hw_pass),
            actual=hw_value,
            expected='0.5 to 3 (FINDING-1: h-gate swap prevents repolarisation)',
            unit='ms',
            message='Spike width at half amplitude.',
        )

        # ---- 5. Repetitive firing -------------------------------------------
        proto = CurrentClamp(amp_A=2e-9, onset_s=1e-3, dur_s=28e-3,
                             target_idx=soma)
        rec   = self.run_active(protocol=proto, duration_s=32e-3,
                                record_idxs=[soma])
        _, v  = _trace(rec)
        n_spikes = int(np.sum((v[:-1] < spike_V) & (v[1:] >= spike_V)))
        report.add_check(
            name='repetitive_firing',
            passed=bool(n_spikes >= 2),
            actual=n_spikes,
            expected='>= 2 (FINDING-1: no repolarisation → at most one spike)',
            unit='spikes',
            message='Upward 0 mV crossings during a sustained 2 nA pulse.',
        )

        # ---- 6. After-hyperpolarisation depth -------------------------------
        proto        = CurrentClamp(amp_A=I_strong, onset_s=1e-3, dur_s=5e-3,
                                    target_idx=soma)
        rec          = self.run_active(protocol=proto, duration_s=16e-3,
                                       record_idxs=[soma])
        t_arr, v     = _trace(rec)
        v_base       = _baseline(t_arr, v, 1e-3)
        post         = t_arr >= 10e-3
        if np.any(post):
            ahp_mV    = (v_base - float(np.min(v[post]))) * 1e3
            ahp_pass  = ahp_mV > 0.5
            ahp_value = round(ahp_mV, 3)
        else:
            ahp_pass  = False
            ahp_value = None
        report.add_check(
            name='ahp_depth',
            passed=bool(ahp_pass),
            actual=ahp_value,
            expected='> 0.5 (FINDING-1: no undershoot without repolarisation)',
            unit='mV',
            message='Post-pulse undershoot below the pre-pulse baseline.',
        )

        return report

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
    def is_active(self) -> bool:
        """True when built with active=True (voltage-gated channels)."""
        return self.active

    @property
    def build_time_ms(self) -> float:
        return self._build_time_s * 1e3

    def __repr__(self) -> str:
        if self._built:
            mode = 'active' if self.active else 'passive'
            return (f'NeuronCell('
                    f'n={self.n_compartments}, '
                    f'dt={self.dt_s*1e6:.1f}µs, '
                    f'mode={mode}, '
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
