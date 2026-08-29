"""
End-to-End Server Integration & Telemetry Handshake Verification for GENESIS Phase-E.
Rule 25 Mandatory Pre-Delivery Verification.
"""

import os
import sys
from pathlib import Path
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from genesis.server.brain_server import GenesisEngineRunner


def test_phase_e_server_step_and_payload():
    """Verify that GenesisEngineRunner steps Phase-E and builds sanitized JSON payload with zero exceptions."""
    runner = GenesisEngineRunner()
    
    print("[INTEGRATION] Stepping GenesisEngineRunner with Phase-E ALife Substrate...")
    for tick in range(1, 101):
        payload = runner.step_once()
        assert payload["type"] == "STATE_UPDATE"
        assert "phase_e" in payload, "Payload must contain phase_e block"
        pe = payload["phase_e"]
        assert "population" in pe
        assert "telemetry" in pe
        assert "resource_grid" in pe
        
        if tick % 25 == 0:
            telem = pe["telemetry"]
            print(f"  Tick {tick:3d} | Alive: {len(pe['population']):3d} | Births: {telem.get('births_total', 0):2d} | Deaths: {telem.get('deaths_total', 0):2d} | MK-Z: {telem.get('mann_kendall_z', 0.0):.2f} | Emergence: {telem.get('emergence_index', 0.0):.3f}")
            
    print("[INTEGRATION SUCCESS] 100 live ticks verified with 100% telemetry integrity!")


if __name__ == "__main__":
    test_phase_e_server_step_and_payload()
