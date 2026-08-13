"""morphology_builder.py — 3-D geometry for the front-end, from the real data.

What this module does
---------------------
It re-walks the parametric section tree in
:mod:`biophysical.morphology.l5_pyramidal_data` using **exactly** the same
rules as :func:`biophysical.morphology.l5_pyramidal.build_l5_pyramidal`:

* a section starts at its parent section's distal end,
* compartment centres sit at ``(i + 0.5) * L_comp`` along the unit direction,
* diameters are interpolated at the midpoint fraction ``(i + 0.5) / n_comps``.

The difference is that the electrical builder only needs one *centre* and one
*diameter* per compartment, while a high-fidelity renderer needs the
**boundaries**: the proximal/distal point and the proximal/distal radius of
every compartment.  Those are what produce genuinely tapered tubes rather than
stacked constant-radius cylinders.

Because the same interpolation is used, the boundary radii average back to the
compartment diameter exactly::

    (r(k/n) + r((k+1)/n)) / 2 == r((k + 0.5)/n) == compartment.diameter_m / 2

Everything is then cross-checked against the built cell and the maximum
deviation is reported in ``payload["validation"]``, so the geometry on screen
is provably the geometry the solver is integrating.

Visual-only extras (never touch the electrical model)
-----------------------------------------------------
``curvature``
    Deterministic sideways bow applied to the *interior* boundary points of a
    section so branches look organic instead of laser-straight.  Section
    endpoints are never moved, so junctions stay exact.  Set to 0 for perfectly
    straight sections.  The reported ``curvature_max_offset_um`` quantifies it.

``soma_attachment_fix``
    In the source data every child of the soma starts at the soma's *distal*
    end, so the basal tree and the axon visually sprout from the top of the
    soma and the AIS passes straight through it.  With this flag the subtrees
    that point downwards start at the soma's proximal pole instead.  Compartment
    positions are decorative in this cable model (the solver uses length,
    diameter and connectivity only), so this changes nothing electrically.

Branch angles
-------------
The angle of each section to its parent is measured from the data and reported
per section as ``branch_angle_deg``.  Note that the apical obliques in
``l5_pyramidal_data.py`` are specified with direction ``(1.0, 0.2, 0.0)``,
which is about 79 deg from the trunk axis rather than the 30-60 deg quoted in
anatomy texts.  That is what the data says, so that is what is drawn; use
``oblique_angle_deg`` if you deliberately want a visual override.

CLI
---
    python -m biophysical.visualizer.morphology_builder --summary
    python -m biophysical.visualizer.morphology_builder > morphology.json
"""

from __future__ import annotations

import argparse
import json
import math
import zlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

from biophysical.morphology.l5_pyramidal_data import EXPECTED_N_COMPS, get_section_specs

try:  # reuse the builder's own normaliser so directions match bit for bit
    from biophysical.morphology.l5_pyramidal import _normalise as _unit
except Exception:  # pragma: no cover - identical fallback
    def _unit(dx: float, dy: float, dz: float) -> Tuple[float, float, float]:
        mag = math.sqrt(dx * dx + dy * dy + dz * dz)
        if mag < 1e-15:
            return 0.0, 1.0, 0.0
        return dx / mag, dy / mag, dz / mag


#: Region palette used by the front-end for region highlighting.
REGION_COLORS: Dict[str, str] = {
    "SOMA": "#ffd479",
    "AIS": "#ff7b5a",
    "APICAL_TRUNK": "#7fd4ff",
    "APICAL_OBLIQUE": "#5ab0e0",
    "APICAL_TUFT": "#a98bff",
    "BASAL": "#5ce6b5",
    "MYELIN": "#e8eef7",
    "NODE": "#ffe27a",
    "AXON_TERMINAL": "#ff9ecb",
}

#: Relative spine density per compartment type (visual detail only).
SPINE_TYPE_FACTOR: Dict[str, float] = {
    "BASAL": 1.0,
    "APICAL_OBLIQUE": 1.0,
    "APICAL_TUFT": 0.9,
    "APICAL_TRUNK": 0.45,
    "SOMA": 0.0,
    "AIS": 0.0,
    "MYELIN": 0.0,
    "NODE": 0.0,
    "AXON_TERMINAL": 0.0,
}

_AXON_TYPES = ("AIS", "MYELIN", "NODE", "AXON_TERMINAL")


def _r3(value: float) -> float:
    """Round to nanometre precision (payload is in micrometres)."""
    return round(float(value), 3)


class MorphologyBuilder:
    """Builds the renderer-facing morphology payload.

    Parameters
    ----------
    cell : NeuronCell | None
        A built cell to validate against and to read channel densities from.
        When ``None`` a fresh active cell is built.
    curvature : float
        Organic bow amplitude as a fraction of section length (0 disables).
    soma_attachment_fix : bool
        Start downward-pointing children of the soma at its proximal pole.
    spine_density_per_um : float
        Base spine density for the procedural spine instances.
    oblique_angle_deg : float | None
        Visual override for the apical oblique branch angle. ``None`` keeps the
        directions exactly as specified in the data.
    """

    def __init__(
        self,
        cell: Any = None,
        *,
        curvature: float = 0.035,
        soma_attachment_fix: bool = True,
        spine_density_per_um: float = 0.06,
        oblique_angle_deg: Optional[float] = None,
    ) -> None:
        self.cell = cell
        self.curvature = max(0.0, min(0.25, float(curvature)))
        self.soma_attachment_fix = bool(soma_attachment_fix)
        self.spine_density_per_um = max(0.0, min(2.0, float(spine_density_per_um)))
        self.oblique_angle_deg = oblique_angle_deg

    # ------------------------------------------------------------------

    def _ensure_cell(self) -> Any:
        if self.cell is None:
            from biophysical.neuron_cell import NeuronCell
            self.cell = NeuronCell().build(active=True)
        return self.cell

    @staticmethod
    def _type_name(value: Any) -> str:
        """SectionSpec.comp_type is a plain string; Compartment holds an enum."""
        return getattr(value, "name", None) or str(value)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _perpendicular_basis(u: Sequence[float]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Two unit vectors spanning the plane perpendicular to ``u``."""
        ref = (0.0, 0.0, 1.0) if abs(u[1]) > 0.9 or abs(u[0]) > 0.9 else (0.0, 1.0, 0.0)
        ax = u[1] * ref[2] - u[2] * ref[1]
        ay = u[2] * ref[0] - u[0] * ref[2]
        az = u[0] * ref[1] - u[1] * ref[0]
        a = _unit(ax, ay, az)
        bx = u[1] * a[2] - u[2] * a[1]
        by = u[2] * a[0] - u[0] * a[2]
        bz = u[0] * a[1] - u[1] * a[0]
        return a, _unit(bx, by, bz)

    def _bow_offsets(
        self,
        label: str,
        u: Sequence[float],
        length_um: float,
        n_points: int,
    ) -> List[Tuple[float, float, float]]:
        """Deterministic per-section sideways offsets for the interior points."""
        zero = [(0.0, 0.0, 0.0)] * n_points
        if self.curvature <= 0.0 or n_points < 3:
            return zero

        # Stable across processes and machines (unlike hash()).
        seed = zlib.crc32(label.encode("utf-8"))
        angle = (seed % 3600) / 3600.0 * 2.0 * math.pi
        amp = self.curvature * length_um

        a, b = self._perpendicular_basis(u)
        dir_x = math.cos(angle) * a[0] + math.sin(angle) * b[0]
        dir_y = math.cos(angle) * a[1] + math.sin(angle) * b[1]
        dir_z = math.cos(angle) * a[2] + math.sin(angle) * b[2]

        offsets: List[Tuple[float, float, float]] = []
        last = n_points - 1
        for k in range(n_points):
            # sin() envelope: exactly zero at both ends, maximal mid-section.
            w = math.sin(math.pi * (k / last)) * amp
            offsets.append((dir_x * w, dir_y * w, dir_z * w))
        return offsets

    # ------------------------------------------------------------------
    # Main build
    # ------------------------------------------------------------------

    def build(self) -> Dict[str, Any]:
        cell = self._ensure_cell()
        comps = cell.compartments
        specs = get_section_specs()

        # -- channel densities (for the density overlay) -------------------
        from biophysical.visualizer.data_streamer import ChannelSampler
        sampler = ChannelSampler(comps)

        root_label: Optional[str] = None
        start_pos: Dict[str, Tuple[float, float, float]] = {}
        end_pos: Dict[str, Tuple[float, float, float]] = {}
        dirs: Dict[str, Tuple[float, float, float]] = {}

        sections: List[Dict[str, Any]] = []
        compartments: List[Dict[str, Any]] = []

        next_idx = 0
        pos_error = 0.0
        diam_error = 0.0
        bow_max = 0.0

        for spec in specs:
            type_name = self._type_name(spec.comp_type)
            n = int(spec.n_comps)

            # -- proximal anchor -------------------------------------------
            if spec.parent_label is None:
                root_label = spec.label
                p = (0.0, 0.0, 0.0)
            else:
                p = end_pos[spec.parent_label]

            u = _unit(spec.dir_x, spec.dir_y, spec.dir_z)

            # Visual correction: downward children of the soma leave from its
            # proximal pole, not from the top of the soma.
            if (
                self.soma_attachment_fix
                and spec.parent_label is not None
                and spec.parent_label == root_label
                and u[1] < -1e-9
            ):
                p = start_pos[root_label]

            L_um = float(spec.length_um)
            L_comp_um = L_um / n

            # -- straight boundary points (micrometres) ---------------------
            straight: List[Tuple[float, float, float]] = []
            for k in range(n + 1):
                s = k * L_comp_um
                straight.append((p[0] * 1e6 + u[0] * s, p[1] * 1e6 + u[1] * s, p[2] * 1e6 + u[2] * s))

            # -- validation against the electrical model --------------------
            for k in range(n):
                comp = comps[next_idx + k]
                cx = (straight[k][0] + straight[k + 1][0]) * 0.5
                cy = (straight[k][1] + straight[k + 1][1]) * 0.5
                cz = (straight[k][2] + straight[k + 1][2]) * 0.5
                # The fix intentionally moves subtrees; only validate untouched ones.
                if p is start_pos.get(root_label) and spec.parent_label == root_label:
                    pass
                else:
                    pos_error = max(
                        pos_error,
                        abs(cx - comp.x * 1e6),
                        abs(cy - comp.y * 1e6),
                        abs(cz - comp.z * 1e6),
                    )
                frac = (k + 0.5) / n
                d_expect = spec.diam_start_um + (spec.diam_end_um - spec.diam_start_um) * frac
                diam_error = max(diam_error, abs(d_expect - comp.diameter_m * 1e6))

            # -- organic bow (visual only) ----------------------------------
            offsets = self._bow_offsets(spec.label, u, L_um, n + 1)
            points: List[List[float]] = []
            for k in range(n + 1):
                off = offsets[k]
                bow_max = max(bow_max, math.sqrt(off[0] ** 2 + off[1] ** 2 + off[2] ** 2))
                points.append([
                    _r3(straight[k][0] + off[0]),
                    _r3(straight[k][1] + off[1]),
                    _r3(straight[k][2] + off[2]),
                ])

            # -- boundary radii (true taper) --------------------------------
            radii = [
                _r3((spec.diam_start_um + (spec.diam_end_um - spec.diam_start_um) * (k / n)) * 0.5)
                for k in range(n + 1)
            ]

            # -- branch angle to parent -------------------------------------
            if spec.parent_label is None:
                angle_deg = 0.0
            else:
                pu = dirs[spec.parent_label]
                dot = max(-1.0, min(1.0, u[0] * pu[0] + u[1] * pu[1] + u[2] * pu[2]))
                angle_deg = math.degrees(math.acos(dot))

            idxs = list(range(next_idx, next_idx + n))
            sections.append({
                "label": spec.label,
                "type": type_name,
                "parent": spec.parent_label,
                "dir": [_r3(u[0]), _r3(u[1]), _r3(u[2])],
                "branch_angle_deg": round(angle_deg, 2),
                "length_um": _r3(L_um),
                "points": points,
                "radii": radii,
                "comps": idxs,
            })

            # -- per-compartment records ------------------------------------
            spine_factor = SPINE_TYPE_FACTOR.get(type_name, 0.0)
            for k in range(n):
                i = next_idx + k
                comp = comps[i]
                area_m2 = float(comp.surface_area_m2)
                g_na = sampler.g_na_bar_S[i] / area_m2 if area_m2 > 0 else 0.0
                g_k = sampler.g_k_bar_S[i] / area_m2 if area_m2 > 0 else 0.0
                centre = [
                    _r3((points[k][0] + points[k + 1][0]) * 0.5),
                    _r3((points[k][1] + points[k + 1][1]) * 0.5),
                    _r3((points[k][2] + points[k + 1][2]) * 0.5),
                ]
                compartments.append({
                    "idx": i,
                    "type": self._type_name(comp.comp_type),
                    "section": spec.label,
                    "k": k,
                    "parent": int(comp.parent_idx) if comp.parent_idx is not None else -1,
                    "children": [int(c) for c in comp.children_idxs],
                    "c": centre,
                    "r0": radii[k],
                    "r1": radii[k + 1],
                    "len_um": _r3(comp.length_m * 1e6),
                    "diam_um": _r3(comp.diameter_m * 1e6),
                    "area_um2": _r3(area_m2 * 1e12),
                    "g_na": round(g_na, 3),
                    "g_k": round(g_k, 3),
                    "spines": int(round(comp.length_m * 1e6 * self.spine_density_per_um * spine_factor)),
                })

            dirs[spec.label] = u
            start_pos[spec.label] = p
            end_pos[spec.label] = (
                p[0] + u[0] * L_um * 1e-6,
                p[1] + u[1] * L_um * 1e-6,
                p[2] + u[2] * L_um * 1e-6,
            )
            next_idx += n

        # -- bounds ---------------------------------------------------------
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for section in sections:
            for k, point in enumerate(section["points"]):
                r = section["radii"][k]
                for axis in range(3):
                    lo[axis] = min(lo[axis], point[axis] - r)
                    hi[axis] = max(hi[axis], point[axis] + r)
        size = [hi[a] - lo[a] for a in range(3)]
        centre = [(hi[a] + lo[a]) * 0.5 for a in range(3)]

        meta = dict(getattr(cell, "meta", {}) or {})
        regions = {
            key.replace("_idxs", "").upper(): list(value)
            for key, value in meta.items()
            if isinstance(value, (list, tuple))
        }
        soma_idx = int(meta.get("soma_idx", 0))
        regions.setdefault("SOMA", [soma_idx])

        payload: Dict[str, Any] = {
            "version": 1,
            "source": "biophysical.morphology.l5_pyramidal_data.get_section_specs()",
            "units": "um",
            "n_compartments": len(compartments),
            "n_sections": len(sections),
            "soma_idx": soma_idx,
            "bounds": {
                "min": [_r3(v) for v in lo],
                "max": [_r3(v) for v in hi],
                "size": [_r3(v) for v in size],
                "center": [_r3(v) for v in centre],
            },
            "sections": sections,
            "compartments": compartments,
            "regions": regions,
            "region_names": {
                "SOMA": "Soma",
                "AIS": "Axon initial segment",
                "APICAL_TRUNK": "Apical trunk",
                "APICAL_OBLIQUE": "Apical obliques",
                "APICAL_TUFT": "Apical tuft",
                "BASAL": "Basal dendrites",
                "MYELIN": "Myelinated axon",
                "NODE": "Nodes of Ranvier",
                "AXON_TERMINAL": "Axon terminals",
            },
            "axon": self._axon_path(compartments),
            "channel_max": {
                "g_na": round(max((c["g_na"] for c in compartments), default=0.0), 3),
                "g_k": round(max((c["g_k"] for c in compartments), default=0.0), 3),
            },
            "render": {
                "up": [0, 1, 0],
                "scale": 0.01,
                "radius_gain": 2.4,
                "min_radius_um": 0.32,
                "soma_radius_um": _r3(max(
                    (c["diam_um"] * 0.5 for c in compartments if c["type"] == "SOMA"),
                    default=10.0,
                )),
                "spine_density_per_um": self.spine_density_per_um,
                "region_colors": REGION_COLORS,
                "voltage_range_mV": [-90.0, 40.0],
            },
            "meta": {
                "total_area_um2": round(float(meta.get("total_area_um2", 0.0)), 2),
                "expected_n_comps": int(EXPECTED_N_COMPS),
                "active": bool(getattr(cell, "is_active", False)),
            },
            "validation": {
                "n_comps_match": len(compartments) == len(comps) == int(EXPECTED_N_COMPS),
                "n_comps_geometry": len(compartments),
                "n_comps_model": len(comps),
                "position_max_error_um": round(pos_error, 9),
                "diameter_max_error_um": round(diam_error, 9),
                "curvature_max_offset_um": round(bow_max, 4),
                "soma_attachment_fix": self.soma_attachment_fix,
                "note": (
                    "position/diameter errors are measured against the built "
                    "cell (compartment.x/y/z, .diameter_m); subtrees moved by "
                    "soma_attachment_fix are excluded from the position check, "
                    "and curvature is a visual bow that leaves section "
                    "endpoints untouched"
                ),
            },
        }
        return payload

    # ------------------------------------------------------------------

    @staticmethod
    def _axon_path(compartments: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Ordered soma -> terminal chain used by the current-flow particles."""
        by_idx = {c["idx"]: c for c in compartments}
        axonal = [c for c in compartments if c["type"] in _AXON_TYPES]
        if not axonal:
            return {"idxs": [], "points": []}

        def depth(comp: Dict[str, Any]) -> int:
            steps = 0
            cur = comp
            while cur["parent"] >= 0 and steps < 1000:
                cur = by_idx[cur["parent"]]
                steps += 1
            return steps

        deepest = max(axonal, key=depth)
        chain: List[Dict[str, Any]] = []
        cur: Optional[Dict[str, Any]] = deepest
        while cur is not None and cur["type"] in _AXON_TYPES:
            chain.append(cur)
            parent = cur["parent"]
            cur = by_idx.get(parent) if parent >= 0 else None
        chain.reverse()
        return {
            "idxs": [c["idx"] for c in chain],
            "points": [c["c"] for c in chain],
        }


def build_morphology(cell: Any = None, **kwargs: Any) -> Dict[str, Any]:
    """Convenience wrapper around :class:`MorphologyBuilder`."""
    return MorphologyBuilder(cell=cell, **kwargs).build()


# ---------------------------------------------------------------------------
# CLI — local verification without a browser
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m biophysical.visualizer.morphology_builder",
        description="Build the 3-D morphology payload from the real section data.",
    )
    parser.add_argument("--summary", action="store_true", help="print a report instead of JSON")
    parser.add_argument("--curvature", type=float, default=0.035)
    parser.add_argument("--no-soma-fix", action="store_true")
    parser.add_argument("--indent", type=int, default=None)
    args = parser.parse_args(argv)

    payload = build_morphology(
        curvature=args.curvature,
        soma_attachment_fix=not args.no_soma_fix,
    )

    if not args.summary:
        print(json.dumps(payload, indent=args.indent))
        return 0

    v = payload["validation"]
    b = payload["bounds"]
    print("GENESIS morphology")
    print(f"  compartments      : {payload['n_compartments']} in {payload['n_sections']} sections")
    print(f"  bounds (um)       : x {b['min'][0]:.1f}..{b['max'][0]:.1f}"
          f"  y {b['min'][1]:.1f}..{b['max'][1]:.1f}"
          f"  z {b['min'][2]:.1f}..{b['max'][2]:.1f}")
    print(f"  total area (um2)  : {payload['meta']['total_area_um2']:.1f}")
    print(f"  axon chain        : {len(payload['axon']['idxs'])} compartments")
    print("  validation")
    print(f"    count match     : {v['n_comps_match']}")
    print(f"    max pos error   : {v['position_max_error_um']:.3e} um")
    print(f"    max diam error  : {v['diameter_max_error_um']:.3e} um")
    print(f"    visual bow      : {v['curvature_max_offset_um']:.2f} um")
    print("  branch angles (deg, section -> parent)")
    seen = set()
    for section in payload["sections"]:
        key = section["type"]
        if key in seen or section["parent"] is None:
            continue
        seen.add(key)
        print(f"    {key:<15} {section['branch_angle_deg']:6.1f}   (e.g. {section['label']})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
