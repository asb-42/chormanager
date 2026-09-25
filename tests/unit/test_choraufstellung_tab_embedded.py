"""Phase 2 (M0): embedded editor in ChorAufstellungTab (increment 2/3).

Plan ref: docs/plans/2026-06-11_choraufstellung-migration.md, Phase 2.
The tab gains an embedded FormationEditorWidget (stacked page) next
to the file list. The legacy subprocess path (``_edit_formation`` ->
``main_window._open_choraufstellung_file``) stays intact until
increment 3/3 flips the default — both paths are tested here.
"""
from __future__ import annotations

import json

import pytest


def _formation_payload():
    return {
        "version": "1.0",
        "saved_at": "2026-09-26T10:00:00",
        "rows": 4,
        "cols": 5,
        "staggered": False,
        "voicing_config": [],
        "singers": [
            {"name": "Berta", "voice_group": "Sopran 2", "height": 165,
             "singer_id": "s-berta", "row": -1, "col": -1,
             "affinity": "", "external_id": "", "affinity_uuid": ""},
        ],
        "placed": [
            {"singer": {"name": "Anna", "voice_group": "Sopran 1",
                        "height": 170, "singer_id": "s-anna", "row": -1,
                        "col": -1, "affinity": "", "external_id": "",
                        "affinity_uuid": ""},
             "row": 0, "col": 1},
        ],
        "metadata": {"project": "P", "event": "E",
                     "event_date": "2026-09-26", "event_type": "Probe"},
    }


@pytest.fixture
def embedded_tab(qtbot, tmp_path):
    """ChorAufstellungTab with _data_dir pointed at a tmp dir holding
    one formation file in real storage shape."""
    from chormanager.ui.views.choraufstellung_tab import ChorAufstellungTab

    data_dir = tmp_path / "formations"
    data_dir.mkdir()
    (data_dir / "choraufstellung-test.json").write_text(
        json.dumps(_formation_payload(), ensure_ascii=False), encoding="utf-8"
    )
    tab = ChorAufstellungTab(db=None)
    tab._data_dir = str(data_dir)
    tab._load_formations()
    qtbot.addWidget(tab)
    tab.table.selectRow(0)
    yield tab
    tab.close()


class _FakeMainWindow:
    def __init__(self):
        self.opened_file = "__not_called__"

    def _open_choraufstellung_file(self, filepath):
        self.opened_file = filepath


def _attach_fake(tab, fake):
    tab.window = lambda: fake  # type: ignore[assignment]


def test_tab_embeds_editor_and_starts_on_list(embedded_tab):
    from chormanager.choraufstellung.editor_widget import (
        FormationEditorWidget,
    )

    assert isinstance(embedded_tab.editor, FormationEditorWidget)
    assert embedded_tab._stack.currentWidget() == embedded_tab._list_page


def test_open_embedded_shows_editor_without_subprocess(embedded_tab):
    import os

    fake = _FakeMainWindow()
    _attach_fake(embedded_tab, fake)
    filepath = os.path.join(embedded_tab._data_dir,
                            "choraufstellung-test.json")
    assert embedded_tab.open_embedded(filepath) is True
    assert embedded_tab._stack.currentWidget() == embedded_tab._editor_page
    assert "s-anna" in embedded_tab.editor.placed_singer_ids()
    assert fake.opened_file == "__not_called__"


def test_open_embedded_missing_file_stays_on_list(embedded_tab, tmp_path):
    missing = str(tmp_path / "nope.json")
    assert embedded_tab.open_embedded(missing) is False
    assert embedded_tab._stack.currentWidget() == embedded_tab._list_page


def test_save_embedded_round_trip(embedded_tab):
    import os

    filepath = os.path.join(embedded_tab._data_dir,
                            "choraufstellung-test.json")
    assert embedded_tab.open_embedded(filepath) is True
    # Berta is unplaced: place her, then save.
    berta = next(s for s in embedded_tab.editor.singers
                 if s.singer_id == "s-berta")
    assert embedded_tab.editor.add_to_grid(berta) is True
    assert embedded_tab.save_embedded() is True
    with open(filepath, encoding="utf-8") as f:
        saved = json.load(f)
    placed_ids = {p["singer"]["singer_id"] for p in saved["placed"]}
    assert {"s-anna", "s-berta"} <= placed_ids
    # Metadata survives the round-trip.
    assert saved["metadata"]["project"] == "P"


def test_close_embedded_returns_to_list(embedded_tab):
    import os

    filepath = os.path.join(embedded_tab._data_dir,
                            "choraufstellung-test.json")
    embedded_tab.open_embedded(filepath)
    embedded_tab.close_embedded()
    assert embedded_tab._stack.currentWidget() == embedded_tab._list_page


def test_legacy_subprocess_path_still_intact(embedded_tab):
    """Until increment 3/3, _edit_formation still delegates to the
    MainWindow subprocess opener (parallel operation)."""
    import os

    fake = _FakeMainWindow()
    _attach_fake(embedded_tab, fake)
    embedded_tab._edit_formation()
    assert fake.opened_file == os.path.join(
        embedded_tab._data_dir, "choraufstellung-test.json")
