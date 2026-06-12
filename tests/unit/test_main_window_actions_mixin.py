# TDD RED: Regression tests for M-1 Schritt 8 — MainWindowActionsMixin.
#
# The wrapper/handler methods on ``MainWindow`` that bridge the menu
# actions to the underlying tab widgets move into
# ``chormanager.ui.main_window_actions.MainWindowActionsMixin``:
#
#   * Singer:   _add_singer, _edit_singer, _delete_singer
#   * Event:    _edit_event, _delete_event, _duplicate_event,
#               _manage_availability, _list_events, _new_event
#   * Project:  _new_projekt, _edit_project, _delete_project,
#               _duplicate_project, _save_projekt, _open_projekt
#
# All of these are short, simple wrappers (or one-screen dialog
# handlers). The Mixin must be inherited by ``MainWindow`` and the
# methods must be defined in the Mixin.

from __future__ import annotations

import importlib
from typing import Iterator

import pytest


# ---------------------------------------------------------------------------
# 1. The Mixin exists and exposes all the methods.
# ---------------------------------------------------------------------------

EXPECTED_METHODS = (
    # Singer
    "_add_singer",
    "_edit_singer",
    "_delete_singer",
    # Event
    "_edit_event",
    "_delete_event",
    "_duplicate_event",
    "_manage_availability",
    "_list_events",
    "_new_event",
    # Project
    "_new_projekt",
    "_edit_project",
    "_delete_project",
    "_duplicate_project",
    "_save_projekt",
    "_open_projekt",
)


class TestMainWindowActionsMixinExists:
    def test_module_exists(self):
        mod = importlib.import_module("chormanager.ui.main_window_actions")
        assert mod is not None

    def test_mixin_exported(self):
        mod = importlib.import_module("chormanager.ui.main_window_actions")
        assert hasattr(mod, "MainWindowActionsMixin"), (
            "MainWindowActionsMixin must be exported from "
            "chormanager.ui.main_window_actions"
        )

    def test_mixin_has_all_methods(self):
        from chormanager.ui.main_window_actions import (
            MainWindowActionsMixin,
        )
        for name in EXPECTED_METHODS:
            assert hasattr(MainWindowActionsMixin, name), (
                f"MainWindowActionsMixin is missing {name}"
            )


# ---------------------------------------------------------------------------
# 2. MainWindow inherits the Mixin.
# ---------------------------------------------------------------------------

class TestMainWindowInheritsActionsMixin:
    def test_main_window_inherits(self):
        from chormanager.ui.main_window import MainWindow
        from chormanager.ui.main_window_actions import (
            MainWindowActionsMixin,
        )
        assert issubclass(MainWindow, MainWindowActionsMixin)


# ---------------------------------------------------------------------------
# 3. All methods *defined* in the Mixin (not duplicated in main_window).
# ---------------------------------------------------------------------------

class TestMethodsMovedToMixin:
    def _qualname(self, name):
        from chormanager.ui.main_window_actions import (
            MainWindowActionsMixin,
        )
        return getattr(MainWindowActionsMixin, name).__qualname__

    @pytest.mark.parametrize("name", EXPECTED_METHODS)
    def test_method_defined_in_mixin(self, name):
        qual = self._qualname(name)
        assert qual.startswith("MainWindowActionsMixin."), (
            f"{name} defined in {qual!r}, expected MainWindowActionsMixin"
        )


# ---------------------------------------------------------------------------
# 4. Behavioural tests with a stub.
# ---------------------------------------------------------------------------

class _StubTab:
    """Stand-in for a tab: each test sets the method it expects
    to be called, then we assert it was called."""

    def __init__(self) -> None:
        self.calls = []


@pytest.fixture
def stub_window() -> Iterator[object]:
    from chormanager.ui.main_window_actions import (
        MainWindowActionsMixin,
    )

    class W(MainWindowActionsMixin):
        def __init__(self_inner) -> None:
            self_inner.singers_tab = _StubTab()
            self_inner.events_tab = _StubTab()
            self_inner.projects_tab = _StubTab()
            self_inner.db = object()
            self_inner.db_path = "/tmp/test-chor.db"
            self_inner.current_project = None
            self_inner.calls = []

    yield W()


class TestSingerWrappers:
    def test_add_singer_delegates(self, stub_window):
        stub_window.singers_tab._add_singer = lambda: stub_window.singers_tab.calls.append("add")
        stub_window._add_singer()
        assert stub_window.singers_tab.calls == ["add"]

    def test_edit_singer_delegates(self, stub_window):
        stub_window.singers_tab._edit_singer = lambda: stub_window.singers_tab.calls.append("edit")
        stub_window._edit_singer()
        assert stub_window.singers_tab.calls == ["edit"]

    def test_delete_singer_delegates(self, stub_window):
        stub_window.singers_tab._delete_singer = lambda: stub_window.singers_tab.calls.append("del")
        stub_window._delete_singer()
        assert stub_window.singers_tab.calls == ["del"]


class TestEventWrappers:
    def test_edit_event_delegates(self, stub_window):
        stub_window.events_tab._edit_event = lambda: stub_window.events_tab.calls.append("edit")
        stub_window._edit_event()
        assert stub_window.events_tab.calls == ["edit"]

    def test_delete_event_delegates(self, stub_window):
        stub_window.events_tab._delete_event = lambda: stub_window.events_tab.calls.append("del")
        stub_window._delete_event()
        assert stub_window.events_tab.calls == ["del"]

    def test_duplicate_event_delegates(self, stub_window):
        stub_window.events_tab._duplicate_event = lambda: stub_window.events_tab.calls.append("dup")
        stub_window._duplicate_event()
        assert stub_window.events_tab.calls == ["dup"]

    def test_manage_availability_delegates(self, stub_window):
        stub_window.events_tab._manage_availability = lambda: stub_window.events_tab.calls.append("avail")
        stub_window._manage_availability()
        assert stub_window.events_tab.calls == ["avail"]


class TestProjectWrappers:
    def test_edit_project_delegates(self, stub_window):
        stub_window.projects_tab._edit_project = lambda: stub_window.projects_tab.calls.append("edit")
        stub_window._edit_project()
        assert stub_window.projects_tab.calls == ["edit"]

    def test_delete_project_delegates(self, stub_window):
        stub_window.projects_tab._delete_project = lambda: stub_window.projects_tab.calls.append("del")
        stub_window._delete_project()
        assert stub_window.projects_tab.calls == ["del"]

    def test_duplicate_project_delegates(self, stub_window):
        stub_window.projects_tab._duplicate_project = lambda: stub_window.projects_tab.calls.append("dup")
        stub_window._duplicate_project()
        assert stub_window.projects_tab.calls == ["dup"]


class TestNewEventWiring:
    """The ``_new_event`` method is more than a wrapper: it opens
    the EventDialog, validates the name, creates a record and
    refreshes the projects/events tabs. We patch all of those and
    assert the orchestration works."""

    def test_new_event_calls_repo_and_refreshes(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QDialog

        captured = {}

        # Mock EventDialog
        class _FakeDlg:
            def __init__(self, db, parent, prefilled_project_id=None):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def get_data(self):
                return {"name": "Probe"}

        # EventDialog is imported locally inside ``_new_event`` via
        # ``from .dialogs import EventDialog``. We must patch the symbol
        # at its source module (``chormanager.ui.dialogs``) so that the
        # local import resolves to our fake at call time.
        monkeypatch.setattr(
            "chormanager.ui.dialogs.EventDialog",
            _FakeDlg,
        )

        # Mock EventRepository
        class _FakeRepo:
            def __init__(self, db):
                captured["db"] = db

            def create(self, **kw):
                captured["created"] = kw

        monkeypatch.setattr(
            "chormanager.domain.repository.EventRepository",
            _FakeRepo,
        )

        # Mock QMessageBox
        from PyQt6.QtWidgets import QMessageBox

        monkeypatch.setattr(
            QMessageBox, "warning",
            staticmethod(lambda *a, **kw: None),
        )

        stub_window.projects_tab._load_projects = (
            lambda: stub_window.projects_tab.calls.append("projects")
        )
        stub_window.events_tab._load_events = (
            lambda: stub_window.events_tab.calls.append("events")
        )

        # Mock statusBar
        class _SB:
            def showMessage(self_, msg):
                captured["status"] = msg
        stub_window.statusBar = lambda: _SB()

        stub_window._new_event()

        # The repo was called and the tabs were refreshed
        assert captured["created"] == {"name": "Probe"}
        assert stub_window.projects_tab.calls == ["projects"]
        assert stub_window.events_tab.calls == ["events"]
        assert "Termin erstellt" in captured["status"]

    def test_new_event_empty_name_warns_and_does_nothing(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QDialog, QMessageBox

        class _FakeDlg:
            def __init__(self, db, parent, prefilled_project_id=None):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def get_data(self):
                return {"name": ""}  # empty

        # Patch the source module: EventDialog is a local import in
        # ``_new_event`` (``from .dialogs import EventDialog``).
        monkeypatch.setattr(
            "chormanager.ui.dialogs.EventDialog",
            _FakeDlg,
        )

        warnings = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            staticmethod(
                lambda parent, title, text: warnings.append((title, text))
            ),
        )

        # No repo call should happen
        def boom(*a, **kw):
            raise RuntimeError("repo should not be called")

        monkeypatch.setattr(
            "chormanager.domain.repository.EventRepository",
            boom,
        )

        stub_window._new_event()
        assert warnings, "An empty name must produce a QMessageBox.warning"
        assert "Name ist erforderlich" in warnings[0][1]


class TestSaveProjektWiring:
    """``_save_projekt`` checks whether a project is selected and
    shows a QMessageBox.information (or warning if no project)."""

    def test_save_projekt_with_project_shows_info(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QMessageBox

        class _P:
            name = "TestChor"

        stub_window.projects_tab.current_project = _P()

        info_calls = []
        monkeypatch.setattr(
            QMessageBox, "information",
            staticmethod(
                lambda parent, title, text: info_calls.append((title, text))
            ),
        )

        stub_window._save_projekt()
        assert info_calls
        assert "TestChor" in info_calls[0][1]

    def test_save_projekt_without_project_shows_warning(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QMessageBox

        stub_window.projects_tab.current_project = None

        warn_calls = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            staticmethod(
                lambda parent, title, text: warn_calls.append((title, text))
            ),
        )

        stub_window._save_projekt()
        assert warn_calls
        assert "Kein Projekt" in warn_calls[0][1]
