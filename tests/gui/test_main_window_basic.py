"""Basic smoke tests for MainWindow."""

import pytest
from chormanager.data.database import Database
from chormanager.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot, tmp_path):
    """Create MainWindow for testing with temp database."""
    db_path = str(tmp_path / "test.db")
    win = MainWindow(db_path=db_path)
    qtbot.addWidget(win)
    yield win
    win.db.close()


class TestMainWindowSmoke:
    """Basic smoke tests for MainWindow."""

    def test_window_creation(self, qtbot, window):
        """Window can be created without errors."""
        assert window.windowTitle() == "ChorManager"

    def test_window_has_central_widget(self, qtbot, window):
        """Window has a central widget."""
        assert window.centralWidget() is not None

    def test_window_has_menubar(self, qtbot, window):
        """Window has a menu bar."""
        assert window.menuBar() is not None

    def test_window_has_statusbar(self, qtbot, window):
        """Window has a status bar."""
        assert window.statusBar() is not None

    def test_window_has_tabs(self, qtbot, window):
        """Window has tab views."""
        assert hasattr(window, "projects_tab")
        assert hasattr(window, "singers_tab")
        assert hasattr(window, "events_tab")

    def test_switch_view(self, qtbot, window):
        """Can switch between views."""
        window._switch_view(1)
        assert window.content_stack.currentIndex() == 1
        window._switch_view(0)
        assert window.content_stack.currentIndex() == 0

    def test_set_light_theme(self, qtbot, window):
        """Light theme can be applied."""
        window._set_light_theme()
        assert window.styleSheet() != ""

    def test_set_dark_theme(self, qtbot, window):
        """Dark theme can be applied."""
        window._set_dark_theme()
        assert window.styleSheet() != ""
