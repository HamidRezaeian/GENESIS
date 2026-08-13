"""server.py — FastAPI + WebSocket server for the GENESIS neuron visualiser.

The browser talks to a **live** simulation.  There is no export step and no
``visualization_data/*.json`` round-trip anywhere in this file: the process
owns a :class:`~biophysical.visualizer.simulation_engine.SimulationEngine`,
the engine owns ``NeuronCell(active=True)`` and its ``ActiveSolver``, and the
WebSocket streams whatever the solver just computed.

Endpoints
---------
``GET  /``                    front-end page (templates/index.html).
``GET  /static/*``            front-end assets.
``GET  /api/morphology``      3-D morphology built from the live cell.
``GET  /api/meta``            model description (compartments, channels, dt).
``GET  /api/status``          transport state (t, fps, spike counts).
``GET  /api/frame``           most recent state frame (JSON).
``GET  /api/inspect/{idx}``   live per-compartment readout.
``GET  /api/health``          liveness probe.
``WS   /ws``                  live state stream + control protocol.

Run it
------
    pip install fastapi uvicorn websockets
    python -m biophysical.visualizer.server --port 8000
    # or
    uvicorn biophysical.visualizer.server:app --port 8000
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Make `python src/biophysical/visualizer/server.py` work as well as `-m`.
# ---------------------------------------------------------------------------
_SRC_DIR = Path(__file__).resolve().parents[2]          # .../src
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    from fastapi import FastAPI, WebSocket
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
    raise ModuleNotFoundError(
        "The GENESIS visualiser server needs FastAPI:\n"
        "    pip install fastapi uvicorn websockets"
    ) from exc

from biophysical.visualizer.data_streamer import WebSocketStreamer
from biophysical.visualizer.simulation_engine import SimulationConfig, SimulationEngine

log = logging.getLogger("genesis.visualizer.server")

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"
TEMPLATES_DIR = HERE / "templates"

_PLACEHOLDER = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>GENESIS visualiser</title>
<style>body{background:#0a0d14;color:#c9d4e4;font:15px/1.6 ui-monospace,monospace;
padding:48px;max-width:60em;margin:auto}code{color:#7fd4ff}h1{color:#fff}
a{color:#7fd4ff}</style></head><body>
<h1>GENESIS neuron visualiser</h1>
<p>The backend is running, but the front-end page was not found at
<code>{path}</code>.</p>
<p>The live API is already available:</p>
<ul>
  <li><code>GET  /api/meta</code> &mdash; model description</li>
  <li><code>GET  /api/morphology</code> &mdash; 3-D morphology</li>
  <li><code>GET  /api/status</code> &mdash; transport state</li>
  <li><code>WS   /ws</code> &mdash; live ActiveSolver stream</li>
</ul>
</body></html>
"""


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(
    *,
    dt_s: float = 25e-6,
    active: bool = True,
    prebuild: bool = True,
    config: Optional[Dict[str, Any]] = None,
) -> FastAPI:
    """Create the FastAPI application and its shared simulation engine.

    Parameters
    ----------
    dt_s : float      solver timestep [s].
    active : bool     build with voltage-gated channels.
    prebuild : bool   build the cell now so the first page load is instant.
    config : dict     initial :class:`SimulationConfig` overrides.
    """
    engine = SimulationEngine(
        dt_s=dt_s,
        active=active,
        config=SimulationConfig.from_dict(config) if config else None,
    )

    app = FastAPI(
        title="GENESIS neuron visualiser",
        version="1.0",
        description="Real-time 3-D visualisation of a live 224-compartment "
                    "L5 pyramidal neuron driven by ActiveSolver.",
    )
    app.state.engine = engine
    app.state.morphology = None

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    else:  # pragma: no cover
        log.warning("static directory missing: %s", STATIC_DIR)

    if prebuild:
        engine.build()

    # -- pages ------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> Response:
        for candidate in (TEMPLATES_DIR / "index.html", STATIC_DIR / "index.html"):
            if candidate.is_file():
                return FileResponse(str(candidate), media_type="text/html")
        return HTMLResponse(_PLACEHOLDER.format(path=TEMPLATES_DIR / "index.html"), status_code=200)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        icon = STATIC_DIR / "favicon.ico"
        if icon.is_file():
            return FileResponse(str(icon))
        return Response(status_code=204)

    # -- REST API ---------------------------------------------------------

    @app.get("/api/health")
    def health() -> Dict[str, Any]:
        return {
            "ok": True,
            "built": engine.is_built,
            "clients": engine.n_subscribers,
        }

    @app.get("/api/meta")
    def meta() -> Dict[str, Any]:
        return engine.describe()

    @app.get("/api/status")
    def status() -> Dict[str, Any]:
        return engine.status()

    @app.get("/api/frame")
    def frame() -> Response:
        last = engine.last_frame()
        if last is None:
            return JSONResponse({"error": "no frame yet \u2014 start the simulation"}, status_code=404)
        return JSONResponse(last)

    @app.get("/api/inspect/{idx}")
    def inspect(idx: int) -> Dict[str, Any]:
        return engine.inspect(idx)

    @app.get("/api/morphology")
    def morphology(refresh: bool = False) -> Response:
        """3-D morphology derived from the *live* cell.

        Static geometry only (positions, radii, taper, connectivity, channel
        densities); voltages never travel this way — they arrive on ``/ws``.
        """
        if app.state.morphology is not None and not refresh:
            return JSONResponse(app.state.morphology)
        try:
            from biophysical.visualizer.morphology_builder import build_morphology
        except ModuleNotFoundError as exc:
            return JSONResponse(
                {"error": "morphology_builder is not available", "detail": str(exc)},
                status_code=503,
            )
        payload = build_morphology(cell=engine.cell)
        app.state.morphology = payload
        return JSONResponse(payload)

    # -- live stream ------------------------------------------------------

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        peer = getattr(websocket.client, "host", "?")
        log.info("client connected (%s)", peer)
        streamer = WebSocketStreamer(websocket, engine)
        try:
            await streamer.run()
        finally:
            log.info(
                "client disconnected (%s) sent=%d dropped=%d",
                peer, streamer.frames_sent, streamer.frames_dropped,
            )

    @app.on_event("shutdown")
    def _shutdown() -> None:  # pragma: no cover
        engine.stop()

    return app


# ---------------------------------------------------------------------------
# Lazily-created module-level app (for `uvicorn ...server:app`)
# ---------------------------------------------------------------------------

_APP: Optional[FastAPI] = None


def get_app() -> FastAPI:
    global _APP
    if _APP is None:
        _APP = create_app()
    return _APP


def __getattr__(name: str) -> Any:
    """PEP 562: build the app only when someone actually asks for it."""
    if name == "app":
        return get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    app: Optional[FastAPI] = None,
    log_level: str = "info",
) -> None:
    """Serve the visualiser with uvicorn (blocking)."""
    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "uvicorn is required to serve the visualiser:\n"
            "    pip install fastapi uvicorn websockets"
        ) from exc

    try:
        import websockets  # noqa: F401
    except ModuleNotFoundError:  # pragma: no cover
        try:
            import wsproto  # noqa: F401
        except ModuleNotFoundError:
            log.warning(
                "no WebSocket implementation found \u2014 /ws will fail. "
                "Install one with:  pip install websockets"
            )

    application = app or get_app()
    print(f"\n  GENESIS neuron visualiser  \u2192  http://{host}:{port}")
    print("  Live ActiveSolver stream on /ws \u2014 no exported data, no file round-trip.")
    print("  Ctrl+C to stop.\n")
    uvicorn.run(application, host=host, port=port, log_level=log_level)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m biophysical.visualizer.server",
        description="Real-time 3-D visualiser for the GENESIS L5 pyramidal neuron.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dt-us", type=float, default=25.0, help="solver timestep [us]")
    parser.add_argument("--passive", action="store_true", help="build without voltage-gated channels")
    parser.add_argument("--no-prebuild", action="store_true", help="build the cell on first request")
    parser.add_argument("--stream-every", type=int, default=10, help="timesteps per streamed frame")
    parser.add_argument("--duration-ms", type=float, default=30.0)
    parser.add_argument("--amp-pa", type=float, default=1500.0, dest="amp_pa")
    parser.add_argument("--onset-ms", type=float, default=1.0)
    parser.add_argument("--dur-ms", type=float, default=5.0)
    parser.add_argument("--target-idx", type=int, default=None, help="stimulus compartment (default soma)")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    global _APP
    _APP = create_app(
        dt_s=args.dt_us * 1e-6,
        active=not args.passive,
        prebuild=not args.no_prebuild,
        config={
            "stream_every": args.stream_every,
            "duration_ms": args.duration_ms,
            "amp_pA": args.amp_pa,
            "onset_ms": args.onset_ms,
            "dur_ms": args.dur_ms,
            "target_idx": args.target_idx,
        },
    )
    run_server(args.host, args.port, app=_APP, log_level=args.log_level)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
