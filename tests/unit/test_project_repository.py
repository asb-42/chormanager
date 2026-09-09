"""Tests for ProjectRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import ProjectRepository


class TestProjectRepository:
    """Tests for Project CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return ProjectRepository(db)

    def test_create_project(self, repo):
        project = repo.create(name="Test Project")
        assert project.id
        assert project.name == "Test Project"

    def test_get_by_id(self, repo):
        created = repo.create(name="My Project")
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "My Project"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self, repo):
        repo.create(name="Project A")
        repo.create(name="Project B")
        projects = repo.get_all()
        assert len(projects) == 2

    def test_get_all_sorted_by_name(self, repo):
        repo.create(name="Zebra")
        repo.create(name="Alpha")
        projects = repo.get_all()
        assert projects[0].name == "Alpha"
        assert projects[1].name == "Zebra"

    def test_get_active(self, repo):
        p1 = repo.create(name="Active")
        repo.set_active(p1.id)
        active = repo.get_active()
        assert active is not None
        assert active.name == "Active"

    def test_get_active_none(self, repo):
        assert repo.get_active() is None

    def test_set_active(self, repo):
        p1 = repo.create(name="Project 1")
        p2 = repo.create(name="Project 2")
        repo.set_active(p1.id)
        active = repo.get_active()
        assert active.id == p1.id

    def test_set_active_clears_others(self, repo):
        p1 = repo.create(name="Project 1")
        p2 = repo.create(name="Project 2")
        repo.set_active(p1.id)
        repo.set_active(p2.id)
        active = repo.get_active()
        assert active.id == p2.id

    def test_update_project(self, repo):
        project = repo.create(name="Old Name")
        updated = repo.update(project.id, name="New Name")
        assert updated.name == "New Name"

    def test_delete_project(self, repo):
        project = repo.create(name="To Delete")
        assert repo.delete(project.id) is True
        assert repo.get_by_id(project.id) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nonexistent") is False
