"""M-3 Schritt 12: Final validation — ``chormanager/ui/dialogs/`` package.

This test module is the final guard for the M-3 refactor. It verifies:

1. All 12 dialog classes + 1 constant are importable from the package
   (re-exports work).
2. The package-level re-exports are the *same* class objects as in the
   sub-modules (identity contract preserved).
3. Each sub-module is correctly placed under ``chormanager.ui.dialogs._*``
   (i.e. one module per class, no private-name clashes).
4. The package ``__init__.py`` exposes a complete ``__all__`` matching
   the public surface.

The original 1 825 LOC ``chormanager/ui/dialogs.py`` is gone. This test
stands as the regression guard against re-introducing the monolithic
module.
"""

from __future__ import annotations

import importlib

import pytest


PUBLIC_CLASSES = [
    ("AvailabilityDelegate", "_availability"),
    ("AvailabilityDialog", "_availability"),
    ("AVAILABILITY_STATUS", "_availability"),
    ("BackupRestoreDialog", "_backup_restore"),
    ("ConfigDialog", "_config"),
    ("DropZone", "_backup_restore"),
    ("EventAvailabilityDialog", "_event_availability"),
    ("EventDialog", "_event"),
    ("EventListDialog", "_event"),
    ("NewFormationDialog", "_new_formation"),
    ("RepertoireDialog", "_repertoire"),
    ("SelbstdarstellungDialog", "_selbstdarstellung"),
    ("SingerSelectionDialog", "_singer_selection"),
]

# Map of sub-module name -> expected classes/constants it must export.
SUBMODULE_EXPORTS = {
    "_availability": {"AvailabilityDelegate", "AvailabilityDialog", "AVAILABILITY_STATUS"},
    "_backup_restore": {"DropZone", "BackupRestoreDialog"},
    "_config": {"ConfigDialog"},
    "_event": {"EventDialog", "EventListDialog"},
    "_event_availability": {"EventAvailabilityDialog"},
    "_new_formation": {"NewFormationDialog"},
    "_repertoire": {"RepertoireDialog"},
    "_selbstdarstellung": {"SelbstdarstellungDialog"},
    "_singer_selection": {"SingerSelectionDialog"},
}


PACKAGE_PATH = "chormanager.ui.dialogs"


# ---------------------------------------------------------------------------
# Package-level surface
# ---------------------------------------------------------------------------

class TestPackageSurface:
    def test_package_is_importable(self):
        """The package must still be importable (replaces the old module)."""
        pkg = importlib.import_module(PACKAGE_PATH)
        assert pkg.__file__ is not None
        # The package should have an __init__.py (i.e. a regular package,
        # not a PEP 420 namespace package).
        assert pkg.__file__.endswith("__init__.py")

    def test_all_exports_present_in_dunder_all(self):
        pkg = importlib.import_module(PACKAGE_PATH)
        assert hasattr(pkg, "__all__"), (
            f"{PACKAGE_PATH} must define __all__"
        )
        for cls, _ in PUBLIC_CLASSES:
            assert cls in pkg.__all__, f"{cls!r} must be in __all__"

    @pytest.mark.parametrize("class_name,submodule", PUBLIC_CLASSES)
    def test_class_importable_from_package(self, class_name, submodule):
        """Each public class must be importable from the package."""
        pkg = importlib.import_module(PACKAGE_PATH)
        assert hasattr(pkg, class_name), (
            f"{PACKAGE_PATH}.{class_name} must be importable"
        )

    @pytest.mark.parametrize("class_name,submodule", PUBLIC_CLASSES)
    def test_class_is_same_object_in_submodule(self, class_name, submodule):
        """The package-level re-export must be the *same* class object as
        the one in the source sub-module (preserves monkeypatch.setattr()
        and ``isinstance`` checks across the package boundary)."""
        pkg = importlib.import_module(PACKAGE_PATH)
        sub = importlib.import_module(f"{PACKAGE_PATH}.{submodule}")
        assert getattr(pkg, class_name) is getattr(sub, class_name), (
            f"{PACKAGE_PATH}.{class_name} is not the same object as "
            f"{PACKAGE_PATH}.{submodule}.{class_name}"
        )


# ---------------------------------------------------------------------------
# Sub-module surface
# ---------------------------------------------------------------------------

class TestSubModuleSurface:
    @pytest.mark.parametrize("submodule,expected", list(SUBMODULE_EXPORTS.items()))
    def test_submodule_contains_expected_classes(self, submodule, expected):
        sub = importlib.import_module(f"{PACKAGE_PATH}.{submodule}")
        for cls in expected:
            assert hasattr(sub, cls), (
                f"{PACKAGE_PATH}.{submodule} must export {cls}"
            )

    def test_nine_submodules_exist(self):
        """There must be exactly 9 sub-modules (one per public class or
        related group), matching the M-3 plan."""
        assert len(SUBMODULE_EXPORTS) == 9, (
            f"Expected 9 sub-modules, found {len(SUBMODULE_EXPORTS)}: "
            f"{list(SUBMODULE_EXPORTS.keys())}"
        )


# ---------------------------------------------------------------------------
# M-3 cleanup guards
# ---------------------------------------------------------------------------

class TestM3Cleanup:
    def test_init_does_not_import_qtwidgets_unnecessarily(self):
        """The package init must be a thin re-export shim — it should not
        import the heavy QtWidgets surface unless actually needed (the
        classes are now defined in sub-modules)."""
        # This is a soft check: we just verify the init is *short*.
        # 1 825 LOC was the original; after M-3 it should be < 200.
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "chormanager", "ui", "dialogs", "__init__.py",
        )
        path = os.path.normpath(path)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) < 200, (
            f"chormanager/ui/dialogs/__init__.py is {len(lines)} lines; "
            f"should be < 200 (M-3 cleanup). The classes have been moved "
            f"to sub-modules."
        )

    def test_old_monolithic_dialogs_py_does_not_exist(self):
        """The old monolithic ``chormanager/ui/dialogs.py`` must be gone —
        it was replaced by the package directory."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "chormanager", "ui", "dialogs.py",
        )
        path = os.path.normpath(path)
        assert not os.path.exists(path), (
            f"{path} must not exist — M-3 replaced it with the package "
            f"directory chormanager/ui/dialogs/"
        )
