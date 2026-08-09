"""test_compartment_tree.py — Unit tests for the L5PC compartment tree.

Covers:
  build_l5_pyramidal()     — compartment count, parent-child links, types
  Compartment properties  — idx, dimensions, area, capacitance
  Electrotonic accuracy   — all compartments < lambda/2 in length
"""

import math
import pytest
from biophysical.morphology.l5_pyramidal import build_l5_pyramidal
from biophysical.morphology.compartment import CompartmentType
from biophysical.morphology.l5_pyramidal_data import EXPECTED_N_COMPS
from biophysical.core.constants import MEM


# ---- Shared fixture -------------------------------------------------------

@pytest.fixture(scope='module')
def tree_no_bilayer():
    """Build tree without bilayer (no mechanisms) for structural tests."""
    comps, meta = build_l5_pyramidal(apply_bilayer=False)
    return comps, meta


@pytest.fixture(scope='module')
def tree_with_bilayer():
    """Build tree with passive membrane mechanisms."""
    comps, meta = build_l5_pyramidal(apply_bilayer=True)
    return comps, meta


# ---- Tree structure -------------------------------------------------------

class TestTreeCount:
    def test_total_count_equals_expected(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        assert len(comps) == EXPECTED_N_COMPS
        assert meta['n_compartments'] == EXPECTED_N_COMPS

    def test_expected_n_comps_is_224(self):
        """APPROX-6: parametric tree produces 224 compartments."""
        assert EXPECTED_N_COMPS == 224

    def test_meta_lists_sum_to_total(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        total = (
            1  # soma
            + len(meta['apical_trunk_idxs'])
            + len(meta['apical_oblique_idxs'])
            + len(meta['apical_tuft_idxs'])
            + len(meta['basal_idxs'])
            + len(meta['ais_idxs'])
            + len(meta['myelin_idxs'])
            + len(meta['node_idxs'])
            + len(meta['terminal_idxs'])
        )
        assert total == EXPECTED_N_COMPS, (
            f'Meta index lists sum to {total}, expected {EXPECTED_N_COMPS}'
        )


class TestRootSoma:
    def test_soma_has_idx_zero(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        assert meta['soma_idx'] == 0
        assert comps[0].idx == 0

    def test_soma_is_CompartmentType_SOMA(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        assert comps[0].comp_type == CompartmentType.SOMA

    def test_soma_has_no_parent(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        assert comps[meta['soma_idx']].parent_idx is None

    def test_soma_diameter_20um(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        d = comps[meta['soma_idx']].diameter_m
        assert abs(d - 20e-6) < 1e-9, f'Soma d = {d*1e6:.2f} µm, expected 20 µm'

    def test_soma_length_20um(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        L = comps[meta['soma_idx']].length_m
        assert abs(L - 20e-6) < 1e-9, f'Soma L = {L*1e6:.2f} µm, expected 20 µm'


class TestConnectivity:
    def test_sequential_indices(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        for i, comp in enumerate(comps):
            assert comp.idx == i, f'Expected idx {i}, got {comp.idx}'

    def test_parent_references_child(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        for comp in comps:
            if comp.parent_idx is not None:
                parent = comps[comp.parent_idx]
                assert comp.idx in parent.children_idxs, (
                    f'comp {comp.idx} not in children of parent {parent.idx}'
                )

    def test_child_references_parent(self, tree_no_bilayer):
        """Every child index in children_idxs has that parent_idx."""
        comps, _ = tree_no_bilayer
        for comp in comps:
            for child_idx in comp.children_idxs:
                assert comps[child_idx].parent_idx == comp.idx

    def test_apical_trunk_root_parent_is_soma(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        if not meta['apical_trunk_idxs']:
            pytest.skip('No apical trunk compartments')
        first_trunk = comps[meta['apical_trunk_idxs'][0]]
        assert first_trunk.parent_idx == meta['soma_idx'], (
            f'First trunk parent = {first_trunk.parent_idx}, '
            f'expected soma {meta["soma_idx"]}'
        )

    def test_ais_root_parent_is_soma(self, tree_no_bilayer):
        comps, meta = tree_no_bilayer
        if not meta['ais_idxs']:
            pytest.skip('No AIS compartments')
        first_ais = comps[meta['ais_idxs'][0]]
        assert first_ais.parent_idx == meta['soma_idx'], (
            f'First AIS parent = {first_ais.parent_idx}, expected soma'
        )


class TestCompartmentTypes:
    def test_all_required_types_present(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        types = {c.comp_type for c in comps}
        required = {
            CompartmentType.SOMA,
            CompartmentType.APICAL_TRUNK,
            CompartmentType.APICAL_OBLIQUE,
            CompartmentType.APICAL_TUFT,
            CompartmentType.BASAL,
            CompartmentType.AIS,
        }
        missing = required - types
        assert not missing, f'Missing CompartmentType values: {missing}'


class TestCompartmentProperties:
    def test_positive_diameter_and_length(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        for comp in comps:
            assert comp.diameter_m > 0, f'comp {comp.idx}: d <= 0'
            assert comp.length_m   > 0, f'comp {comp.idx}: L <= 0'

    def test_positive_surface_area(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        for comp in comps:
            assert comp.surface_area_m2 > 0, f'comp {comp.idx}: A <= 0'

    def test_positive_total_capacitance(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        for comp in comps:
            assert comp.total_capacitance_F > 0, (
                f'comp {comp.idx}: C = {comp.total_capacitance_F}'
            )

    def test_soma_surface_area(self, tree_no_bilayer):
        """Soma area = pi * d * L = pi * 20e-6 * 20e-6 = 1257 µm²."""
        comps, meta = tree_no_bilayer
        soma = comps[meta['soma_idx']]
        expected_um2 = math.pi * 20.0 * 20.0
        measured_um2 = soma.surface_area_m2 * 1e12
        assert abs(measured_um2 - expected_um2) / expected_um2 < 1e-6, (
            f'Soma area = {measured_um2:.1f} µm², expected {expected_um2:.1f} µm²'
        )

    def test_total_area_plausible(self, tree_no_bilayer):
        """Total membrane area should be between 5000 and 50000 µm²."""
        comps, meta = tree_no_bilayer
        area_um2 = meta['total_area_um2']
        assert 5_000 < area_um2 < 50_000, f'Total area = {area_um2:.0f} µm²'


class TestElectrotonicAccuracy:
    def test_all_compartments_shorter_than_half_lambda(self, tree_no_bilayer):
        """Every compartment L < 0.5 * lambda for accurate cable discretisation."""
        from biophysical.morphology.geometry import lambda_dc_m
        comps, _ = tree_no_bilayer
        violations = []
        for comp in comps:
            lam = lambda_dc_m(comp.diameter_m, MEM.Rm_SI, MEM.Ra_SI)
            ratio = comp.length_m / lam
            if ratio >= 0.5:
                violations.append(
                    f'comp {comp.idx} ({comp.comp_type.name}): '
                    f'L/λ = {ratio:.3f} (≥ 0.5)'
                )
        assert not violations, (
            f'{len(violations)} compartments too long:\n' +
            '\n'.join(violations[:5])
        )


class TestBilayerAttachment:
    def test_no_mechanisms_without_bilayer(self, tree_no_bilayer):
        comps, _ = tree_no_bilayer
        for comp in comps:
            assert len(comp.mechanisms) == 0, (
                f'comp {comp.idx} has mechanisms without bilayer'
            )

    def test_mechanisms_attached_with_bilayer(self, tree_with_bilayer):
        comps, _ = tree_with_bilayer
        for comp in comps:
            assert len(comp.mechanisms) >= 1, (
                f'comp {comp.idx} has no mechanisms after bilayer attachment'
            )
