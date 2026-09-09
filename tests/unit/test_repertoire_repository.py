"""Tests for RepertoireRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import RepertoireRepository, ProjectRepository


class TestRepertoireRepository:
    """Tests for Repertoire CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return RepertoireRepository(db)

    @pytest.fixture
    def project(self, db):
        project_repo = ProjectRepository(db)
        return project_repo.create(name="Test Project")

    def test_create_repertoire(self, repo, project):
        entry = repo.create(composer="Mozart", title="Requiem", project_id=project.id)
        assert entry.id
        assert entry.composer == "Mozart"
        assert entry.title == "Requiem"

    def test_get_by_id(self, repo, project):
        created = repo.create(composer="Bach", title="Mass", project_id=project.id)
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.composer == "Bach"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self, repo, project):
        repo.create(composer="Mozart", title="Requiem", project_id=project.id)
        repo.create(composer="Bach", title="Mass", project_id=project.id)
        entries = repo.get_all()
        assert len(entries) == 2

    def test_get_all_sorted_by_title(self, repo, project):
        repo.create(composer="Mozart", title="Zebra", project_id=project.id)
        repo.create(composer="Bach", title="Alpha", project_id=project.id)
        entries = repo.get_all()
        assert entries[0].title == "Alpha"

    def test_get_by_project_id(self, repo, project):
        project_repo = ProjectRepository(repo.db)
        project2 = project_repo.create(name="Project 2")
        repo.create(composer="Mozart", title="Requiem", project_id=project.id)
        repo.create(composer="Bach", title="Mass", project_id=project2.id)
        result = repo.get_by_project_id(project.id)
        assert len(result) == 1
        assert result[0].composer == "Mozart"

    def test_update_repertoire(self, repo, project):
        entry = repo.create(composer="Old", title="Title", project_id=project.id)
        updated = repo.update(entry.id, composer="New")
        assert updated.composer == "New"

    def test_delete_repertoire(self, repo, project):
        entry = repo.create(composer="To Delete", title="Title", project_id=project.id)
        assert repo.delete(entry.id) is True
        assert repo.get_by_id(entry.id) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete("nonexistent") is False

    def test_create_with_all_fields(self, repo, project):
        entry = repo.create(
            composer="Mozart",
            title="Requiem",
            dates="1756-1791",
            country="Österreich",
            publisher="Breitkopf",
            arrangement="Gemischter Chor",
            location="Notenarchiv",
            project_id=project.id,
        )
        assert entry.dates == "1756-1791"
        assert entry.country == "Österreich"
