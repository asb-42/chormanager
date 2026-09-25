"""Phase 2 (M0): embedded editor in ChorAufstellungTab (increment 2/3).

Plan ref: docs/plans/2026-06-11_choraufstellung-migration.md, Phase 2.
The tab gains an embedded FormationEditorWidget (stacked page) next
to the file list. The legacy subprocess path (``_edit_formation`` ->
``main_window._open_choraufstellung_file``) stays intact until
increment 3/3 flips the default — both paths are tested here.
"""
from __future__ import annotations

import json
import os

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
    """Since increment 3/3, _edit_formation defaults to the embedded
    editor (parallel subprocess operation is gone)."""
    import os

    fake = _FakeMainWindow()
    _attach_fake(embedded_tab, fake)
    embedded_tab._edit_formation()
    assert embedded_tab._stack.currentWidget() == embedded_tab._editor_page
    assert "s-anna" in embedded_tab.editor.placed_singer_ids()
    assert fake.opened_file == "__not_called__"


@pytest.fixture
def db_tab(qtbot, tmp_path):
    """ChorAufstellungTab backed by a real tmp database with one
    project, one event and one available singer."""
    from chormanager.data.database import Database
    from chormanager.domain.repository import (
        AvailabilityRepository,
        EventRepository,
        ProjectRepository,
        SingerRepository,
    )
    from chormanager.ui.views.choraufstellung_tab import ChorAufstellungTab

    db = Database(str(tmp_path / "t.db"))
    db.connect()
    db.create_tables()
    project = ProjectRepository(db).create(name="P")
    event = EventRepository(db).create(
        name="Probe", date="2026-09-26", event_type="Probe",
        project_id=project.id,
    )
    singer = SingerRepository(db).create(
        full_name="Anna Muster", short_name="Anna",
        voice_group="Sopran 1", height=170,
    )
    AvailabilityRepository(db).create(
        singer_id=singer.id, event_id=event.id, status="yes",
    )
    data_dir = tmp_path / "formations"
    data_dir.mkdir()
    tab = ChorAufstellungTab(db)
    tab._data_dir = str(data_dir)
    tab._load_formations()
    qtbot.addWidget(tab)
    yield tab, event
    db.close()
    tab.close()


def test_open_new_for_event_seeds_editor(qtbot, db_tab):
    tab, event = db_tab
    assert tab.open_new_for_event(event) is True
    assert tab._stack.currentWidget() == tab._editor_page
    names = [s.name for s in tab.editor.singers]
    assert names == ["Anna"]
    assert tab._embedded_file is not None
    assert tab._embedded_file.endswith(".json")
    assert os.path.dirname(tab._embedded_file) == tab._data_dir
    assert tab._embedded_meta["event"] == "Probe"
    # Not yet saved: the file must not exist before save_embedded().
    assert not os.path.exists(tab._embedded_file)
    assert tab.save_embedded() is True
    assert os.path.exists(tab._embedded_file)


def test_open_new_for_event_without_yes_singers(qtbot, tmp_path):
    """No availability rows: the editor still opens, pool stays empty."""
    from chormanager.data.database import Database
    from chormanager.domain.repository import EventRepository
    from chormanager.ui.views.choraufstellung_tab import ChorAufstellungTab

    db = Database(str(tmp_path / "t2.db"))
    db.connect()
    db.create_tables()
    event = EventRepository(db).create(
        name="Leer", date="2026-09-27", event_type="Probe",
    )
    data_dir = tmp_path / "formations"
    data_dir.mkdir()
    tab = ChorAufstellungTab(db)
    tab._data_dir = str(data_dir)
    qtbot.addWidget(tab)
    try:
        assert tab.open_new_for_event(event) is True
        assert tab.editor.singers == []
    finally:
        db.close()
        tab.close()


def test_load_from_chormanager_event_goes_embedded(qtbot, db_tab):
    tab, event = db_tab

    class _Fake:
        opened_file = "__not_called__"

        def _open_choraufstellung_for_event(self, _event):
            self.opened_file = "SUBPROCESS"

    fake = _Fake()
    tab.window = lambda: fake  # type: ignore[assignment]
    tab._load_from_chormanager(event)
    assert tab._stack.currentWidget() == tab._editor_page
    assert [s.name for s in tab.editor.singers] == ["Anna"]
    assert fake.opened_file == "__not_called__"
