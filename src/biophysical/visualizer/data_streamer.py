"""data_streamer.py — live solver state -> compact JSON frames -> WebSocket.

This module has two responsibilities and no simulation logic of its own.

1. :class:`ChannelSampler`
   Pre-indexes every :class:`VoltageGatedChannel` attached to the cell's
   compartments and, on demand, reads their **live** state:

     * ``g_Na`` / ``g_K``  — instantaneous conductance [S] obtained with the
       public-API probe ``channel_conductance_S()`` from
       :mod:`biophysical.simulation.active_solver` (the exact same helper the
       solver itself uses), i.e. ``-I(E_rev + 1 V) / 1 V = gbar * open``.
     * ``I_chan``         — ``mech.current(V_i, t)`` [A], inward-positive.
     * gate states        — ``mech.gate_state`` (``m``/``h`` for NaV1.6,
       ``n`` for SKv3.1).

   Nothing is modelled or approximated here: the sampler only reads state the
   solver has already computed.

2. :class:`WebSocketStreamer`
   Bridges the *threaded* :class:`~biophysical.visualizer.simulation_engine.
   SimulationEngine` to an *asyncio* WebSocket connection using
   ``loop.call_soon_threadsafe`` and a bounded drop-oldest queue, so that a
   slow or backgrounded browser tab can never stall the solver thread.
   It also implements the small client -> server control protocol.

Wire format (server -> client)
------------------------------
``state``  — one per streamed frame::

    {"type": "state", "t_ms": 1.234, "step": 50, "frame": 5,
     "V_mV": [224 values],
     "g_Na_nS": [224 values or null],
     "g_K_nS": [224 values or null],
     "I_chan_pA": [224 values or null],
     "spike_events": [compartment indices that crossed threshold this frame],
     "v_soma_mV": ..., "spike_count": ..., "fps": ..., "sim_state": ...}

``hello``  — sent once on connect (model description + current config).
``status`` — sent on every state transition and control acknowledgement.
``detail`` — full per-compartment inspection (voltage, conductances, gates).
``error``  — human-readable problem report.

Wire format (client -> server)
------------------------------
``{"type": "start", "config": {...}}``, ``pause``, ``resume``, ``toggle``,
``reset``, ``stop``, ``{"type": "speed", "value": 4.0}``,
``{"type": "stimulus", "amp_pA": 1500, "onset_ms": 1, "dur_ms": 5,
  "target_idx": 0}``, ``{"type": "inspect", "idx": 42}``, ``ping``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from biophysical.channels.base_channel import VoltageGatedChannel

try:  # the solver's own conductance probe — single source of truth
    from biophysical.simulation.active_solver import channel_conductance_S
except Exception:  # pragma: no cover - defensive fallback, same formula
    def channel_conductance_S(mech: Any, t: float = 0.0) -> float:
        """g = -I(E_rev + 1 V) / (1 V) = gbar * open_fraction  [S]."""
        return -float(mech.current(float(mech.E_rev_V) + 1.0, t))

try:  # starlette ships with FastAPI; keep this module importable without it
    from starlette.websockets import WebSocketDisconnect
except Exception:  # pragma: no cover
    class WebSocketDisconnect(Exception):  # type: ignore[no-redef]
        """Fallback so this module imports without starlette installed."""


log = logging.getLogger("genesis.visualizer.stream")

# JSON cannot carry NaN/Infinity; clamp instead of emitting invalid JSON.
_FINITE_MAX = 1.0e12


# ----------------------------------------------------------------------------
# Serialisation helpers
# ----------------------------------------------------------------------------

def _round_list(values: np.ndarray, decimals: int) -> List[float]:
    """NaN/Inf-safe ``np.ndarray -> list[float]`` with fixed precision.

    Rounding is purely a bandwidth optimisation: 3 decimals on millivolts is
    1 nV of resolution, far below anything the model resolves.
    """
    arr = np.asarray(values, dtype=np.float64)
    arr = np.nan_to_num(arr, nan=0.0, posinf=_FINITE_MAX, neginf=-_FINITE_MAX)
    return np.round(arr, decimals).tolist()


def _gbar_is_density(mech: Any) -> bool:
    """True if ``mech.gbar_SI`` is a *density* [S m-2] rather than a total [S].

    ``VoltageGatedChannel`` stores whatever was handed to its constructor and
    uses it directly in ``current()``.  ``NaV16Channel`` / ``KvChannel`` pass
    ``density * area`` to the base class but *override* the public ``gbar_SI``
    property to return the density.  Detecting that override is therefore an
    exact test, and it keeps this module working for future channel classes
    that follow either convention.
    """
    own = getattr(type(mech), "gbar_SI", None)
    base = getattr(VoltageGatedChannel, "gbar_SI", None)
    return own is not None and own is not base


def _gbar_total_S(mech: Any, area_m2: float) -> float:
    """Maximum (fully open) conductance of ``mech`` in siemens."""
    gbar = float(getattr(mech, "gbar_SI", 0.0))
    return gbar * float(area_m2) if _gbar_is_density(mech) else gbar


# ----------------------------------------------------------------------------
# ChannelSampler
# ----------------------------------------------------------------------------

class ChannelSampler:
    """Fast per-frame reader for the live voltage-gated channel population.

    The (compartment, channel) index is built once at construction time so the
    per-frame cost is a flat loop over the channel objects — no isinstance
    checks, no dictionary lookups, no allocation.

    Parameters
    ----------
    compartments : sequence of Compartment
        The *same* objects the solver holds, so the gate variables read here
        are the ones the solver just advanced.
    """

    def __init__(self, compartments: Sequence[Any]) -> None:
        self.n: int = len(compartments)

        self._na: List[Tuple[int, Any]] = []
        self._k: List[Tuple[int, Any]] = []
        self._other: List[Tuple[int, Any]] = []
        self._by_comp: Dict[int, List[Tuple[str, Any, float]]] = {}

        # Static maxima — used for channel-density visualisation and for the
        # open-fraction readout in the inspector.
        self.g_na_bar_S = np.zeros(self.n, dtype=np.float64)
        self.g_k_bar_S = np.zeros(self.n, dtype=np.float64)

        for comp in compartments:
            idx = int(comp.idx)
            area = float(comp.surface_area_m2)
            for mech in getattr(comp, "mechanisms", ()) or ():
                if not isinstance(mech, VoltageGatedChannel):
                    continue  # leak / passive mechanisms live in the G matrix
                kind = self._classify(mech)
                if kind == "na":
                    self._na.append((idx, mech))
                    self.g_na_bar_S[idx] += _gbar_total_S(mech, area)
                elif kind == "k":
                    self._k.append((idx, mech))
                    self.g_k_bar_S[idx] += _gbar_total_S(mech, area)
                else:
                    self._other.append((idx, mech))
                self._by_comp.setdefault(idx, []).append((kind, mech, area))

        self.n_channels: int = len(self._na) + len(self._k) + len(self._other)

        # Reusable output buffers (avoid per-frame allocation).
        self._g_na = np.zeros(self.n, dtype=np.float64)
        self._g_k = np.zeros(self.n, dtype=np.float64)
        self._i_chan = np.zeros(self.n, dtype=np.float64)

    # -- classification ----------------------------------------------------

    @staticmethod
    def _classify(mech: Any) -> str:
        """'na' / 'k' / 'other' from the channel's own identity."""
        name = str(getattr(mech, "name", "") or "").lower()
        if name.startswith("nav") or "sodium" in name:
            return "na"
        if name.startswith("kv") or name.startswith("skv") or "potassium" in name:
            return "k"
        # Unknown class: fall back on the reversal potential (E_Na > 0 > E_K).
        try:
            return "na" if float(mech.E_rev_V) > 0.0 else "k"
        except Exception:
            return "other"

    # -- properties --------------------------------------------------------

    @property
    def has_channels(self) -> bool:
        return self.n_channels > 0

    # -- per-frame sampling ------------------------------------------------

    def sample(self, V: np.ndarray, t: float = 0.0) -> Optional[Dict[str, np.ndarray]]:
        """Read live conductances and channel currents.

        Parameters
        ----------
        V : ndarray (N,)  membrane voltage [V] as returned by ``solver.step``.
        t : float         simulation time [s].

        Returns
        -------
        dict with ``g_Na_S``, ``g_K_S``, ``I_chan_A`` ndarrays, or ``None``
        when the cell carries no voltage-gated channels (passive build).
        """
        if not self.has_channels:
            return None

        g_na = self._g_na
        g_k = self._g_k
        i_chan = self._i_chan
        g_na.fill(0.0)
        g_k.fill(0.0)
        i_chan.fill(0.0)

        for idx, mech in self._na:
            g_na[idx] += channel_conductance_S(mech, t)
            i_chan[idx] += float(mech.current(float(V[idx]), t))
        for idx, mech in self._k:
            g_k[idx] += channel_conductance_S(mech, t)
            i_chan[idx] += float(mech.current(float(V[idx]), t))
        for idx, mech in self._other:
            i_chan[idx] += float(mech.current(float(V[idx]), t))

        return {"g_Na_S": g_na, "g_K_S": g_k, "I_chan_A": i_chan}

    # -- single-compartment inspection ------------------------------------

    def describe(self, idx: int, V: np.ndarray, t: float = 0.0) -> Dict[str, Any]:
        """Full channel readout for one compartment (click-to-inspect)."""
        V_i = float(V[idx])
        g_na = 0.0
        g_k = 0.0
        i_chan = 0.0
        channels: List[Dict[str, Any]] = []

        for kind, mech, area in self._by_comp.get(int(idx), ()):  # type: ignore[arg-type]
            g_S = channel_conductance_S(mech, t)
            I_A = float(mech.current(V_i, t))
            g_max = _gbar_total_S(mech, area)
            if kind == "na":
                g_na += g_S
            elif kind == "k":
                g_k += g_S
            i_chan += I_A

            gates = {}
            try:
                gates = {k: round(float(v), 5) for k, v in mech.gate_state.items()}
            except Exception:  # pragma: no cover - channel without gates
                pass

            channels.append({
                "name": str(getattr(mech, "name", type(mech).__name__)),
                "ion": kind,
                "g_nS": round(g_S * 1e9, 5),
                "g_max_nS": round(g_max * 1e9, 5),
                "open_fraction": round(g_S / g_max, 6) if g_max > 0.0 else 0.0,
                "gbar_S_m2": round(float(getattr(mech, "gbar_SI", 0.0)), 4),
                "E_rev_mV": round(float(mech.E_rev_V) * 1e3, 3),
                "I_pA": round(I_A * 1e12, 4),
                "gates": gates,
            })

        return {
            "g_Na_nS": round(g_na * 1e9, 5),
            "g_K_nS": round(g_k * 1e9, 5),
            "I_chan_pA": round(i_chan * 1e12, 4),
            "channels": channels,
        }

    def gates_of(self, idx: int) -> Dict[str, float]:
        """Flat ``{'NaV16Channel.m': 0.05, ...}`` gate map for one compartment."""
        out: Dict[str, float] = {}
        for _kind, mech, _area in self._by_comp.get(int(idx), ()):  # type: ignore[arg-type]
            try:
                label = str(getattr(mech, "name", type(mech).__name__))
                for gate, value in mech.gate_state.items():
                    out[f"{label}.{gate}"] = round(float(value), 5)
            except Exception:  # pragma: no cover
                continue
        return out


# ----------------------------------------------------------------------------
# Message builders
# ----------------------------------------------------------------------------

def build_state_message(
    *,
    t_s: float,
    V: np.ndarray,
    sample: Optional[Dict[str, np.ndarray]] = None,
    spike_events: Iterable[int] = (),
    step: int = 0,
    frame: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one ``state`` frame from the solver's own output.

    ``V`` is in volts (solver units) and is converted to millivolts here; no
    smoothing, filtering or interpolation is applied anywhere in this path.
    """
    V_arr = np.asarray(V, dtype=np.float64)

    message: Dict[str, Any] = {
        "type": "state",
        "t_ms": round(float(t_s) * 1e3, 6),
        "step": int(step),
        "frame": int(frame),
        "V_mV": _round_list(V_arr * 1e3, 3),
        "g_Na_nS": None,
        "g_K_nS": None,
        "I_chan_pA": None,
        "spike_events": [int(i) for i in spike_events],
    }

    if sample is not None:
        message["g_Na_nS"] = _round_list(sample["g_Na_S"] * 1e9, 4)
        message["g_K_nS"] = _round_list(sample["g_K_S"] * 1e9, 4)
        message["I_chan_pA"] = _round_list(sample["I_chan_A"] * 1e12, 3)

    if extra:
        message.update(extra)
    return message


def build_error_message(detail: str, *, context: str = "") -> Dict[str, Any]:
    return {"type": "error", "message": str(detail), "context": context}


# ----------------------------------------------------------------------------
# WebSocketStreamer
# ----------------------------------------------------------------------------

class WebSocketStreamer:
    """Serve one WebSocket client from the shared :class:`SimulationEngine`.

    Threading model
    ---------------
    The engine publishes frames from its **solver thread**.  Those callbacks
    hop onto the event loop with ``call_soon_threadsafe`` and land in a bounded
    queue.  When the queue is full the *oldest* frame is discarded: the browser
    always receives the freshest state and the solver never blocks on I/O.

    The engine is shared between clients, so several browser tabs watch the
    same simulation and every tab sees identical numbers.
    """

    def __init__(self, websocket: Any, engine: Any, *, max_queue: int = 4) -> None:
        self.ws = websocket
        self.engine = engine
        self._queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=max_queue)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._closed = False
        self._inspect_idx: Optional[int] = None
        self.frames_sent = 0
        self.frames_dropped = 0

    # -- engine -> event loop ---------------------------------------------

    def _on_engine_message(self, message: Dict[str, Any]) -> None:
        """Engine subscriber callback. Runs on the SOLVER THREAD."""
        loop = self._loop
        if loop is None or self._closed:
            return
        try:
            # Attach live gate/conductance detail for the compartment the user
            # has selected. Done here (solver thread) so it is consistent with
            # the frame and costs the event loop nothing.
            if message.get("type") == "state" and self._inspect_idx is not None:
                message = dict(message)
                message["detail"] = self.engine.inspect(self._inspect_idx)
            loop.call_soon_threadsafe(self._enqueue, message)
        except RuntimeError:
            pass  # loop closed between the check and the call
        except Exception as exc:  # pragma: no cover - never kill the solver
            log.debug("streamer callback failed: %s", exc)

    def _enqueue(self, message: Dict[str, Any]) -> None:
        """Runs on the EVENT LOOP. Drop-oldest backpressure."""
        if self._closed:
            return
        if self._queue.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
                self.frames_dropped += 1
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(message)

    # -- lifecycle ---------------------------------------------------------

    async def run(self) -> None:
        """Serve this client until it disconnects."""
        self._loop = asyncio.get_running_loop()
        sender = asyncio.create_task(self._send_loop(), name="genesis-ws-send")
        try:
            await self._send_json({
                "type": "hello",
                "protocol": 1,
                **self.engine.describe(),
            })
            await self._send_json(self.engine.status())
            last = self.engine.last_frame()
            if last is not None:
                await self._send_json(last)

            self.engine.subscribe(self._on_engine_message)
            await self._receive_loop()
        finally:
            self._closed = True
            self.engine.unsubscribe(self._on_engine_message)
            sender.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sender

    async def _send_loop(self) -> None:
        while not self._closed:
            message = await self._queue.get()
            try:
                await self.ws.send_json(message)
                self.frames_sent += 1
            except (WebSocketDisconnect, RuntimeError):
                self._closed = True
                return
            except Exception as exc:  # pragma: no cover
                log.debug("send failed: %s", exc)
                self._closed = True
                return

    async def _send_json(self, message: Dict[str, Any]) -> None:
        if self._closed:
            return
        try:
            await self.ws.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            self._closed = True
        except Exception as exc:  # pragma: no cover
            log.debug("send failed: %s", exc)
            self._closed = True

    async def _receive_loop(self) -> None:
        while not self._closed:
            try:
                raw = await self.ws.receive_text()
            except WebSocketDisconnect:
                return
            except RuntimeError:
                return
            except Exception as exc:  # pragma: no cover
                log.debug("receive failed: %s", exc)
                return

            try:
                message = json.loads(raw)
            except (TypeError, ValueError):
                await self._send_json(build_error_message("malformed JSON"))
                continue
            if not isinstance(message, dict):
                await self._send_json(build_error_message("expected a JSON object"))
                continue

            try:
                await self._handle_control(message)
            except Exception as exc:  # pragma: no cover - report, keep serving
                log.exception("control command failed")
                await self._send_json(
                    build_error_message(str(exc), context=str(message.get("type")))
                )

    # -- control protocol --------------------------------------------------

    async def _handle_control(self, message: Dict[str, Any]) -> None:
        kind = str(message.get("type", "")).lower()
        engine = self.engine

        if kind in ("start", "run"):
            engine.start(config=message.get("config"), restart=bool(message.get("restart", True)))
        elif kind == "pause":
            engine.pause()
        elif kind == "resume":
            engine.resume()
        elif kind == "toggle":
            engine.toggle()
        elif kind == "reset":
            engine.reset(config=message.get("config"))
        elif kind == "stop":
            engine.stop()
        elif kind == "speed":
            engine.set_speed(message.get("value", 1.0))
        elif kind in ("stimulus", "config"):
            payload = message.get("config")
            if not isinstance(payload, dict):
                payload = {k: v for k, v in message.items() if k != "type"}
            engine.configure(payload)
        elif kind == "inspect":
            idx = message.get("idx")
            if idx is None:
                self._inspect_idx = None
            else:
                self._inspect_idx = int(idx)
                await self._send_json(engine.inspect(self._inspect_idx))
            return
        elif kind == "ping":
            await self._send_json({"type": "pong", "t": message.get("t")})
            return
        else:
            await self._send_json(build_error_message(f"unknown command {kind!r}"))
            return

        # Guaranteed acknowledgement (status frames can be dropped by the
        # drop-oldest queue, this reply cannot).
        await self._send_json(engine.status())
