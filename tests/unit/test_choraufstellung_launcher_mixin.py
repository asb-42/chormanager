# Regression tests for the ChorAufstellung entry points.
#
# M-1 Schritt 6 extracted the four "open choraufstellung" methods
# into the Mixin (byte-for-byte). M0 Phase 2 (increment 3/3) removed
# the subprocess layer: every entry point now delegates to the
# embedded tab editor:
#
#   * ``_open_choraufstellung``              → tab ``_new_formation`` dialog
#   * ``_open_choraufstellung_selected_or_new`` → row → ``_edit_formation``
#                                                (embedded), else dialog
#   * ``_open_choraufstellung_file``         → tab ``open_embedded``
#                                                (fallback: dialog)
#   * ``_open_choraufstellung_for_event``    → tab switch + tab
#                                                ``open_new_for_event``
#
# These tests run WITHOUT Qt event loops for the delegation paths —
# a stub window records the calls.
#
from __future__ import annotations

import importlib
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
                "_new_formation": lambda self_: self.calls.append(
                    "choraufstellung_tab._new_formation"
                ),
                "open_embedded": lambda self_, fp: self.calls.append(
                    ("choraufstellung_tab.open_embedded", (fp,))
                ) or True,
                "open_new_for_event": lambda self_, ev: self.calls.append(
                    ("choraufstellung_tab.open_new_for_event", (ev,))
                ) or True,
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
    def test_open_choraufstellung_delegates_to_tab_new_formation(
        self, stub_window
    ):
        """``_open_choraufstellung`` (fresh) routes to the tab's
        new-formation dialog (no subprocess since 3/3)."""
        stub_window._open_choraufstellung()
        assert (
            "choraufstellung_tab._new_formation" in stub_window.calls
        ), f"expected tab._new_formation; got {stub_window.calls}"

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
# 6. Embedded delegation: no subprocess is ever spawned (3/3).
# ---------------------------------------------------------------------------

class TestOpenChoraufstellungFileEmbedded:
    def test_open_file_delegates_to_embedded(self, stub_window):
        """With a filepath, ``_open_choraufstellung_file`` opens it
        embedded and does NOT fall back to the dialog."""
        stub_window._open_choraufstellung_file("/tmp/foo.json")
        assert (
            ("choraufstellung_tab.open_embedded", ("/tmp/foo.json",))
            in stub_window.calls
        )
        assert (
            "choraufstellung_tab._new_formation" not in stub_window.calls
        )

    def test_open_file_without_filepath_falls_back_to_new(
        self, stub_window
    ):
        """Without a filepath, fall back to the new-formation dialog."""
        stub_window._open_choraufstellung_file(None)
        assert (
            "choraufstellung_tab._new_formation" in stub_window.calls
        )

    def test_no_subprocess_in_launcher_module(self):
        """Direction guard: the launcher module must not spawn
        subprocesses anymore (docstring mentions are fine)."""
        import re

        src = Path(
            "chormanager/ui/choraufstellung_launcher.py"
        ).read_text(encoding="utf-8")
        code = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
        code = re.sub(r"#.*", "", code)
        assert "subprocess" not in code
        assert "CHOR_EVENT_DATA" not in code
        assert "CHOR_FILE" not in code


# ---------------------------------------------------------------------------
# 7. for_event seeds the embedded editor (no temp JSON).
# ---------------------------------------------------------------------------

class TestOpenChoraufstellungForEventEmbedded:
    def _make_event(self):
        from dataclasses import dataclass

        @dataclass
        class _E:
            id: str = "ev-1"
            name: str = "Probe"
            date: str = "2026-06-12T18:00:00"
            event_type: str = "Probe"

        return _E()

    def test_for_event_switches_tab_and_seeds(
        self, stub_window, monkeypatch
    ):
        """``_open_choraufstellung_for_event`` switches to the
        ChorAufstellung tab and seeds its embedded editor."""
        switched = []
        monkeypatch.setattr(
            stub_window.content_stack,
            "setCurrentIndex",
            lambda i: switched.append(i),
            raising=False,
        )
        event = self._make_event()
        stub_window._open_choraufstellung_for_event(event)
        assert switched == [4]
        assert (
            ("choraufstellung_tab.open_new_for_event", (event,))
            in stub_window.calls
        )
