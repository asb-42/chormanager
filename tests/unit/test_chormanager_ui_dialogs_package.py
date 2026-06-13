"""TDD RED: M-3 Schritt 1 — `chormanager/ui/dialogs/`-Package-Skelett.

Verifies that:
1. The old import path `from chormanager.ui.dialogs import X` still works
2. The new import path `from chormanager.ui.dialogs._event import X` works
3. All 12 dialog classes are importable via the package
4. `dialogs.py` (single file) no longer exists; `dialogs/__init__.py` does
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

import pytest


# The 12 dialog class names that must be importable after M-3
EXPECTED_CLASSES: List[str] = [
    "AvailabilityDelegate",
    "AvailabilityDialog",
    "EventDialog",
    "EventListDialog",
    "EventAvailabilityDialog",
    "ConfigDialog",
    "SelbstdarstellungDialog",
    "SingerSelectionDialog",
    "DropZone",
    "BackupRestoreDialog",
    "NewFormationDialog",
    "RepertoireDialog",
]


class TestDialogsPackageLayout:
    def test_dialogs_directory_exists(self):
        p = Path("chormanager/ui/dialogs")
        assert p.is_dir(), f"{p} is not a directory"

    def test_dialogs_init_module_exists(self):
        p = Path("chormanager/ui/dialogs/__init__.py")
        assert p.is_file(), f"{p} is not a file"

    def test_legacy_dialogs_file_does_not_exist(self):
        p = Path("chormanager/ui/dialogs.py")
        assert not p.exists(), f"{p} still exists (should have been moved)"


class TestDialogsReExports:
    @pytest.mark.parametrize("class_name", EXPECTED_CLASSES)
    def test_class_importable_from_package(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name, None)
        assert cls is not None, f"{class_name} not re-exported by dialogs/"
        # The class must be a real class (not a function or sentinel)
        assert isinstance(cls, type), f"{class_name} is not a class"


class TestDialogsReExportIdentity:
    """Re-exports must be the *same* class as the one in the sub-module.

    This is what makes ``monkeypatch.setattr("chormanager.ui.dialogs.X", ...)``
    in the existing test_phase{2,3,4}_*_dialogs.py work: Python resolves
    the dotted path dynamically so both names point to the same object.
    """

    @pytest.mark.parametrize("class_name", [
        "EventDialog", "ConfigDialog", "BackupRestoreDialog",
        "SingerSelectionDialog", "NewFormationDialog", "RepertoireDialog",
        "EventAvailabilityDialog", "SelbstdarstellungDialog",
    ])
    def test_re_export_is_same_object(self, class_name: str):
        from chormanager.ui import dialogs
        # Try to find the sub-module that owns this class by introspection
        # We walk the re-export's __module__ attribute.
        cls = getattr(dialogs, class_name)
        mod_name = cls.__module__
        # The class's __module__ must point to chormanager.ui.dialogs.*
        assert mod_name.startswith("chormanager.ui.dialogs."), (
            f"{class_name}.__module__ is {mod_name!r}, expected "
            "chormanager.ui.dialogs.<sub>"
        )


class TestAllExpectedClassesPresent:
    def test_all_twelve_classes_present(self):
        from chormanager.ui import dialogs
        for name in EXPECTED_CLASSES:
            assert hasattr(dialogs, name), f"missing: {name}"
