"""TDD RED: Initial window-size regression.

Pinned-down defaults (2026-06-13, user request):

* ChorManager  : ``setGeometry(80, 80, 1024, 768)``
* ChorAufstellung: ``self.resize(1280, 768)``

Why these specific values?
  * 1024x768 is the de-facto "fits on every laptop" baseline and
    gives a comfortable default for the 4-tab main window.
  * 1280x768 for the choraufstellung plugin leaves room for the
    singer pool on the left and at least ~1100 px for the grid --
    the M-2 resize-bug fix relies on the QScrollArea being able to
    show more than the 5.5 columns the old 1100 px window allowed.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from pathlib import Path

import pytest

# Make sure ``from chormanager...`` resolves whether the test is
# invoked from the repo root or from inside tests/.
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


# ---------------------------------------------------------------------------
# ChorManager  ->  setGeometry(80, 80, 1024, 768)
# ---------------------------------------------------------------------------

class TestChorManagerWindowSize:
    """ChorManager main window must open at 1024x768 px, top-left (80,80)."""

    def test_main_window_geometry(self, qtbot, tmp_path):
        from chormanager.ui.main_window import MainWindow
        db_path = tmp_path / "test_geom.db"
        window = MainWindow(db_path=str(db_path))
        qtbot.addWidget(window)

        x, y, w, h = window.geometry().getRect()
        assert (x, y) == (80, 80), (
            f"ChorManager position is {(x, y)}, expected (80, 80)"
        )
        assert w == 1024, f"ChorManager width is {w}, expected 1024"
        assert h == 768, f"ChorManager height is {h}, expected 768"

        window.close()


# ---------------------------------------------------------------------------
# ChorAufstellung  ->  self.resize(1280, 768)
# ---------------------------------------------------------------------------

@pytest.fixture
def choraufstellung_window(qtbot, tmp_path):
    """Build a fresh ChorAufstellung MainWindow.

    Uses ``chormanager_mode=True`` with a tmp database so the
    constructor skips the (slow, side-effectful) recovery check
    that runs in standalone mode.  The initial size is set in
    ``__init__`` *before* either branch runs, so it is observable
    here.
    """
    from chormanager.choraufstellung.main import MainWindow
    db_path = tmp_path / "chorauf.db"
    window = MainWindow(
        chormanager_mode=True,
        project_name="T",
        event_date="2026-06-13",
        event_name="Test",
        db_path=str(db_path),
        event_id="1",
        event_type="c",
    )
    qtbot.addWidget(window)
    yield window
    window.close()


class TestChorAufstellungWindowSize:
    """ChorAufstellung plugin must open at 1280x768 px."""

    def test_initial_size_is_1280x768(self, choraufstellung_window):
        w = choraufstellung_window
        assert w.width() == 1280, (
            f"ChorAufstellung width is {w.width()}, expected 1280"
        )
        assert w.height() == 768, (
            f"ChorAufstellung height is {w.height()}, expected 768"
        )
