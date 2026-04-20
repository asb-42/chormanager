"""Tests for main window."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_app(qtbot):
    """Create mock application for testing."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qtbot, tmp_path):
    """Create main window for testing."""
    from chormanager.ui.main_window import MainWindow
    
    # Create a temporary database
    db_path = tmp_path / "test.db"
    
    window = MainWindow(db_path=str(db_path))
    qtbot.addWidget(window)
    
    yield window
    
    window.close()


class TestMainWindow:
    """Tests for MainWindow."""

    def test_window_title(self, main_window):
        """Test window has correct title."""
        assert "ChorManager" in main_window.windowTitle()

    def test_singers_table_exists(self, main_window):
        """Test singers table is created."""
        from PyQt6.QtWidgets import QTableWidget
        table = main_window.findChild(QTableWidget)
        assert table is not None

    def test_add_button_exists(self, main_window):
        """Test add button exists."""
        from PyQt6.QtWidgets import QPushButton
        buttons = main_window.findChildren(QPushButton)
        assert any(b.text() == "Hinzufügen" for b in buttons)

    def test_menu_exists(self, main_window):
        """Test menu bar exists."""
        menu_bar = main_window.menuBar()
        assert menu_bar is not None
        assert menu_bar.actions() is not None
