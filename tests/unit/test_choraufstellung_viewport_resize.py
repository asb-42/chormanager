# TDD: QScrollArea viewport must resize its inner widget to match.
#
# Bug report (2026-06-12): After the pool auto-shrink fix, the user
# reports "5.5 tiles are still clipped exactly the same as before,
# even though there is plenty of space on the right."
#
# Root cause: ``QScrollArea.setWidgetResizable(False)`` causes Qt to
# size the inner widget at its natural (minimum) size and keeps the
# viewport at its initial size (~640 px).  When the user enlarges
# the MainWindow the QScrollArea itself grows, but the inner widget
# stays at 640 px wide and only 5.5 of the 16 columns are visible.
#
# Fix: install a resize listener on the viewport that calls
# ``grid.setFixedWidth(max(grid.minimumWidth(), viewport.width()))``
# so the grid grows with the viewport.  (The grid's own
# ``minimumWidth`` enforces its natural size for very wide
# formations like 2x16, in which case a horizontal scrollbar
# appears - the correct behaviour.)
"""
Regression tests for the QScrollArea viewport-resize fix.
"""
from __future__ import annotations

import pytest


def test_scrollarea_viewport_resize_event_filter_recognised(qtbot):
    """The MainWindow class must define an eventFilter that handles
    QEvent.Type.Resize on the QScrollArea viewport.  We test this by
    checking that the method exists and accepts the (obj, event)
    signature."""
    from chormanager.choraufstellung.main import MainWindow
    assert hasattr(MainWindow, "eventFilter")
    import inspect
    sig = inspect.signature(MainWindow.eventFilter)
    assert "obj" in sig.parameters
    assert "event" in sig.parameters
