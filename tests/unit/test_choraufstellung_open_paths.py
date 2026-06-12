# TDD: Regression tests for "Choraufstellung öffnen" entry points.
#
# User-Report (2026-06-12, nach M-1 Schritt 5):
#   "Wenn eine gespeicherte Choraufstellung geladen wird, wird das
#    Choraufstellungs-Plugin aufgerufen. Erwartetes Verhalten: die
#    platzierten Sänger erscheinen im Raster. Tatsächliches Verhalten:
#    Das Raster ist leer, alle Sänger im Pool.
#
#    Konkret gibt es VIER verschiedene Wege:
#      1. Hauptmenü → Aufstellung → 'In Aufstellung öffnen…'  → BUG
#      2. Großer Button 'Aus Chormanager laden'                → BUG
#      3. Context-Toolbar → 'Bearbeiten'                       → OK
#      4. Rechtsklick → 'Bearbeiten'                           → OK
#
#    Bug ist vorhanden bei Weg 1 und 2 (sie starten den Subshell ohne
#    CHOR_FILE, also ohne gespeicherte Plätze). Weg 3 und 4 starten
#    mit CHOR_FILE=<selektierte Datei> → gespeicherte Plätze werden
#    korrekt geladen.
#
# Fix: Der große Button wird entfernt. Der Menüpunkt 'In Aufstellung
# öffnen…' wird auf denselben Handler verdrahtet, den Context-Toolbar
# und Rechtsklick verwenden. So gibt es nur noch EINE korrekte
# 'gespeicherte Aufstellung laden'-Logik."

from __future__ import annotations

import json
import os
from pathlib import Path  # noqa: F401  (used by fixtures)
from typing import Iterator

import pytest


# ---------------------------------------------------------------------------
# Test fixtures: real ChorAufstellung-tab with one saved formation file
# ---------------------------------------------------------------------------

@pytest.fixture
def choraufstellung_data_dir(tmp_path, monkeypatch) -> Iterator[Path]:
    """Create a real data dir with one formation file and point the
    ChorAufstellungTab at it via monkeypatch.

    The test data dir is the one passed into ``ChorAufstellungTab``
    instead of the production directory. We achieve that by
    monkey-patching ``ChorAufstellungTab._load_formations`` callers
    to use the test dir. The cleanest path is to set the private
    ``_data_dir`` attribute after construction.
    """
    data_dir = tmp_path / "choraufstellung_data"
    data_dir.mkdir()

    # Create a minimal formation file with placed singers
    formation = {
        "version": "1.0",
        "saved_at": "2026-06-12T10:00:00",
        "rows": 3,
        "cols": 4,
        "staggered": False,
        "voicing_config": [],
        "singers": [
            {
                "name": "Pool Sänger",
                "voice_group": "Sopran 1",
                "height": 0,
                "singer_id": "pool-singer-1",
                "row": -1,
                "col": -1,
                "affinity": "",
                "external_id": "",
                "affinity_uuid": "",
            }
        ],
        "placed": [
            {
                "singer": {
                    "name": "Anna",
                    "voice_group": "Sopran 1",
                    "height": 0,
                    "singer_id": "anna-1",
                    "row": 0,
                    "col": 0,
                    "affinity": "",
                    "external_id": "",
                    "affinity_uuid": "",
                },
                "row": 0,
                "col": 0,
            }
        ],
        "metadata": {
            "project": "TestChor",
            "event": "Probe",
            "event_date": "2026-06-12",
            "event_type": "Probe",
        },
    }
    (data_dir / "choraufstellung-2026-06-12_Probe.json").write_text(
        json.dumps(formation, ensure_ascii=False, indent=2)
    )
    yield data_dir


@pytest.fixture
def choraufstellung_tab(qtbot, choraufstellung_data_dir):
    """A real ChorAufstellungTab whose ``_data_dir`` points at the
    test data dir (so the table lists the file we wrote)."""
    from chormanager.ui.views.choraufstellung_tab import ChorAufstellungTab

    tab = ChorAufstellungTab(db=None)
    tab._data_dir = str(choraufstellung_data_dir)
    tab._load_formations()
    qtbot.addWidget(tab)
    yield tab
    tab.close()


# ---------------------------------------------------------------------------
# Helper: patch the MainWindow-side opener so we don't spawn subshells
# ---------------------------------------------------------------------------

class _FakeMainWindow:
    """Stand-in for MainWindow: only records the filepath argument
    that ``_open_choraufstellung_file`` (or ``_edit_formation``) was
    called with. The latter is the new, correct entry point.
    """

    def __init__(self) -> None:
        self.opened_file: object = "__not_called__"

    def _open_choraufstellung(self):
        self.opened_file = None  # No filepath → bug path

    def _open_choraufstellung_file(self, filepath):
        self.opened_file = filepath  # With filepath → correct path

    def _edit_formation(self):
        # Production: this calls
        # ``self.choraufstellung_tab._edit_formation()`` which
        # reads the table's current row and calls
        # ``main_window._open_choraufstellung_file(filepath)`` on
        # the real MainWindow. In the test we delegate to the
        # choraufstellung tab so the same end state is reached.
        tab = getattr(self, "_choraufstellung_tab", None)
        if tab is not None:
            tab._edit_formation()


def _attach_fake_main_window(tab, fake: _FakeMainWindow) -> None:
    """Make ``tab.window()`` return the fake. ``ChorAufstellungTab``
    uses ``self.window()`` to reach MainWindow in production.
    """
    tab._fake_main = fake
    tab.window = lambda: fake  # type: ignore[assignment]
    # Give the fake a back-reference to the tab so its
    # ``_edit_formation`` wrapper can drive the tab end-to-end.
    fake._choraufstellung_tab = tab


# ---------------------------------------------------------------------------
# Test the fix
# ---------------------------------------------------------------------------

class TestOpenChoraufstellungEntryPoints:
    def test_no_big_load_button(self, choraufstellung_tab):
        """The big 'Aus ChorManager laden' button must be removed.
        Only the context-toolbar/rechtsklick/menu remain."""
        # In the buggy version there was a 'load_btn' attribute. After
        # the fix, no such button exists. Walk the children and
        # assert no QPushButton with that label is present.
        from PyQt6.QtWidgets import QPushButton
        buttons = [
            c for c in choraufstellung_tab.findChildren(QPushButton)
            if c.text() == "Aus ChorManager laden"
        ]
        assert buttons == [], (
            f"'Aus ChorManager laden' button still present: {buttons}"
        )

    def test_load_from_chormanager_delegates_to_edit_formation(
        self, choraufstellung_tab, choraufstellung_data_dir
    ):
        """The legacy ``_load_from_chormanager`` (formerly wired to
        the removed big button) must delegate to ``_edit_formation``
        when a row is selected. It used to always spawn a fresh
        editor (no CHOR_FILE) and that's the bug we are fixing.
        """
        choraufstellung_tab.table.selectRow(0)
        fake = _FakeMainWindow()
        _attach_fake_main_window(choraufstellung_tab, fake)
        choraufstellung_tab._load_from_chormanager()
        expected = os.path.join(
            str(choraufstellung_data_dir),
            "choraufstellung-2026-06-12_Probe.json",
        )
        assert fake.opened_file == expected, (
            f"_load_from_chormanager opened {fake.opened_file!r}, "
            f"expected {expected!r}"
        )

    def test_load_from_chormanager_no_selection_falls_back(
        self, choraufstellung_tab
    ):
        """If no row is selected, ``_load_from_chormanager`` must
        fall back to a fresh editor (the original behaviour, useful
        for creating a new formation from scratch)."""
        # No row selected: rowCount=1, currentRow=-1
        assert choraufstellung_tab.table.rowCount() == 1
        assert choraufstellung_tab.table.currentRow() == -1
        fake = _FakeMainWindow()
        _attach_fake_main_window(choraufstellung_tab, fake)
        choraufstellung_tab._load_from_chormanager()
        # ``_open_choraufstellung`` sets opened_file = None
        assert fake.opened_file is None

    def test_context_menu_edit_still_works(
        self, choraufstellung_tab, choraufstellung_data_dir
    ):
        """Sanity: the right-click 'Bearbeiten' still passes the
        selected filepath (this was the working path)."""
        choraufstellung_tab.table.selectRow(0)
        fake = _FakeMainWindow()
        _attach_fake_main_window(choraufstellung_tab, fake)
        choraufstellung_tab._edit_formation()
        expected = os.path.join(
            str(choraufstellung_data_dir),
            "choraufstellung-2026-06-12_Probe.json",
        )
        assert fake.opened_file == expected

    def test_context_toolbar_edit_still_works(
        self, choraufstellung_tab, choraufstellung_data_dir
    ):
        """Sanity: MainWindow's _edit_formation wrapper still works."""
        choraufstellung_tab.table.selectRow(0)
        fake = _FakeMainWindow()
        _attach_fake_main_window(choraufstellung_tab, fake)
        fake._edit_formation = (
            lambda: choraufstellung_tab._edit_formation()
        )
        fake._edit_formation()
        expected = os.path.join(
            str(choraufstellung_data_dir),
            "choraufstellung-2026-06-12_Probe.json",
        )
        assert fake.opened_file == expected


class TestMainWindowMenuWiring:
    """The MainWindow menu action 'In Aufstellung öffnen…' must be
    wired to the same handler as the context-toolbar/rechtsklick
    'Bearbeiten' (i.e. the choraufstellung_tab._edit_formation
    wrapper that opens the selected file).

    We assert the wiring by reading the source of
    ``chormanager/ui/main_window.py``: after the fix, the line that
    creates the 'In Aufstellung öffnen…' action must connect to a
    method that ultimately calls
    ``_open_choraufstellung_file(<selected filepath>)`` (i.e. NOT
    ``_open_choraufstellung`` which always passes ``None``).
    """

    MAIN_WINDOW_PY = (
        Path(__file__).resolve().parent.parent.parent
        / "chormanager"
        / "ui"
        / "main_window.py"
    )

    def test_menu_action_not_wired_to_buggy_opener(self):
        """The 'In Aufstellung öffnen…' QAction must NOT be connected
        to ``self._open_choraufstellung`` (the buggy opener that
        spawns a fresh editor with no CHOR_FILE).

        After the bug-fix the menu action is wired to
        ``_open_choraufstellung_selected_or_new`` (which delegates
        to ``_edit_formation`` when a row is selected, or to
        ``_open_choraufstellung`` otherwise). We assert the
        connection goes through the new method and that the buggy
        direct call ``self._open_choraufstellung()`` is gone.
        """
        text = self.MAIN_WINDOW_PY.read_text(encoding="utf-8")
        idx = text.find('"In Aufstellung öffnen')
        assert idx != -1, (
            "menu action 'In Aufstellung öffnen…' not found in main_window.py"
        )
        snippet = text[idx : idx + 600]
        assert "triggered.connect" in snippet, (
            f"no .triggered.connect near 'In Aufstellung öffnen…':\n{snippet}"
        )
        # After the fix the menu must go through the new selector
        # (not directly to the buggy _open_choraufstellung).
        assert "_open_choraufstellung_selected_or_new" in snippet, (
            "Menu 'In Aufstellung öffnen…' is NOT connected to "
            "_open_choraufstellung_selected_or_new (the new method "
            "that picks the selected row's file or falls back to a "
            "fresh editor)."
        )
        # The direct, buggy call must not be present in the snippet.
        buggy = "self._open_choraufstellung)"  # closing-paren excludes
        # ``_open_choraufstellung_file`` and the new selector
        snippet_cleaned = snippet.replace(
            "_open_choraufstellung_selected_or_new", ""
        )
        assert buggy not in snippet_cleaned, (
            "Menu 'In Aufstellung öffnen…' is still connected "
            "directly to self._open_choraufstellung() — the BUG path."
        )
