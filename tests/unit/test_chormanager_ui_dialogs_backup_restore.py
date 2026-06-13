"""TDD RED: M-3 Schritt 8 — `chormanager/ui/dialogs/_backup_restore.py`.

Verifies that ``DropZone`` + ``BackupRestoreDialog`` live in their own
sub-module so the package stays slim. ``DropZone`` is a small drag-and-drop
widget (42 LOC); ``BackupRestoreDialog`` is the larger backup/restore UI
(155 LOC). Per the M-3 plan, both are extracted together because of their
tight coupling via ``BackupRestoreDialog._on_file_dropped``.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestBackupRestoreSubmoduleLayout:
    def test_module_exists(self):
        p = Path("chormanager/ui/dialogs/_backup_restore.py")
        assert p.is_file(), f"{p} is not a file"

    def test_module_is_importable(self):
        from chormanager.ui.dialogs import _backup_restore  # noqa: F401


class TestDropZoneAndBackupRestoreDialogInSubmodule:
    @pytest.mark.parametrize("class_name", ["DropZone", "BackupRestoreDialog"])
    def test_class_lives_in_backup_restore_submodule(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name)
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._backup_restore", (
            f"{class_name}.__module__ is {mod_name!r}, expected "
            f"chormanager.ui.dialogs._backup_restore"
        )


class TestBackupRestoreReExportsFromPackage:
    @pytest.mark.parametrize("class_name", ["DropZone", "BackupRestoreDialog"])
    def test_re_exported_by_package_init(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name, None)
        assert cls is not None
        assert isinstance(cls, type)

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _backup_restore
        assert dialogs.DropZone is _backup_restore.DropZone
        assert dialogs.BackupRestoreDialog is _backup_restore.BackupRestoreDialog


class TestBackupRestoreClassesStillWork:
    def test_drop_zone_is_subclass_of_qframe(self):
        from chormanager.ui.dialogs._backup_restore import DropZone
        from PyQt6.QtWidgets import QFrame
        assert issubclass(DropZone, QFrame)

    def test_backup_restore_dialog_is_subclass_of_qdialog(self):
        from chormanager.ui.dialogs._backup_restore import BackupRestoreDialog
        from PyQt6.QtWidgets import QDialog
        assert issubclass(BackupRestoreDialog, QDialog)

    def test_construct_backup_restore_dialog(self, qtbot):
        from chormanager.ui.dialogs._backup_restore import BackupRestoreDialog
        dlg = BackupRestoreDialog(parent=None)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle()
