"""Tests for event management."""

import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEventDialog:
    """Tests for EventDialog."""

    def test_event_dialog_creation(self):
        """Test creating EventDialog."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        
        from chormanager.ui.dialogs import EventDialog
        dialog = EventDialog()
        assert dialog is not None


class TestAvailabilityDialog:
    """Tests for AvailabilityDialog."""

    def test_availability_dialog_creation(self):
        """Test creating AvailabilityDialog."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        
        from chormanager.ui.dialogs import AvailabilityDialog
        dialog = AvailabilityDialog(singer_id="test", event_id="test2")
        assert dialog is not None


class TestEventManagement:
    """Tests for event management in main window."""

    def test_create_event(self, tmp_path):
        """Test creating an event."""
        from PyQt6.QtWidgets import QApplication
        from chormanager.ui.main_window import MainWindow
        
        app = QApplication.instance() or QApplication([])
        db_path = tmp_path / "test.db"
        
        window = MainWindow(db_path=str(db_path))
        
        # Create an event
        from chormanager.domain.repository import EventRepository
        repo = EventRepository(window.db)
        event = repo.create(
            name="Probe",
            date="2026-05-01",
            event_type="probe"
        )
        
        assert event.name == "Probe"
        assert event.event_type == "probe"
        
        window.db.close()
