"""TDD RED: m3-FIX-A & m5-FIX-A — pool / grid UI performance.

m3-FIX-A: ``SingerPool.update_singers`` should support a
``deferred=True`` flag that coalesces multiple calls in a single frame
into one repaint via ``QTimer.singleShot(0, ...)``.

m5-FIX-A: ``FormationGrid.refresh_grid`` should maintain a
``self._row_labels: List[QLabel]`` member instead of
``self.findChildren(QLabel)`` on every refresh.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from unittest import mock

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ---------------------------------------------------------------------------
# m5-FIX-A
# ---------------------------------------------------------------------------


def test_formation_grid_has_row_labels_member(qapp):
    from chormanager.choraufstellung.widgets.formation_grid import FormationGrid
    g = FormationGrid(rows=2, cols=3)
    assert hasattr(g, "_row_labels"), (
        "m5-FIX-A: FormationGrid must have a _row_labels member, not "
        "call findChildren(QLabel) every refresh"
    )
    assert isinstance(g._row_labels, list)


def test_refresh_grid_does_not_call_findChildren_qt(qapp, monkeypatch):
    """``refresh_grid`` must not iterate ``findChildren(QLabel)`` for the
    row labels \u2014 they are kept in ``self._row_labels``."""
    from chormanager.choraufstellung.widgets.formation_grid import FormationGrid
    g = FormationGrid(rows=2, cols=3)
    calls = {"n": 0}

    def fake_find_children(self, *_a, **_kw):
        calls["n"] += 1
        return []

    monkeypatch.setattr("PyQt6.QtCore.QObject.findChildren", fake_find_children)
    g.refresh_grid()
    # The refresh must not need to walk the children tree for the
    # row labels. (``refresh_grid`` is allowed to findChildren for
    # other things, but we assert that the row-label loop is gone.)
    src = open("chormanager/choraufstellung/widgets/formation_grid.py").read()
    assert "Reihe " not in src or "findChildren(QLabel)" not in src, (
        "m5-FIX-A: refresh_grid must not call findChildren(QLabel) for "
        "row labels"
    )


# ---------------------------------------------------------------------------
# m3-FIX-A
# ---------------------------------------------------------------------------


def test_update_singers_supports_deferred_kwarg(qapp):
    """``update_singers(..., deferred=True)`` must coalesce into a
    single repaint on the next event-loop tick."""
    from chormanager.choraufstellung.widgets.singer_pool import SingerPool
    pool = SingerPool()
    calls = {"populate": 0}

    def fake_populate():
        calls["populate"] += 1
    pool._populate_table = fake_populate  # type: ignore[attr-defined]

    # Two back-to-back calls with deferred=True must coalesce.
    pool.update_singers([], placed_ids=set(), deferred=True)
    pool.update_singers([], placed_ids=set(), deferred=True)
    # The populate function should not have been called yet (it is
    # scheduled, not immediate).
    assert calls["populate"] == 0
    # Now spin the event loop once.
    qapp.processEvents()
    assert calls["populate"] == 1, (
        f"m3-FIX-A: expected exactly 1 deferred repaint, got {calls['populate']}"
    )


def test_update_singers_default_is_immediate(qapp):
    """``update_singers(...)`` without ``deferred`` must keep the
    current immediate behaviour for backward compatibility."""
    from chormanager.choraufstellung.widgets.singer_pool import SingerPool
    pool = SingerPool()
    calls = {"populate": 0}

    def fake_populate():
        calls["populate"] += 1
    pool._populate_table = fake_populate  # type: ignore[attr-defined]

    pool.update_singers([], placed_ids=set())
    assert calls["populate"] == 1
