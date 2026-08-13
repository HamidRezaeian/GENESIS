"""visualizer/ — real-time 3-D visualisation of the LIVE GENESIS neuron model.

Everything this package renders is produced by the *real* biophysical model:
``NeuronCell().build(active=True)`` driving
``biophysical.simulation.active_solver.ActiveSolver.step()``.

No trace is pre-computed, interpolated, replayed from disk, or synthesised.
There is no JSON round-trip: the browser talks to the running solver over a
WebSocket and every millivolt on screen is exactly what the solver returned.

Architecture
------------
    morphology_builder.py   SectionSpec (l5_pyramidal_data.py) -> 3-D tubes
    simulation_engine.py    ActiveSolver driven from a background thread
    data_streamer.py        solver state -> compact JSON frames -> WebSocket
    server.py               FastAPI app: HTTP morphology + /ws live stream
    static/ templates/      Three.js front-end (WebGL, PBR, bloom)

Data flow
---------
    browser  --"start"-->  /ws  -->  SimulationEngine.start()
                                        |
                                        |  background thread
                                        v
                                 ActiveSolver.step()  x stream_every
                                        |
                                        v
                              build_state_message(V, t, solver)
                                        |
                            loop.call_soon_threadsafe(queue)
                                        v
    browser  <--"state"--  /ws  <--  WebSocketStreamer._send_loop()

Quick start
-----------
    pip install fastapi uvicorn websockets
    python -m biophysical.visualizer.server --port 8000
    # open http://localhost:8000

Programmatic use (no web server required)
-----------------------------------------
    from biophysical.visualizer import SimulationEngine

    engine = SimulationEngine().build()
    engine.subscribe(lambda msg: print(msg["t_ms"], msg.get("v_soma_mV")))
    engine.start()          # real ActiveSolver on a background thread
    ...
    engine.stop()

Attributes are resolved lazily (PEP 562) so that importing this package never
requires FastAPI/uvicorn — only :mod:`biophysical.visualizer.server` does.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

__all__ = [
    # simulation_engine
    "SimulationEngine",
    "SimulationConfig",
    "BASELINE_FPS",
    # data_streamer
    "ChannelSampler",
    "WebSocketStreamer",
    "build_state_message",
    # morphology_builder
    "build_morphology",
    "MorphologyBuilder",
    # server
    "create_app",
    "run_server",
]

# public name -> (module, attribute)
_LAZY: Dict[str, Tuple[str, str]] = {
    "SimulationEngine": ("simulation_engine", "SimulationEngine"),
    "SimulationConfig": ("simulation_engine", "SimulationConfig"),
    "BASELINE_FPS": ("simulation_engine", "BASELINE_FPS"),
    "ChannelSampler": ("data_streamer", "ChannelSampler"),
    "WebSocketStreamer": ("data_streamer", "WebSocketStreamer"),
    "build_state_message": ("data_streamer", "build_state_message"),
    "build_morphology": ("morphology_builder", "build_morphology"),
    "MorphologyBuilder": ("morphology_builder", "MorphologyBuilder"),
    "create_app": ("server", "create_app"),
    "run_server": ("server", "run_server"),
}


def __getattr__(name: str) -> Any:
    """Lazily import public symbols (PEP 562)."""
    try:
        module_name, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None

    try:
        module = import_module(f"{__name__}.{module_name}")
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
        raise ModuleNotFoundError(
            f"{name!r} requires biophysical.visualizer.{module_name}, which "
            f"could not be imported ({exc}). The web server needs:\n"
            f"    pip install fastapi uvicorn websockets"
        ) from exc

    return getattr(module, attr)


def __dir__() -> list:
    return sorted(set(list(globals().keys()) + __all__))
