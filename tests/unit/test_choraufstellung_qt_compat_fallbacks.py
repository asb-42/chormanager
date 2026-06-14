"""Tests for the A2-FIX-A slimmed-down ``qt_compat`` module.

A2-FIX-A removed the dead ``FallbackSinger``, ``FallbackOptimizerDialog``
and ``FallbackGridEngine`` classes from ``qt_compat.py``. PyQt6 is now
the only supported binding; the cross-compat shim is reduced to
``exec_qt``, the enum aliases, and the re-exported Qt classes.

These tests now assert the *removed* behaviour (the fallbacks are
gone) and the *kept* behaviour (exec_qt, enums, re-exports).
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import pytest


class TestQtCompatNoFallbacks:
    """A2-FIX-A: the Fallback* classes are gone (dead code)."""

    def test_fallback_singer_removed(self):
        from chormanager.choraufstellung import qt_compat
        assert not hasattr(qt_compat, "FallbackSinger"), (
            "A2-FIX-A: FallbackSinger should be removed from qt_compat"
        )

    def test_fallback_optimizer_dialog_removed(self):
        from chormanager.choraufstellung import qt_compat
        assert not hasattr(qt_compat, "FallbackOptimizerDialog"), (
            "A2-FIX-A: FallbackOptimizerDialog should be removed from qt_compat"
        )

    def test_fallback_grid_engine_removed(self):
        from chormanager.choraufstellung import qt_compat
        assert not hasattr(qt_compat, "FallbackGridEngine"), (
            "A2-FIX-A: FallbackGridEngine should be removed from qt_compat"
        )


class TestQtCompatExecQt:
    """qt_compat.exec_qt handles PyQt5/PyQt6 .exec()/.exec_() difference."""

    def test_exec_qt_callable(self):
        from chormanager.choraufstellung.qt_compat import exec_qt
        assert callable(exec_qt)

    def test_qt_version_is_six(self):
        """We always run on PyQt6 in tests, so QT_VERSION must be 6."""
        from chormanager.choraufstellung.qt_compat import QT_VERSION
        assert QT_VERSION == 6


class TestQtCompatReExportsQtClasses:
    """qt_compat must re-export the most-used Qt classes so that
    main.py can do ``from qt_compat import QApplication, ...``."""

    @pytest.mark.parametrize("name", [
        "QApplication", "QMainWindow", "QWidget", "QVBoxLayout", "QHBoxLayout",
        "QGridLayout", "QLabel", "QPushButton", "QMenuBar", "QMenu",
        "QFileDialog", "QDialog", "QFormLayout", "QLineEdit", "QComboBox",
        "QListWidget", "QListWidgetItem", "QScrollArea", "QMessageBox",
        "QFrame", "QCheckBox", "QSplitter", "QGraphicsDropShadowEffect",
        "QRubberBand", "QCompleter", "QTableWidget", "QTableWidgetItem",
        "QHeaderView", "QRadioButton",
    ])
    def test_qtwidgets_class_re_exported(self, name):
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, name), (
            f"qt_compat.{name} is missing; main.py needs it for "
            f"``from qt_compat import {name}``"
        )

    @pytest.mark.parametrize("name", [
        "Qt", "QMimeData", "pyqtSignal", "QRect", "QTimer", "QPoint",
    ])
    def test_qtcore_class_re_exported(self, name):
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, name)

    @pytest.mark.parametrize("name", [
        "QDrag", "QColor", "QPalette", "QFont", "QAction",
        "QUndoStack", "QUndoCommand", "QActionGroup",
    ])
    def test_qtgui_class_re_exported(self, name):
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, name)

    @pytest.mark.parametrize("name", ["QPrinter", "QPrintDialog"])
    def test_qtprintsupport_class_re_exported(self, name):
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, name)


class TestQtCompatEnumMappings:
    """qt_compat must expose the enum-aliased names that main.py uses.

    These are the names that were assigned in main.py lines 29-44 to
    bridge PyQt5 (<Qt6) and PyQt6 enums. They must be available in
    qt_compat so that main.py no longer needs to assign them locally.
    """

    @pytest.mark.parametrize("attr,enum_name", [
        ("Panel", "Shape"),
        ("Raised", "Shadow"),
        ("Sunken", "Shadow"),
        ("HLine", "Shape"),
        ("VLine", "Shape"),
        ("StyledPanel", "Shape"),
        ("NoFrame", "Shape"),
    ])
    def test_qframe_enum_aliases(self, attr, enum_name):
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        from chormanager.choraufstellung.qt_compat import QFrame
        # After import, the aliases must be on the QFrame class itself
        assert hasattr(QFrame, attr), (
            f"QFrame.{attr} alias is missing; it must be assigned in "
            f"qt_compat so that main.py does not need its own try-block."
        )

    @pytest.mark.parametrize("attr", [
        "Horizontal", "Vertical", "AlignCenter", "AlignRight", "AlignTop",
        "LeftButton", "RightButton", "ControlModifier",
    ])
    def test_qt_enum_aliases(self, attr):
        from chormanager.choraufstellung.qt_compat import Qt
        assert hasattr(Qt, attr), (
            f"Qt.{attr} alias is missing in qt_compat"
        )
