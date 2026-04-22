"""Database layer for ChorManager."""

import sqlite3
import uuid
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Generator, Optional

from ..config import load_app_config, get_data_dir


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database.

        Args:
            db_path: Path to database file. If None, uses default from config.
        """
        if db_path is None:
            config = load_app_config()
            data_dir = get_data_dir()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / config["database"]["filename"]

        self.db_path = str(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Connect to the database."""
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def get_connection(self) -> sqlite3.Connection:
        """Get the database connection.

        Returns:
            sqlite3.Connection: The database connection.

        Raises:
            RuntimeError: If not connected to database.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self._connection

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query.

        Args:
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            sqlite3.Cursor: Query cursor.
        """
        conn = self.get_connection()
        return conn.execute(query, params)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.get_connection().commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.get_connection().rollback()

    def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        conn = self.get_connection()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS singers (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                short_name TEXT,
                birth_date TEXT,
                voice_group TEXT,
                email TEXT,
                phone TEXT,
                street TEXT,
                postal_code TEXT,
                city TEXT,
                gender TEXT,
                guardian1 TEXT,
                guardian1_phone TEXT,
                guardian2 TEXT,
                guardian2_phone TEXT,
                social_contacts TEXT,
                joined_year INTEGER,
                joined_month INTEGER,
                left_year INTEGER,
                left_month INTEGER,
                affinity_uuid TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT,
                project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS selbstdarstellung (
                id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS availability (
                id TEXT PRIMARY KEY,
                singer_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (singer_id) REFERENCES singers(id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                UNIQUE(singer_id, event_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS besetzung (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                singer_ids TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()

        for col, typ in [
            ("street", "TEXT"),
            ("postal_code", "TEXT"),
            ("city", "TEXT"),
            ("guardian1", "TEXT"),
            ("guardian1_phone", "TEXT"),
            ("guardian2", "TEXT"),
            ("guardian2_phone", "TEXT"),
            ("is_adult", "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE singers ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        conn.commit()

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for transactions.

        Yields:
            None

        Raises:
            Exception: If transaction fails, rolls back automatically.
        """
        conn = self.get_connection()
        try:
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def generate_id(self) -> str:
        """Generate a new UUID.

        Returns:
            str: UUID string.
        """
        return str(uuid.uuid4())

    def __enter__(self) -> "Database":
        """Enter context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()
