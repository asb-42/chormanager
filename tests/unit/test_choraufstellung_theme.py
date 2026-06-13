"""TDD RED: Regression tests for M-2 Schritt 12 — ThemeApplier extrahieren.

The applier owns the stylesheet strings + the post-apply refresh:

* Sets a QSS on the host window (light or dark)
* Clears the color cache
* Triggers ``host.grid.refresh_grid()`` and
  ``host.pool.update_singers(...)`` so the new theme colors
  propagate immediately

Public surface
--------------
* ``ThemeApplier(host)``
* ``ThemeApplier.apply(theme: str) -> None``
* ``ThemeApplier.LIGHT_STYLESHEET`` / ``DARK_STYLESHEET`` (class constants)
"""
from __future__ import annotations

import os
import sys
import types
from typing import Any, List, Optional

import pytest


# --- helpers ----------------------------------------------------------------

class _FakeGrid:
    def __init__(self):
        self.refresh_calls: int = 0

    def refresh_grid(self) -> None:
        self.refresh_calls += 1


class _FakePool:
    def __init__(self, singers: Optional[list] = None,
                 placed_ids: Optional[set] = None):
        self.singers = singers or []
        self.placed_singer_ids = placed_ids or set()
        self.update_calls: List[tuple] = []

    def update_singers(self, singers, placed_ids=None) -> None:
        self.update_calls.append((singers, placed_ids))


class _FakeHost:
    """Stand-in for the MainWindow (or any QWidget)."""

    def __init__(self):
        self.grid = _FakeGrid()
        self.pool = _FakePool(singers=[1, 2, 3], placed_ids={1, 2})
        self.singers = [1, 2, 3]  # host.singers is what gets pushed to pool
        self._stylesheets: List[str] = []
        self._color_cache_clears: int = 0

    def setStyleSheet(self, qss: str) -> None:  # noqa: N802 — Qt naming
        self._stylesheets.append(qss)


# --- tests -------------------------------------------------------------------

class TestModuleShape:
    def test_theme_module_exists(self):
        try:
            from theme import ThemeApplier  # noqa: F401
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"theme module missing: {exc}")

    def test_theme_applier_is_a_class(self):
        from theme import ThemeApplier
        assert isinstance(ThemeApplier, type)

    def test_theme_applier_api(self):
        from theme import ThemeApplier
        for name in ("apply", "LIGHT_STYLESHEET", "DARK_STYLESHEET"):
            assert hasattr(ThemeApplier, name), f"missing: {name}"


class TestApplyLightTheme:
    def test_light_theme_sets_light_stylesheet(self, monkeypatch):
        from theme import ThemeApplier
        # Make clear_color_cache a no-op
        import theme as _theme  # noqa: WPS433
        monkeypatch.setattr(_theme, "clear_color_cache", lambda: None, raising=False)

        host = _FakeHost()
        applier = ThemeApplier(host)
        applier.apply("light")
        assert len(host._stylesheets) == 1
        qss = host._stylesheets[0]
        # Light theme has light backgrounds
        assert "background: #f8f4eb" in qss or "background:#f8f4eb" in qss

    def test_unknown_theme_falls_back_to_light(self, monkeypatch):
        from theme import ThemeApplier
        import theme as _theme  # noqa: WPS433
        monkeypatch.setattr(_theme, "clear_color_cache", lambda: None, raising=False)

        host = _FakeHost()
        applier = ThemeApplier(host)
        applier.apply("nope-not-a-theme")
        # Falls back to light
        assert "background: #f8f4eb" in host._stylesheets[0] or \
               "background:#f8f4eb" in host._stylesheets[0]


class TestApplyDarkTheme:
    def test_dark_theme_sets_dark_stylesheet(self, monkeypatch):
        from theme import ThemeApplier
        import theme as _theme  # noqa: WPS433
        monkeypatch.setattr(_theme, "clear_color_cache", lambda: None, raising=False)

        host = _FakeHost()
        applier = ThemeApplier(host)
        applier.apply("dark")
        assert len(host._stylesheets) == 1
        qss = host._stylesheets[0]
        # Dark theme has dark backgrounds
        assert "background: #2b2b2b" in qss or "background:#2b2b2b" in qss


class TestApplyTriggersRefresh:
    def test_apply_clears_color_cache(self, monkeypatch):
        from theme import ThemeApplier
        import theme as _theme  # noqa: WPS433
        clears: list = []
        monkeypatch.setattr(_theme, "clear_color_cache",
                            lambda: clears.append(1), raising=False)

        host = _FakeHost()
        applier = ThemeApplier(host)
        applier.apply("light")
        assert clears == [1]

    def test_apply_refreshes_grid(self, monkeypatch):
        from theme import ThemeApplier
        import theme as _theme  # noqa: WPS433
        monkeypatch.setattr(_theme, "clear_color_cache", lambda: None, raising=False)

        host = _FakeHost()
        applier = ThemeApplier(host)
        applier.apply("light")
        assert host.grid.refresh_calls == 1

    def test_apply_updates_pool(self, monkeypatch):
        from theme import ThemeApplier
        import theme as _theme  # noqa: WPS433
        monkeypatch.setattr(_theme, "clear_color_cache", lambda: None, raising=False)

        host = _FakeHost()
        applier = ThemeApplier(host)
        applier.apply("dark")
        assert len(host.pool.update_calls) == 1
        # The pool was updated with the host's singers
        assert host.pool.update_calls[0][0] == host.singers  # [1, 2, 3]
