# TDD: SingerPool auto-shrink behavior.
#
# The choraufstellung MainWindow uses a QSplitter with the SingerPool on
# the left and the FormationGrid on the right. The user reports that for
# 2x16 grids (~2200 px wide) the splitter does not give the grid enough
# room - only ~5.5 columns are visible, even when the user enlarges the
# window.
#
# Part of the diagnosis is that the SingerPool, when empty, claims a
# relatively wide chunk of the splitter (~250 px by default). To make
# the grid more usable, the pool must auto-shrink to a narrow strip
# (~50 px) when empty, and expand back to the default when a singer is
# moved back into the pool.
"""
Regression tests for SingerPool auto-shrink behavior.

The pool must:
  * shrink to ~50 px wide when empty (no singers in the pool)
  * expand back to its default width as soon as a singer is in the pool
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Constants mirror the implementation (kept in sync deliberately)
# ---------------------------------------------------------------------------
EMPTY_POOL_WIDTH = 50
#: Anything strictly larger than EMPTY_POOL_WIDTH is considered
#: "default" (non-shrunk).  We don't pin a specific value because the
#: exact default depends on the table's column widths.
NON_EMPTY_POOL_MIN = 200


def _make_pool(qtbot):
    """Import + instantiate the SingerPool widget."""
    from chormanager.choraufstellung.ui.pool_widget import SingerPool
    pool = SingerPool()
    qtbot.addWidget(pool)
    return pool


def _make_singer(name="S1", vg="Sopran 1", sid=None):
    """Create a real Singer instance for the pool."""
    from chormanager.choraufstellung.singer_model import Singer, VoiceGroup
    return Singer(
        name=name,
        voice_group=VoiceGroup(vg),
        singer_id=sid or name,
    )


# ---------------------------------------------------------------------------
# Empty pool -> shrink
# ---------------------------------------------------------------------------


class TestEmptyPoolShrinks:
    """When the pool is empty it must collapse to a narrow strip."""

    def test_empty_pool_has_maximum_width_50(self, qtbot):
        pool = _make_pool(qtbot)
        # Prime the pool (simulating MainWindow.setup_ui calling
        # update_singers with empty singers at construct time).
        pool.update_singers([], placed_ids=set())
        # Now drive it empty again - the second call must shrink.
        pool.update_singers([], placed_ids=set())
        assert pool.maximumWidth() == EMPTY_POOL_WIDTH

    def test_empty_pool_has_minimum_width_50(self, qtbot):
        pool = _make_pool(qtbot)
        # Prime: see comment in test_empty_pool_has_maximum_width_50.
        pool.update_singers([], placed_ids=set())
        pool.update_singers([], placed_ids=set())
        assert pool.minimumWidth() == EMPTY_POOL_WIDTH

    def test_empty_pool_after_clearing_all_singers(self, qtbot):
        """If all singers are placed, the pool becomes empty and shrinks."""
        s1 = _make_singer(name="Alice", sid="1")
        s2 = _make_singer(name="Bob", sid="2")
        pool = _make_pool(qtbot)
        # First populate, then mark all as placed
        pool.update_singers([s1, s2], placed_ids=set())
        # After populating with no placed_ids, both are in the pool (not shrunk)
        # Now mark both as placed
        pool.update_singers([s1, s2], placed_ids={"1", "2"})
        assert pool.maximumWidth() == EMPTY_POOL_WIDTH


# ---------------------------------------------------------------------------
# Non-empty pool -> expand
# ---------------------------------------------------------------------------


class TestNonEmptyPoolExpands:
    """When at least one singer is in the pool, default width is restored."""

    def test_pool_with_singer_has_no_maximum_width_constraint(self, qtbot):
        s1 = _make_singer(name="Alice", sid="1")
        pool = _make_pool(qtbot)
        pool.update_singers([s1], placed_ids=set())
        # maximumWidth() returns 16777215 (QWIDGETSIZE_MAX) when unconstrained
        assert pool.maximumWidth() >= NON_EMPTY_POOL_MIN

    def test_pool_with_singer_clamp_released(self, qtbot):
        """When a singer is in the pool, the max-width must be
        unconstrained (i.e. QWIDGETSIZE_MAX), which proves the
        empty-pool clamp has been released.
        """
        s1 = _make_singer(name="Alice", sid="1")
        pool = _make_pool(qtbot)
        pool.update_singers([s1], placed_ids=set())
        # 16777215 is QWIDGETSIZE_MAX in Qt.
        assert pool.maximumWidth() == 16777215

    def test_pool_with_one_singer_among_many_placed_expands(self, qtbot):
        """One singer unplaced among many placed -> pool must show that singer."""
        s_placed1 = _make_singer(name="P1", sid="p1")
        s_placed2 = _make_singer(name="P2", sid="p2")
        s_unplaced = _make_singer(name="U1", sid="u1")
        pool = _make_pool(qtbot)
        pool.update_singers(
            [s_placed1, s_placed2, s_unplaced],
            placed_ids={"p1", "p2"},
        )
        # s_unplaced is in the pool -> pool must NOT be shrunk
        assert pool.maximumWidth() >= NON_EMPTY_POOL_MIN


# ---------------------------------------------------------------------------
# Round-trip: shrink -> expand -> shrink
# ---------------------------------------------------------------------------


class TestPoolWidthRoundTrip:
    """The width must follow the empty/non-empty state of the pool."""

    def test_shrink_then_expand_then_shrink(self, qtbot):
        s1 = _make_singer(name="Alice", sid="1")
        pool = _make_pool(qtbot)

        # 0) Prime: first call is a no-op (skipped to avoid QSplitter
        # propagateSizeHints hang during construction).
        pool.update_singers([], placed_ids=set())

        # 1) start empty -> shrunk
        pool.update_singers([], placed_ids=set())
        assert pool.maximumWidth() == EMPTY_POOL_WIDTH

        # 2) add a singer -> expand
        pool.update_singers([s1], placed_ids=set())
        assert pool.maximumWidth() == 16777215  # QWIDGETSIZE_MAX

        # 3) remove the singer -> shrink again
        pool.update_singers([], placed_ids=set())
        assert pool.maximumWidth() == EMPTY_POOL_WIDTH

    def test_shrink_then_partially_place_then_shrink(self, qtbot):
        """A singer placed back into the grid (via placed_ids update) shrinks
        the pool again."""
        s1 = _make_singer(name="Alice", sid="1")
        pool = _make_pool(qtbot)

        pool.update_singers([s1], placed_ids=set())
        assert pool.maximumWidth() >= NON_EMPTY_POOL_MIN

        # Place Alice on the grid -> pool becomes empty -> shrink
        pool.update_singers([s1], placed_ids={"1"})
        assert pool.maximumWidth() == EMPTY_POOL_WIDTH


# ---------------------------------------------------------------------------
# Multiple singers (e.g. 31 singers, 0 placed -> all in pool)
# ---------------------------------------------------------------------------


class TestPoolWidthWithManySingers:
    """A pool with many singers must not be shrunk."""

    def test_31_singers_zero_placed_pool_not_shrunk(self, qtbot):
        singers = [
            _make_singer(name=f"S{i:02d}", sid=str(i)) for i in range(31)
        ]
        pool = _make_pool(qtbot)
        pool.update_singers(singers, placed_ids=set())
        assert pool.maximumWidth() >= NON_EMPTY_POOL_MIN



# ---------------------------------------------------------------------------
# Regression test: the SingerPool in main.py is the ACTIVE one in the
# choraufstellung subshell. It must have the same auto-shrink behavior
# as the duplicate in ui/pool_widget.py.
# ---------------------------------------------------------------------------


class TestMainPySingerPoolAutoShrinks:
    """The ``SingerPool`` defined in main.py must auto-shrink too.

    M-2 Schritt 5 (planned) will extract this widget into its own
    module, but until then both copies must behave identically.
    """

    def test_main_py_singer_pool_has_empty_pool_width_constant(self):
        from chormanager.choraufstellung.main import SingerPool
        assert hasattr(SingerPool, "EMPTY_POOL_WIDTH")
        assert SingerPool.EMPTY_POOL_WIDTH == EMPTY_POOL_WIDTH

    def test_main_py_singer_pool_shrinks_when_empty(self, qtbot):
        from chormanager.choraufstellung.main import SingerPool
        pool = SingerPool()
        qtbot.addWidget(pool)
        # Prime: see comment in the ui/pool_widget.py test.
        pool.update_singers([], placed_ids=set())
        pool.update_singers([], placed_ids=set())
        assert pool.maximumWidth() == EMPTY_POOL_WIDTH
        assert pool.minimumWidth() == EMPTY_POOL_WIDTH

    def test_main_py_singer_pool_expands_when_non_empty(self, qtbot):
        from chormanager.choraufstellung.main import SingerPool
        pool = SingerPool()
        qtbot.addWidget(pool)
        s1 = _make_singer(name="Alice", sid="1")
        pool.update_singers([s1], placed_ids=set())
        # 16777215 is QWIDGETSIZE_MAX in Qt.
        assert pool.maximumWidth() == 16777215
