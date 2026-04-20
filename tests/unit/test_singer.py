"""Tests for domain models."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSingerModel:
    """Tests for Singer model."""

    def test_create_singer(self):
        """Test creating a Singer instance."""
        from chormanager.domain.models import Singer
        
        singer = Singer(
            id="test-id",
            full_name="Max Mustermann",
            short_name="Max"
        )
        
        assert singer.id == "test-id"
        assert singer.full_name == "Max Mustermann"
        assert singer.short_name == "Max"

    def test_singer_to_dict(self):
        """Test converting Singer to dictionary."""
        from chormanager.domain.models import Singer
        
        singer = Singer(
            id="test-id",
            full_name="Max Mustermann",
            email="max@example.com"
        )
        
        data = singer.to_dict()
        
        assert data["id"] == "test-id"
        assert data["full_name"] == "Max Mustermann"
        assert data["email"] == "max@example.com"

    def test_singer_from_dict(self):
        """Test creating Singer from dictionary."""
        from chormanager.domain.models import Singer
        
        data = {
            "id": "test-id",
            "full_name": "Max Mustermann",
            "email": "max@example.com"
        }
        
        singer = Singer.from_dict(data)
        
        assert singer.id == "test-id"
        assert singer.full_name == "Max Mustermann"

    def test_singer_joined_yearmonth(self):
        """Test joined year/month handling."""
        from chormanager.domain.models import Singer
        
        singer = Singer(
            id="test-id",
            full_name="Max Mustermann",
            joined_year=2020,
            joined_month=3
        )
        
        assert singer.joined_year == 2020
        assert singer.joined_month == 3
        assert singer.joined_display == "03/2020"

    def test_singer_joined_display_no_month(self):
        """Test joined display without month."""
        from chormanager.domain.models import Singer
        
        singer = Singer(
            id="test-id",
            full_name="Max Mustermann",
            joined_year=2020
        )
        
        assert singer.joined_display == "2020"


class TestSingerRepository:
    """Tests for SingerRepository."""

    def test_create_singer_in_repository(self):
        """Test creating a singer in the repository."""
        import tempfile
        import os
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            repo = SingerRepository(db)
            singer = repo.create(
                full_name="Max Mustermann",
                email="max@example.com"
            )
            
            assert singer.id is not None
            assert singer.full_name == "Max Mustermann"
            
            db.close()

    def test_get_singer_by_id(self):
        """Test getting a singer by ID."""
        import tempfile
        import os
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            repo = SingerRepository(db)
            created = repo.create(full_name="Max Mustermann")
            
            retrieved = repo.get_by_id(created.id)
            
            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.full_name == "Max Mustermann"
            
            db.close()

    def test_get_all_singers(self):
        """Test getting all singers."""
        import tempfile
        import os
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            repo = SingerRepository(db)
            repo.create(full_name="Max Mustermann")
            repo.create(full_name="Erika Mustermann")
            
            all_singers = repo.get_all()
            
            assert len(all_singers) == 2
            
            db.close()

    def test_update_singer(self):
        """Test updating a singer."""
        import tempfile
        import os
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            repo = SingerRepository(db)
            singer = repo.create(full_name="Max Mustermann")
            
            updated = repo.update(singer.id, full_name="Max Müller")
            
            assert updated.full_name == "Max Müller"
            
            db.close()

    def test_delete_singer(self):
        """Test deleting a singer."""
        import tempfile
        import os
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            repo = SingerRepository(db)
            singer = repo.create(full_name="Max Mustermann")
            
            result = repo.delete(singer.id)
            
            assert result is True
            assert repo.get_by_id(singer.id) is None
            
            db.close()

    def test_filter_by_voice_group(self):
        """Test filtering by voice group."""
        import tempfile
        import os
        from chormanager.data.database import Database
        from chormanager.domain.repository import SingerRepository
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            repo = SingerRepository(db)
            repo.create(full_name="Singer 1", voice_group="Sopran 1")
            repo.create(full_name="Singer 2", voice_group="Sopran 2")
            repo.create(full_name="Singer 3", voice_group="Alt 1")
            
            sopran1 = repo.get_by_voice_group("Sopran 1")
            
            assert len(sopran1) == 1
            assert sopran1[0].voice_group == "Sopran 1"
            
            db.close()
