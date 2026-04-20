"""Tests for database layer."""

import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestDatabaseConnection:
    """Tests for database connection."""

    def test_create_database(self):
        """Test creating a new database."""
        from chormanager.data.database import Database
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            assert os.path.exists(db_path)
            db.close()

    def test_get_connection(self):
        """Test getting database connection."""
        from chormanager.data.database import Database
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            conn = db.get_connection()
            assert conn is not None
            db.close()

    def test_execute_query(self):
        """Test executing a query."""
        from chormanager.data.database import Database
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            result = db.execute("SELECT 1 as test")
            row = result.fetchone()
            assert row[0] == 1
            db.close()


class TestDatabaseSchema:
    """Tests for database schema."""

    def test_create_tables(self):
        """Test creating database tables."""
        from chormanager.data.database import Database
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            result = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in result.fetchall()]
            assert "singers" in tables
            db.close()

    def test_singers_table_columns(self):
        """Test that singers table has required columns."""
        from chormanager.data.database import Database
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            result = db.execute("PRAGMA table_info(singers)")
            columns = {row[1]: row[2] for row in result.fetchall()}
            
            assert "id" in columns
            assert "full_name" in columns
            assert "email" in columns
            db.close()

    def test_transaction_context_manager(self):
        """Test transaction context manager."""
        from chormanager.data.database import Database
        from datetime import datetime
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            db.connect()
            db.create_tables()
            
            now = datetime.now().isoformat()
            
            with db.transaction():
                conn = db.get_connection()
                conn.execute(
                    "INSERT INTO singers (id, full_name, created_at, updated_at) VALUES ('test-1', 'Test', ?, ?)",
                    (now, now)
                )
            
            result = db.execute("SELECT COUNT(*) FROM singers")
            assert result.fetchone()[0] == 1
            
            db.close()
