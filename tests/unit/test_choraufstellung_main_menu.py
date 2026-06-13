"""TDD RED: Regression tests for M-2 Schritt 13 — MainMenuBuilder extrahieren.

Encapsulates the menu/toolbar construction that was previously inlined
in :meth:`MainWindow.menu` (Z. 386-466 in the post-Schritt-12 main.py,
~80 LOC).

The builder:

* Creates the four sub-menus: Datei, Bearbeiten, Aufstellen,
  Konfigurieren, Ansicht, Hilfe
* Wires the QAction triggered signals to the host's methods
* Stashes the action handles (``swap_action``, ``undo_action``,
  ``redo_action``, ``actionLight``, ``actionDark``, ``theme_group``)
  on the host so other code paths can toggle/enable them

The builder is **duck-typed** and **pure-Qt** — the tests can use
``qtbot`` (a real QApplication) to assert the menu structure.
"""
from __future__ import annotations

import sys
from typing import Any, List

import pytest


# These tests need a real QApplication (qtbot fixture). They are placed
# in tests/unit because they are fast and do not need network/db/etc.
# Use ``QT_QPA_PLATFORM=offscreen`` in CI.


class TestModuleShape:
    def test_main_menu_module_exists(self):
        try:
            from main_menu import MainMenuBuilder  # noqa: F401
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"main_menu module missing: {exc}")

    def test_main_menu_builder_is_a_class(self):
        from main_menu import MainMenuBuilder
        assert isinstance(MainMenuBuilder, type)

    def test_main_menu_builder_api(self):
        from main_menu import MainMenuBuilder
        assert hasattr(MainMenuBuilder, "build")


class TestBuildCreatesSubmenus:
    def test_build_creates_five_submenus(self, qtbot):
        from main_menu import MainMenuBuilder
        from PyQt6.QtWidgets import QMainWindow

        win = QMainWindow()
        qtbot.addWidget(win)

        # Stash minimal attributes the builder will read
        win.grid = type("_Grid", (), {
            "auto_arrange_by_height": lambda: None,
            "auto_arrange_men_outer": lambda: None,
            "auto_arrange_satb": lambda: None,
            "auto_arrange_sbta": lambda: None,
            "auto_arrange_s1s2b2b1t2t1a2a1": lambda: None,
            "auto_arrange_s1s2a1a2t1t2b1b2": lambda: None,
            "auto_arrange_s1s2b1b2t1t2a1a2": lambda: None,
        })()
        win._apply_theme = lambda t: None  # noqa: E731
        win.new_f = lambda: None
        win.open_f = lambda: None
        win.save_f = lambda: None
        win.save_as_f = lambda: None
        win.export_pdf = lambda: None
        win.add_singer_via_menu = lambda: None
        win.swap_selected_singers = lambda: None
        win.undo_last_action = lambda: None
        win.redo_last_action = lambda: None
        win.apply_all_affinity_proximity = lambda: None
        win.reset_formation = lambda: None
        win.run_optimizer = lambda: None
        win.show_cfg = lambda: None
        win.show_about = lambda: None
        win._menu_legenda = lambda: None

        builder = MainMenuBuilder(win)
        builder.build()

        mb = win.menuBar()
        titles = [a.text() for a in mb.actions() if a.menu() is not None]
        # Expected menus: Datei, Bearbeiten, Aufstellen, Konfigurieren, Ansicht, Hilfe
        assert "Datei" in titles
        assert "Bearbeiten" in titles
        assert "Aufstellen" in titles
        assert "Konfigurieren" in titles
        assert any("Ansicht" in t for t in titles)
        assert "Hilfe" in titles or "&Hilfe" in titles


class TestBuildStashesActionHandles:
    def test_build_stashes_swap_undo_redo_actions(self, qtbot):
        from main_menu import MainMenuBuilder
        from PyQt6.QtWidgets import QMainWindow

        win = QMainWindow()
        qtbot.addWidget(win)
        win.grid = type("_Grid", (), {
            "auto_arrange_by_height": lambda: None,
            "auto_arrange_men_outer": lambda: None,
            "auto_arrange_satb": lambda: None,
            "auto_arrange_sbta": lambda: None,
            "auto_arrange_s1s2b2b1t2t1a2a1": lambda: None,
            "auto_arrange_s1s2a1a2t1t2b1b2": lambda: None,
            "auto_arrange_s1s2b1b2t1t2a1a2": lambda: None,
        })()
        win._apply_theme = lambda t: None
        win.new_f = lambda: None
        win.open_f = lambda: None
        win.save_f = lambda: None
        win.save_as_f = lambda: None
        win.export_pdf = lambda: None
        win.add_singer_via_menu = lambda: None
        win.swap_selected_singers = lambda: None
        win.undo_last_action = lambda: None
        win.redo_last_action = lambda: None
        win.apply_all_affinity_proximity = lambda: None
        win.reset_formation = lambda: None
        win.run_optimizer = lambda: None
        win.show_cfg = lambda: None
        win.show_about = lambda: None
        win._menu_legenda = lambda: None

        builder = MainMenuBuilder(win)
        builder.build()

        # All action handles must be stashed on the host
        assert hasattr(win, "swap_action")
        assert hasattr(win, "undo_action")
        assert hasattr(win, "redo_action")
        assert hasattr(win, "actionLight")
        assert hasattr(win, "actionDark")
        assert hasattr(win, "theme_group")

        # swap_action starts disabled
        assert win.swap_action.isEnabled() is False
        # undo/redo start disabled
        assert win.undo_action.isEnabled() is False
        assert win.redo_action.isEnabled() is False
