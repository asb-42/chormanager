"""Tests for BesetzungRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import BesetzungRepository, ProjectRepository


class TestBesetzungRepository:
    """Tests for Besetzung CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repos(self, db):
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Test Project")
        besetzung_repo = BesetzungRepository(db)
        return besetzung_repo, project

    def test_create_besetzung(self, repos):
        repo, project = repos
        besetzung = repo.create(name="Main Choir", project_id=project.id, singer_ids=["s1", "s2"])
        assert besetzung.id
        assert besetzung.name == "Main Choir"

    def test_get_by_id(self, repos):
        repo, project = repos
        created = repo.create(name="Test", project_id=project.id, singer_ids=["s1"])
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "Test"

    def test_get_by_id_not_found(self, repos):
        repo, _ = repos
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self, repos):
        repo, project = repos
        repo.create(name="B1", project_id=project.id, singer_ids=[])
        repo.create(name="B2", project_id=project.id, singer_ids=[])
        result = repo.get_all()
        assert len(result) == 2

    def test_get_by_project(self, repos):
        repo, project = repos
        repo.create(name="B1", project_id=project.id, singer_ids=[])
        repo.create(name="B2", project_id=project.id, singer_ids=[])
        result = repo.get_by_project(project.id)
        assert len(result) == 2

    def test_get_singer_ids(self, repos):
        repo, project = repos
        besetzung = repo.create(name="Test", project_id=project.id, singer_ids=["s1", "s2", "s3"])
        ids = besetzung.get_singer_ids()
        assert len(ids) == 3
        assert "s1" in ids

    def test_get_singer_ids_empty(self, repos):
        repo, project = repos
        besetzung = repo.create(name="Empty", project_id=project.id, singer_ids=[])
        ids = besetzung.get_singer_ids()
        assert len(ids) == 0

    def test_update_besetzung(self, repos):
        repo, project = repos
        besetzung = repo.create(name="Old", project_id=project.id, singer_ids=[])
        updated = repo.update(besetzung.id, name="New")
        assert updated.name == "New"

    def test_update_singer_ids_as_list(self, repos):
        repo, project = repos
        besetzung = repo.create(name="Test", project_id=project.id, singer_ids=[])
        repo.update(besetzung.id, singer_ids=["s1", "s2"])
        updated = repo.get_by_id(besetzung.id)
        ids = updated.get_singer_ids()
        assert len(ids) == 2

    def test_delete_besetzung(self, repos):
        repo, project = repos
        besetzung = repo.create(name="To Delete", project_id=project.id, singer_ids=[])
        assert repo.delete(besetzung.id) is True
        assert repo.get_by_id(besetzung.id) is None

    def test_delete_nonexistent(self, repos):
        repo, _ = repos
        assert repo.delete("nonexistent") is False
