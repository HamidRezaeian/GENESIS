"""test_channel_distributions.py — 16 unit tests for ChannelDistribution.

All expected densities are the Hay et al. (2011) values held by the CHAN
singleton [S m^-2]:

    AIS / NODE      Na = 31 370.0   K = 19 100.0    (AP initiation, saltatory)
    SOMA            Na =  9 830.0   K =  3 030.0
    APICAL_*        Na =    213.0   K =      2.6
    BASAL / MYELIN / AXON_TERMINAL  both 0.0        (passive)

Region composition of the Phase 0a 224-compartment L5PC:
    active  86 = soma 1 + trunk 15 + oblique 28 + tuft 30 + AIS 7 + node 5
    passive 138 = basal 108 + myelin 25 + terminal 5

Each active compartment ends up with exactly one NaV16Channel and one
KvChannel on top of its Phase 0a LeakChannel; passive compartments keep the
leak alone (no voltage-gated channel object is created for gbar = 0).
"""

import pytest

from biophysical.channels.base_channel import VoltageGatedChannel
from biophysical.channels.channel_distributions import (
    HAY_2011_DENSITIES,
    ChannelDistribution,
    DensityProvider,
    RegionDensity,
    resolve_compartment_type,
)
from biophysical.channels.potassium_channel import KvChannel
from biophysical.channels.sodium_channel import NaV16Channel
from biophysical.core.constants import CHAN
from biophysical.morphology.compartment import Compartment, CompartmentType
from biophysical.neuron_cell import NeuronCell


N_COMPARTMENTS = 224
N_ACTIVE = 86
N_PASSIVE = 138

ACTIVE_BY_REGION = {
    'SOMA':           1,
    'APICAL_TRUNK':  15,
    'APICAL_OBLIQUE': 28,
    'APICAL_TUFT':   30,
    'AIS':            7,
    'NODE':           5,
}

APICAL_TYPES = (
    CompartmentType.APICAL_TRUNK,
    CompartmentType.APICAL_OBLIQUE,
    CompartmentType.APICAL_TUFT,
)

PASSIVE_TYPES = (
    CompartmentType.BASAL,
    CompartmentType.MYELIN,
    CompartmentType.AXON_TERMINAL,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def dist() -> ChannelDistribution:
    """Default literature distribution."""
    return ChannelDistribution()


@pytest.fixture
def cell() -> NeuronCell:
    """Freshly built 224-compartment neuron (function scope: tests mutate it)."""
    return NeuronCell().build()


def _count(comps, channel_cls) -> int:
    """Number of attached mechanisms of the given class across compartments."""
    return sum(1 for c in comps for m in c.mechanisms if isinstance(m, channel_cls))


def _channel_of(comp, channel_cls):
    """First attached mechanism of the given class, or None."""
    for mech in comp.mechanisms:
        if isinstance(mech, channel_cls):
            return mech
    return None


class _MRNADensityProvider:
    """Phase 0e stand-in: literature densities scaled by an expression level."""

    def __init__(self, expression: float = 1.0) -> None:
        self._table = ChannelDistribution()
        self._expression = float(expression)

    def density_na(self, compartment) -> float:
        return self._expression * self._table.density_na(compartment)

    def density_k(self, compartment) -> float:
        return self._expression * self._table.density_k(compartment)


class _ScaledDistribution(ChannelDistribution):
    """Phase 0e subclassing hook: doubles every Na density."""

    def density_na(self, compartment) -> float:
        return 2.0 * super().density_na(compartment)


# ---------------------------------------------------------------------------
# 1. AIS has the highest density
# ---------------------------------------------------------------------------

def test_ais_has_highest_density(dist):
    """AIS: Na = 31 370 S/m^2, K = 19 100 S/m^2 — highest in the cell."""
    assert dist.density_na(CompartmentType.AIS) == pytest.approx(31_370.0)
    assert dist.density_k(CompartmentType.AIS) == pytest.approx(19_100.0)

    for comp_type in CompartmentType:
        if comp_type in (CompartmentType.AIS, CompartmentType.NODE):
            continue
        assert dist.density_na(comp_type) < dist.density_na(CompartmentType.AIS)
        assert dist.density_k(comp_type) < dist.density_k(CompartmentType.AIS)


# ---------------------------------------------------------------------------
# 2. Soma has moderate density
# ---------------------------------------------------------------------------

def test_soma_has_moderate_density(dist):
    """Soma: Na = 9 830 S/m^2, K = 3 030 S/m^2."""
    assert dist.density_na(CompartmentType.SOMA) == pytest.approx(9_830.0)
    assert dist.density_k(CompartmentType.SOMA) == pytest.approx(3_030.0)
    assert dist.is_active_region(CompartmentType.SOMA)


# ---------------------------------------------------------------------------
# 3. Apical dendrites have low density
# ---------------------------------------------------------------------------

def test_apical_has_low_density(dist):
    """Trunk, obliques and tuft all get Na = 213 S/m^2, K = 2.6 S/m^2."""
    for comp_type in APICAL_TYPES:
        assert dist.density_na(comp_type) == pytest.approx(213.0)
        assert dist.density_k(comp_type) == pytest.approx(2.6)
        assert dist.is_active_region(comp_type)


# ---------------------------------------------------------------------------
# 4. Basal dendrites are passive
# ---------------------------------------------------------------------------

def test_basal_has_zero_density(dist):
    """Basal dendrites carry no voltage-gated conductance in Phase 0b."""
    assert dist.density_na(CompartmentType.BASAL) == 0.0
    assert dist.density_k(CompartmentType.BASAL) == 0.0
    assert dist.is_passive_region(CompartmentType.BASAL)


# ---------------------------------------------------------------------------
# 5. Myelin is passive
# ---------------------------------------------------------------------------

def test_myelin_has_zero_density(dist):
    """Myelinated internodes are insulating: both densities are zero."""
    assert dist.density_na(CompartmentType.MYELIN) == 0.0
    assert dist.density_k(CompartmentType.MYELIN) == 0.0
    assert dist.is_passive_region(CompartmentType.MYELIN)


# ---------------------------------------------------------------------------
# 6. Nodes of Ranvier match the AIS
# ---------------------------------------------------------------------------

def test_node_equals_ais(dist):
    """Nodes get AIS-level density for saltatory conduction."""
    assert dist.density_na(CompartmentType.NODE) == dist.density_na(CompartmentType.AIS)
    assert dist.density_k(CompartmentType.NODE) == dist.density_k(CompartmentType.AIS)
    assert dist.region_density(CompartmentType.NODE) == dist.region_density(
        CompartmentType.AIS
    )


# ---------------------------------------------------------------------------
# 7. Every compartment of the built neuron is classified
# ---------------------------------------------------------------------------

def test_all_compartments_assigned(dist, cell):
    """224 compartments -> 86 active + 138 passive, region by region."""
    stats = dist.apply_to_neuron(cell)

    assert len(cell.compartments) == N_COMPARTMENTS
    assert stats['n_compartments'] == N_COMPARTMENTS
    assert stats['n_active'] == N_ACTIVE
    assert stats['n_passive'] == N_PASSIVE
    assert stats['n_active'] + stats['n_passive'] == N_COMPARTMENTS
    assert stats['active_by_region'] == ACTIVE_BY_REGION
    assert dist.last_apply_stats is stats


# ---------------------------------------------------------------------------
# 8. Density ordering AIS > soma > apical > basal
# ---------------------------------------------------------------------------

def test_density_ordering(dist):
    """AIS > soma > apical > basal for both Na and K."""
    for density in (dist.density_na, dist.density_k):
        assert (
            density(CompartmentType.AIS)
            > density(CompartmentType.SOMA)
            > density(CompartmentType.APICAL_TRUNK)
            > density(CompartmentType.BASAL)
        )
    assert dist.density_na(CompartmentType.BASAL) == 0.0
    assert dist.density_k(CompartmentType.BASAL) == 0.0


# ---------------------------------------------------------------------------
# 9. apply_to_neuron creates 86 Na + 86 K channels
# ---------------------------------------------------------------------------

def test_apply_creates_channels(dist, cell):
    """86 NaV16Channel + 86 KvChannel objects, one pair per active compartment."""
    assert _count(cell.compartments, NaV16Channel) == 0
    assert _count(cell.compartments, KvChannel) == 0

    stats = dist.apply_to_neuron(cell)

    assert _count(cell.compartments, NaV16Channel) == N_ACTIVE
    assert _count(cell.compartments, KvChannel) == N_ACTIVE
    assert stats['n_na_channels'] == N_ACTIVE
    assert stats['n_k_channels'] == N_ACTIVE
    assert stats['n_channels_created'] == 2 * N_ACTIVE

    active = [c for c in cell.compartments if dist.is_active_region(c)]
    assert len(active) == N_ACTIVE
    for comp in active:
        assert _channel_of(comp, NaV16Channel) is not None
        assert _channel_of(comp, KvChannel) is not None


# ---------------------------------------------------------------------------
# 10. Attached channels carry the right gbar and area
# ---------------------------------------------------------------------------

def test_channels_have_correct_gbar(dist, cell):
    """Sample 5 compartments (soma, AIS, node, trunk, tuft) and check gbar_SI."""
    dist.apply_to_neuron(cell)
    meta = cell.meta

    samples = [
        (meta['soma_idx'],               CHAN.gbar_Na_soma,   CHAN.gbar_K_soma),
        (meta['ais_idxs'][0],            CHAN.gbar_Na_AIS,    CHAN.gbar_K_AIS),
        (meta['node_idxs'][0],           CHAN.gbar_Na_node,   CHAN.gbar_K_node),
        (meta['apical_trunk_idxs'][0],   CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
        (meta['apical_tuft_idxs'][-1],   CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
    ]
    assert len(samples) == 5

    for idx, gbar_na, gbar_k in samples:
        comp = cell.compartments[idx]
        na = _channel_of(comp, NaV16Channel)
        kv = _channel_of(comp, KvChannel)
        assert na is not None and kv is not None

        # gbar_SI is the conductance *density* [S m^-2]
        assert na.gbar_SI == pytest.approx(gbar_na)
        assert kv.gbar_SI == pytest.approx(gbar_k)

        # area is taken from the compartment as-is (already SI)
        assert na.state_dict()['area_m2'] == pytest.approx(comp.surface_area_m2)
        assert kv.state_dict()['area_m2'] == pytest.approx(comp.surface_area_m2)


# ---------------------------------------------------------------------------
# 11. DensityProvider protocol (Phase 0e hook)
# ---------------------------------------------------------------------------

def test_density_provider_protocol(dist):
    """Protocol accepts the table, duck-typed providers, and subclasses."""
    assert isinstance(dist, DensityProvider)
    assert isinstance(_MRNADensityProvider(), DensityProvider)
    assert not isinstance(object(), DensityProvider)

    # Subclassing for Phase 0e
    scaled = _ScaledDistribution()
    assert isinstance(scaled, DensityProvider)
    assert scaled.density_na(CompartmentType.AIS) == pytest.approx(2.0 * CHAN.gbar_Na_AIS)
    assert scaled.density_k(CompartmentType.AIS) == pytest.approx(CHAN.gbar_K_AIS)

    # A provider can drive apply_to_neuron over a bare compartment list
    comps = [
        Compartment(
            _idx=0,
            comp_type=CompartmentType.SOMA,
            diameter_m=20e-6,
            length_m=20e-6,
        ),
        Compartment(
            _idx=1,
            comp_type=CompartmentType.BASAL,
            diameter_m=2e-6,
            length_m=50e-6,
        ),
    ]
    stats = ChannelDistribution().apply_to_neuron(
        comps, provider=_MRNADensityProvider(0.5)
    )

    assert stats['n_active'] == 1
    assert stats['n_passive'] == 1
    na = _channel_of(comps[0], NaV16Channel)
    kv = _channel_of(comps[0], KvChannel)
    assert na.gbar_SI == pytest.approx(0.5 * CHAN.gbar_Na_soma)
    assert kv.gbar_SI == pytest.approx(0.5 * CHAN.gbar_K_soma)
    assert _channel_of(comps[1], NaV16Channel) is None
    assert _channel_of(comps[1], KvChannel) is None


# ---------------------------------------------------------------------------
# 12. Axon terminals are passive
# ---------------------------------------------------------------------------

def test_terminal_has_zero_density(dist):
    """AXON_TERMINAL (not TERMINAL) has zero density in Phase 0b."""
    assert dist.density_na(CompartmentType.AXON_TERMINAL) == 0.0
    assert dist.density_k(CompartmentType.AXON_TERMINAL) == 0.0
    assert dist.is_passive_region(CompartmentType.AXON_TERMINAL)


# ---------------------------------------------------------------------------
# 13. Every enum member appears in the table
# ---------------------------------------------------------------------------

def test_all_compartment_types_have_densities(dist):
    """No CompartmentType may be missing, or apply_to_neuron would KeyError."""
    for comp_type in CompartmentType:
        assert comp_type in HAY_2011_DENSITIES
        assert comp_type in dist.densities
        density = dist.region_density(comp_type)
        assert isinstance(density, RegionDensity)
        assert density.gbar_na_SI >= 0.0
        assert density.gbar_k_SI >= 0.0
        assert density.is_active is not density.is_passive

    assert len(HAY_2011_DENSITIES) == len(list(CompartmentType)) == 9


# ---------------------------------------------------------------------------
# 14. No drift from the CHAN singleton
# ---------------------------------------------------------------------------

def test_densities_match_chan_constants(dist):
    """The table must read CHAN, not copies of its numbers."""
    expected = {
        CompartmentType.AIS:            (CHAN.gbar_Na_AIS,    CHAN.gbar_K_AIS),
        CompartmentType.NODE:           (CHAN.gbar_Na_node,   CHAN.gbar_K_node),
        CompartmentType.SOMA:           (CHAN.gbar_Na_soma,   CHAN.gbar_K_soma),
        CompartmentType.APICAL_TRUNK:   (CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
        CompartmentType.APICAL_OBLIQUE: (CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
        CompartmentType.APICAL_TUFT:    (CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
        CompartmentType.BASAL:          (CHAN.gbar_Na_basal,  CHAN.gbar_K_basal),
        CompartmentType.MYELIN:         (CHAN.gbar_Na_myelin, CHAN.gbar_K_myelin),
        CompartmentType.AXON_TERMINAL:  (0.0,                 0.0),
    }
    for comp_type, (gbar_na, gbar_k) in expected.items():
        assert dist.density_na(comp_type) == gbar_na
        assert dist.density_k(comp_type) == gbar_k

    # A Compartment instance resolves to the same region as its enum
    comp = Compartment(
        _idx=0,
        comp_type=CompartmentType.AIS,
        diameter_m=1.2e-6,
        length_m=5e-6,
    )
    assert resolve_compartment_type(comp) is CompartmentType.AIS
    assert dist.density_na(comp) == CHAN.gbar_Na_AIS
    assert dist.density_k(comp) == CHAN.gbar_K_AIS


# ---------------------------------------------------------------------------
# 15. apply_to_neuron is idempotent
# ---------------------------------------------------------------------------

def test_apply_is_idempotent(dist, cell):
    """A second apply reuses the channels instead of double-counting them."""
    first = dict(dist.apply_to_neuron(cell))
    n_mechs_first = sum(len(c.mechanisms) for c in cell.compartments)

    second = dist.apply_to_neuron(cell)
    n_mechs_second = sum(len(c.mechanisms) for c in cell.compartments)

    assert n_mechs_second == n_mechs_first
    for key in (
        'n_compartments',
        'n_active',
        'n_passive',
        'n_na_channels',
        'n_k_channels',
    ):
        assert second[key] == first[key]

    assert first['n_channels_created'] == 2 * N_ACTIVE
    assert second['n_channels_created'] == 0
    assert second['n_channels_reused'] == 2 * N_ACTIVE
    assert second['total_g_na_S'] == pytest.approx(first['total_g_na_S'])

    assert _count(cell.compartments, NaV16Channel) == N_ACTIVE
    assert _count(cell.compartments, KvChannel) == N_ACTIVE
    for comp in cell.compartments:
        assert sum(1 for m in comp.mechanisms if isinstance(m, NaV16Channel)) <= 1
        assert sum(1 for m in comp.mechanisms if isinstance(m, KvChannel)) <= 1


# ---------------------------------------------------------------------------
# 16. Zero-density regions get no channel objects at all
# ---------------------------------------------------------------------------

def test_zero_density_regions_have_no_channels(dist, cell):
    """The 138 passive compartments keep their leak and no VGC."""
    dist.apply_to_neuron(cell)

    passive = [c for c in cell.compartments if c.comp_type in PASSIVE_TYPES]
    assert len(passive) == N_PASSIVE

    for comp in passive:
        assert not any(isinstance(m, VoltageGatedChannel) for m in comp.mechanisms)
        assert not any(isinstance(m, (NaV16Channel, KvChannel)) for m in comp.mechanisms)
        # Phase 0a passive mechanisms are untouched
        assert len(comp.mechanisms) >= 1

    assert _count(passive, VoltageGatedChannel) == 0
