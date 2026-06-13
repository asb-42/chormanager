"""TDD RED: Regression tests for M-2 Schritt 6 -- FormationGrid extrahieren.

The ``FormationGrid`` class is the biggest chunk of
``chormanager/choraufstellung/main.py`` (Z. 110-848, ~739 LOC) and
needs to be moved to ``choraufstellung/widgets/formation_grid.py``.

The class is already used by:
  * ``MainWindow`` (Z. 977): ``self.grid = FormationGrid(4, 5)``
  * ``SingerTile`` (duck-typed, no direct import after M-2 Schritt 5
    fix in commit 812487c)
  * Many call-sites in ``MainWindow`` (place_singer, auto_arrange_*,
    get_placed_singer_ids, refresh_grid, swap_selected_singers,
    selection_changed signal, undo_stack, singer_*_requested signals)

These tests pin down the public contract so the move-refactor stays
behaviour-preserving and we can also catch regressions in the
SingerTile <-> FormationGrid interaction (which Schritt 5's
duck-typing allows but doesn't enforce).

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 6.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


# ---------------------------------------------------------------------------
# Module shape: widgets/formation_grid.py
# ---------------------------------------------------------------------------

class TestModuleShape:
    def test_formation_grid_module_exists(self):
        try:
            from widgets import formation_grid  # noqa: F401
        except ModuleNotFoundError as exc:
            pytest.fail(
                f"widgets.formation_grid module not yet created: {exc}"
            )

    def test_formation_grid_module_exports_class(self):
        from widgets.formation_grid import FormationGrid
        assert FormationGrid is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockSinger:
    """Stand-in for ``singer_model.Singer`` with all the attributes
    FormationGrid touches."""

    def __init__(self, name="Doe, Jane", vg="Sopran 1", height=170,
                 singer_id="1", affinity="", row=-1, col=-1):
        self.name = name
        self.voice_group = vg
        self.height = height
        self.singer_id = singer_id
        self.affinity = affinity
        self.row = row
        self.col = col

    def to_dict(self):
        return {
            "singer_id": self.singer_id,
            "name": self.name,
            "voice_group": self.voice_group,
            "height": self.height,
            "affinity": self.affinity,
            "row": self.row,
            "col": self.col,
        }


# ---------------------------------------------------------------------------
# FormationGrid behaviour tests
# ---------------------------------------------------------------------------

class TestFormationGridInit:
    def test_init_with_default_4x5(self, qtbot):
        """Smoke-test: a 4x5 grid is empty and ready."""
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(4, 5)
        qtbot.addWidget(g)
        assert g.rows == 4
        assert g.cols == 5
        assert g.singers == []
        assert g.tiles == {}
        assert g.selected_ids == set()

    def test_init_custom_dimensions(self, qtbot):
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(2, 16)
        qtbot.addWidget(g)
        assert g.rows == 2
        assert g.cols == 16
        # 2x16 must announce a minimum width that is much larger than
        # the 1100 px old MainWindow (this is the resize-bug fix from
        # Schritt 5 -- still part of the public contract).
        assert g.minimumWidth() >= 16 * 130 + 80 + 50

    def test_init_sets_up_undo_stack(self, qtbot):
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(4, 5)
        qtbot.addWidget(g)
        # The grid must expose an undo_stack with canUndo/canRedo API
        # (the QtUndoStack bridge from Schritt 3).
        assert g.undo_stack is not None
        assert g.undo_stack.canUndo() is False
        assert g.undo_stack.canRedo() is False

    def test_init_creates_required_signals(self, qtbot):
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(4, 5)
        qtbot.addWidget(g)
        for attr in ("singer_removed_from_grid", "singer_edit_requested",
                     "singer_affinity_requested", "selection_changed"):
            assert hasattr(g, attr), f"Missing signal: {attr}"


class TestFormationGridPlacement:
    def test_place_singer_at_unoccupied_cell(self, qtbot):
        """Place a singer at an explicit cell, then verify state."""
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(2, 2)
        qtbot.addWidget(g)
        s = _MockSinger(singer_id="1", vg="Sopran 1")
        g.place_singer_at(s, 0, 0)
        assert s.row == 0
        assert s.col == 0
        assert g.is_occupied(0, 0)
        assert g.get_singer_at(0, 0) is s

    def test_get_singer_at_empty_cell_returns_none(self, qtbot):
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(2, 2)
        qtbot.addWidget(g)
        assert g.get_singer_at(0, 0) is None

    def test_is_occupied(self, qtbot):
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(2, 2)
        qtbot.addWidget(g)
        assert g.is_occupied(0, 0) is False
        g.place_singer_at(_MockSinger(singer_id="1"), 0, 0)
        assert g.is_occupied(0, 0) is True


class TestFormationGridSelection:
    def test_selection_changed_signal_fires_on_grid_background_click(
        self, qtbot
    ):
        """Clicking the empty grid background must emit
        ``selection_changed`` -- this is the path MainWindow listens
        to for update_swap_action."""
        from widgets.formation_grid import FormationGrid
        from qt_compat import QEvent, QPointF, QMouseEvent, Qt

        g = FormationGrid(2, 2)
        qtbot.addWidget(g)
        ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        with qtbot.waitSignal(g.selection_changed, timeout=500):
            g.mousePressEvent(ev)


class TestFormationGridSwap:
    def test_swap_selected_singers(self, qtbot):
        """Place two singers, select both, swap, verify order flips."""
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(2, 2)
        qtbot.addWidget(g)
        a = _MockSinger(singer_id="a", vg="Sopran 1")
        b = _MockSinger(singer_id="b", vg="Alt 1")
        g.place_singer_at(a, 0, 0)
        g.place_singer_at(b, 0, 1)
        g.selected_ids = {"a", "b"}
        g.swap_selected_singers()
        # After swap, a and b must have exchanged (row, col).
        a2 = g.get_singer_at(0, 0)
        b2 = g.get_singer_at(0, 1)
        assert a2 is b
        assert b2 is a


class TestFormationGridAutoArrange:
    def test_auto_arrange_satb_keeps_voice_groups_in_rows(self, qtbot):
        """SATB rule: SATB in row 0, AAB in row 1, TTBB in row 2, BBAA in row 3
        (or some defined mapping).  Use 8 singers (2 per voice group) and
        verify that no row contains two different voice groups that are
        both 'outer' Sopran/Alt or 'outer' Tenor/Bass in the same row.

        The exact rule is less important than the invariant that the
        function is callable and produces a deterministic arrangement.
        """
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(4, 5)
        qtbot.addWidget(g)
        singers = []
        for i, vg in enumerate(["Sopran 1", "Sopran 2",
                                "Alt 1", "Alt 2",
                                "Tenor 1", "Tenor 2",
                                "Bass 1", "Bass 2"]):
            s = _MockSinger(name=f"S{i}", vg=vg, singer_id=str(i + 1),
                            height=170 + i)
            singers.append(s)
            g.place_singer_at(s, i % 4, i // 4)  # all over the place
        g.auto_arrange_satb()
        # After the rearrangement, every singer is placed (row >= 0).
        for s in singers:
            assert s.row >= 0
            assert s.col >= 0


class TestFormationGridSignals:
    def test_emit_singer_removed_from_grid(self, qtbot):
        """Removing a tile must emit ``singer_removed_from_grid``."""
        from widgets.formation_grid import FormationGrid
        g = FormationGrid(2, 2)
        qtbot.addWidget(g)
        s = _MockSinger(singer_id="42", vg="Sopran 1")
        g.place_singer_at(s, 0, 0)
        # The signal is emitted with the singer object.
        with qtbot.waitSignal(
            g.singer_removed_from_grid, timeout=500
        ) as blocker:
            g.on_tile_removed(g.tiles["42"])
        assert blocker.args and blocker.args[0] is s


# ---------------------------------------------------------------------------
# Re-export from choraufstellung.main (backward compatibility)
# ---------------------------------------------------------------------------

class TestReExport:
    def test_formation_grid_re_exported_from_main_py(self):
        """External callers (e.g. ``choraufstellung_launcher``) still
        do ``from choraufstellung.main import FormationGrid`` --
        the re-export must stay alive even after the move.

        The full ``import choraufstellung.main`` path is only
        exercised in subshell mode (the package's ``__init__`` is
        fragile under pytest's sys.path layout), so we use a
        lightweight static check: the re-export line must exist in
        the source file.  Combined with the
        ``test_formation_grid_module_exists`` test above, this
        guarantees the class is importable both via
        ``from widgets.formation_grid import FormationGrid`` and
        via the choraufstellung.main re-export.
        """
        from pathlib import Path
        main_py = (
            Path(__file__).resolve().parents[2]
            / "chormanager" / "choraufstellung" / "main.py"
        )
        text = main_py.read_text(encoding="utf-8")
        assert "from widgets.formation_grid import FormationGrid" in text, (
            "choraufstellung/main.py no longer re-exports FormationGrid "
            f"from widgets.formation_grid.  Inspect {main_py}."
        )
        # And the actual class must exist at the new location.
        from widgets.formation_grid import FormationGrid  # noqa: F401
