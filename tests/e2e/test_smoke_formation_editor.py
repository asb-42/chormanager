"""Smoke 1 (MS3): Formation Editor paritätisch (M0-Spec, aktiv ab M3).

Quelle: docs/plans/2026-09-26_m0_erd-openapi.md §4 + MS3-Akzeptanz
(Analyse §4): Pool→Grid, Swap, Gruppen-Drag, Rubber-Band, Undo,
Optimizer-Diff — je 1 Playwright-Test. Abnahmegerät: Notebook mit
Maus/Trackpad (Analyse §5.1); kein Mobile-Smoke.

Jeder Test ist ein ausführbarer Schritt-Plan; die Selektoren
(``data-testid``) vergibt das Frontend in M2/M3 danach.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Web-App (M1-M3) ausstehend: Smoke 1 aktiv ab M3"
)


def test_drag_pool_to_grid_places_tile(web_page, seeded_formation):
    """Pool→Grid: Kachel aus dem Pool auf eine freie Zelle ziehen
    (dnd-kit) → Sänger steht auf (row, col), Poolzähler sinkt."""


def test_drop_on_occupied_cell_swaps(web_page, seeded_formation):
    """Drop auf belegte Zelle: Bewohner und gezogene Kachel tauschen
    die Plätze (Desktop-``dropEvent``-Semantik, §2.2)."""


def test_group_drag_moves_selection(web_page, seeded_formation):
    """Rubber-Band-Mehrfachselektion + Gruppen-Drag: alle Kacheln
    wandern um dasselbe Delta; am Rand Vorab-Validierung
    (Desktop-``MoveGroupCommand``-Semantik)."""


def test_rubber_band_selects_tiles(web_page, seeded_formation):
    """Leere Fläche + Ziehen: Rubber-Band-Rechteck selektiert alle
    geschnittenen Kacheln (``selection_changed``)."""


def test_undo_redo_after_move(web_page, seeded_formation):
    """Ctrl+Z / Ctrl+Shift+Z nach Move: Grid stellt Vorzustand her
    (TS-Port von ``core/commands.py``)."""


def test_optimizer_diff_and_apply(web_page, seeded_formation):
    """Optimizer-Dialog: ``POST /formations/{id}/optimize`` zeigt
    ``swap_count``/``cost`` + Vorher/Nachher-Diff; „Übernehmen"
    pusht auf den Undo-Stack (Analyse §3.3)."""
