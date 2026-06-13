"""TDD RED: M-3 Schritt 4 — `chormanager/ui/dialogs/_event_availability.py`.

Verifies that ``EventAvailabilityDialog`` lives in its own sub-module so
the package stays slim. This is the largest dialog (591 LOC) with PDF
export, CSV/HTML export, and complex per-singer availability editing.

The class is the back-end of the "Verfügbarkeit" tab in MainWindow and
has the most existing test coverage (``test_phase4_event_availability.py``,
20+ tests). The TDD strategy here is:

1. Module-shape tests (file exists, importable)
2. Class-identity test (EventAvailabilityDialog.__module__ check)
3. Backward-compat re-export tests
4. Smoke test: minimal construction with stub DB and Event

The heavy lifting (PDF export, CSV export, accept/save) is already
covered by the existing ``test_phase4_*`` tests — we just need to make
sure the extraction doesn't break them.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- Module-shape tests ----------------------------------------------------

class TestEventAvailabilitySubmoduleLayout:
    def test_module_exists(self):
        p = Path("chormanager/ui/dialogs/_event_availability.py")
        assert p.is_file(), f"{p} is not a file"

    def test_module_is_importable(self):
        from chormanager.ui.dialogs import _event_availability  # noqa: F401


# --- Class-identity tests --------------------------------------------------

class TestEventAvailabilityDialogInSubmodule:
    def test_class_lives_in_event_availability_submodule(self):
        from chormanager.ui import dialogs
        cls = dialogs.EventAvailabilityDialog
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._event_availability", (
            f"EventAvailabilityDialog.__module__ is {mod_name!r}, expected "
            f"chormanager.ui.dialogs._event_availability"
        )


# --- Backward-compat re-export tests --------------------------------------

class TestEventAvailabilityReExportsFromPackage:
    def test_re_exported_by_package_init(self):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, "EventAvailabilityDialog", None)
        assert cls is not None, "EventAvailabilityDialog not re-exported by dialogs/"
        assert isinstance(cls, type)

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _event_availability
        # Identity check: re-exports point to the same class object.
        assert dialogs.EventAvailabilityDialog is _event_availability.EventAvailabilityDialog


# --- Functional smoke tests -----------------------------------------------

class _FakeEvent:
    """Minimal stand-in for the Event dataclass."""
    def __init__(self, name="Probetermin", event_id="evt-1", date="2026-01-01"):
        self.name = name
        self.id = event_id
        self.date = date


class _FakeSinger:
    def __init__(self, singer_id="s1", name="Doe, Jane", vg="Sopran"):
        self.id = singer_id
        self.name = name
        self.voice_group = vg
        self.short_name = "DoeJ"
        self.full_name = "Jane Doe"
        self.height = 170
        self.voice_groups = [vg]


class _FakeAvailRepo:
    def __init__(self, *args, **kwargs):
        self._data = {}

    def get_for_event(self, event_id):
        return {}

    def update(self, *args, **kwargs):
        pass


class _FakeSingerRepo:
    def __init__(self, *args, **kwargs):
        self._singers = [_FakeSinger()]

    def get_active(self):
        return self._singers


class TestEventAvailabilityDialogStillWorks:
    def test_import_via_submodule(self):
        """``EventAvailabilityDialog`` must be importable via the sub-module path."""
        from chormanager.ui.dialogs._event_availability import EventAvailabilityDialog
        assert EventAvailabilityDialog is not None
        assert EventAvailabilityDialog.__name__ == "EventAvailabilityDialog"

    def test_class_is_subclass_of_qdialog(self):
        """``EventAvailabilityDialog`` must be a QDialog subclass."""
        from chormanager.ui.dialogs._event_availability import EventAvailabilityDialog
        from PyQt6.QtWidgets import QDialog
        assert issubclass(EventAvailabilityDialog, QDialog)
