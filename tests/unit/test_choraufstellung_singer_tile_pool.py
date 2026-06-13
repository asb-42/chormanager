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
