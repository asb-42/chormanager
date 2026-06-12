"""TDD RED: Regression tests for M-2 Schritt 1.

Refactor: chormanager/choraufstellung/main.py lines 1-86 (PyQt5/PyQt6
cross-compat try/except block + Klassen-Fallbacks) are extracted into
chormanager/choraufstellung/qt_compat.py.

Before the refactor:
  main.py has:
    - try/except importing exec_qt (line 5-12)
    - try/except importing PyQt6 classes with enum mappings (14-58)
    - try/except importing config helpers with stub fallbacks (60-69)
    - try/except importing domain classes (Singer, FormationStorage, etc.)
      with stub fallbacks (76-104)

After the refactor:
  qt_compat.py is the single source of truth for:
    - exec_qt() (already there)
    - All Qt classes (already re-exported via *)
    - Fallback classes: FallbackSinger, FallbackOptimizerDialog, etc.
  main.py does ``from qt_compat import ...`` (no try/except).

These tests pin down the EXISTING behavior of the fallback classes
and the cross-compat layer so we can refactor safely.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import pytest


class TestQtCompatFallbackSinger:
    """When singer_model.Singer cannot be imported, qt_compat must
    provide a FallbackSinger with the same constructor signature."""

    def test_fallback_singer_module_attribute(self):
        """qt_compat must expose FallbackSinger as a module attribute."""
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, "FallbackSinger"), (
            "qt_compat.FallbackSinger is missing; it must be importable "
            "so that main.py can use it without a try/except."
        )

    def test_fallback_singer_constructible(self):
        """FallbackSinger(name, voice_group, height, singer_id) works."""
        from chormanager.choraufstellung.qt_compat import FallbackSinger
        s = FallbackSinger("Anna", "Sopran 1", height=165, singer_id="s-1")
        assert s.name == "Anna"
        assert s.voice_group == "Sopran 1"
        assert s.height == 165
        assert s.singer_id == "s-1"

    def test_fallback_singer_default_height(self):
        """FallbackSinger default height is 0."""
        from chormanager.choraufstellung.qt_compat import FallbackSinger
        s = FallbackSinger("Bea", "Alt 1")
        assert s.height == 0
        assert s.singer_id == "1"


class TestQtCompatFallbackOptimizerDialog:
    """When ui.optimizer_dialog.OptimizerDialog cannot be imported,
    qt_compat must provide a FallbackOptimizerDialog."""

    def test_fallback_optimizer_dialog_module_attribute(self):
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, "FallbackOptimizerDialog"), (
            "qt_compat.FallbackOptimizerDialog is missing"
        )

    def test_fallback_optimizer_dialog_inherits_qdialog(self):
        """FallbackOptimizerDialog must be a QDialog so callers can
        call .exec()/.show() on it without crashing."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        from chormanager.choraufstellung.qt_compat import FallbackOptimizerDialog
        dlg = FallbackOptimizerDialog()
        # Must be a QDialog subclass
        from PyQt6.QtWidgets import QDialog
        assert isinstance(dlg, QDialog)

    def test_fallback_optimizer_dialog_has_title(self):
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        from chormanager.choraufstellung.qt_compat import FallbackOptimizerDialog
        dlg = FallbackOptimizerDialog()
        # The original fallback set a window title
        assert dlg.windowTitle() != ""


class TestQtCompatFallbackGridEngine:
    """When core.grid_engine.GridEngine cannot be imported, qt_compat
    must provide a FallbackGridEngine stub."""

    def test_fallback_grid_engine_module_attribute(self):
        from chormanager.choraufstellung import qt_compat
        assert hasattr(qt_compat, "FallbackGridEngine"), (
            "qt_compat.FallbackGridEngine is missing"
        )

    def test_fallback_grid_engine_constructible(self):
        from chormanager.choraufstellung.qt_compat import FallbackGridEngine
        engine = FallbackGridEngine()
        assert engine is not None


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
