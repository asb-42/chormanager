"""Unit tests for Event model and repository."""

import pytest
from datetime import datetime

from chormanager.domain.models import Event
from chormanager.data.database import Database


class TestEventModel:
    """Tests for Event model."""
    
    def test_create_event(self):
        """Test creating a new event."""
        event = Event(
            name="Test Event",
            date="2026-05-15",
            event_type="gp",
            project_id="project-123"
        )
        
        assert event.name == "Test Event"
        assert event.date == "2026-05-15"
        assert event.event_type == "gp"
        assert event.project_id == "project-123"
    
    def test_event_without_project(self):
        """Test event without project_id."""
        event = Event(
            name="Standalone Event",
            date="2026-05-15",
            event_type="probe"
        )
        
        assert event.name == "Standalone Event"
        assert event.project_id is None
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = Event(
            id="event-123",
            name="Test Event",
            date="2026-05-15",
            event_type="gp",
            project_id="project-123",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00"
        )
        
        data = event.to_dict()
        
        assert data["id"] == "event-123"
        assert data["name"] == "Test Event"
        assert data["project_id"] == "project-123"
    
    def test_event_is_past(self):
        """Test checking if event is in the past."""
        event = Event(
            id="event-123",
            name="Test Event",
            date="2020-01-01",
            event_type="gp"
        )
        
        assert event.is_past is True


class TestEventRepository:
    """Tests for EventRepository."""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db.connect()
        db.create_tables()
        yield db
        db.close()
    
    def test_create_event_with_project(self, db):
        """Test creating an event with a project."""
        from chormanager.domain.repository import ProjectRepository, EventRepository
        
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Test Project")
        
        event_repo = EventRepository(db)
        event = event_repo.create(
            name="Test Event",
            date="2026-05-15",
            event_type="gp",
            project_id=project.id
        )
        
        assert event.name == "Test Event"
        assert event.project_id == project.id
    
    def test_get_events_by_project(self, db):
        """Test getting events by project."""
        from chormanager.domain.repository import ProjectRepository, EventRepository
        
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Test Project")
        other_project = project_repo.create(name="Other Project")
        
        event_repo = EventRepository(db)
        event_repo.create(name="Event 1", date="2026-05-15", event_type="gp", project_id=project.id)
        event_repo.create(name="Event 2", date="2026-05-16", event_type="op", project_id=project.id)
        event_repo.create(name="Other Event", date="2026-05-17", event_type="probe", project_id=other_project.id)
        
        events = event_repo.get_all()
        project_events = [e for e in events if e.project_id == project.id]
        
        assert len(project_events) == 2
    
    def test_update_event_project(self, db):
        """Test updating event's project."""
        from chormanager.domain.repository import ProjectRepository, EventRepository
        
        project_repo = ProjectRepository(db)
        project1 = project_repo.create(name="Project 1")
        project2 = project_repo.create(name="Project 2")
        
        event_repo = EventRepository(db)
        event = event_repo.create(
            name="Test Event",
            date="2026-05-15",
            event_type="gp",
            project_id=project1.id
        )
        
        event_repo.update(event.id, project_id=project2.id)
        
        updated = event_repo.get_by_id(event.id)
        assert updated.project_id == project2.id


class TestAvailabilityRepository:
    """Tests for AvailabilityRepository."""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db.connect()
        db.create_tables()
        yield db
        db.close()
    
    def test_create_availability(self, db):
        """Test creating availability."""
        from chormanager.domain.repository import SingerRepository, EventRepository, AvailabilityRepository
        
        singer_repo = SingerRepository(db)
        singer = singer_repo.create(full_name="Test Singer", voice_group="Sopran 1")
        
        event_repo = EventRepository(db)
        event = event_repo.create(name="Test Event", date="2026-05-15", event_type="gp")
        
        avail_repo = AvailabilityRepository(db)
        avail = avail_repo.update(singer.id, event.id, "yes")
        
        assert avail.singer_id == singer.id
        assert avail.event_id == event.id
        assert avail.status == "yes"
    
    def test_get_availability_by_singer(self, db):
        """Test getting availability by singer."""
        from chormanager.domain.repository import SingerRepository, EventRepository, AvailabilityRepository
        
        singer_repo = SingerRepository(db)
        singer = singer_repo.create(full_name="Test Singer", voice_group="Sopran 1")
        
        event_repo = EventRepository(db)
        event = event_repo.create(name="Test Event", date="2026-05-15", event_type="gp")
        
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(singer.id, event.id, "yes")
        
        availabilities = avail_repo.get_by_singer(singer.id)
        
        assert len(availabilities) == 1
        assert availabilities[0].status == "yes"
    
    def test_get_availability_by_event(self, db):
        """Test getting availability by event."""
        from chormanager.domain.repository import SingerRepository, EventRepository, AvailabilityRepository
        
        singer_repo = SingerRepository(db)
        singer1 = singer_repo.create(full_name="Singer 1", voice_group="Sopran 1")
        singer2 = singer_repo.create(full_name="Singer 2", voice_group="Sopran 2")
        
        event_repo = EventRepository(db)
        event = event_repo.create(name="Test Event", date="2026-05-15", event_type="gp")
        
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(singer1.id, event.id, "yes")
        avail_repo.update(singer2.id, event.id, "no")
        
        availabilities = avail_repo.get_by_event(event.id)
        
        assert len(availabilities) == 2
    
    def test_availability_counts(self, db):
        """Test availability status counts."""
        from chormanager.domain.repository import SingerRepository, EventRepository, AvailabilityRepository
        
        singer_repo = SingerRepository(db)
        singer1 = singer_repo.create(full_name="Singer 1", voice_group="Sopran 1")
        singer2 = singer_repo.create(full_name="Singer 2", voice_group="Sopran 2")
        
        event_repo = EventRepository(db)
        event = event_repo.create(name="Test Event", date="2026-05-15", event_type="gp")
        
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(singer1.id, event.id, "yes")
        avail_repo.update(singer2.id, event.id, "conditional")
        
        availabilities = avail_repo.get_by_event(event.id)
        yes_count = sum(1 for a in availabilities if a.status == "yes")
        conditional_count = sum(1 for a in availabilities if a.status == "conditional")
        
        assert yes_count == 1
        assert conditional_count == 1