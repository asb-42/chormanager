"""TDD RED: M-3 Schritt 7 — `chormanager/ui/dialogs/_singer_selection.py`.

Verifies that ``SingerSelectionDialog`` lives in its own sub-module
so the package stays slim. This class has 9 methods including
``_export_singers`` (94 LOC) which uses the ExportService.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestSingerSelectionSubmoduleLayout:
    def test_module_exists(self):
        p = Path("chormanager/ui/dialogs/_singer_selection.py")
        assert p.is_file(), f"{p} is not a file"

    def test_module_is_importable(self):
        from chormanager.ui.dialogs import _singer_selection  # noqa: F401


class TestSingerSelectionDialogInSubmodule:
    def test_class_lives_in_singer_selection_submodule(self):
        from chormanager.ui import dialogs
        cls = dialogs.SingerSelectionDialog
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._singer_selection"


class TestSingerSelectionReExportsFromPackage:
    def test_re_exported_by_package_init(self):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, "SingerSelectionDialog", None)
        assert cls is not None
        assert isinstance(cls, type)

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _singer_selection
        assert dialogs.SingerSelectionDialog is _singer_selection.SingerSelectionDialog


class TestSingerSelectionDialogStillWorks:
    def test_class_is_subclass_of_qdialog(self):
        from chormanager.ui.dialogs._singer_selection import SingerSelectionDialog
        from PyQt6.QtWidgets import QDialog
        assert issubclass(SingerSelectionDialog, QDialog)

    def test_construct_with_stub_db(self, qtbot):
        from chormanager.ui.dialogs._singer_selection import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=MagicMock(), parent=None)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle()

    def test_get_selected_ids_returns_empty_list_by_default(self, qtbot):
        """``get_selected_ids()`` must return a list (possibly empty)."""
        from chormanager.ui.dialogs._singer_selection import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=MagicMock(), parent=None)
        qtbot.addWidget(dlg)
        ids = dlg.get_selected_ids()
        assert isinstance(ids, list)
