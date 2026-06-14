"""TDD RED: C-6 Sub-Plan \u2014 ``Database.connect_pool()`` with WAL mode.

The legacy ``Database`` class has a single connection that is
shared across tabs. SQLite forbids concurrent use of one
connection from multiple threads (\"SQLite objects created in a
thread can only be used in that same thread\"). C-6 introduces
``connect_pool(max_connections=10)`` that returns a
:class:`ConnectionPool` with its own dedicated connection
(``check_same_thread=False``) plus WAL mode enabled for parallel
reads.
"""
from __future__ import annotations

import os
import sqlite3

import pytest


def test_database_has_connect_pool_method():
    from chormanager.data.database import Database
    assert hasattr(Database, "connect_pool"), (
        "C-6: Database must expose connect_pool()"
    )
    assert callable(Database.connect_pool)


def test_connect_pool_returns_a_connection_pool():
    from chormanager.data.database import Database, ConnectionPool
    db = Database(db_path=":memory:")
    pool = db.connect_pool(max_connections=4)
    assert isinstance(pool, ConnectionPool)
    pool.close()


def test_connection_pool_uses_check_same_thread_false():
    """Each pooled connection must be safe to use from any thread.

    We assert this by spawning a thread that uses the connection;
    a connection with ``check_same_thread=True`` would raise
    ``ProgrammingError: SQLite objects created in a thread can only
    be used in that same thread.``
    """
    import sqlite3 as _sqlite3
    from chormanager.data.database import ConnectionPool
    pool = ConnectionPool(":memory:", max_connections=2)
    try:
        with pool.connection() as conn:
            conn.execute("CREATE TABLE t (x INT)")
            err: list = []
            def worker() -> None:
                try:
                    conn.execute("INSERT INTO t VALUES (1)")
                except Exception as e:  # noqa: BLE001
                    err.append(e)
            import threading
            th = threading.Thread(target=worker)
            th.start(); th.join()
            assert not err, (
                f"C-6: pooled connection is not thread-safe: {err!r}"
            )
    finally:
        pool.close()


def test_connection_pool_enables_wal_mode(tmp_path):
    """WAL mode allows parallel readers during a write transaction."""
    from chormanager.data.database import ConnectionPool
    db_path = str(tmp_path / "wal.db")
    pool = ConnectionPool(db_path, max_connections=2)
    try:
        with pool.connection() as conn:
            cur = conn.execute("PRAGMA journal_mode")
            mode = cur.fetchone()[0]
            assert mode.lower() == "wal", (
                f"C-6: ConnectionPool must enable WAL mode; got {mode!r}"
            )
    finally:
        pool.close()


def test_connection_pool_acquires_distinct_connections_per_call():
    """Two concurrent ``with`` blocks must each get a distinct
    connection (within the pool's capacity)."""
    from chormanager.data.database import ConnectionPool
    pool = ConnectionPool(":memory:", max_connections=3)
    try:
        with pool.connection() as c1:
            with pool.connection() as c2:
                assert c1 is not c2
    finally:
        pool.close()


def test_connection_pool_returns_to_pool_after_with():
    """``with pool.connection() as conn:`` returns the connection
    to the pool instead of closing it."""
    from chormanager.data.database import ConnectionPool
    pool = ConnectionPool(":memory:", max_connections=1)
    try:
        with pool.connection() as c1:
            c1.execute("CREATE TABLE t (x INT)")
        # Re-acquire: must be the SAME object (returned to pool).
        with pool.connection() as c2:
            assert c1 is c2
    finally:
        pool.close()


def test_connection_pool_overflow_raises():
    """When all connections are checked out, the next acquire must
    raise rather than blocking forever."""
    from chormanager.data.database import ConnectionPool
    pool = ConnectionPool(":memory:", max_connections=1)
    try:
        with pool.connection():
            with pytest.raises((ConnectionError, RuntimeError, TimeoutError)):
                # Strict mode: timeout=0.1s so the test does not hang.
                with pool.connection(timeout=0.1):
                    pass
    finally:
        pool.close()
