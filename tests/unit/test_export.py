"""Unit tests for Export/Sync module."""

import pytest
import json
import csv
from pathlib import Path

from chormanager.data.database import Database
from chormanager.export.sync import (
    export_singers_json,
    export_events_json,
    export_availability_json,
    export_singers_csv,
    export_all_sync,
    get_sync_dir
)


class TestExportSync:
    """Tests for sync export functions."""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db.connect()
        db.create_tables()
        yield db
        db.close()
    
    @pytest.fixture
    def singers_and_events(self, db):
        """Create test singers and events."""
        from chormanager.domain.repository import SingerRepository, EventRepository
        
        singer_repo = SingerRepository(db)
        singer1 = singer_repo.create(full_name="Test Singer 1", short_name="Singer1", voice_group="Sopran 1")
        singer2 = singer_repo.create(full_name="Test Singer 2", short_name="Singer2", voice_group="Sopran 2")
        
        event_repo = EventRepository(db)
        event1 = event_repo.create(name="Test Event 1", date="2026-05-15", event_type="gp")
        
        return [singer1, singer2], [event1]
    
    def test_get_sync_dir(self):
        """Test getting sync directory."""
        sync_dir = get_sync_dir()
        
        assert sync_dir.name == "data"
    
    def test_export_singers_json(self, db, singers_and_events, tmp_path):
        """Test exporting singers to JSON."""
        singers, events = singers_and_events
        
        output_path = tmp_path / "singers.json"
        result = export_singers_json(db, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 2
        assert data[0]["name"] == "Singer1"
        assert data[0]["voice_group"] == "Sopran 1"
        assert "singer_id" in data[0]
    
    def test_export_singers_json_fields(self, db, singers_and_events, tmp_path):
        """Test that singer JSON has required fields."""
        singers, events = singers_and_events
        
        output_path = tmp_path / "singers.json"
        export_singers_json(db, output_path)
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        required_fields = ["singer_id", "name", "voice_group", "affinity"]
        for field in required_fields:
            assert field in data[0]
    
    def test_export_events_json(self, db, singers_and_events, tmp_path):
        """Test exporting events to JSON."""
        singers, events = singers_and_events
        
        output_path = tmp_path / "events.json"
        result = export_events_json(db, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["name"] == "Test Event 1"
        assert data[0]["event_type"] == "gp"
        assert "event_id" in data[0]
    
    def test_export_availability_json(self, db, singers_and_events, tmp_path):
        """Test exporting availability matrix."""
        singers, events = singers_and_events
        from chormanager.domain.repository import AvailabilityRepository
        
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(singers[0].id, events[0].id, "yes")
        
        output_path = tmp_path / "availability.json"
        export_availability_json(db, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["event_name"] == "Test Event 1"
        assert len(data[0]["availability"]) == 2
        
        yes_avail = [a for a in data[0]["availability"] if a["status"] == "yes"]
        assert len(yes_avail) == 1
    
    def test_export_singers_csv(self, db, singers_and_events, tmp_path):
        """Test exporting singers to CSV."""
        singers, events = singers_and_events
        
        output_path = tmp_path / "singers.csv"
        result = export_singers_csv(db, output_path)
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0] == ["singer_id", "name", "voice_group", "affinity"]
        assert rows[1][1] == "Singer1"
    
    def test_export_all_sync(self, db, singers_and_events, tmp_path):
        """Test exporting all sync files."""
        singers, events = singers_and_events
        from chormanager.domain.repository import AvailabilityRepository
        
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(singers[0].id, events[0].id, "yes")
        
        result = export_all_sync(db)
        
        assert "singers" in result
        assert "termine" in result
        assert "verfuegbarkeit" in result
        assert "csv_fallback" in result
        
        assert result["singers"].exists()
        assert result["termine"].exists()
        assert result["verfuegbarkeit"].exists()
        assert result["csv_fallback"].exists()