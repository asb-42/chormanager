"""TDD RED: M-3 Schritt 3 — `chormanager/ui/dialogs/_event.py`.

Verifies that ``EventDialog`` and ``EventListDialog`` live in their own
sub-module so the package stays slim and the existing
``test_phase2_dialogs.py``/``test_event_list_dialog_dropdown.py`` tests
keep working via the package re-exports.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


# --- Module-shape tests ----------------------------------------------------

class TestEventSubmoduleLayout:
    def test_event_module_exists(self):
        p = Path("chormanager/ui/dialogs/_event.py")
        assert p.is_file(), f"{p} is not a file"

    def test_event_module_is_importable(self):
        from chormanager.ui.dialogs import _event  # noqa: F401


# --- Class-identity tests --------------------------------------------------

class TestEventClassesInSubmodule:
    @pytest.mark.parametrize("class_name", ["EventDialog", "EventListDialog"])
    def test_class_lives_in_event_submodule(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name)
        mod_name = cls.__module__
        assert mod_name == "chormanager.ui.dialogs._event", (
            f"{class_name}.__module__ is {mod_name!r}, expected "
            f"chormanager.ui.dialogs._event"
        )


# --- Backward-compat re-export tests --------------------------------------

class TestEventReExportsFromPackage:
    @pytest.mark.parametrize("class_name", ["EventDialog", "EventListDialog"])
    def test_re_exported_by_package_init(self, class_name: str):
        from chormanager.ui import dialogs
        cls = getattr(dialogs, class_name, None)
        assert cls is not None, f"{class_name} not re-exported by dialogs/"
        assert isinstance(cls, type), f"{class_name} is not a class"

    def test_re_export_is_same_object_as_submodule(self):
        from chormanager.ui import dialogs
        from chormanager.ui.dialogs import _event
        # Identity check: re-exports point to the same class objects.
        assert dialogs.EventDialog is _event.EventDialog
        assert dialogs.EventListDialog is _event.EventListDialog


# --- Functional smoke tests -----------------------------------------------

class _FakeDb:
    """Stand-in for ``Database`` that returns no events/singers."""
    def execute(self, *args, **kwargs):
        class _Cur:
            description = []
            def fetchall(self_inner):
                return []
        return _Cur()


class _EmptyRepo:
    def __init__(self, *args, **kwargs):
        pass
    def get_all(self):
        return []


class TestEventClassesStillWork:
    def test_event_list_dialog_importable_via_submodule(self, qtbot):
        """``EventListDialog`` must construct via the sub-module import path.

        ``EventListDialog`` lazily imports ``EventRepository`` inside
        ``_load_events``, so we patch the source module
        ``chormanager.domain.repository``.
        """
        from chormanager.ui.dialogs._event import EventListDialog
        with patch(
            "chormanager.domain.repository.EventRepository", _EmptyRepo
        ):
            dlg = EventListDialog(db=_FakeDb(), parent=None)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle()  # title set in _setup_ui

    def test_event_dialog_importable_via_submodule(self, qtbot):
        """``EventDialog`` (with no event) must construct via the sub-module path.

        ``EventDialog`` lazily imports ``ProjectRepository`` inside
        ``_setup_ui``, so we patch the source module
        ``chormanager.domain.repository``.
        """
        from chormanager.ui.dialogs._event import EventDialog
        with patch(
            "chormanager.domain.repository.ProjectRepository", _EmptyRepo
        ):
            dlg = EventDialog(event=None, db=None, parent=None)
        qtbot.addWidget(dlg)
        # Window title when no event: "Termin hinzufügen"
        assert "Termin hinzufügen" in dlg.windowTitle()
