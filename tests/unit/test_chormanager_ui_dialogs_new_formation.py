"""TDD RED: M-3 Schritt 9 — `chormanager/ui/dialogs/_new_formation.py`.

After extraction, the package-level re-export ``chormanager.ui.dialogs.NewFormationDialog``
must be the *same* class object as ``chormanager.ui.dialogs._new_formation.NewFormationDialog``.

These tests guard that identity contract plus the public attributes of the dialog
so that downstream monkeypatch.setattr() calls in other tests remain stable.
"""

from __future__ import annotations

import importlib

import pytest


NEW_FORMATION_PATH = "chormanager.ui.dialogs._new_formation"
PACKAGE_PATH = "chormanager.ui.dialogs"


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------

class TestModuleShape:
    def test_module_exists(self):
        try:
            importlib.import_module(NEW_FORMATION_PATH)
        except ImportError as exc:
            pytest.fail(f"{NEW_FORMATION_PATH} must be importable: {exc}")

    def test_module_exports_new_formation_dialog(self):
        mod = importlib.import_module(NEW_FORMATION_PATH)
        assert hasattr(mod, "NewFormationDialog"), (
            f"{NEW_FORMATION_PATH}.NewFormationDialog must exist"
        )


# ---------------------------------------------------------------------------
# Class identity re-export
# ---------------------------------------------------------------------------

class TestReExportIdentity:
    def test_package_level_is_same_class(self):
        pkg = importlib.import_module(PACKAGE_PATH)
        sub = importlib.import_module(NEW_FORMATION_PATH)
        assert pkg.NewFormationDialog is sub.NewFormationDialog, (
            "chormanager.ui.dialogs.NewFormationDialog must be the *same* "
            "class object as chormanager.ui.dialogs._new_formation.NewFormationDialog"
        )

    def test_module_attribute_is_set(self):
        sub = importlib.import_module(NEW_FORMATION_PATH)
        assert sub.NewFormationDialog.__module__ == NEW_FORMATION_PATH, (
            f"NewFormationDialog.__module__ must be {NEW_FORMATION_PATH!r}, "
            f"got {sub.NewFormationDialog.__module__!r}"
        )

    def test_class_subclass_of_qdialog(self):
        from PyQt5.QtWidgets import QDialog  # type: ignore
        from PyQt6.QtWidgets import QDialog as QDialog6
        sub = importlib.import_module(NEW_FORMATION_PATH)
        assert issubclass(sub.NewFormationDialog, (QDialog, QDialog6)), (
            "NewFormationDialog must subclass QDialog"
        )


# ---------------------------------------------------------------------------
# Constructor / attribute smoke tests
# ---------------------------------------------------------------------------

class TestNewFormationDialogShape:
    def test_construct_with_stub_db(self, qtbot, tmp_path):
        """The dialog must construct with just a database and have a window title."""
        from chormanager.data.database import Database
        db = Database(str(tmp_path / "schema.db"))
        db.connect()
        db.create_tables()
        try:
            from chormanager.ui.dialogs import NewFormationDialog
            dlg = NewFormationDialog(db=db)
            qtbot.addWidget(dlg)
            assert dlg.windowTitle() == "Neue Choraufstellung"
            assert dlg.minimumWidth() == 400
            assert dlg.selected_event is None
            assert dlg.get_event() is None
        finally:
            db.close()

    def test_has_project_and_event_combos(self, qtbot, tmp_path):
        from chormanager.data.database import Database
        db = Database(str(tmp_path / "schema.db"))
        db.connect()
        db.create_tables()
        try:
            from chormanager.ui.dialogs import NewFormationDialog
            dlg = NewFormationDialog(db=db)
            qtbot.addWidget(dlg)
            assert hasattr(dlg, "project_combo")
            assert hasattr(dlg, "event_combo")
            assert hasattr(dlg, "info_label")
        finally:
            db.close()
