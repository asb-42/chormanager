"""TDD RED: A2-FIX-A — Dead PyQt5 fallbacks removed from qt_compat.

The ``FallbackSinger``, ``FallbackOptimizerDialog``, and
``FallbackGridEngine`` classes in ``qt_compat.py`` exist "just in case"
the corresponding domain modules fail to import. In practice that never
happens (singer_model, optimizer_dialog, and grid_engine all import
cleanly on PyQt6). A2-FIX-A removes the dead code.

The remaining ``qt_compat`` module still provides:

* ``exec_qt`` helper (real, used by code)
* PyQt5/PyQt6 enum aliases (``QFrame.Panel`` etc.)
* re-exported Qt classes

This test pins the *removed* behaviour: the fallbacks must NOT be
importable from ``qt_compat`` anymore.
"""
from __future__ import annotations

import pytest


def test_fallback_singer_removed():
    from chormanager.choraufstellung import qt_compat
    assert not hasattr(qt_compat, "FallbackSinger"), (
        "A2-FIX-A: FallbackSinger must be removed from qt_compat"
    )


def test_fallback_optimizer_dialog_removed():
    from chormanager.choraufstellung import qt_compat
    assert not hasattr(qt_compat, "FallbackOptimizerDialog"), (
        "A2-FIX-A: FallbackOptimizerDialog must be removed from qt_compat"
    )


def test_fallback_grid_engine_removed():
    from chormanager.choraufstellung import qt_compat
    assert not hasattr(qt_compat, "FallbackGridEngine"), (
        "A2-FIX-A: FallbackGridEngine must be removed from qt_compat"
    )


def test_exec_qt_still_present():
    """exec_qt is a real helper, must stay."""
    from chormanager.choraufstellung.qt_compat import exec_qt
    assert callable(exec_qt)


def test_qt_version_still_exported():
    from chormanager.choraufstellung.qt_compat import QT_VERSION
    assert QT_VERSION == 6


def test_qt_classes_still_reexported():
    """The Qt class re-exports must still work for all callers."""
    from chormanager.choraufstellung import qt_compat
    for name in ("QApplication", "QMainWindow", "QDialog", "QFrame"):
        assert hasattr(qt_compat, name), f"qt_compat.{name} missing"


def test_qt_enum_aliases_still_work():
    """PyQt5-style enum aliases on QFrame / Qt are still attached."""
    from chormanager.choraufstellung.qt_compat import QFrame, Qt
    # QFrame.Panel was the PyQt5 name; qt_compat aliases it for PyQt6.
    assert hasattr(QFrame, "Panel")
    assert hasattr(Qt, "AlignCenter")
