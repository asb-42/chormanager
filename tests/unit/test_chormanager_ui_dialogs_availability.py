"""TDD RED: M-3 Schritt 2 — `chormanager/ui/dialogs/_availability.py`.

Verifies that ``AvailabilityDelegate`` and ``AvailabilityDialog`` (and the
``AVAILABILITY_STATUS`` constant) live in their own sub-module so that the
sub-module is the canonical location and the package re-exports work.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# --- Module-shape tests ----------------------------------------------------

class TestAvailabilitySubmoduleLayout:
    def test_availability_module_exists(self):
        p = Path("chormanager/ui/dialogs/_availability.py")
        assert p.is_file(), f"{p} is not a file"

    def test_availability_module_is_importable(self):
        from chormanager.ui.dialogs import _availability  # noqa: F401


# --- Class-identity tests --------------------------------------------------

class TestAvailabilityClassesInSubmodule:
    @pytest.mark.parametrize("class_name", ["AvailabilityDelegate", "AvailabilityDialog"])
    def test_class_lives_in_availability_submodule(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name)
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._availability", (
            f"{class_name}.__module__ is {mod_name!r}, expected "
            f"chormanager.ui.dialogs._availability"
        )

    def test_availability_status_constant_lives_in_submodule(self):
        from chormanager.ui.dialogs import _availability
        # AVAILABILITY_STATUS must be defined on the submodule
        assert hasattr(_availability, "AVAILABILITY_STATUS"), (
            "AVAILABILITY_STATUS missing from _availability module"
        )
        assert isinstance(_availability.AVAILABILITY_STATUS, list)
        assert len(_availability.AVAILABILITY_STATUS) == 6


# --- Backward-compat re-export tests --------------------------------------

class TestAvailabilityReExportsFromPackage:
    @pytest.mark.parametrize("class_name", ["AvailabilityDelegate", "AvailabilityDialog"])
    def test_re_exported_by_package_init(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name, None)
        assert cls is not None, f"{class_name} not re-exported by dialogs/"
        assert isinstance(cls, type), f"{class_name} is not a class"

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _availability
        # The package re-export must be the *same* class object as the
        # canonical one in the sub-module. This is what makes
        # ``monkeypatch.setattr("chormanager.ui.dialogs.AvailabilityDialog", ...)``
        # work in the existing test_phase*_dialogs.py suites.
        assert dialogs.AvailabilityDelegate is _availability.AvailabilityDelegate
        assert dialogs.AvailabilityDialog is _availability.AvailabilityDialog

    def test_availability_status_reexported(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _availability
        # The constant is shared (identity), not a copy
        assert dialogs.AVAILABILITY_STATUS is _availability.AVAILABILITY_STATUS


# --- Functional smoke tests -----------------------------------------------

class TestAvailabilityClassesStillWork:
    def test_availability_dialog_importable_via_submodule(self, qtbot):
        """``AvailabilityDialog`` must construct via the sub-module import path."""
        from chormanager.ui.dialogs._availability import AvailabilityDialog
        dlg = AvailabilityDialog(singer_id="s1", event_id="e1")
        qtbot.addWidget(dlg)
        assert dlg.singer_id == "s1"
        assert dlg.event_id == "e1"
        # Status combo populated
        assert dlg.status_combo.count() == 6
