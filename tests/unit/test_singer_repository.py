"""Tests for SingerRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import SingerRepository


class TestSingerRepository:
    """Tests for Singer CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return SingerRepository(db)

    def test_create_singer(self, repo):
        singer = repo.create(full_name="Test Singer", voice_group="Sopran 1")
        assert singer.id
        assert singer.full_name == "Test Singer"
        assert singer.voice_group == "Sopran 1"

    def test_create_singer_with_all_fields(self, repo):
        singer = repo.create(
            full_name="Alice Smith",
            short_name="Alice",
            voice_group="Sopran 1",
            email="alice@test.de",
            phone="12345",
            height=165,
        )
        assert singer.short_name == "Alice"
        assert singer.email == "alice@test.de"
        assert singer.height == 165

    def test_get_by_id(self, repo):
        created = repo.create(full_name="Alice")
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.full_name == "Alice"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self, repo):
        repo.create(full_name="Alice")
        repo.create(full_name="Bob")
        singers = repo.get_all()
        assert len(singers) == 2

    def test_get_all_sorted_by_name(self, repo):
        repo.create(full_name="Zoe")
        repo.create(full_name="Alice")
        singers = repo.get_all()
        assert singers[0].full_name == "Alice"
        assert singers[1].full_name == "Zoe"

    def test_update_singer(self, repo):
        singer = repo.create(full_name="Alice")
        updated = repo.update(singer.id, full_name="Alice Updated")
        assert updated.full_name == "Alice Updated"

    def test_update_sets_updated_at(self, repo):
        singer = repo.create(full_name="Alice")
        old_updated = singer.updated_at
        import time
        time.sleep(0.01)
        updated = repo.update(singer.id, full_name="Bob")
        assert updated.updated_at >= old_updated

    def test_delete_singer(self, repo):
        singer = repo.create(full_name="Alice")
        assert repo.delete(singer.id) is True
        assert repo.get_by_id(singer.id) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nonexistent") is False

    def test_search_by_name(self, repo):
        repo.create(full_name="Alice Smith")
        repo.create(full_name="Bob Jones")
        results = repo.search("Alice")
        assert len(results) == 1
        assert results[0].full_name == "Alice Smith"

    def test_search_by_short_name(self, repo):
        repo.create(full_name="Alice Smith", short_name="Ali")
        results = repo.search("Ali")
        assert len(results) == 1

    def test_search_by_email(self, repo):
        repo.create(full_name="Alice", email="alice@test.de")
        results = repo.search("alice@test")
        assert len(results) == 1

    def test_search_no_results(self, repo):
        repo.create(full_name="Alice")
        results = repo.search("ZZZ")
        assert len(results) == 0

    def test_get_by_voice_group(self, repo):
        repo.create(full_name="Alice", voice_group="Sopran 1")
        repo.create(full_name="Bob", voice_group="Bass 1")
        sopran = repo.get_by_voice_group("Sopran 1")
        assert len(sopran) == 1
        assert sopran[0].full_name == "Alice"

    def test_get_active(self, repo):
        repo.create(full_name="Alice")
        repo.create(full_name="Bob", left_year=2024)
        active = repo.get_active()
        assert len(active) == 1
        assert active[0].full_name == "Alice"
