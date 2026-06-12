"""TDD RED: Regression test for the 'Window too small for 2x16 grid' bug.

Reported 2026-06-12 by user:
  * Aufstellung mit 31 Saengern, Raster 2 Reihen + 16 Spalten
  * Beim Oeffnen: Fenster zeigt nur 5.5 Spalten + halbe Spalte rechts
  * Auch nach Vergroessern des Fensters: nur 5.5 Spalten sichtbar
  * Workaround: Raster auf 2x17 vergroessern, komplettes Raster wird
    angezeigt, dann zurueck auf 2x16.

Verdict: Pre-existing display bug in the choraufstellung subapp,
NOT introduced by M-1 or M-2 refactor.

This test pins down the contract:
  * When set_dimensions(rows=2, cols=16) is called on a FormationGrid
    instance whose parent is a MainWindow with a QScrollArea wrapper,
    the grid must keep a width that is reasonable for 16 columns.
  * Specifically, the QScrollArea must show the full grid width if
    the user enlarges the MainWindow; it must NOT be stuck at the
    initial 1100 px window width.

We approximate this by checking that after MainWindow resize the
QScrollArea's viewport width grows.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import pytest
from PyQt6.QtWidgets import QApplication


_app = QApplication.instance() or QApplication(sys.argv)


class TestFormationGridMinimumSize:
    """FormationGrid must announce a minimum size that scales with cols/rows."""

    def test_minimum_size_2x16(self):
        """For 2 rows x 16 cols, minimum width must be much larger than
        the 1100 px initial MainWindow size (else the window can't
        show the full grid even when enlarged)."""
        from chormanager.choraufstellung.main import FormationGrid
        g = FormationGrid(2, 16)
        # CELL_WIDTH=130, MARGIN_LEFT=80, +50 padding
        # = 16 * 130 + 80 + 50 = 2210 px
        assert g.minimumWidth() >= 16 * 130 + 80 + 50, (
            f"FormationGrid 2x16 minimumWidth is {g.minimumWidth()}, "
            f"expected >= 2210 px. Bug: minimumWidth does not scale "
            f"with columns."
        )

    def test_set_dimensions_updates_minimum(self):
        """set_dimensions(2, 16) must update minimumWidth accordingly."""
        from chormanager.choraufstellung.main import FormationGrid
        g = FormationGrid(2, 5)
        g.set_dimensions(2, 16)
        assert g.minimumWidth() >= 16 * 130 + 80 + 50, (
            f"After set_dimensions(2, 16), minimumWidth is "
            f"{g.minimumWidth()}, expected >= 2210 px."
        )


class TestMainWindowResizeUnblocksGrid:
    """When the user enlarges the MainWindow, the QScrollArea wrapping
    the FormationGrid must grow with the window, so the user can scroll
    the full grid into view."""

    def test_splitter_right_pane_takes_most_space(self, tmp_path, monkeypatch, qtbot):
        """With a 2x16 grid, the right pane of the splitter must be
        large enough to show the full grid (or close to it). The bug
        was: the splitter was stuck at ~640 px regardless of window
        size, showing only ~5 columns. After the fix the right pane
        must be wider than the pool pane."""
        from chormanager.choraufstellung.main import MainWindow
        from PyQt6.QtWidgets import QSplitter

        monkeypatch.setattr(
            "chormanager.choraufstellung.config.get_data_dir",
            lambda: str(tmp_path),
        )

        w = MainWindow(chormanager_mode=False)
        qtbot.addWidget(w)
        w.show()
        _app.processEvents()
        w.grid.set_dimensions(2, 16)
        # Give the layout a moment to recalculate
        _app.processEvents()

        sps = w.findChildren(QSplitter)
        assert len(sps) == 1
        sp = sps[0]
        sizes = sp.sizes()
        assert len(sizes) == 2
        # The right pane (grid) must be at least as wide as the pool,
        # and there must be horizontal scroll-room in the grid's
        # QScrollArea. The pool starts at 250 px; the grid must
        # claim the rest.
        assert sizes[1] > sizes[0], (
            f"Splitter sizes are {sizes}; the grid pane (right) is "
            f"smaller than the pool pane (left). This is the bug: the "
            f"right side does not grow even though the window has "
            f"plenty of space."
        )

    def test_grid_horizontal_scrollbar_has_range(self, tmp_path, monkeypatch, qtbot):
        """For a 2x16 grid (~2210 px wide), the QScrollArea around
        the grid must expose a non-zero horizontal scroll range so
        the user can pan to the rightmost columns."""
        from chormanager.choraufstellung.main import MainWindow
        from PyQt6.QtWidgets import QScrollArea

        monkeypatch.setattr(
            "chormanager.choraufstellung.config.get_data_dir",
            lambda: str(tmp_path),
        )

        w = MainWindow(chormanager_mode=False)
        qtbot.addWidget(w)
        w.show()
        _app.processEvents()
        w.grid.set_dimensions(2, 16)
        _app.processEvents()

        sas = w.findChildren(QScrollArea)
        assert sas
        hbar = sas[0].horizontalScrollBar()
        # The grid is 16 * 130 + 80 + 50 = 2210 px wide. The scroll
        # bar must report a range > 0, i.e. there is overflow to
        # scroll. If the bar's maximum is 0, the user cannot reach
        # the rightmost columns.
        assert hbar.maximum() > 0, (
            f"QScrollArea horizontal scroll maximum is 0; the user "
            f"cannot pan to the rightmost columns. grid.minimumWidth="
            f"{w.grid.minimumWidth()}, viewport.width="
            f"{sas[0].viewport().width()}. This is the 'Window too "
            f"small' bug."
        )
