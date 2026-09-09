"""Tests for Singer model conversion between domain and formation models."""

import pytest
from chormanager.domain.models import Singer as DomainSinger
from chormanager.choraufstellung.singer_model import Singer as FormationSinger, VoiceGroup


class TestDomainToFormationConversion:
    def test_to_formation_singer_basic(self):
        """Should convert domain Singer to formation Singer with correct fields."""
        domain = DomainSinger(
            id="singer-123",
            full_name="Anna Alt",
            short_name="Anna",
            voice_group="Alt 1",
            height=165,
            affinity_uuid="partner-456",
        )
        formation = domain.to_formation_singer()

        assert isinstance(formation, FormationSinger)
        assert formation.name == "Anna"
        assert formation.voice_group == VoiceGroup.ALT_1
        assert formation.height == 165
        assert formation.singer_id == "singer-123"
        assert formation.affinity == "partner-456"
        assert formation.row == -1
        assert formation.col == -1

    def test_to_formation_singer_uses_full_name_when_no_short(self):
        """Should fall back to full_name when short_name is None."""
        domain = DomainSinger(
            id="s1",
            full_name="Berthold Bass",
            voice_group="Bass 1",
        )
        formation = domain.to_formation_singer()
        assert formation.name == "Berthold Bass"

    def test_to_formation_singer_unknown_voice_group(self):
        """Should default to SOPRAN_1 for unknown voice group."""
        domain = DomainSinger(
            id="s1",
            full_name="Test",
            voice_group="Unknown Group",
        )
        formation = domain.to_formation_singer()
        assert formation.voice_group == VoiceGroup.SOPRAN_1

    def test_to_formation_singer_no_affinity(self):
        """Should set empty affinity when affinity_uuid is None."""
        domain = DomainSinger(
            id="s1",
            full_name="Test",
            voice_group="Sopran 1",
        )
        formation = domain.to_formation_singer()
        assert formation.affinity == ""

    def test_to_formation_singer_no_height(self):
        """Should default height to 0 when None."""
        domain = DomainSinger(
            id="s1",
            full_name="Test",
            voice_group="Tenor 1",
            height=None,
        )
        formation = domain.to_formation_singer()
        assert formation.height == 0


class TestFormationToDomainConversion:
    def test_from_domain_singer_basic(self):
        """Should create formation Singer from domain Singer."""
        domain = DomainSinger(
            id="singer-123",
            full_name="Clara Sopran",
            short_name="Clara",
            voice_group="Sopran 1",
            height=158,
        )
        formation = FormationSinger.from_domain_singer(domain)

        assert isinstance(formation, FormationSinger)
        assert formation.name == "Clara"
        assert formation.voice_group == VoiceGroup.SOPRAN_1
        assert formation.height == 158
        assert formation.singer_id == "singer-123"

    def test_from_domain_singer_all_voice_groups(self):
        """Should handle all voice group values."""
        for vg_name, expected_enum in [
            ("Sopran 1", VoiceGroup.SOPRAN_1),
            ("Sopran 2", VoiceGroup.SOPRAN_2),
            ("Alt 1", VoiceGroup.ALT_1),
            ("Alt 2", VoiceGroup.ALT_2),
            ("Tenor 1", VoiceGroup.TENOR_1),
            ("Tenor 2", VoiceGroup.TENOR_2),
            ("Bass 1", VoiceGroup.BASS_1),
            ("Bass 2", VoiceGroup.BASS_2),
        ]:
            domain = DomainSinger(
                id="s1", full_name="Test", voice_group=vg_name
            )
            formation = FormationSinger.from_domain_singer(domain)
            assert formation.voice_group == expected_enum, f"Failed for {vg_name}"


class TestSingerDictRoundtrip:
    def test_domain_to_dict_roundtrip(self):
        """Should round-trip through dict serialization."""
        original = DomainSinger(
            id="s1",
            full_name="Dieter Tenor",
            voice_group="Tenor 1",
            height=175,
        )
        d = original.to_dict()
        restored = DomainSinger.from_dict(d)
        assert restored.id == original.id
        assert restored.full_name == original.full_name
        assert restored.voice_group == original.voice_group
        assert restored.height == original.height

    def test_formation_to_dict_roundtrip(self):
        """Should round-trip through dict serialization."""
        original = FormationSinger(
            name="Eva Sopran",
            voice_group=VoiceGroup.SOPRAN_2,
            height=162,
            singer_id="s5",
            row=2,
            col=0,
        )
        d = original.to_dict()
        restored = FormationSinger.from_dict(d)
        assert restored.name == original.name
        assert restored.voice_group == original.voice_group
        assert restored.height == original.height
        assert restored.singer_id == original.singer_id
        assert restored.row == original.row
        assert restored.col == original.col
