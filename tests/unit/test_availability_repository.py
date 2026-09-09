"""Tests for AvailabilityRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import SingerRepository, EventRepository, AvailabilityRepository


class TestAvailabilityRepository:
    """Tests for Availability CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repos(self, db):
        singer_repo = SingerRepository(db)
        event_repo = EventRepository(db)
        avail_repo = AvailabilityRepository(db)
        singer = singer_repo.create(full_name="Alice")
        event = event_repo.create(name="Concert", date="2026-06-01", event_type="konzert")
        return avail_repo, singer, event

    def test_create_availability(self, repos):
        avail_repo, singer, event = repos
        avail = avail_repo.create(singer_id=singer.id, event_id=event.id, status="yes")
        assert avail.status == "yes"
        assert avail.singer_id == singer.id

    def test_get_by_ids(self, repos):
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avail = avail_repo.get_by_ids(singer.id, event.id)
        assert avail is not None
        assert avail.status == "yes"

    def test_get_by_ids_not_found(self, repos):
        avail_repo, singer, event = repos
        avail = avail_repo.get_by_ids(singer.id, event.id)
        assert avail is None

    def test_upsert_creates_new(self, repos):
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avail = avail_repo.get_by_ids(singer.id, event.id)
        assert avail.status == "yes"

    def test_upsert_updates_existing(self, repos):
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avail_repo.update(singer.id, event.id, "no")
        avail = avail_repo.get_by_ids(singer.id, event.id)
        assert avail.status == "no"

    def test_get_by_event(self, repos):
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avails = avail_repo.get_by_event(event.id)
        assert len(avails) == 1

    def test_get_by_singer(self, repos):
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avails = avail_repo.get_by_singer(singer.id)
        assert len(avails) == 1

    def test_delete_availability(self, repos):
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        assert avail_repo.delete(singer.id, event.id) is True
        avail = avail_repo.get_by_ids(singer.id, event.id)
        assert avail is None

    def test_delete_nonexistent(self, repos):
        avail_repo, singer, event = repos
        assert avail_repo.delete(singer.id, event.id) is False
