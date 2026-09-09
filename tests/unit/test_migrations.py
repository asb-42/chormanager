"""Tests for database schema migrations."""

import pytest
import sqlite3
from chormanager.data.database import Database


class TestDatabaseMigrations:
    """Tests for schema creation and migration."""

    def test_create_tables_creates_all_tables(self, tmp_path):
        """All expected tables are created."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()

        cursor = db.get_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected = {"singers", "events", "projects", "availability", "besetzung", "repertoire", "selbstdarstellung"}
        assert expected.issubset(tables)
        db.close()

    def test_create_tables_idempotent(self, tmp_path):
        """Calling create_tables twice doesn't error."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        db.create_tables()
        db.close()

    def test_add_column_idempotent(self, tmp_path):
        """ALTER TABLE ADD COLUMN is idempotent."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        db.create_tables()
        db.close()

    def test_foreign_keys_enabled(self, tmp_path):
        """Foreign keys are enforced."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()

        result = db.get_connection().execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1
        db.close()

    def test_indexes_created(self, tmp_path):
        """Database indexes are created."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()

        cursor = db.get_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_events_project_id" in indexes
        assert "idx_singers_voice_group" in indexes
        assert "idx_availability_event_id" in indexes
        db.close()

    def test_singers_table_schema(self, tmp_path):
        """Singers table has expected columns."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()

        cursor = db.get_connection().execute("PRAGMA table_info(singers)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "id" in columns
        assert "full_name" in columns
        assert "voice_group" in columns
        assert "email" in columns
        db.close()

    def test_events_table_schema(self, tmp_path):
        """Events table has expected columns."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()

        cursor = db.get_connection().execute("PRAGMA table_info(events)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "id" in columns
        assert "name" in columns
        assert "date" in columns
        assert "event_type" in columns
        db.close()

    def test_foreign_key_enforcement(self, tmp_path):
        """Foreign key constraint prevents invalid references."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO availability (id, singer_id, event_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("test-id", "nonexistent-singer", "nonexistent-event", "yes", "2026-01-01", "2026-01-01"),
            )
        db.close()

    def test_spielzeit_column_migrated(self, tmp_path):
        """A pre-spielzeit projects table gets the column added."""
        db_path = str(tmp_path / "old.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        conn.execute(
            "INSERT INTO projects (id, name, created_at, updated_at) "
            "VALUES ('p1', 'Altes Projekt', '2026-01-01', '2026-01-01')"
        )
        conn.commit()
        conn.close()

        db = Database(db_path)
        db.connect()
        db.create_tables()

        cols = {
            row[1]
            for row in db.get_connection().execute("PRAGMA table_info(projects)")
        }
        assert "spielzeit" in cols, (
            "create_tables must migrate legacy projects tables by "
            "adding the spielzeit column (added in the ChorManager "
            "spielzeit feature)."
        )

        # The pre-existing row must still be readable and map onto the
        # Project model (SELECT * must not crash with a missing column).
        from chormanager.domain.repository import ProjectRepository
        repo = ProjectRepository(db)
        project = repo.get_by_id("p1")
        assert project is not None
        assert project.name == "Altes Projekt"
        db.close()
