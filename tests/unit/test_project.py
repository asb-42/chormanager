"""Unit tests for Project model and repository."""

import pytest
from datetime import datetime

from chormanager.domain.models import Project
from chormanager.data.database import Database


class TestProjectModel:
    """Tests for Project model."""
    
    def test_create_project_with_id(self):
        """Test creating a new project with explicit ID."""
        project = Project(
            id="proj-123",
            name="Test Project",
            description="A test project",
            is_active=1,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00"
        )
        
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.is_active == 1
        assert project.id == "proj-123"
    
    def test_project_to_dict(self):
        """Test converting project to dictionary."""
        project = Project(
            id="test-123",
            name="Test Project",
            description="Description",
            is_active=1,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00"
        )
        
        data = project.to_dict()
        
        assert data["id"] == "test-123"
        assert data["name"] == "Test Project"
        assert data["description"] == "Description"
        assert data["is_active"] == 1


class TestProjectRepository:
    """Tests for ProjectRepository."""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db.connect()
        db.create_tables()
        yield db
        db.close()
    
    def test_create_project(self, db):
        """Test creating a project."""
        from chormanager.domain.repository import ProjectRepository
        
        repo = ProjectRepository(db)
        project = repo.create(
            name="Test Project",
            description="Test Description",
            is_active=1
        )
        
        assert project.name == "Test Project"
        assert project.description == "Test Description"
        assert project.is_active == 1
        assert project.id != ""
    
    def test_get_all_projects(self, db):
        """Test getting all projects."""
        from chormanager.domain.repository import ProjectRepository
        
        repo = ProjectRepository(db)
        repo.create(name="Project 1")
        repo.create(name="Project 2")
        
        projects = repo.get_all()
        
        assert len(projects) == 2
    
    def test_get_active_project(self, db):
        """Test getting active project."""
        from chormanager.domain.repository import ProjectRepository
        
        repo = ProjectRepository(db)
        p1 = repo.create(name="Active Project", is_active=1)
        repo.create(name="Inactive Project")
        
        active = repo.get_active()
        
        assert active is not None
        assert active.name == "Active Project"
    
    def test_set_active(self, db):
        """Test setting a project as active."""
        from chormanager.domain.repository import ProjectRepository
        
        repo = ProjectRepository(db)
        p1 = repo.create(name="Project 1", is_active=1)
        p2 = repo.create(name="Project 2")
        
        repo.set_active(p2.id)
        
        active = repo.get_active()
        assert active.name == "Project 2"
    
    def test_update_project(self, db):
        """Test updating a project."""
        from chormanager.domain.repository import ProjectRepository
        
        repo = ProjectRepository(db)
        project = repo.create(name="Original Name")
        
        updated = repo.update(project.id, name="Updated Name")
        
        assert updated.name == "Updated Name"
    
    def test_delete_project(self, db):
        """Test deleting a project."""
        from chormanager.domain.repository import ProjectRepository
        
        repo = ProjectRepository(db)
        project = repo.create(name="To Delete")
        
        result = repo.delete(project.id)
        
        assert result is True
        assert repo.get_by_id(project.id) is None