"""TDD RED: M-3 Schritt 10 — `chormanager/ui/dialogs/_repertoire.py`.

After extraction, the package-level re-export
``chormanager.ui.dialogs.RepertoireDialog`` must be the *same* class object as
``chormanager.ui.dialogs._repertoire.RepertoireDialog``.

These tests guard that identity contract plus the public attributes of the
dialog so that downstream monkeypatch.setattr() calls in other tests remain
stable.
"""

from __future__ import annotations

import importlib

import pytest


REPERTOIRE_PATH = "chormanager.ui.dialogs._repertoire"
PACKAGE_PATH = "chormanager.ui.dialogs"


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------

class TestModuleShape:
    def test_module_exists(self):
        try:
            importlib.import_module(REPERTOIRE_PATH)
        except ImportError as exc:
            pytest.fail(f"{REPERTOIRE_PATH} must be importable: {exc}")

    def test_module_exports_repertoire_dialog(self):
        mod = importlib.import_module(REPERTOIRE_PATH)
        assert hasattr(mod, "RepertoireDialog"), (
            f"{REPERTOIRE_PATH}.RepertoireDialog must exist"
        )


# ---------------------------------------------------------------------------
# Class identity re-export
# ---------------------------------------------------------------------------

class TestReExportIdentity:
    def test_package_level_is_same_class(self):
        pkg = importlib.import_module(PACKAGE_PATH)
        sub = importlib.import_module(REPERTOIRE_PATH)
        assert pkg.RepertoireDialog is sub.RepertoireDialog, (
            "chormanager.ui.dialogs.RepertoireDialog must be the *same* "
            "class object as chormanager.ui.dialogs._repertoire.RepertoireDialog"
        )

    def test_module_attribute_is_set(self):
        sub = importlib.import_module(REPERTOIRE_PATH)
        assert sub.RepertoireDialog.__module__ == REPERTOIRE_PATH, (
            f"RepertoireDialog.__module__ must be {REPERTOIRE_PATH!r}, "
            f"got {sub.RepertoireDialog.__module__!r}"
        )

    def test_class_subclass_of_qdialog(self):
        from PyQt5.QtWidgets import QDialog  # type: ignore
        from PyQt6.QtWidgets import QDialog as QDialog6
        sub = importlib.import_module(REPERTOIRE_PATH)
        assert issubclass(sub.RepertoireDialog, (QDialog, QDialog6)), (
            "RepertoireDialog must subclass QDialog"
        )


# ---------------------------------------------------------------------------
# Constructor / attribute smoke tests
# ---------------------------------------------------------------------------

class TestRepertoireDialogShape:
    def test_construct_new_repertoire(self, qtbot, tmp_path):
        """The dialog must construct with a database and have the right window title."""
        from chormanager.data.database import Database
        db = Database(str(tmp_path / "schema.db"))
        db.connect()
        db.create_tables()
        try:
            from chormanager.ui.dialogs import RepertoireDialog
            dlg = RepertoireDialog(db=db)
            qtbot.addWidget(dlg)
            assert dlg.windowTitle() == "Neues Repertoire"
            assert dlg.minimumWidth() == 400
        finally:
            db.close()

    def test_has_all_input_fields(self, qtbot, tmp_path):
        from chormanager.data.database import Database
        db = Database(str(tmp_path / "schema.db"))
        db.connect()
        db.create_tables()
        try:
            from chormanager.ui.dialogs import RepertoireDialog
            dlg = RepertoireDialog(db=db)
            qtbot.addWidget(dlg)
            assert hasattr(dlg, "composer_input")
            assert hasattr(dlg, "title_input")
            assert hasattr(dlg, "dates_input")
            assert hasattr(dlg, "country_input")
            assert hasattr(dlg, "publisher_input")
            assert hasattr(dlg, "arrangement_input")
            assert hasattr(dlg, "location_input")
            assert hasattr(dlg, "program_combo")
        finally:
            db.close()
