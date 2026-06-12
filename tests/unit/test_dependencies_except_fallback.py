"""Regression tests for M-4 (bare except: -> concrete exceptions).

These tests pin down the EXISTING behaviour of three functions in
``chormanager.choraufstellung.dependencies`` whose ``try``-blocks
silently swallowed all exceptions. They are written BEFORE the
refactor so the fallback contract cannot regress.

Important context (from diagnosis 2026-06-12):

* ``config/voice_groups.json`` currently holds a *theme* colour map
  (``{"themes": {"light": {...}, "dark": {...}}}``), not the
  ``voice_groups`` list the functions are looking for. As a
  result, the ``try``-block always returns ``[]`` (or never matches)
  and the hard-coded fallback is taken. M-4 refactor must NOT change
  that behaviour.

* The functions are therefore *functionally dead* in production, but
  we still need to ensure the exception-type change does not break
  callers or change observable behaviour.
"""
from __future__ import annotations

import json
import sys
from unittest import mock

import pytest

from chormanager.choraufstellung import dependencies as deps


# ---------------------------------------------------------------------------
# 1. get_valid_voice_groups()
# ---------------------------------------------------------------------------

class TestGetValidVoiceGroupsFallback:
    """The current file structure makes the function return [] and
    then the hard-coded eight-group fallback is used. After M-4 this
    must still hold."""

    def test_returns_empty_list_when_file_lacks_key(self, monkeypatch):
        """The real config/voice_groups.json exists but has the
        'themes' key, not 'voice_groups'. Therefore the list-comprehension
        returns []. This is the CURRENT (dead-code) behaviour that
        M-4 refactor must NOT change."""
        # The function uses a *relative* path. We must not let it
        # actually open a wrong file, so we make os.path.exists return
        # False to force the function down the no-file path.
        with mock.patch.object(deps.os.path, "exists", return_value=False):
            result = deps.get_valid_voice_groups()
        # With no file at all, the function still returns the 8-group
        # default (because the function reads the file only if it exists).
        assert result == [
            "Sopran 1", "Sopran 2",
            "Alt 1", "Alt 2",
            "Tenor 1", "Tenor 2",
            "Bass 1", "Bass 2",
        ]

    def test_no_crash_on_unreadable_file(self, tmp_path, monkeypatch):
        """If os.path.exists lies or open() fails, the function must
        not propagate the exception. We patch open() to raise
        OSError and check that the default list comes back."""
        monkeypatch.chdir(tmp_path)
        with mock.patch.object(deps.os.path, "exists", return_value=True), \
             mock.patch("builtins.open",
                        side_effect=OSError("simulated read failure")):
            result = deps.get_valid_voice_groups()
        assert result == [
            "Sopran 1", "Sopran 2",
            "Alt 1", "Alt 2",
            "Tenor 1", "Tenor 2",
            "Bass 1", "Bass 2",
        ]

    def test_no_crash_on_malformed_json(self, tmp_path, monkeypatch):
        """If json.load() raises JSONDecodeError the function must
        swallow it (current contract) and return the default list."""
        monkeypatch.chdir(tmp_path)
        with mock.patch.object(deps.os.path, "exists", return_value=True), \
             mock.patch("builtins.open",
                        mock.mock_open(read_data="{ this is not valid json")):
            result = deps.get_valid_voice_groups()
        assert result == [
            "Sopran 1", "Sopran 2",
            "Alt 1", "Alt 2",
            "Tenor 1", "Tenor 2",
            "Bass 1", "Bass 2",
        ]

    def test_returns_empty_list_when_key_missing(self, tmp_path, monkeypatch):
        """If the dict does not contain the 'voice_groups' key, the
        function returns []. The function does NOT fall through to
        the hard-coded default in that case - it returns [] directly.
        M-4 must preserve this subtle behaviour."""
        monkeypatch.chdir(tmp_path)
        payload = json.dumps({"unrelated": "key"})
        with mock.patch.object(deps.os.path, "exists", return_value=True), \
             mock.patch("builtins.open", mock.mock_open(read_data=payload)):
            result = deps.get_valid_voice_groups()
        assert result == []


# ---------------------------------------------------------------------------
# 2. get_voice_group_color_fallback()
# ---------------------------------------------------------------------------

class TestGetVoiceGroupColorFallback:
    def test_returns_grey_for_unknown_id(self, monkeypatch):
        """Any id (existing or not) currently returns #cccccc because
        the JSON file does not contain the 'voice_groups' key. M-4
        refactor must not change this."""
        assert deps.get_voice_group_color_fallback("Sopran 1") == "#cccccc"
        assert deps.get_voice_group_color_fallback("Bass 8") == "#cccccc"
        assert deps.get_voice_group_color_fallback("") == "#cccccc"

    def test_no_crash_on_unreadable_file(self, monkeypatch):
        with mock.patch.object(deps.os.path, "exists", return_value=True), \
             mock.patch("builtins.open",
                        side_effect=OSError("simulated read failure")):
            assert deps.get_voice_group_color_fallback("Sopran 1") == "#cccccc"

    def test_no_crash_on_malformed_json(self, monkeypatch):
        with mock.patch.object(deps.os.path, "exists", return_value=True), \
             mock.patch("builtins.open",
                        mock.mock_open(read_data="definitely not json")):
            assert deps.get_voice_group_color_fallback("Sopran 1") == "#cccccc"

    def test_no_crash_on_keyerror_in_loop(self, monkeypatch):
        """If a vg entry lacks the 'id' or 'color' key, the bare-except
        path would swallow the KeyError. Concrete except must also
        catch it (so the call still returns #cccccc)."""
        payload = json.dumps({
            "voice_groups": [
                {"id": "Sopran 1"},   # missing 'color'
            ]
        })
        with mock.patch.object(deps.os.path, "exists", return_value=True), \
             mock.patch("builtins.open", mock.mock_open(read_data=payload)):
            assert deps.get_voice_group_color_fallback("Sopran 1") == "#cccccc"


# ---------------------------------------------------------------------------
# 3. create_singer_fallback() -- the inner try around VoiceGroup(...)
# ---------------------------------------------------------------------------

class TestCreateSingerFallbackVoiceGroup:
    def test_voicegroup_value_error_is_swallowed(self):
        """When ``VoiceGroup`` is set but receives an unknown value,
        ``ValueError`` (raised by Enum.__call__) must be caught and a
        ``FallbackVoiceGroup`` must be used. This documents that
        ``except ValueError`` is the correct concrete replacement.

        We exercise the inner code via ``FallbackSinger.from_dict``,
        which is the only place where the ``try``-block lives."""
        from enum import Enum

        class StrictVg(Enum):
            SOPRAN1 = "Sopran 1"
            SOPRAN2 = "Sopran 2"

        with mock.patch.object(deps, "VoiceGroup", StrictVg):
            singer = deps.create_singer_fallback(
                "Anna", "Sopran 1"
            ).from_dict({"name": "Anna", "voice_group": "Unknown value"})
        assert singer.name == "Anna"
        # The FallbackVoiceGroup is defined inside create_singer_fallback,
        # but its behaviour is: .value equals the raw string passed in.
        assert hasattr(singer.voice_group, "value")
        assert singer.voice_group.value == "Unknown value"

    def test_no_voicegroup_uses_fallback_directly(self):
        """When ``VoiceGroup`` is None the inner try is short-circuited
        and FallbackVoiceGroup is used immediately. No exception path
        is hit. Documenting that behaviour to lock it in."""
        with mock.patch.object(deps, "VoiceGroup", None):
            singer = deps.create_singer_fallback(
                "Bea", "Sopran 1"
            ).from_dict({"name": "Bea", "voice_group": "Any value"})
        assert singer.name == "Bea"
        assert singer.voice_group.value == "Any value"
