"""channel_distributions.py — Spatial mapping of channel densities to regions.

Phase 0b Step 3.  Maps every CompartmentType to a (gbar_Na, gbar_K) pair and
attaches NaV16Channel / KvChannel objects to the compartments of a built
neuron.  This is the only place where "which region gets how much
conductance" is decided; the numbers themselves live in core/constants.py.

Density table  [S m^-2]  (Hay et al. 2011, ModelDB #139653; read from CHAN)
---------------------------------------------------------------------------
    region            gbar_Na      gbar_K    n_comps (224-comp L5PC)
    AIS              31 370.0    19 100.0      7    active
    NODE             31 370.0    19 100.0      5    active
    SOMA              9 830.0     3 030.0      1    active
    APICAL_TRUNK        213.0         2.6     15    active
    APICAL_OBLIQUE      213.0         2.6     28    active
    APICAL_TUFT         213.0         2.6     30    active
    BASAL                 0.0         0.0    108    passive
    MYELIN                0.0         0.0     25    passive
    AXON_TERMINAL         0.0         0.0      5    passive
                                              ---
                              active 86 / passive 138 / total 224

The AIS and the nodes of Ranvier carry the highest density (action-potential
initiation site and saltatory conduction), the soma is intermediate, the
apical tree is weakly excitable, and the basal tree, myelin sheaths and
boutons stay passive in Phase 0b.

Units
-----
All densities are SI [S m^-2].  1 pS um^-2 = 1 S m^-2 and 1 S cm^-2 = 1e4
S m^-2, so the Hay values published in S cm^-2 appear here multiplied by 1e4
(3.137 S cm^-2 -> 31 370 S m^-2).  Areas are read from
Compartment.surface_area_m2, which is already SI: no unit conversion is
performed anywhere in this module.

Zero-density regions receive NO channel object at all (rather than a channel
with gbar = 0), so the Phase 0a passive cable behaviour is preserved exactly
and no gate integration time is spent on silent mechanisms.

Idempotence
-----------
apply_to_neuron() reconciles instead of appending: a compartment never ends
up with two NaV16Channel (or two KvChannel) objects, so the function can be
called repeatedly — e.g. after changing densities via overrides or a Phase 0e
provider — without double-counting conductance.

Phase 0e hook
-------------
DensityProvider is the extension point for gene expression:
mRNA abundance -> protein copy number -> gbar [S m^-2].  Any object exposing
density_na(compartment) and density_k(compartment) satisfies it, and
apply_to_neuron(neuron, provider=...) will use it in place of the literature
table.  ChannelDistribution is itself a DensityProvider, so it can be
subclassed to scale or re-shape the distribution.

References
----------
[H11]  Hay E et al. (2011) PLoS Comput Biol 7:e1002107; ModelDB #139653
[MS96] Mainen ZF, Sejnowski TJ (1996) J Neurophysiol 76:1329-1338
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Union,
    runtime_checkable,
)

from biophysical.channels.potassium_channel import KvChannel
from biophysical.channels.sodium_channel import NaV16Channel
from biophysical.core.constants import CHAN
from biophysical.morphology.compartment import Compartment, CompartmentType


# ---------------------------------------------------------------------------
# Phase 0e extension point
# ---------------------------------------------------------------------------

@runtime_checkable
class DensityProvider(Protocol):
    """Phase 0e extension point: mRNA -> protein -> conductance density.

    Implementations return maximum conductance *densities* [S m^-2] for a
    Compartment (a bare CompartmentType is also accepted by the concrete
    implementations in this module).
    """

    def density_na(self, compartment: Any) -> float: ...

    def density_k(self, compartment: Any) -> float: ...


# ---------------------------------------------------------------------------
# Region density record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegionDensity:
    """Maximum conductance densities for one region [S m^-2]."""

    gbar_na_SI: float
    gbar_k_SI: float

    @property
    def is_passive(self) -> bool:
        """True when the region carries no voltage-gated conductance."""
        return self.gbar_na_SI <= 0.0 and self.gbar_k_SI <= 0.0

    @property
    def is_active(self) -> bool:
        """True when at least one voltage-gated conductance is non-zero."""
        return not self.is_passive


# Density table sourced from the CHAN singleton (Hay 2011).  No literal
# conductance values are written here, so core/constants.py remains the single
# source of truth and cannot drift away from this table.
# AXON_TERMINAL has no CHAN entry: boutons stay passive until Phase 0d
# (synaptic release), hence the explicit zeros.
HAY_2011_DENSITIES: Dict[CompartmentType, RegionDensity] = {
    CompartmentType.AIS:            RegionDensity(CHAN.gbar_Na_AIS,    CHAN.gbar_K_AIS),
    CompartmentType.NODE:           RegionDensity(CHAN.gbar_Na_node,   CHAN.gbar_K_node),
    CompartmentType.MYELIN:         RegionDensity(CHAN.gbar_Na_myelin, CHAN.gbar_K_myelin),
    CompartmentType.AXON_TERMINAL:  RegionDensity(0.0,                 0.0),
    CompartmentType.SOMA:           RegionDensity(CHAN.gbar_Na_soma,   CHAN.gbar_K_soma),
    CompartmentType.APICAL_TRUNK:   RegionDensity(CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
    CompartmentType.APICAL_OBLIQUE: RegionDensity(CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
    CompartmentType.APICAL_TUFT:    RegionDensity(CHAN.gbar_Na_apical, CHAN.gbar_K_apical),
    CompartmentType.BASAL:          RegionDensity(CHAN.gbar_Na_basal,  CHAN.gbar_K_basal),
}


CompartmentLike = Union[Compartment, CompartmentType, Any]


def resolve_compartment_type(target: CompartmentLike) -> CompartmentType:
    """Return the CompartmentType of a compartment; pass an enum through.

    Accepts a Compartment (any object exposing ``comp_type``) or a bare
    CompartmentType, so density queries work both on a built tree and on the
    enum directly (handy in tests and in Phase 0e providers).
    """
    if isinstance(target, CompartmentType):
        return target
    comp_type = getattr(target, 'comp_type', None)
    if isinstance(comp_type, CompartmentType):
        return comp_type
    raise TypeError(
        'Expected a Compartment or CompartmentType, got '
        f'{type(target).__name__!r}'
    )


# ---------------------------------------------------------------------------
# ChannelDistribution
# ---------------------------------------------------------------------------

class ChannelDistribution(DensityProvider):
    """Hard-coded literature densities (Hay 2011), sourced from CHAN.

    Parameters
    ----------
    overrides : Mapping[CompartmentType, RegionDensity] or None
        Per-region replacements applied on top of HAY_2011_DENSITIES.  Useful
        for parameter sweeps and for silencing a region in an experiment
        (e.g. ``{CompartmentType.AIS: RegionDensity(0.0, 0.0)}``).

    Examples
    --------
        cell = NeuronCell().build()
        dist = ChannelDistribution()
        dist.apply_to_neuron(cell)
        dist.last_apply_stats['n_active']   # -> 86
    """

    def __init__(
        self,
        overrides: Optional[Mapping[CompartmentType, RegionDensity]] = None,
    ) -> None:
        self._densities: Dict[CompartmentType, RegionDensity] = dict(HAY_2011_DENSITIES)
        if overrides:
            unknown = [key for key in overrides if not isinstance(key, CompartmentType)]
            if unknown:
                raise KeyError(f'Override keys must be CompartmentType, got {unknown!r}')
            self._densities.update(overrides)
        missing = [t.name for t in CompartmentType if t not in self._densities]
        if missing:
            raise KeyError(f"No density defined for region(s): {', '.join(missing)}")
        self.last_apply_stats: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Density lookup
    # ------------------------------------------------------------------

    @property
    def densities(self) -> Mapping[CompartmentType, RegionDensity]:
        """Read-only view of the region -> RegionDensity table."""
        return MappingProxyType(self._densities)

    def region_density(self, compartment: CompartmentLike) -> RegionDensity:
        """RegionDensity for a compartment (or CompartmentType)."""
        return self._densities[resolve_compartment_type(compartment)]

    def density_na(self, compartment: CompartmentLike) -> float:
        """NaV1.6 maximum conductance density [S m^-2]."""
        return self.region_density(compartment).gbar_na_SI

    def density_k(self, compartment: CompartmentLike) -> float:
        """Kv (SKv3.1) maximum conductance density [S m^-2]."""
        return self.region_density(compartment).gbar_k_SI

    def is_passive_region(self, compartment: CompartmentLike) -> bool:
        """True when the region gets no voltage-gated channel objects."""
        return self.region_density(compartment).is_passive

    def is_active_region(self, compartment: CompartmentLike) -> bool:
        """True when the region gets at least one voltage-gated channel."""
        return not self.is_passive_region(compartment)

    # ------------------------------------------------------------------
    # Attachment
    # ------------------------------------------------------------------

    @staticmethod
    def _compartments_of(neuron: Any) -> Sequence[Compartment]:
        """Accept a NeuronCell, or any iterable of compartments."""
        if hasattr(neuron, 'compartments'):
            comps = neuron.compartments
            if comps is None:
                raise RuntimeError(
                    'Call NeuronCell.build() before applying a channel distribution.'
                )
            return comps
        return list(neuron)

    @staticmethod
    def _find_channel(comp: Compartment, channel_cls: Any) -> Any:
        """Return the attached channel of this class, or None."""
        for mech in comp.mechanisms:
            if isinstance(mech, channel_cls):
                return mech
        return None

    def _attach(
        self,
        comp: Compartment,
        channel_cls: Any,
        gbar_SI: float,
        stats: Dict[str, Any],
    ) -> None:
        """Attach — or reconcile — one voltage-gated channel on ``comp``.

        Creates the channel when absent, reuses it when the density is
        unchanged, and swaps it in place when the density changed.  Never
        appends a second copy of the same channel type, which keeps repeated
        calls to apply_to_neuron() idempotent.
        """
        existing = self._find_channel(comp, channel_cls)

        if existing is None:
            channel = channel_cls(gbar_SI=gbar_SI, area_m2=comp.surface_area_m2)
            comp.add_mechanism(channel)
            stats['n_channels_created'] += 1
        elif existing.gbar_SI != gbar_SI:
            channel = channel_cls(gbar_SI=gbar_SI, area_m2=comp.surface_area_m2)
            comp.mechanisms[comp.mechanisms.index(existing)] = channel
            stats['n_channels_replaced'] += 1
        else:
            channel = existing
            stats['n_channels_reused'] += 1

        # Gates start at the compartment's present voltage (resting state).
        channel.set_steady_state(comp.V)

    def apply_to_neuron(
        self,
        neuron: Any,
        provider: Optional[DensityProvider] = None,
    ) -> Dict[str, Any]:
        """Attach NaV16Channel and KvChannel to the excitable compartments.

        Parameters
        ----------
        neuron : NeuronCell (built) or any iterable of Compartment.
        provider : DensityProvider or None
            Phase 0e hook.  When given, densities come from the provider
            instead of the literature table (``self``).

        Returns
        -------
        dict — the same statistics also stored in ``last_apply_stats``:
            n_compartments, n_active, n_passive, n_na_channels, n_k_channels,
            n_channels_created, n_channels_reused, n_channels_replaced,
            total_g_na_S, total_g_k_S, active_by_region.

        Notes
        -----
        Compartments whose Na and K densities are both zero are skipped
        entirely: they keep only their passive Phase 0a mechanisms.
        """
        comps = self._compartments_of(neuron)
        source: DensityProvider = provider if provider is not None else self

        stats: Dict[str, Any] = {
            'n_compartments':      0,
            'n_active':            0,
            'n_passive':           0,
            'n_na_channels':       0,
            'n_k_channels':        0,
            'n_channels_created':  0,
            'n_channels_reused':   0,
            'n_channels_replaced': 0,
            'total_g_na_S':        0.0,
            'total_g_k_S':         0.0,
            'active_by_region':    {},
        }

        for comp in comps:
            stats['n_compartments'] += 1

            gbar_na = float(source.density_na(comp))
            gbar_k = float(source.density_k(comp))

            # Zero-density region: no channel objects at all.
            if gbar_na <= 0.0 and gbar_k <= 0.0:
                stats['n_passive'] += 1
                continue

            stats['n_active'] += 1
            region = resolve_compartment_type(comp).name
            stats['active_by_region'][region] = (
                stats['active_by_region'].get(region, 0) + 1
            )

            # surface_area_m2 is already SI — no conversion.
            area_m2 = comp.surface_area_m2

            if gbar_na > 0.0:
                self._attach(comp, NaV16Channel, gbar_na, stats)
                stats['n_na_channels'] += 1
                stats['total_g_na_S'] += gbar_na * area_m2

            if gbar_k > 0.0:
                self._attach(comp, KvChannel, gbar_k, stats)
                stats['n_k_channels'] += 1
                stats['total_g_k_S'] += gbar_k * area_m2

        self.last_apply_stats = stats
        return stats

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Human-readable table of the current densities per region."""
        return {
            region.name: {
                'gbar_Na_S_m2': density.gbar_na_SI,
                'gbar_K_S_m2':  density.gbar_k_SI,
                'active':       density.is_active,
            }
            for region, density in self._densities.items()
        }

    def __repr__(self) -> str:
        n_active = sum(1 for d in self._densities.values() if d.is_active)
        return (f'ChannelDistribution(regions={len(self._densities)}, '
                f'active_regions={n_active})')


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def apply_hay_2011_distribution(
    neuron: Any,
    provider: Optional[DensityProvider] = None,
) -> Dict[str, Any]:
    """Attach the Hay (2011) distribution to a built neuron; return stats."""
    return ChannelDistribution().apply_to_neuron(neuron, provider=provider)
