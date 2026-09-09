"""Tests for EventRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import EventRepository


class TestEventRepository:
    """Tests for Event CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return EventRepository(db)

    def test_create_event(self, repo):
        event = repo.create(name="Test Event", date="2026-05-15", event_type="gp")
        assert event.id
        assert event.name == "Test Event"
        assert event.event_type == "gp"

    def test_get_by_id(self, repo):
        created = repo.create(name="Concert", date="2026-06-01", event_type="konzert")
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "Concert"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self, repo):
        repo.create(name="Event 1", date="2026-06-01", event_type="gp")
        repo.create(name="Event 2", date="2026-05-01", event_type="gp")
        events = repo.get_all()
        assert len(events) == 2

    def test_get_all_sorted_by_date_desc(self, repo):
        repo.create(name="Early", date="2026-01-01", event_type="gp")
        repo.create(name="Late", date="2026-12-01", event_type="gp")
        events = repo.get_all()
        assert events[0].date > events[1].date

    def test_update_event(self, repo):
        event = repo.create(name="Old Name", date="2026-05-15", event_type="gp")
        updated = repo.update(event.id, name="New Name")
        assert updated.name == "New Name"

    def test_delete_event(self, repo):
        event = repo.create(name="Test", date="2026-05-15", event_type="gp")
        assert repo.delete(event.id) is True
        assert repo.get_by_id(event.id) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nonexistent") is False

    def test_create_event_with_project(self, repo):
        from chormanager.domain.repository import ProjectRepository
        project_repo = ProjectRepository(repo.db)
        project = project_repo.create(name="Test Project")
        event = repo.create(name="Project Event", date="2026-06-01", event_type="gp", project_id=project.id)
        assert event.project_id == project.id
