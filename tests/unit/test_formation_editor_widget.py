"""Phase 2 (M0): FormationEditorWidget — embeddable editor shell.

Plan ref: docs/plans/2026-06-11_choraufstellung-migration.md, Phase 2
(Embed the Plugin as a Widget). The widget composes the canonical
``widgets/`` components (SingerPool + FormationGrid, see
docs/plans/2026-09-25_web-migration-analyse.md §1.4) into a plain
QWidget so ChorAufstellungTab can embed the editor instead of
spawning a subprocess. No menus, no subprocess, no file dialogs.
"""
from __future__ import annotations

import pytest


def _singers():
    from singer_model import Singer, VoiceGroup

    return [
        Singer(name="Anna", voice_group=VoiceGroup.SOPRAN_1, height=170,
               singer_id="s-anna"),
        Singer(name="Berta", voice_group=VoiceGroup.SOPRAN_2, height=165,
               singer_id="s-berta"),
        Singer(name="Clara", voice_group=VoiceGroup.ALT_1, height=172,
               singer_id="s-clara"),
    ]


def _make_editor(qtbot):
    from editor_widget import FormationEditorWidget

    editor = FormationEditorWidget()
    qtbot.addWidget(editor)
    return editor


def test_constructs_with_pool_and_grid(qtbot):
    from widgets.singer_pool import SingerPool
    from widgets.formation_grid import FormationGrid

    editor = _make_editor(qtbot)
    assert isinstance(editor.pool, SingerPool)
    assert isinstance(editor.grid, FormationGrid)
    assert (editor.grid.rows, editor.grid.cols) == (4, 5)


def test_set_singers_populates_pool(qtbot):
    editor = _make_editor(qtbot)
    singers = _singers()
    editor.set_singers(singers)
    assert list(editor.pool.singers) == singers
    assert set(editor.grid.get_placed_singer_ids()) == set()


def test_load_formation_data_places_singers(qtbot):
    editor = _make_editor(qtbot)
    editor.load_formation_data(
        {
            "rows": 4,
            "cols": 5,
            "staggered": False,
            "singers": [
                {"name": "Anna", "voice_group": "Sopran 1", "height": 170,
                 "singer_id": "s-anna", "row": 0, "col": 1},
                {"name": "Berta", "voice_group": "Sopran 2", "height": 165,
                 "singer_id": "s-berta", "row": -1, "col": -1},
            ],
        }
    )
    assert "s-anna" in set(editor.grid.get_placed_singer_ids())
    assert "s-berta" not in set(editor.grid.get_placed_singer_ids())
    assert editor.is_modified() is False


def test_add_to_grid_places_first_empty_slot(qtbot):
    editor = _make_editor(qtbot)
    (singer,) = _singers()[:1]
    editor.set_singers([singer])
    assert editor.add_to_grid(singer) is True
    assert (singer.row, singer.col) != (-1, -1)
    assert "s-anna" in set(editor.grid.get_placed_singer_ids())


def test_no_subprocess_dependency():
    # Phase-2 direction guard: the embeddable editor must never spawn
    # a subprocess (that path stays in choraufstellung_launcher only).
    # Docstring mentions are fine; only real imports count.
    import re
    from pathlib import Path

    src = Path("chormanager/choraufstellung/editor_widget.py").read_text(
        encoding="utf-8"
    )
    code = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
    code = re.sub(r"#.*", "", code)
    assert "subprocess" not in code
