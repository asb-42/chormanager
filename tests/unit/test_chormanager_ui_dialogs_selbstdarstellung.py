"""TDD RED: M-3 Schritt 6 — `chormanager/ui/dialogs/_selbstdarstellung.py`.

Verifies that ``SelbstdarstellungDialog`` lives in its own sub-module
so the package stays slim.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestSelbstdarstellungSubmoduleLayout:
    def test_module_exists(self):
        p = Path("chormanager/ui/dialogs/_selbstdarstellung.py")
        assert p.is_file(), f"{p} is not a file"

    def test_module_is_importable(self):
        from chormanager.ui.dialogs import _selbstdarstellung  # noqa: F401


class TestSelbstdarstellungDialogInSubmodule:
    def test_class_lives_in_selbstdarstellung_submodule(self):
        from chormanager.ui import dialogs
        cls = dialogs.SelbstdarstellungDialog
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._selbstdarstellung"


class TestSelbstdarstellungReExportsFromPackage:
    def test_re_exported_by_package_init(self):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, "SelbstdarstellungDialog", None)
        assert cls is not None
        assert isinstance(cls, type)

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _selbstdarstellung
        assert dialogs.SelbstdarstellungDialog is _selbstdarstellung.SelbstdarstellungDialog


class TestSelbstdarstellungDialogStillWorks:
    def test_class_is_subclass_of_qdialog(self):
        from chormanager.ui.dialogs._selbstdarstellung import SelbstdarstellungDialog
        from PyQt6.QtWidgets import QDialog
        assert issubclass(SelbstdarstellungDialog, QDialog)

    def test_construct_with_stub_db(self, qtbot):
        from chormanager.ui.dialogs._selbstdarstellung import SelbstdarstellungDialog
        dlg = SelbstdarstellungDialog(db=MagicMock(), parent=None)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle()
