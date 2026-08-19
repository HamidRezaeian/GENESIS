"""test_channels_kinetics.py — Unit tests for channels/kinetics.py.

Covers:
  KineticsSet   — enum members exist and are distinct

No solver, morphology, or membrane dependencies.
"""

import pytest
from biophysical.channels.kinetics import KineticsSet


class TestKineticsSet:
    """KineticsSet enum: members exist, are distinct, and are correctly typed."""

    def test_hh_squid_1952_exists(self):
        """HH_SQUID_1952 member must exist in KineticsSet."""
        assert hasattr(KineticsSet, 'HH_SQUID_1952'), \
            'KineticsSet is missing HH_SQUID_1952'

    def test_mammalian_ms96_exists(self):
        """MAMMALIAN_MS96 member must exist in KineticsSet."""
        assert hasattr(KineticsSet, 'MAMMALIAN_MS96'), \
            'KineticsSet is missing MAMMALIAN_MS96'

    def test_members_are_distinct(self):
        """HH_SQUID_1952 and MAMMALIAN_MS96 must have different values."""
        assert KineticsSet.HH_SQUID_1952 != KineticsSet.MAMMALIAN_MS96, \
            'KineticsSet members are not distinct'

    def test_exactly_two_members(self):
        """KineticsSet must contain exactly 2 members (HH_SQUID_1952, MAMMALIAN_MS96)."""
        members = list(KineticsSet)
        assert len(members) == 2, \
            f'Expected 2 KineticsSet members, found {len(members)}: {members}'

    def test_members_are_kinetics_set_instances(self):
        """Every member must be an instance of KineticsSet."""
        for member in KineticsSet:
            assert isinstance(member, KineticsSet), \
                f'{member!r} is not a KineticsSet instance'
