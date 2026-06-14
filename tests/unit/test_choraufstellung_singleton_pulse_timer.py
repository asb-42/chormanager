"""TDD RED: CC4-FIX-A — Singleton-Search-Pulse-Timer.

Previously, every call to :meth:`FormationGrid.highlight_singer` would
create a *new* ``QTimer``. If the user typed into the search box
faster than the previous pulse finished, the old timer would still
tick and the new one would overlap, leading to visual chaos and
``RuntimeWarning: QObject: Cannot create children for a parent that is
in a different thread``.

CC4-FIX-A ensures the timer is created *once* in ``__init__`` and
re-used (with ``stop()`` before ``start()``) on every call.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def _make_grid(qapp, rows=2, cols=3):
    from chormanager.choraufstellung.widgets.formation_grid import FormationGrid
    g = FormationGrid(rows=rows, cols=cols)
    return g


def test_init_creates_search_pulse_timer(qapp):
    """The pulse timer must exist on a freshly-built grid, not be created
    on demand inside ``highlight_singer``."""
    g = _make_grid(qapp)
    # The attribute is initialised but may be None (no active pulse yet).
    assert hasattr(g, "_search_pulse_timer"), (
        "CC4-FIX-A: _search_pulse_timer must be a member, not created on demand"
    )


def test_highlight_singer_does_not_replace_timer(qapp, monkeypatch):
    """``highlight_singer`` must NOT allocate a *new* ``QTimer`` when
    the singer is missing from the grid (early-return path)."""
    from PyQt6.QtCore import QTimer
    orig_init = QTimer.__init__
    counter = {"n": 0}

    def counting_init(self, *a, **kw):
        counter["n"] += 1
        orig_init(self, *a, **kw)

    monkeypatch.setattr(QTimer, "__init__", counting_init)

    # Build the grid AFTER the patch so the __init__ timer is counted.
    g = _make_grid(qapp, rows=2, cols=2)
    assert counter["n"] == 1, (
        f"Expected exactly one QTimer (from __init__), got {counter['n']}"
    )

    class _S:
        singer_id = "missing"
    g.highlight_singer(_S(), None)
    g.highlight_singer(_S(), None)
    # Must still be 1: no new timer on early-return.
    assert counter["n"] == 1, (
        f"CC4-FIX-A: highlight_singer allocated {counter['n']} timers; "
        "expected exactly 1 (the one from __init__)."
    )
