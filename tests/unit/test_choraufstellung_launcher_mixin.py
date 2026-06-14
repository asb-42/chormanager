# TDD RED: Regression tests for M-1 Schritt 6 — ChorAufstellung-Spawning Mixin.
#
# We need to prove that the four "open choraufstellung" methods
# survive the extraction byte-for-byte:
#
#   * ``_open_choraufstellung``              → wraps ``_open_choraufstellung_file(None)``
#   * ``_open_choraufstellung_selected_or_new`` → picks the row's file via
#                                                ``_edit_formation`` or falls
#                                                back to a fresh editor.
#   * ``_open_choraufstellung_file``         → spawns the ``__main__.py``
#                                                subprocess with the
#                                                appropriate env vars.
#   * ``_open_choraufstellung_for_event``    → builds a temp JSON file and
#                                                hands it to the subshell.
#
# We also assert that the methods are now defined on the new Mixin
# (no longer in ``main_window``).
#
# These tests run WITHOUT spawning a real subshell — every test
# patches the subprocess and the QMessageBox to be a no-op.

from __future__ import annotations

import importlib
import inspect
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. The Mixin exists and exposes the four methods.
# ---------------------------------------------------------------------------

class TestChorAufstellungLauncherMixinExists:
    """M-1 step 6: the ChorAufstellung-Spawning methods must now
    live in ``chormanager.ui.choraufstellung_launcher.ChorAufstellungLauncherMixin``."""

    def test_module_exports_mixin_class(self):
        mod = importlib.import_module(
            "chormanager.ui.choraufstellung_launcher"
        )
        assert hasattr(mod, "ChorAufstellungLauncherMixin"), (
            "ChorAufstellungLauncherMixin must be exported from "
            "chormanager.ui.choraufstellung_launcher"
        )

    def test_mixin_has_the_four_methods(self):
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        for name in (
            "_open_choraufstellung",
            "_open_choraufstellung_selected_or_new",
            "_open_choraufstellung_file",
            "_open_choraufstellung_for_event",
        ):
            assert hasattr(ChorAufstellungLauncherMixin, name), (
                f"ChorAufstellungLauncherMixin is missing {name}"
            )

    def test_mixin_has_edit_formation_wrapper(self):
        """The thin ``_edit_formation`` wrapper stays with the Mixin
        because it delegates to the choraufstellung tab and is
        naturally part of the formation-opening flow."""
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        assert hasattr(ChorAufstellungLauncherMixin, "_edit_formation")

    def test_module_level_refresh_helper_still_there(self):
        """The pre-existing module-level ``refresh_tab_repositories``
        helper (M-1 step 3) must keep working — re-exports are
        resolved at the same name."""
        from chormanager.ui import choraufstellung_launcher
        assert callable(choraufstellung_launcher.refresh_tab_repositories)


# ---------------------------------------------------------------------------
# 2. MainWindow inherits the Mixin.
# ---------------------------------------------------------------------------

class TestMainWindowInheritsMixin:
    def test_main_window_inherits_mixin(self):
        from chormanager.ui.main_window import MainWindow
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        assert issubclass(MainWindow, ChorAufstellungLauncherMixin), (
            "MainWindow must inherit from ChorAufstellungLauncherMixin"
        )


# ---------------------------------------------------------------------------
# 3. Behaviour-preserving: the methods resolve through the MRO and the
#    source location moved.
# ---------------------------------------------------------------------------

class TestMethodsMovedToMixin:
    """Assert that the methods are *defined* in the Mixin (not in
    MainWindow). The check uses ``__qualname__`` which is robust
    against the method being inherited."""

    def test_open_choraufstellung_file_defined_in_mixin(self):
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        qual = ChorAufstellungLauncherMixin._open_choraufstellung_file.__qualname__
        assert qual.startswith("ChorAufstellungLauncherMixin."), (
            f"_open_choraufstellung_file defined in {qual!r}, expected Mixin"
        )

    def test_open_choraufstellung_for_event_defined_in_mixin(self):
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        qual = ChorAufstellungLauncherMixin._open_choraufstellung_for_event.__qualname__
        assert qual.startswith("ChorAufstellungLauncherMixin.")

    def test_open_choraufstellung_selected_or_new_defined_in_mixin(self):
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        qual = (
            ChorAufstellungLauncherMixin._open_choraufstellung_selected_or_new.__qualname__
        )
        assert qual.startswith("ChorAufstellungLauncherMixin.")

    def test_open_choraufstellung_defined_in_mixin(self):
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        qual = ChorAufstellungLauncherMixin._open_choraufstellung.__qualname__
        assert qual.startswith("ChorAufstellungLauncherMixin.")

    def test_edit_formation_wrapper_defined_in_mixin(self):
        from chormanager.ui.choraufstellung_launcher import (
            ChorAufstellungLauncherMixin,
        )
        qual = ChorAufstellungLauncherMixin._edit_formation.__qualname__
        assert qual.startswith("ChorAufstellungLauncherMixin.")


# ---------------------------------------------------------------------------
# 4. Backward-compat re-exports
# ---------------------------------------------------------------------------

class TestBackwardCompatReExports:
    """Other modules may import the spawning helpers via
    ``chormanager.ui.main_window``. Keep them re-exported so we
    don't break the public-ish API."""

    def test_refresh_tab_repositories_re_exported_from_main_window(self):
        from chormanager.ui import main_window
        assert hasattr(main_window, "refresh_tab_repositories"), (
            "refresh_tab_repositories must remain importable from "
            "chormanager.ui.main_window (backward compat)."
        )
        from chormanager.ui import choraufstellung_launcher
        assert (
            main_window.refresh_tab_repositories
            is choraufstellung_launcher.refresh_tab_repositories
        )


# ---------------------------------------------------------------------------
# 5. Behaviour-preserving tests with a real-ish MainWindow stub
# ---------------------------------------------------------------------------

class _RecordingWindow(ChorAufstellungLauncherMixin if False else object):
    """Stub that records every method call so we can assert the
    orchestration without spawning a real subshell."""

    def __init__(self) -> None:
        self.calls = []
        self.db = None
        self.db_path = ""
        self.current_project = None
        self.current_event = None
        self.content_stack = type(
            "S", (), {"setCurrentIndex": lambda self_, i: None}
        )()
        # Fake projects tab / events tab / choraufstellung tab
        self.projects_tab = type("P", (), {"current_project": None})()
        self.events_tab = type(
            "E",
            (),
            {
                "table": type("T", (), {"currentRow": lambda self_: -1})(),
                "event_repo": type("R", (), {"get_by_id": lambda self_, x: None})(),
            },
        )()
        self.choraufstellung_tab = type(
            "C",
            (),
            {
                "table": type("T", (), {"currentRow": lambda self_: -1})(),
                "_load_formations": lambda self_: self.calls.append(
                    "choraufstellung_tab._load_formations"
                ),
                "_edit_formation": lambda self_: self.calls.append(
                    "choraufstellung_tab._edit_formation"
                ),
            },
        )()


@pytest.fixture
def stub_window() -> Iterator[_RecordingWindow]:
    """A barebones object that mixes in the launcher mixin."""
    from chormanager.ui.choraufstellung_launcher import (
        ChorAufstellungLauncherMixin,
    )

    class W(_RecordingWindow, ChorAufstellungLauncherMixin):
        pass

    yield W()


class TestOpenChoraufstellungDelegates:
    def test_open_choraufstellung_calls_file_with_none(
        self, stub_window
    ):
        """``_open_choraufstellung`` must delegate to
        ``_open_choraufstellung_file(None)``."""

        with patch.object(
            _RecordingWindow,  # no-op: prevent inherited calls
            "__getattribute__",
            side_effect=lambda name: (
                lambda *a, **kw: stub_window.calls.append(
                    (name, a)
                )
            )
            if name == "_open_choraufstellung_file"
            else object.__getattribute__(stub_window, name),
        ):
            stub_window._open_choraufstellung()

        assert any(
            c[0] == "_open_choraufstellung_file" and c[1] == (None,)
            for c in stub_window.calls
        ), (
            f"_open_choraufstellung must call "
            f"_open_choraufstellung_file(None); got {stub_window.calls}"
        )

    def test_open_choraufstellung_selected_or_new_no_row_falls_back(
        self, stub_window
    ):
        """No row selected → fall back to fresh editor."""
        with patch.object(
            stub_window,
            "_open_choraufstellung",
            wraps=lambda: stub_window.calls.append(
                "_open_choraufstellung"
            ),
        ) as fresh, patch.object(
            stub_window,
            "_edit_formation",
            wraps=lambda: stub_window.calls.append("_edit_formation"),
        ) as edit:
            stub_window._open_choraufstellung_selected_or_new()
        fresh.assert_called_once()
        edit.assert_not_called()

    def test_open_choraufstellung_selected_or_new_with_row_delegates(
        self, stub_window
    ):
        """A row is selected → delegate to ``_edit_formation``."""
        # Make the choraufstellung table return a valid row
        stub_window.choraufstellung_tab.table = type(
            "T", (), {"currentRow": lambda self_: 0}
        )()
        with patch.object(
            stub_window,
            "_open_choraufstellung",
            wraps=lambda: stub_window.calls.append(
                "_open_choraufstellung"
            ),
        ) as fresh, patch.object(
            stub_window,
            "_edit_formation",
            wraps=lambda: stub_window.calls.append("_edit_formation"),
        ) as edit:
            stub_window._open_choraufstellung_selected_or_new()
        edit.assert_called_once()
        fresh.assert_not_called()

    def test_edit_formation_wrapper_delegates_to_tab(self, stub_window):
        """``_edit_formation`` must call
        ``self.choraufstellung_tab._edit_formation()``."""
        stub_window._edit_formation()
        assert "choraufstellung_tab._edit_formation" in stub_window.calls


# ---------------------------------------------------------------------------
# 6. Subprocess-spawning methods do not raise when the choraufstellung
#    path is missing — they must show a warning and return cleanly.
# ---------------------------------------------------------------------------

class TestOpenChoraufstellungFileNoSubshell:
    def test_missing_choraufstellung_dir_shows_warning_and_returns(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QMessageBox

        with patch.object(QMessageBox, "warning") as warn, patch(
            "os.path.exists", return_value=False
        ), patch(
            "os.path.isdir", return_value=False
        ), patch(
            "os.path.isfile", return_value=False
        ):
            stub_window._open_choraufstellung_file("/tmp/foo.json")
        assert warn.called, (
            "When the choraufstellung package directory is missing, "
            "the method must show a QMessageBox.warning and return."
        )

    def test_spawns_subprocess_with_env(self, stub_window, monkeypatch):
        """The happy path: subprocess.run is called with the
        correct arguments, env contains CHOR_PROJECT, etc."""
        from PyQt6.QtWidgets import QMessageBox

        # Always claim the directory exists
        monkeypatch.setattr(
            "os.path.exists", lambda p: True, raising=True
        )
        # Set db_path on the stub
        stub_window.db_path = "/tmp/test-chor.db"
        captured = {}

        def fake_run(cmd, cwd=None, env=None, **kw):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            captured["env"] = env
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(
            "subprocess.run", fake_run, raising=True
        )
        with patch.object(QMessageBox, "warning") as warn:
            stub_window._open_choraufstellung_file("/tmp/foo.json")

        assert not warn.called, (
            f"Unexpected warning shown: {warn.call_args}"
        )
        assert captured["cmd"][0] == sys.executable
        assert captured["cmd"][1].endswith("__main__.py")
        env = captured["env"]
        # CHOR_FILE passed
        assert env.get("CHOR_FILE") == "/tmp/foo.json"
        # CHOR_DB_PATH passed
        assert env.get("CHOR_DB_PATH") == "/tmp/test-chor.db"
        # _load_formations was called after return
        assert "choraufstellung_tab._load_formations" in stub_window.calls


# ---------------------------------------------------------------------------
# 7. The temp-file method builds a JSON document with the expected
#    fields and writes to a real temp dir.
# ---------------------------------------------------------------------------

class TestOpenChoraufstellungForEvent:
    def _make_event(self):
        from dataclasses import dataclass

        @dataclass
        class _E:
            id: str = "ev-1"
            name: str = "Probe"
            date: str = "2026-06-12T18:00:00"
            event_type: str = "Probe"

        return _E()

    def test_writes_temp_json_and_spawns_subprocess(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QMessageBox

        event = self._make_event()
        # Set up project
        from dataclasses import dataclass

        @dataclass
        class _P:
            name: str = "TestChor"

        stub_window.current_project = _P()

        # Stub SingerRepository / AvailabilityRepository
        class _S:
            def __init__(self, db):
                pass

            def get_all(self):
                return []

        class _A:
            def __init__(self, db):
                pass

            def get_by_ids(self, singer_id, event_id):
                return None

        monkeypatch.setattr(
            "chormanager.domain.repository.SingerRepository", _S
        )
        monkeypatch.setattr(
            "chormanager.domain.repository.AvailabilityRepository", _A
        )
        monkeypatch.setattr("os.path.exists", lambda p: True)

        captured = {}

        def fake_run(cmd, cwd=None, env=None, **kw):
            captured["env"] = env
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr("subprocess.run", fake_run)

        with patch.object(QMessageBox, "warning") as warn:
            stub_window._open_choraufstellung_for_event(event)

        assert not warn.called
        env = captured["env"]
        # The temp file path is set as CHOR_EVENT_DATA
        # (C1.3: now unique per call, see _make_event_temp_path)
        assert env.get("CHOR_EVENT_DATA", "").endswith(".json")
        # Filename pattern: choraufstellung_event-<pid>-<uuid8>.json
        import re as _re
        assert _re.search(
            r"choraufstellung_event-\d+-\w+\.json$",
            env.get("CHOR_EVENT_DATA", ""),
        ), f"unexpected CHOR_EVENT_DATA: {env.get('CHOR_EVENT_DATA')!r}"
        # Legacy env vars
        assert env.get("CHOR_EVENT_NAME") == "Probe"
        assert env.get("CHOR_EVENT_ID") == "ev-1"
        assert env.get("CHOR_EVENT_DATE") == "2026-06-12"
        assert env.get("CHOR_EVENT_TYPE") == "Probe"
        assert env.get("CHOR_PROJECT") == "TestChor"

        # The temp file was written
        temp_file = env["CHOR_EVENT_DATA"]
        assert os.path.exists(temp_file)
        import json as _json
        with open(temp_file, "r", encoding="utf-8") as f:
            data = _json.load(f)
        assert data["project"] == "TestChor"
        assert data["event"]["id"] == "ev-1"
        assert "singers" in data
        assert "created_at" in data

        # And _load_formations was triggered
        assert "choraufstellung_tab._load_formations" in stub_window.calls
