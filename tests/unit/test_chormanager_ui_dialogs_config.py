"""TDD RED: M-3 Schritt 5 — `chormanager/ui/dialogs/_config.py`.

Verifies that ``ConfigDialog`` lives in its own sub-module so the
package stays slim and ``from chormanager.ui.dialogs import ConfigDialog``
still works (back-compat).
"""
from __future__ import annotations

from pathlib import Path

import pytest


# --- Module-shape tests ----------------------------------------------------

class TestConfigSubmoduleLayout:
    def test_config_module_exists(self):
        p = Path("chormanager/ui/dialogs/_config.py")
        assert p.is_file(), f"{p} is not a file"

    def test_config_module_is_importable(self):
        from chormanager.ui.dialogs import _config  # noqa: F401


# --- Class-identity tests --------------------------------------------------

class TestConfigDialogInSubmodule:
    def test_class_lives_in_config_submodule(self):
        from chormanager.ui import dialogs
        cls = dialogs.ConfigDialog
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._config", (
            f"ConfigDialog.__module__ is {mod_name!r}, expected "
            f"chormanager.ui.dialogs._config"
        )


# --- Backward-compat re-export tests --------------------------------------

class TestConfigReExportsFromPackage:
    def test_re_exported_by_package_init(self):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, "ConfigDialog", None)
        assert cls is not None
        assert isinstance(cls, type)

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _config
        assert dialogs.ConfigDialog is _config.ConfigDialog


# --- Functional smoke tests -----------------------------------------------

class TestConfigDialogStillWorks:
    def test_class_is_subclass_of_qdialog(self):
        from chormanager.ui.dialogs._config import ConfigDialog
        from PyQt6.QtWidgets import QDialog
        assert issubclass(ConfigDialog, QDialog)

    def test_construct_with_stub_db(self, qtbot):
        """``ConfigDialog`` must construct via the sub-module import path."""
        from chormanager.ui.dialogs._config import ConfigDialog
        from unittest.mock import MagicMock
        dlg = ConfigDialog(db=MagicMock(), parent=None)
        qtbot.addWidget(dlg)
        # Window title set in _setup_ui
        assert dlg.windowTitle()
