"""TDD RED: Regression tests for M-2 Schritt 5 — SingerTile + SingerPool extrahieren.

Both classes currently live in ``choraufstellung/main.py`` (Z. 84-208
and Z. 970-1206).  M-2 Schritt 5 moves them to
``choraufstellung/widgets/singer_tile.py`` and
``choraufstellung/widgets/singer_pool.py`` respectively, and re-exports
the class names from ``choraufstellung.main`` for backward compatibility.

The classes are tested via the new module path.  See
plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 5.
"""
from __future__ import annotations

import pytest
from qt_compat import QObject, QWidget, pyqtSignal


# ---------------------------------------------------------------------------
# Module shape: widgets/singer_tile.py and widgets/singer_pool.py
# ---------------------------------------------------------------------------

class TestModuleShape:
    def test_singer_tile_module_exists(self):
        try:
            from widgets import singer_tile as m  # noqa: F401
        except ModuleNotFoundError as exc:
            pytest.fail(f"widgets.singer_tile module not yet created: {exc}")

    def test_singer_tile_module_exports_singer_tile(self):
        from widgets.singer_tile import SingerTile
        assert SingerTile is not None

    def test_singer_pool_module_exists(self):
        try:
            from widgets import singer_pool as m  # noqa: F401
        except ModuleNotFoundError as exc:
            pytest.fail(f"widgets.singer_pool module not yet created: {exc}")

    def test_singer_pool_module_exports_singer_pool(self):
        from widgets.singer_pool import SingerPool
        assert SingerPool is not None


# ---------------------------------------------------------------------------
# SingerTile
# ---------------------------------------------------------------------------

class _MockSinger:
    """Stand-in for ``singer_model.Singer`` with the four attributes
    SingerTile touches: name, voice_group, height, singer_id, affinity."""

    def __init__(self, name="Müller, Anna", vg="Sopran 1",
                 height=170, singer_id="42", affinity=""):
        self.name = name
        self.voice_group = vg
        self.height = height
        self.singer_id = singer_id
        self.affinity = affinity


class TestSingerTile:
    def test_singer_tile_constructs_with_singer(self, qtbot):
        from widgets.singer_tile import SingerTile
        singer = _MockSinger()
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        assert tile.singer is singer
        assert tile.position is None

    def test_singer_tile_uses_voice_group_color(self, qtbot):
        from widgets.singer_tile import SingerTile
        singer = _MockSinger(vg="Sopran 1")
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        # The background should mention the voice-group color (we
        # don't pin the exact hex; we just assert the style sheet
        # is non-empty and contains a hex color).
        ss = tile.styleSheet()
        assert "#" in ss

    def test_singer_tile_emits_removed_on_remove(self, qtbot):
        from widgets.singer_tile import SingerTile
        singer = _MockSinger()
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        with qtbot.waitSignal(tile.removed, timeout=500):
            tile.on_remove()

    def test_singer_tile_signals_exist(self):
        from widgets.singer_tile import SingerTile
        # The class must expose these three Qt signals.
        assert hasattr(SingerTile, "removed")
        assert hasattr(SingerTile, "edit_requested")
        assert hasattr(SingerTile, "affinity_requested")

    def test_singer_tile_set_selected_toggles_border(self, qtbot):
        from widgets.singer_tile import SingerTile
        singer = _MockSinger()
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        tile.set_selected(True)
        assert "3px" in tile.styleSheet() or "solid #0066cc" in tile.styleSheet()
        tile.set_selected(False)
        assert "1px" in tile.styleSheet()


# ---------------------------------------------------------------------------
# SingerPool
# ---------------------------------------------------------------------------

class TestSingerPool:
    def _make_pool(self, qtbot):
        from widgets.singer_pool import SingerPool
        pool = SingerPool()
        qtbot.addWidget(pool)
        return pool

    def test_singer_pool_signals_exist(self, qtbot):
        pool = self._make_pool(qtbot)
        assert hasattr(pool, "singer_selected")
        assert hasattr(pool, "singer_added")
        assert hasattr(pool, "singer_edit_requested")
        assert hasattr(pool, "place_all_requested")

    def test_singer_pool_empty_pool_width_constant(self, qtbot):
        from widgets.singer_pool import SingerPool
        assert SingerPool.EMPTY_POOL_WIDTH == 50

    def test_singer_pool_update_singers_adds_rows(self, qtbot):
        pool = self._make_pool(qtbot)
        s1 = _MockSinger(name="Anna", singer_id="a")
        s2 = _MockSinger(name="Bert", singer_id="b")
        # First call: initializes the pool, no width clamp.
        pool.update_singers([s1, s2])
        assert pool.table.rowCount() == 2

    def test_singer_pool_update_singers_skips_placed(self, qtbot):
        pool = self._make_pool(qtbot)
        s1 = _MockSinger(name="Anna", singer_id="a")
        s2 = _MockSinger(name="Bert", singer_id="b")
        # First call (initial), then test data.
        pool.update_singers([s1, s2])
        pool.update_singers([s1, s2], placed_ids={"a"})
        # Only s2 should be visible in the pool because s1 is placed.
        assert pool.table.rowCount() == 1

    def test_singer_pool_empty_after_shrinking(self, qtbot):
        from widgets.singer_pool import SingerPool as _SP
        pool = self._make_pool(qtbot)
        s1 = _MockSinger(name="Anna", singer_id="a")
        # First call: initializes.
        pool.update_singers([s1])
        # Second call with empty list: pool should collapse.
        pool.update_singers([])
        assert pool.table.rowCount() == 0
        # The pool's maximum width should be clamped to EMPTY_POOL_WIDTH.
        assert pool.maximumWidth() == _SP.EMPTY_POOL_WIDTH

    def test_singer_pool_expands_back_when_singer_added(self, qtbot):
        pool = self._make_pool(qtbot)
        # Initialize, then collapse.
        pool.update_singers([_MockSinger(singer_id="a")])
        pool.update_singers([])
        assert pool.maximumWidth() == 50
        # Add a singer back: clamp should be released.
        pool.update_singers([_MockSinger(singer_id="b")])
        assert pool.maximumWidth() > 50

    def test_singer_pool_add_singer_appends(self, qtbot):
        pool = self._make_pool(qtbot)
        # First update_singers is the initialization call.
        pool.update_singers([])
        s = _MockSinger(name="Anna", singer_id="a")
        pool.add_singer(s)
        assert s in pool.singers
        assert pool.table.rowCount() == 1

    def test_singer_pool_count_label_updates(self, qtbot):
        pool = self._make_pool(qtbot)
        # Initial call: no singers.
        pool.update_singers([])
        assert "0" in pool.pool_count_label.text()
        # Add a singer: label updates.
        pool.update_singers([_MockSinger(singer_id="a")])
        assert "1" in pool.pool_count_label.text()


# ---------------------------------------------------------------------------
# Regression: "Positionen tauschen" menu-action must enable on tile click
# ---------------------------------------------------------------------------
#
# Bug context (2026-06-13):
#   User marked two SingerTiles (left-click, no Ctrl), then opened the
#   "Bearbeiten" menu.  The action "Positionen tauschen" stayed greyed
#   out even though ``len(grid.selected_ids) == 2``.
#
# Root cause:
#   The grid's ``selection_changed`` Qt signal was only emitted from
#   ``FormationGrid.mousePressEvent`` / ``mouseReleaseEvent`` -- which
#   are never called for clicks on a child tile (Qt routes the event
#   to the tile directly).  So the MainWindow's ``update_swap_action``
#   slot was never invoked, leaving the QAction disabled.
#
# Fix in ``widgets/singer_tile.py``: ``mousePressEvent`` now emits
# ``parent_grid.selection_changed`` after updating the selection.
# The duck-typed ``hasattr`` check keeps the tile compatible with
# both the current main.py ``FormationGrid`` and the future
# ``widgets.formation_grid.FormationGrid``.

class _SelectionSignalHost(QObject):
    """Tiny QObject that exposes a real Qt ``selection_changed`` signal."""

    selection_changed = pyqtSignal()


class _MockGrid(QWidget):
    """Duck-typed stand-in for ``FormationGrid``.

    Inherits ``QWidget`` so ``SingerTile.setParent(grid)`` works.
    Carries the four attributes ``SingerTile`` touches:
    ``selected_ids``, ``update_selection_visuals``,
    ``is_group_dragging`` and ``selection_changed``.
    """

    def __init__(self):
        super().__init__()
        self.selected_ids = set()
        self._visuals_calls = 0
        self.is_group_dragging = False
        self._signal_host = _SelectionSignalHost()

    @property
    def selection_changed(self):
        return self._signal_host.selection_changed

    def update_selection_visuals(self):
        self._visuals_calls += 1


class TestSingerTileSelectionSignal:
    def test_left_click_emits_selection_changed(self, qtbot):
        from widgets.singer_tile import SingerTile
        from qt_compat import Qt, QMouseEvent, QEvent, QPointF

        grid = _MockGrid()
        singer = _MockSinger(singer_id="42")
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        tile.setParent(grid)  # so ``self.parent()`` returns the grid

        ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        with qtbot.waitSignal(grid.selection_changed, timeout=500):
            tile.mousePressEvent(ev)

        assert "42" in grid.selected_ids
        assert grid._visuals_calls == 1
        assert grid.is_group_dragging is False

    def test_ctrl_click_toggle_emits_selection_changed(self, qtbot):
        from widgets.singer_tile import SingerTile
        from qt_compat import Qt, QMouseEvent, QEvent, QPointF

        grid = _MockGrid()
        singer = _MockSinger(singer_id="7")
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        tile.setParent(grid)
        grid.selected_ids = {"7"}  # start selected

        ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
        )
        # We mock ``QApplication.keyboardModifiers`` because the
        # production code reads the *current* keyboard state instead
        # of the modifier attached to the synthetic QMouseEvent --
        # which is the correct behaviour for real OS events but
        # makes synthetic events hard to drive.  Patching it
        # lets us prove the toggle branch runs and the signal fires.
        from unittest.mock import patch
        from qt_compat import QApplication
        with patch.object(
            QApplication,
            "keyboardModifiers",
            return_value=Qt.KeyboardModifier.ControlModifier,
        ), qtbot.waitSignal(grid.selection_changed, timeout=500):
            tile.mousePressEvent(ev)
        # Ctrl+click on an already-selected singer removes it.
        assert "7" not in grid.selected_ids

    def test_no_grid_does_not_crash(self, qtbot):
        """If the tile has no grid parent, mousePress must be a no-op."""
        from widgets.singer_tile import SingerTile
        from qt_compat import Qt, QMouseEvent, QEvent, QPointF

        singer = _MockSinger(singer_id="42")
        tile = SingerTile(singer)
        qtbot.addWidget(tile)
        # No setParent() -- parent is None / not a grid.

        ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        # Must not raise.
        tile.mousePressEvent(ev)
