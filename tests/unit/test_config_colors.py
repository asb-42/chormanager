"""Tests for voice group color config functions."""

import pytest
from chormanager.config import (
    get_voice_group_color,
    get_text_color,
    _clear_vg_color_cache,
)


class TestGetVoiceGroupColor:
    def setup_method(self):
        _clear_vg_color_cache()

    def test_returns_light_theme_colors(self):
        """Should return valid hex color for known voice group."""
        color = get_voice_group_color("Sopran 1")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_returns_fallback_for_unknown_group(self):
        """Should return fallback color for unknown voice group."""
        color = get_voice_group_color("Nonexistent Group")
        assert color == "#cccccc"

    def test_all_voice_groups_have_colors(self):
        """Should return a color for every standard voice group."""
        groups = ["Sopran 1", "Sopran 2", "Alt 1", "Alt 2",
                  "Tenor 1", "Tenor 2", "Bass 1", "Bass 2"]
        for group in groups:
            color = get_voice_group_color(group)
            assert color.startswith("#"), f"No color for {group}"

    def test_explicit_theme_override(self):
        """Should accept theme override parameter."""
        color_light = get_voice_group_color("Sopran 1", theme="light")
        color_dark = get_voice_group_color("Sopran 1", theme="dark")
        assert color_light.startswith("#")
        assert color_dark.startswith("#")

    def test_returns_same_color_on_repeated_calls(self):
        """Should cache results for same theme."""
        c1 = get_voice_group_color("Alt 1")
        c2 = get_voice_group_color("Alt 1")
        assert c1 == c2


class TestGetTextColor:
    def test_returns_valid_hex(self):
        """Should return a hex color string."""
        color = get_text_color()
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7
