"""Database layer for ChorManager.

C-6 (subplan_db_connection_pool.md): in addition to the legacy
single-connection ``Database``, this module now exposes
:class:`ConnectionPool` and :meth:`Database.connect_pool`. The pool
hands out connections with ``check_same_thread=False``,
``journal_mode=WAL`` and ``busy_timeout=5000`` so multiple tabs
(and threads) can read and write concurrently.
"""
import logging
import sqlite3
import threading
import uuid
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Generator, List, Optional

from ..config import load_app_config, get_data_dir

_logger = logging.getLogger(__name__)


class ConnectionPool:
    """A small fixed-size pool of SQLite connections.

    C-6 sub-plan: each tab (or thread) acquires a connection via
    ``with pool.connection() as conn:`` and the pool hands out one
    of its slots. Connections are returned on ``__exit__`` rather
    than closed, so a high-frequency caller does not pay the
    open/close cost. The pool commits any pending transaction
    before returning the connection to the idle list.
    """

    def __init__(self, db_path: str, max_connections: int = 4):
        if max_connections < 1:
            raise ValueError("max_connections must be >= 1")
        self._db_path = db_path
        self._max = max_connections
        self._lock = threading.Lock()
        self._idle: List[sqlite3.Connection] = []
        self._in_use = 0
        try:
            head = self._make_connection()
            self._idle.append(head)
        except sqlite3.Error as exc:
            _logger.warning("Could not pre-warm pool connection: %s", exc)

    @property
    def max_connections(self) -> int:
        return self._max

    def _make_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
        except sqlite3.OperationalError:
            pass
        return conn

    @contextmanager
    def connection(self, timeout: float = 2.0) -> Generator[sqlite3.Connection, None, None]:
        import time as _time
        deadline = _time.monotonic() + timeout
        conn: Optional[sqlite3.Connection] = None
        while True:
            with self._lock:
                if self._idle:
                    conn = self._idle.pop()
                    self._in_use += 1
                    break
                if self._in_use < self._max:
                    self._in_use += 1
                    conn = None
                    break
            if _time.monotonic() >= deadline:
                raise ConnectionError(
                    f"ConnectionPool exhausted (max={self._max})"
                )
            _time.sleep(0.01)
        if conn is None:
            try:
                conn = self._make_connection()
            except Exception:
                with self._lock:
                    self._in_use -= 1
                raise
        try:
            yield conn
        finally:
            try:
                conn.commit()
            except sqlite3.Error:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
            with self._lock:
                self._in_use -= 1
                self._idle.append(conn)

    def close(self) -> None:
        with self._lock:
            for c in self._idle:
                try:
                    c.close()
                except sqlite3.Error:
                    pass
            self._idle.clear()


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

    def connect_pool(self, max_connections: int = 4) -> ConnectionPool:
        """Return a fresh :class:`ConnectionPool` rooted at this DB.

        C-6 sub-plan: each tab calls this once at startup and
        acquires connections from the pool thereafter.
        """
        return ConnectionPool(self.db_path, max_connections=max_connections)

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
                height INTEGER,
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
                location TEXT,
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
                spielzeit TEXT,
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS repertoire (
                id TEXT PRIMARY KEY,
                composer TEXT,
                title TEXT NOT NULL,
                dates TEXT,
                country TEXT,
                publisher TEXT,
                arrangement TEXT,
                location TEXT,
                project_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
        """)

        try:
            conn.execute("ALTER TABLE repertoire RENAME COLUMN program TO project_id")
        except sqlite3.OperationalError:
            pass

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
            ("height", "INTEGER"),
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
