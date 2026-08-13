"""test_integration.py — Phase 0b Step 5: NeuronCell ↔ ActiveSolver integration.

Covers:
  build(active=True)   — attaches the Hay 2011 channels, uses ActiveSolver
  build(active=False)  — Phase 0a passive regression (behaviour unchanged)
  run_active()         — simple API returning Recorder traces; AP generation
  validate_active()    — 6-protocol AP validation report

Known findings carried over from Step 4 mean some validate_active() checks are
expected to FAIL; the integration tests assert the report structure and the
presence of the AP metrics, not that every check passes:
  FINDING-1: nata_alpha_h / nata_beta_h swapped in gating.py → no repolarisation
  FINDING-2: −70 mV is not an equilibrium of the active model
"""

from __future__ import annotations

import numpy as np
import pytest

from biophysical.channels.base_channel import VoltageGatedChannel
from biophysical.morphology.compartment import CompartmentType
from biophysical.neuron_cell import NeuronCell
from biophysical.simulation.active_solver import ActiveSolver
from biophysical.simulation.crank_nicolson import CrankNicolsonSolver
from biophysical.simulation.current_clamp import CurrentClampProtocol
from biophysical.simulation.recorder import Recorder
from biophysical.validation.report import ValidationReport


# Expected channel counts from channel_distributions.py (Step 3):
#   86 active compartments (AIS 7, NODE 5, SOMA 1, TRUNK 15, OBLIQUE 28,
#   TUFT 30), each receiving one NaV16Channel + one KvChannel.
_N_ACTIVE_COMPS = 86
_N_CHANNELS = 2 * _N_ACTIVE_COMPS

_PASSIVE_TYPES = (
    CompartmentType.BASAL,
    CompartmentType.MYELIN,
    CompartmentType.AXON_TERMINAL,
)


@pytest.fixture(scope='module')
def passive_cell():
    """Default Phase 0a build (passive only).  Shared across the module."""
    return NeuronCell(dt_s=25e-6).build()


@pytest.fixture(scope='module')
def active_cell():
    """Phase 0b active build.  run_active() re-initialises gates each call,
    so sharing one instance across tests is safe."""
    return NeuronCell(dt_s=25e-6).build(active=True)


@pytest.fixture(scope='module')
def active_report(active_cell):
    """Run validate_active() once for the whole module (it is expensive)."""
    return active_cell.validate_active()


def _count_vg_channels(cell: NeuronCell) -> int:
    return sum(
        1
        for comp in cell.compartments
        for mech in comp.mechanisms
        if isinstance(mech, VoltageGatedChannel)
    )


# ---------------------------------------------------------------------------
# build(active=True)
# ---------------------------------------------------------------------------

class TestBuildActive:
    def test_returns_self_for_chaining(self, active_cell):
        assert isinstance(active_cell, NeuronCell)
        assert active_cell.is_active is True

    def test_uses_active_solver(self, active_cell):
        assert isinstance(active_cell.solver, ActiveSolver)
        assert active_cell.solver.has_active_channels

    def test_channels_attached_to_active_regions(self, active_cell):
        assert _count_vg_channels(active_cell) == _N_CHANNELS
        assert active_cell.solver.n_active_channels == _N_CHANNELS

    def test_passive_regions_have_no_channels(self, active_cell):
        for comp in active_cell.compartments:
            if comp.comp_type in _PASSIVE_TYPES:
                assert not any(
                    isinstance(m, VoltageGatedChannel) for m in comp.mechanisms
                ), f'{comp.name} should have stayed passive'

    def test_gates_initialised_in_unit_range(self, active_cell):
        for comp in active_cell.compartments:
            for mech in comp.mechanisms:
                if isinstance(mech, VoltageGatedChannel):
                    for gate, x in mech.gate_state.items():
                        assert 0.0 <= x <= 1.0, (
                            f'{mech.name} gate {gate} = {x} outside [0, 1]'
                        )


# ---------------------------------------------------------------------------
# build(active=False) — Phase 0a regression
# ---------------------------------------------------------------------------

class TestBuildPassiveRegression:
    def test_default_build_is_passive(self, passive_cell):
        assert passive_cell.is_active is False

    def test_default_build_uses_plain_crank_nicolson(self, passive_cell):
        # Exact type check: ActiveSolver subclasses CrankNicolsonSolver,
        # so isinstance() alone would not catch a regression.
        assert type(passive_cell.solver) is CrankNicolsonSolver

    def test_passive_build_has_no_channels(self, passive_cell):
        assert _count_vg_channels(passive_cell) == 0

    def test_passive_resting_run_stays_at_el(self, passive_cell):
        """Phase 0a invariant: leak-only tree at rest must not drift."""
        rec = passive_cell.run(t_max_s=5e-3, record_idxs=[0], record_every=1)
        v = rec.get_trace(0)
        assert np.max(np.abs(v - MEM_REST_V)) < 1e-4


MEM_REST_V = -0.070   # MEM.E_leak_V — module constant to keep the test above tidy


# ---------------------------------------------------------------------------
# run_active()
# ---------------------------------------------------------------------------

class TestRunActive:
    def test_returns_recorder_with_labels(self, active_cell):
        rec = active_cell.run_active(duration_s=2e-3)
        assert isinstance(rec, Recorder)
        assert 'soma' in rec.traces_mV()

    def test_generates_action_potential(self, active_cell):
        """A 1 nA somatic pulse must drive the soma above 0 mV."""
        proto = CurrentClampProtocol(
            amp_A=1e-9, onset_s=1e-3, dur_s=6e-3,
            target_idx=active_cell.soma_idx,
        )
        rec = active_cell.run_active(
            protocol=proto, duration_s=10e-3,
            record_idxs=[active_cell.soma_idx],
        )
        v_soma = rec.get_trace(active_cell.soma_idx)
        assert float(np.max(v_soma)) > 0.0, (
            f'No AP upstroke: soma peak = {float(np.max(v_soma)) * 1e3:.1f} mV'
        )

    def test_trace_is_finite(self, active_cell):
        proto = CurrentClampProtocol(
            amp_A=5e-10, onset_s=1e-3, dur_s=3e-3,
            target_idx=active_cell.soma_idx,
        )
        rec = active_cell.run_active(
            protocol=proto, duration_s=8e-3,
            record_idxs=[active_cell.soma_idx],
        )
        assert np.all(np.isfinite(rec.get_trace(active_cell.soma_idx)))

    def test_requires_active_build(self, passive_cell):
        with pytest.raises(RuntimeError, match='active=True'):
            passive_cell.run_active(duration_s=1e-3)


# ---------------------------------------------------------------------------
# validate_active()
# ---------------------------------------------------------------------------

class TestValidateActive:
    _EXPECTED_PROTOCOLS = {
        'resting_potential_active',
        'ap_threshold',
        'ap_amplitude',
        'ap_half_width',
        'repetitive_firing',
        'ahp_depth',
    }

    def test_returns_validation_report(self, active_report):
        assert isinstance(active_report, ValidationReport)
        assert active_report.n_total == 6

    def test_all_six_protocols_present(self, active_report):
        names = {r.name for r in active_report.results}
        assert names == self._EXPECTED_PROTOCOLS

    def test_ap_metrics_recorded(self, active_report):
        """AP amplitude / threshold / half-width must each carry a finite
        measurement (or None when the metric is undefined) plus metadata —
        regardless of whether the check itself passes (FINDING-1/2)."""
        by_name = {r.name: r for r in active_report.results}
        for key in ('ap_amplitude', 'ap_threshold', 'ap_half_width'):
            r = by_name[key]
            assert isinstance(r.passed, bool)
            assert r.expected_range != ''
            if r.actual_value is not None:
                assert np.isfinite(float(r.actual_value)), (
                    f'{key}: non-finite measurement {r.actual_value}'
                )

    def test_report_serialises_to_dict(self, active_report):
        d = active_report.to_dict()
        assert d['title'] == 'Phase 0b Active Validation'
        assert d['n_total'] == 6
        assert len(d['results']) == 6
