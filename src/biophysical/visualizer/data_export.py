"""data_export.py - Export REAL simulation data for visualization with 3D layout."""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from biophysical.morphology.compartment import Compartment, CompartmentType
from biophysical.simulation.recorder import Recorder

COMPARTMENT_COLORS = {
    CompartmentType.SOMA: "#E74C3C",
    CompartmentType.AIS: "#F39C12",
    CompartmentType.MYELIN: "#F5E6CC",
    CompartmentType.NODE: "#E67E22",
    CompartmentType.AXON_TERMINAL: "#D35400",
    CompartmentType.APICAL_TRUNK: "#3498DB",
    CompartmentType.APICAL_OBLIQUE: "#5DADE2",
    CompartmentType.APICAL_TUFT: "#85C1E9",
    CompartmentType.BASAL: "#27AE60",
}


def compute_3d_layout(compartments: List[Compartment]) -> List[Dict[str, float]]:
    """Compute 3D positions for all compartments based on tree structure.
    
    Layout algorithm:
    - Soma at origin (0, 0, 0)
    - Apical trunk grows upward (+Y)
    - Apical obliques branch off to sides
    - Apical tuft spreads at top
    - Basal dendrites grow downward (-Y) and spread
    - AIS and axon grow downward (-Y)
    - Myelin and terminals continue downward
    """
    positions = [{"x": 0.0, "y": 0.0, "z": 0.0} for _ in compartments]
    n = len(compartments)
    
    # Build children map
    children_map = {i: [] for i in range(n)}
    for comp in compartments:
        if comp.parent_idx is not None and comp.parent_idx >= 0:
            children_map[comp.parent_idx].append(comp.idx)
    
    # Track cumulative position
    pos_y = [0.0] * n  # Y position (vertical)
    pos_x = [0.0] * n  # X position (horizontal spread)
    pos_z = [0.0] * n  # Z position (depth spread)
    
    # Spacing parameters (in micrometers)
    SPACING_Y = 15.0  # Vertical spacing per compartment
    SPREAD_X = 8.0    # Horizontal spread per branch level
    SPREAD_Z = 8.0    # Depth spread per branch level
    
    def assign_positions(idx: int, parent_y: float, x_offset: float, z_offset: float, 
                         direction: str, branch_depth: int, sibling_idx: int, n_siblings: int):
        """Recursively assign positions."""
        comp = compartments[idx]
        comp_type = comp.comp_type
        length_um = comp.length_m * 1e6
        
        # Determine direction based on compartment type
        if comp_type == CompartmentType.SOMA:
            pos_y[idx] = 0.0
            pos_x[idx] = 0.0
            pos_z[idx] = 0.0
        elif comp_type in (CompartmentType.APICAL_TRUNK, CompartmentType.APICAL_OBLIQUE, 
                          CompartmentType.APICAL_TUFT):
            # Apical grows upward
            pos_y[idx] = parent_y + SPACING_Y
            pos_x[idx] = x_offset
            pos_z[idx] = z_offset
        elif comp_type in (CompartmentType.BASAL,):
            # Basal grows downward and spreads
            pos_y[idx] = parent_y - SPACING_Y
            pos_x[idx] = x_offset
            pos_z[idx] = z_offset
        elif comp_type in (CompartmentType.AIS, CompartmentType.MYELIN, 
                          CompartmentType.NODE, CompartmentType.AXON_TERMINAL):
            # Axon grows downward
            pos_y[idx] = parent_y - SPACING_Y
            pos_x[idx] = x_offset
            pos_z[idx] = z_offset
        else:
            pos_y[idx] = parent_y
            pos_x[idx] = x_offset
            pos_z[idx] = z_offset
        
        # Spread children
        children = children_map[idx]
        n_children = len(children)
        
        for i, child_idx in enumerate(children):
            child = compartments[child_idx]
            child_type = child.comp_type
            
            # Calculate spread angle
            if n_children > 1:
                spread = (i - (n_children - 1) / 2.0) * SPREAD_X
            else:
                spread = 0.0
            
            # Add random-ish variation based on index (deterministic)
            angle = (child_idx * 137.5) % 360  # Golden angle
            rad = math.radians(angle)
            
            # Direction-specific spreading
            if child_type in (CompartmentType.APICAL_TRUNK,):
                # Trunk stays mostly straight up
                new_x = pos_x[idx] + spread * 0.3
                new_z = pos_z[idx] + math.sin(rad) * SPREAD_Z * 0.2
            elif child_type == CompartmentType.APICAL_OBLIQUE:
                # Obliques spread to sides
                new_x = pos_x[idx] + spread * 1.5 + math.cos(rad) * SPREAD_X
                new_z = pos_z[idx] + math.sin(rad) * SPREAD_Z
            elif child_type == CompartmentType.APICAL_TUFT:
                # Tuft spreads widely at top
                new_x = pos_x[idx] + spread * 2.0 + math.cos(rad) * SPREAD_X * 2
                new_z = pos_z[idx] + math.sin(rad) * SPREAD_Z * 2
            elif child_type == CompartmentType.BASAL:
                # Basal spreads in all directions downward
                new_x = pos_x[idx] + spread * 1.8 + math.cos(rad) * SPREAD_X * 1.5
                new_z = pos_z[idx] + math.sin(rad) * SPREAD_Z * 1.5
            elif child_type in (CompartmentType.AIS, CompartmentType.MYELIN, 
                               CompartmentType.NODE, CompartmentType.AXON_TERMINAL):
                # Axon stays straight down
                new_x = pos_x[idx] + spread * 0.1
                new_z = pos_z[idx] + spread * 0.1
            else:
                new_x = pos_x[idx] + spread
                new_z = pos_z[idx]
            
            assign_positions(child_idx, pos_y[idx], new_x, new_z, 
                           direction, branch_depth + 1, i, n_children)
    
    # Start from soma (assumed idx=0)
    soma_idx = 0
    assign_positions(soma_idx, 0.0, 0.0, 0.0, "up", 0, 0, 1)
    
    # Build position list
    for i in range(n):
        positions[i] = {
            "x": float(pos_x[i]),
            "y": float(pos_y[i]),
            "z": float(pos_z[i]),
        }
    
    return positions


def voltage_to_color(V_mV: float, V_min: float = -90.0, V_max: float = 50.0) -> str:
    """Map membrane potential to color."""
    t = (V_mV - V_min) / (V_max - V_min)
    t = max(0.0, min(1.0, t))
    if t < 0.4:
        r = int(255 * (t / 0.4) * 0.6)
        g, b = 0, 255
    elif t < 0.7:
        t2 = (t - 0.4) / 0.3
        r = int(153 + 102 * t2)
        g = int(255 * t2 * 0.6)
        b = int(255 * (1 - t2))
    else:
        t2 = (t - 0.7) / 0.3
        r, g, b = 255, int(153 * (1 - t2)), 0
    return f"#{r:02x}{g:02x}{b:02x}"


def export_morphology(compartments: List[Compartment], meta: Dict) -> Dict:
    """Export REAL morphology structure with computed 3D positions."""
    # Compute layout positions
    positions = compute_3d_layout(compartments)
    
    comps_data = []
    for i, comp in enumerate(compartments):
        comps_data.append({
            "idx": comp.idx,
            "type": comp.comp_type.name,
            "color": COMPARTMENT_COLORS.get(comp.comp_type, "#999999"),
            "position": positions[i],
            "geometry": {
                "diameter_um": comp.diameter_m * 1e6,
                "length_um": comp.length_m * 1e6,
                "surface_area_um2": comp.surface_area_m2 * 1e12,
            },
            "parent": comp.parent_idx if comp.parent_idx is not None else -1,
            "has_channels": any(
                type(m).__name__ in ("NaV16Channel", "KvChannel")
                for m in comp.mechanisms
            ),
        })
    return {
        "n_compartments": len(compartments),
        "compartments": comps_data,
        "meta": {k: list(v) if isinstance(v, (list, tuple)) else v for k, v in meta.items()},
    }


def export_recorder(recorder: Recorder, compartments: List[Compartment]) -> Dict:
    """Export REAL recorded traces."""
    traces = {}
    
    # Get recorded indices
    idxs = getattr(recorder, 'recorded_idxs', None)
    if idxs is None:
        idxs = getattr(recorder, 'idxs', None)
    if idxs is None:
        idxs = getattr(recorder, '_idxs', None)
    if idxs is None:
        idxs = getattr(recorder, 'record_idxs', [])
    if idxs is None:
        idxs = []
    
    for idx in idxs:
        trace = recorder.get_trace(idx)
        if trace is not None:
            traces[str(idx)] = {
                "comp_idx": idx,
                "type": compartments[idx].comp_type.name if idx < len(compartments) else "unknown",
                "V_mV": [float(v * 1000.0) for v in trace],
            }
    
    # Get time array
    t_s = getattr(recorder, 't_s', None)
    if t_s is None:
        t_s = getattr(recorder, 'times', None)
    if t_s is None:
        t_s = getattr(recorder, '_t', [])
    if t_s is None:
        t_s = []
    
    n_samples = getattr(recorder, 'n_samples', len(t_s))
    
    return {
        "t_ms": [float(t * 1000.0) for t in t_s],
        "traces": traces,
        "n_samples": n_samples,
    }


def save_visualization_data(
    compartments: List[Compartment],
    meta: Dict,
    solver,
    recorder: Optional[Recorder] = None,
    output_dir: str = "visualization_data",
    snapshot_times: Optional[List[float]] = None,
) -> Path:
    """Save all visualization data to JSON files."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    
    # Morphology with 3D layout
    morph = export_morphology(compartments, meta)
    with open(out / "morphology.json", "w") as f:
        json.dump(morph, f, indent=2)
    print(f"Saved morphology.json ({len(compartments)} compartments with 3D layout)")
    
    # Traces
    if recorder is not None:
        try:
            traces = export_recorder(recorder, compartments)
            with open(out / "traces.json", "w") as f:
                json.dump(traces, f, indent=2)
            print(f"Saved traces.json ({traces['n_samples']} samples)")
        except Exception as e:
            print(f"Warning: Could not export traces: {e}")
    
    return out