"""TDD RED: A3-FIX-A — VoiceGroup-Cache moved to singer_model.

Previously, the ``_build_voice_group_map()`` helper and the lazy
``_VoiceGroup`` global lived in ``chormanager/choraufstellung/chormanager_bridge``.
A3-FIX-A moves the cache into ``singer_model.py`` (as an
``lru_cache``-backed function) so any module can resolve a string to a
``VoiceGroup`` enum without re-implementing its own cache.
"""
from __future__ import annotations

import pytest


def test_singer_model_exposes_voice_group_map_function():
    from chormanager.choraufstellung import singer_model
    assert hasattr(singer_model, "voice_group_map"), (
        "A3-FIX-A: singer_model.voice_group_map() must be exposed"
    )
    assert callable(singer_model.voice_group_map)


def test_voice_group_map_contains_all_enum_values():
    from chormanager.choraufstellung import singer_model
    from chormanager.choraufstellung.singer_model import VoiceGroup
    m = singer_model.voice_group_map()
    # Each enum member must be present under its string value.
    for vg in VoiceGroup:
        assert vg.value in m
        assert m[vg.value] is vg


def test_voice_group_map_is_cached():
    """Calling the function twice returns the SAME dict object."""
    from chormanager.choraufstellung import singer_model
    a = singer_model.voice_group_map()
    b = singer_model.voice_group_map()
    assert a is b, "voice_group_map() must be lru_cached"


def test_singer_model_exposes_resolve_voice_group_helper():
    """A small helper ``resolve_voice_group(name) -> VoiceGroup`` is useful
    so callers don't have to roll their own prefix-matching logic."""
    from chormanager.choraufstellung import singer_model
    from chormanager.choraufstellung.singer_model import VoiceGroup
    assert hasattr(singer_model, "resolve_voice_group")
    assert singer_model.resolve_voice_group("Sopran 1") is VoiceGroup.SOPRAN_1
    assert singer_model.resolve_voice_group("Bass 2") is VoiceGroup.BASS_2
    # Prefix match (was the old fallback behaviour in chormanager_bridge).
    assert singer_model.resolve_voice_group("Alt") is VoiceGroup.ALT_1
    # Unknown / empty -> SOPRAN_1 (the historical safe fallback).
    assert singer_model.resolve_voice_group("") is VoiceGroup.SOPRAN_1
    assert singer_model.resolve_voice_group("not-a-voice-group") is VoiceGroup.SOPRAN_1
