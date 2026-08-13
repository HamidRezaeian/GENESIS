"""simulation_engine.py — background-thread runner for the real ActiveSolver.

This is the only place in the visualiser that advances time.  It owns

    cell   = NeuronCell(dt_s).build(active=True)
    solver = cell.solver              # ActiveSolver

and runs the exact loop from the specification::

    while t < duration_s:
        for _ in range(stream_every):          # 10 timesteps = 250 us
            V = solver.step(V, t, I_ext(t))
            t += solver.dt_s
        publish(build_state_message(V, t, solver))

Every number published downstream is a value ``ActiveSolver.step()`` returned.
Nothing is faked, smoothed, replayed or pre-computed.

Why a thread and not an asyncio task
------------------------------------
``solver.step()`` is synchronous CPU work (sparse solve + Python gate
kinetics).  Running it inside the event loop would block every WebSocket in
the process.  The solver therefore lives on a daemon thread and hands frames
to the event loop through :class:`~biophysical.visualizer.data_streamer.
WebSocketStreamer`, which uses ``loop.call_soon_threadsafe``.

Playback speed
--------------
``speed`` paces the *frame rate*, it never changes ``dt``, so the physics is
identical at every speed setting:

    target frame interval = 1 / (60 x speed)

1x therefore streams 60 frames/s = 600 timesteps/s = **15 ms of simulated
time per wall-clock second**.  At high speeds the solver simply runs flat out
and the reported ``fps`` shows what it actually achieved.

Fidelity notes (inherited from the model, not introduced here)
--------------------------------------------------------------
The active model carries two documented findings — swapped NaTa_t h-gate rates
(FINDING-1) and -70 mV not being an exact equilibrium of the active model
(FINDING-2).  The visualiser deliberately does **not** compensate for either:
it shows what the solver computes, including the resting-state drift.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from biophysical.neuron_cell import NeuronCell
from biophysical.simulation.active_solver import ActiveSolver
from biophysical.simulation.current_clamp import CurrentClampProtocol, MultiProtocol
from biophysical.visualizer.data_streamer import ChannelSampler, build_state_message

log = logging.getLogger("genesis.visualizer.engine")

#: Frames per second that corresponds to 1x playback.
BASELINE_FPS: float = 60.0
MIN_SPEED: float = 0.1
MAX_SPEED: float = 100.0

Subscriber = Callable[[Dict[str, Any]], None]


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

@dataclass
class SimulationConfig:
    """User-facing run parameters (all values arrive from the browser)."""

    duration_ms: float = 30.0
    amp_pA: float = 1500.0
    onset_ms: float = 1.0
    dur_ms: float = 5.0
    target_idx: Optional[int] = None      # None -> soma
    stream_every: int = 10                # timesteps per streamed frame
    speed: float = 1.0                    # 0.1x .. 100x
    spike_threshold_mV: float = 0.0
    loop: bool = False

    # -- validation ------------------------------------------------------

    @staticmethod
    def _num(value: Any, lo: float, hi: float, fallback: float) -> float:
        try:
            out = float(value)
        except (TypeError, ValueError):
            return fallback
        if math.isnan(out) or math.isinf(out):
            return fallback
        return max(lo, min(hi, out))

    @classmethod
    def from_dict(
        cls,
        data: Optional[Dict[str, Any]],
        base: Optional["SimulationConfig"] = None,
    ) -> "SimulationConfig":
        """Merge untrusted client input over ``base``, clamping every field."""
        base = base or cls()
        d = dict(data or {})

        raw_target = d.get("target_idx", base.target_idx)
        try:
            target_idx = None if raw_target is None else int(raw_target)
        except (TypeError, ValueError):
            target_idx = base.target_idx

        return cls(
            duration_ms=cls._num(d.get("duration_ms", base.duration_ms), 0.1, 10_000.0, base.duration_ms),
            amp_pA=cls._num(d.get("amp_pA", base.amp_pA), -50_000.0, 50_000.0, base.amp_pA),
            onset_ms=cls._num(d.get("onset_ms", base.onset_ms), 0.0, 10_000.0, base.onset_ms),
            dur_ms=cls._num(d.get("dur_ms", base.dur_ms), 0.0, 10_000.0, base.dur_ms),
            target_idx=target_idx,
            stream_every=int(cls._num(d.get("stream_every", base.stream_every), 1, 500, base.stream_every)),
            speed=cls._num(d.get("speed", base.speed), MIN_SPEED, MAX_SPEED, base.speed),
            spike_threshold_mV=cls._num(
                d.get("spike_threshold_mV", base.spike_threshold_mV), -100.0, 100.0, base.spike_threshold_mV
            ),
            loop=bool(d.get("loop", base.loop)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------------

class SimulationEngine:
    """Owns the cell, the solver and the thread that advances them.

    A single engine instance is shared by every connected browser, so all
    clients observe the same simulation and identical numbers.

    Parameters
    ----------
    dt_s : float      solver timestep [s] (default 25 us, the model default).
    active : bool     build with voltage-gated channels (default True).
    config : SimulationConfig | None
    """

    def __init__(
        self,
        dt_s: float = 25e-6,
        active: bool = True,
        config: Optional[SimulationConfig] = None,
    ) -> None:
        self.dt_s = float(dt_s)
        self.active = bool(active)
        self.config = config if isinstance(config, SimulationConfig) else SimulationConfig()

        self._cell: Optional[NeuronCell] = None
        self._sampler: Optional[ChannelSampler] = None
        self._build_ms: float = 0.0

        # State (guarded by _lock)
        self._lock = threading.RLock()
        self._V: Optional[np.ndarray] = None
        self._t: float = 0.0
        self._t_end: float = 0.0
        self._step: int = 0
        self._frame: int = 0
        self._spike_count: int = 0
        self._soma_spike_count: int = 0
        self._protocol: Optional[MultiProtocol] = None
        self._last_I: Optional[np.ndarray] = None
        self._zeros: Optional[np.ndarray] = None
        self._state: str = "unbuilt"
        self._fps: float = 0.0
        self._sim_ms_per_s: float = 0.0
        self._last_frame: Optional[Dict[str, Any]] = None

        # Threading
        self._thread: Optional[threading.Thread] = None
        self._playing = threading.Event()
        self._stopping = threading.Event()
        self._generation = 0

        # Subscribers
        self._subs: List[Subscriber] = []
        self._subs_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, force: bool = False) -> "SimulationEngine":
        """Build the 224-compartment cell and its solver (idempotent)."""
        with self._lock:
            if self._cell is not None and not force:
                return self
            t0 = time.perf_counter()
            cell = NeuronCell(dt_s=self.dt_s).build(active=self.active)
            self._build_ms = (time.perf_counter() - t0) * 1e3
            self._cell = cell
            self._sampler = ChannelSampler(cell.compartments)
            self._zeros = np.zeros(len(cell.compartments), dtype=np.float64)
            self._reset_state_locked()
            log.info(
                "built %d compartments (%s, %d channels) in %.0f ms",
                len(cell.compartments),
                type(cell.solver).__name__,
                self._sampler.n_channels,
                self._build_ms,
            )
        return self

    @property
    def is_built(self) -> bool:
        return self._cell is not None

    @property
    def cell(self) -> NeuronCell:
        self.build()
        assert self._cell is not None
        return self._cell

    @property
    def solver(self) -> Any:
        return self.cell.solver

    @property
    def n_compartments(self) -> int:
        return len(self.cell.compartments)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _reset_state_locked(self) -> None:
        """Return the model to t = 0. Caller must hold ``_lock``."""
        cell = self._cell
        assert cell is not None
        solver = cell.solver

        self._V = np.asarray(cell.resting_state(), dtype=np.float64).copy()

        # Gates back to steady state at the resting potential, exactly as
        # ActiveSolver.run(init_gates=True) does before its first step.
        if isinstance(solver, ActiveSolver) and solver.has_active_channels:
            solver.initialise_gates(self._V)
        reset_startup = getattr(solver, "reset_startup", None)
        if callable(reset_startup):
            reset_startup()

        self._t = 0.0
        self._step = 0
        self._frame = 0
        self._spike_count = 0
        self._soma_spike_count = 0
        self._last_I = None
        self._t_end = self.config.duration_ms * 1e-3
        self._protocol = self._make_protocol_locked()
        self._fps = 0.0
        self._sim_ms_per_s = 0.0
        self._last_frame = None
        self._state = "idle"

    def _make_protocol_locked(self) -> Optional[MultiProtocol]:
        """Build the current-clamp protocol from the current config."""
        cell = self._cell
        assert cell is not None
        cfg = self.config
        if abs(cfg.amp_pA) < 1e-9 or cfg.dur_ms <= 0.0:
            return None
        idx = cfg.target_idx if cfg.target_idx is not None else int(cell.soma_idx)
        idx = max(0, min(len(cell.compartments) - 1, int(idx)))
        return MultiProtocol([
            CurrentClampProtocol(
                amp_A=cfg.amp_pA * 1e-12,
                onset_s=cfg.onset_ms * 1e-3,
                dur_s=cfg.dur_ms * 1e-3,
                target_idx=idx,
            )
        ])

    # ------------------------------------------------------------------
    # Transport controls
    # ------------------------------------------------------------------

    def start(self, config: Optional[Dict[str, Any]] = None, restart: bool = True) -> None:
        """Start (or restart) the run and begin streaming."""
        self.build()
        with self._lock:
            if config:
                self.config = SimulationConfig.from_dict(config, self.config)
            if restart or self._state in ("idle", "finished"):
                self._reset_state_locked()
            self._state = "running"
        self._ensure_thread()
        self._playing.set()
        self._publish(self.status())

    def pause(self) -> None:
        self._playing.clear()
        with self._lock:
            if self._state == "running":
                self._state = "paused"
        self._publish(self.status())

    def resume(self) -> None:
        with self._lock:
            if self._state == "finished":
                return
            if self._cell is None:
                return
            self._state = "running"
        self._ensure_thread()
        self._playing.set()
        self._publish(self.status())

    def toggle(self) -> None:
        if self._playing.is_set():
            self.pause()
        else:
            self.resume()

    def reset(self, config: Optional[Dict[str, Any]] = None, publish: bool = True) -> None:
        """Rewind to t = 0 (gates re-initialised, spike counters cleared)."""
        self.build()
        self._playing.clear()
        with self._lock:
            if config:
                self.config = SimulationConfig.from_dict(config, self.config)
            self._reset_state_locked()
        if publish:
            self._publish(self.status())

    def stop(self, join: bool = True, timeout: float = 2.0) -> None:
        """Stop the worker thread (state is preserved; ``resume`` restarts it)."""
        self._stopping.set()
        self._playing.set()          # wake the loop so it can observe the flag
        thread = self._thread
        if join and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        self._playing.clear()
        self._stopping.clear()
        with self._lock:
            self._thread = None
            if self._state == "running":
                self._state = "paused"

    def set_speed(self, value: Any) -> None:
        with self._lock:
            self.config.speed = SimulationConfig._num(value, MIN_SPEED, MAX_SPEED, self.config.speed)

    def configure(self, config: Optional[Dict[str, Any]]) -> None:
        """Apply config changes live (stimulus edits take effect immediately)."""
        with self._lock:
            self.config = SimulationConfig.from_dict(config, self.config)
            if self._cell is not None:
                self._t_end = self.config.duration_ms * 1e-3
                self._protocol = self._make_protocol_locked()
                self._last_I = None      # force a Rannacher re-arm next step
                if self._state == "finished" and self._t < self._t_end:
                    self._state = "paused"

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _ensure_thread(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stopping.clear()
            self._generation += 1
            generation = self._generation
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(generation,),
                name="genesis-solver",
                daemon=True,
            )
            self._thread.start()

    def _frame_interval(self) -> float:
        speed = max(MIN_SPEED, min(MAX_SPEED, float(self.config.speed)))
        return 1.0 / (BASELINE_FPS * speed)

    def _run_loop(self, generation: int) -> None:
        log.debug("solver thread %d started", generation)
        while True:
            if self._stopping.is_set() or generation != self._generation:
                return
            if not self._playing.is_set():
                self._playing.wait(timeout=0.1)
                continue

            t_start = time.perf_counter()
            try:
                frame, finished = self._advance_frame()
            except Exception as exc:  # pragma: no cover - surface, don't die
                log.exception("solver step failed")
                with self._lock:
                    self._state = "error"
                self._playing.clear()
                self._publish({
                    "type": "error",
                    "message": f"solver failed at t = {self._t * 1e3:.3f} ms: {exc}",
                    "context": "step",
                })
                self._publish(self.status())
                continue

            if frame is not None:
                self._publish(frame)

            if finished:
                if self.config.loop:
                    self.reset(publish=False)
                    with self._lock:
                        self._state = "running"
                    self._playing.set()
                    continue
                with self._lock:
                    self._state = "finished"
                self._playing.clear()
                self._publish(self.status())
                continue

            # Pace playback.
            interval = self._frame_interval()
            elapsed = time.perf_counter() - t_start
            if interval > elapsed:
                time.sleep(interval - elapsed)

            total = max(time.perf_counter() - t_start, 1e-9)
            with self._lock:
                inst = 1.0 / total
                self._fps = inst if self._fps <= 0.0 else 0.85 * self._fps + 0.15 * inst
                self._sim_ms_per_s = self._fps * self.config.stream_every * self.dt_s * 1e3

    def _advance_frame(self) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Advance ``stream_every`` timesteps and build one state frame.

        The lock is taken per timestep rather than for the whole frame so a
        concurrent :meth:`inspect` never waits longer than a single step.
        """
        cell = self._cell
        assert cell is not None and self._V is not None
        solver = cell.solver
        n_comp = len(cell.compartments)
        soma_idx = int(cell.soma_idx)
        dt = self.dt_s
        threshold_V = self.config.spike_threshold_mV * 1e-3
        n_sub = max(1, int(self.config.stream_every))

        spikes: List[int] = []
        spiked: set = set()
        steps_done = 0
        stim_A = 0.0

        for _ in range(n_sub):
            with self._lock:
                if self._t >= self._t_end - 1e-15:
                    break

                if self._protocol is not None:
                    I_ext = self._protocol.get_I_ext(self._t, n_comp)
                    stim_A = float(I_ext[self._protocol.protocols[0].target_idx])
                else:
                    I_ext = self._zeros
                    stim_A = 0.0

                # ActiveSolver.run() re-arms Rannacher startup damping whenever
                # the stimulus changes; replicate it so manual stepping is
                # numerically identical to the built-in runner.
                if self._last_I is None or not np.array_equal(I_ext, self._last_I):
                    reset_startup = getattr(solver, "reset_startup", None)
                    if callable(reset_startup):
                        reset_startup()
                    self._last_I = np.array(I_ext, dtype=np.float64, copy=True)

                V_prev = self._V
                V_new = np.asarray(solver.step(V_prev, self._t, I_ext), dtype=np.float64)

                crossed = np.flatnonzero((V_prev < threshold_V) & (V_new >= threshold_V))
                if crossed.size:
                    for i in crossed.tolist():
                        i = int(i)
                        self._spike_count += 1
                        if i == soma_idx:
                            self._soma_spike_count += 1
                        if i not in spiked:
                            spiked.add(i)
                            spikes.append(i)

                self._V = V_new
                self._t += dt
                self._step += 1
                steps_done += 1

        if steps_done == 0:
            return None, True

        with self._lock:
            self._frame += 1
            V = self._V
            t_now = self._t
            sample = self._sampler.sample(V, t_now) if self._sampler is not None else None
            frame = build_state_message(
                t_s=t_now,
                V=V,
                sample=sample,
                spike_events=spikes,
                step=self._step,
                frame=self._frame,
                extra={
                    "v_soma_mV": round(float(V[soma_idx]) * 1e3, 3),
                    "spike_count": self._spike_count,
                    "soma_spike_count": self._soma_spike_count,
                    "stim_pA": round(stim_A * 1e12, 3),
                    "fps": round(self._fps, 1),
                    "sim_ms_per_s": round(self._sim_ms_per_s, 3),
                    "speed": self.config.speed,
                    "progress": round(min(1.0, t_now / self._t_end), 5) if self._t_end > 0 else 1.0,
                    "sim_state": self._state,
                },
            )
            self._last_frame = frame
            finished = self._t >= self._t_end - 1e-15

        return frame, finished

    # ------------------------------------------------------------------
    # Publish / subscribe
    # ------------------------------------------------------------------

    def subscribe(self, callback: Subscriber) -> None:
        with self._subs_lock:
            if callback not in self._subs:
                self._subs.append(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        with self._subs_lock:
            if callback in self._subs:
                self._subs.remove(callback)

    @property
    def n_subscribers(self) -> int:
        with self._subs_lock:
            return len(self._subs)

    def _publish(self, message: Dict[str, Any]) -> None:
        with self._subs_lock:
            subscribers = list(self._subs)
        for callback in subscribers:
            try:
                callback(message)
            except Exception:  # pragma: no cover - a bad client cannot stop us
                log.debug("subscriber raised", exc_info=True)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def last_frame(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last_frame

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "type": "status",
                "state": self._state,
                "t_ms": round(self._t * 1e3, 6),
                "duration_ms": self.config.duration_ms,
                "step": self._step,
                "frame": self._frame,
                "fps": round(self._fps, 1),
                "sim_ms_per_s": round(self._sim_ms_per_s, 3),
                "speed": self.config.speed,
                "spike_count": self._spike_count,
                "soma_spike_count": self._soma_spike_count,
                "playing": self._playing.is_set(),
                "config": self.config.to_dict(),
            }

    def describe(self) -> Dict[str, Any]:
        """Static model description sent once per client on connect."""
        self.build()
        cell = self._cell
        assert cell is not None and self._sampler is not None
        meta = dict(cell.meta)
        regions = {k: list(v) for k, v in meta.items() if isinstance(v, (list, tuple))}
        return {
            "n_compartments": len(cell.compartments),
            "soma_idx": int(cell.soma_idx),
            "dt_us": round(self.dt_s * 1e6, 6),
            "stream_every": self.config.stream_every,
            "frame_dt_us": round(self.dt_s * self.config.stream_every * 1e6, 3),
            "active": bool(getattr(cell, "is_active", self.active)),
            "solver": type(cell.solver).__name__,
            "n_channels": self._sampler.n_channels,
            "total_area_um2": round(float(meta.get("total_area_um2", 0.0)), 2),
            "build_ms": round(self._build_ms, 1),
            "baseline_fps": BASELINE_FPS,
            "speed_range": [MIN_SPEED, MAX_SPEED],
            "regions": regions,
            "config": self.config.to_dict(),
        }

    def inspect(self, idx: int) -> Dict[str, Any]:
        """Full live readout for one compartment (click-to-inspect)."""
        self.build()
        with self._lock:
            cell = self._cell
            assert cell is not None and self._V is not None
            i = max(0, min(len(cell.compartments) - 1, int(idx)))
            comp = cell.compartments[i]
            detail: Dict[str, Any] = {
                "type": "detail",
                "idx": i,
                "t_ms": round(self._t * 1e3, 6),
                "comp_type": comp.comp_type.name,
                "name": getattr(comp, "name", f"comp{i}"),
                "V_mV": round(float(self._V[i]) * 1e3, 4),
                "diameter_um": round(float(comp.diameter_m) * 1e6, 4),
                "length_um": round(float(comp.length_m) * 1e6, 4),
                "area_um2": round(float(comp.surface_area_m2) * 1e12, 4),
                "capacitance_pF": round(float(comp.total_capacitance_F) * 1e12, 4),
                "parent_idx": int(comp.parent_idx) if comp.parent_idx is not None else -1,
                "children_idxs": [int(c) for c in comp.children_idxs],
            }
            if self._sampler is not None:
                detail.update(self._sampler.describe(i, self._V, self._t))
            return detail

    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        state = self._state
        n = len(self._cell.compartments) if self._cell is not None else 0
        return f"<SimulationEngine {state} n={n} t={self._t * 1e3:.3f} ms>"
