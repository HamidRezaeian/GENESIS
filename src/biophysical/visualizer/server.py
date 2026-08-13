"""server.py - Web server for neuron visualization."""

from __future__ import annotations
import json
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

# Use absolute paths
ROOT_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = ROOT_DIR / "visualization_data"
STATIC_DIR = ROOT_DIR / "src" / "biophysical" / "visualizer" / "static"

print(f"Data dir: {DATA_DIR}")
print(f"Static dir: {STATIC_DIR}")
print(f"Index exists: {(STATIC_DIR / 'index.html').exists()}")


@app.route("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return f"Error: index.html not found at {index_file}", 404
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(str(STATIC_DIR), path)


@app.route("/api/morphology")
def morphology():
    morph_file = DATA_DIR / "morphology.json"
    if not morph_file.exists():
        return jsonify({"error": f"morphology.json not found at {morph_file}"}), 404
    with open(morph_file) as f:
        return jsonify(json.load(f))


@app.route("/api/traces")
def traces():
    traces_file = DATA_DIR / "traces.json"
    if not traces_file.exists():
        return jsonify({"error": f"traces.json not found at {traces_file}"}), 404
    with open(traces_file) as f:
        return jsonify(json.load(f))


def run_server(port: int = 5000):
    print(f"\nGENESIS Visualizer: http://localhost:{port}")
    print("Real-time visualization of actual simulation data")
    print("Press Ctrl+C to stop\n")
    app.run(host="localhost", port=port, debug=True)


if __name__ == "__main__":
    run_server()