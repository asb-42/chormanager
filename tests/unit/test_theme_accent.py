"""Unit tests for theme-aware accent colors (theme_manager.accent_color)."""

import pytest

from chormanager.ui.theme_manager import accent_color


class TestAccentColor:
    def test_light_success_is_dark_green(self):
        assert accent_color("success", "light") == "#2e7d32"

    def test_dark_success_is_readable_light_green(self):
        assert accent_color("success", "dark") == "#81c784"

    def test_light_error_is_red(self):
        assert accent_color("error", "light") == "#b00020"

    def test_dark_error_is_readable_light_red(self):
        assert accent_color("error", "dark") == "#ff8a80"

    def test_unknown_kind_returns_empty_string(self):
        assert accent_color("gibtsnicht", "light") == ""

    def test_reads_configured_theme_when_not_given(self, monkeypatch):
        import chormanager.ui.theme_manager as tm

        monkeypatch.setattr(tm, "get_theme", lambda: "dark")
        assert accent_color("success") == "#81c784"

    def test_falls_back_to_light_on_config_error(self, monkeypatch):
        import chormanager.ui.theme_manager as tm

        def broken():
            raise RuntimeError("no config")

        monkeypatch.setattr(tm, "get_theme", broken)
        assert accent_color("success") == "#2e7d32"
