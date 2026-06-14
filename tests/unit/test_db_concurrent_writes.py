"""TDD: C-6 Sub-Plan \u2014 Concurrent operations via the ConnectionPool.

The legacy single-connection database cannot serve two writers
concurrently (\"SQLite objects created in a thread can only be
used in that same thread\"). With
``ConnectionPool(check_same_thread=False)`` + ``journal_mode=WAL`` +
``busy_timeout=5000``, multiple threads can use the DB without
crashing. This module pins the realistic behaviour.
"""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

import pytest


def _make_pool(tmp_path: Path, max_connections: int = 4):
    from chormanager.data.database import ConnectionPool
    pool = ConnectionPool(str(tmp_path / "concurrency.db"), max_connections=max_connections)
    with pool.connection() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS kv ("
            "  k TEXT PRIMARY KEY, v INTEGER NOT NULL"
            ")"
        )
    return pool


def test_pool_supports_concurrent_reads():
    """Two threads can read simultaneously with WAL mode."""
    from chormanager.data.database import ConnectionPool
    with tempfile.TemporaryDirectory() as tmp:
        pool = _make_pool(Path(tmp), max_connections=2)
        try:
            with pool.connection() as c:
                c.execute("INSERT INTO kv VALUES ('seed', 42)")

            errors: list = []
            def reader() -> None:
                try:
                    with pool.connection() as c:
                        for _ in range(20):
                            row = c.execute(
                                "SELECT v FROM kv WHERE k='seed'"
                            ).fetchone()
                            assert row is not None and row["v"] == 42, (
                                f"unexpected row: {row!r}"
                            )
                except Exception as e:  # noqa: BLE001
                    errors.append(e)
            t1 = threading.Thread(target=reader)
            t2 = threading.Thread(target=reader)
            t1.start(); t2.start()
            t1.join(); t2.join()
            assert not errors, f"concurrent reads failed: {errors!r}"
        finally:
            pool.close()


def test_pool_serialization_via_app_lock_under_contention():
    """With ``busy_timeout``, two simultaneous writers either both
    succeed (one after the other) or one raises a clear
    ``OperationalError``. The pool must not deadlock."""
    from chormanager.data.database import ConnectionPool
    with tempfile.TemporaryDirectory() as tmp:
        pool = _make_pool(Path(tmp), max_connections=2)
        try:
            errors: list = []
            successes: list = []
            def writer(i: int) -> None:
                try:
                    with pool.connection() as c:
                        c.execute("INSERT INTO kv VALUES (?, ?)", (f"k{i}", i))
                    successes.append(i)
                except Exception as e:  # noqa: BLE001
                    errors.append((i, e))
            threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
            t0 = time.time()
            for t in threads: t.start()
            for t in threads: t.join()
            elapsed = time.time() - t0
            # Must complete within 6s (busy_timeout is 5s, plus
            # connection-pool overhead).
            assert elapsed < 6.0, f"deadlock suspected: {elapsed:.2f}s"
            # Either: 5 successes, OR some OperationalError('database is
            # locked') on the contended writers.
            for i, exc in errors:
                assert "locked" in str(exc) or "busy" in str(exc), (
                    f"unexpected error from writer {i}: {exc!r}"
                )
            with pool.connection() as c:
                n = c.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
            # 0 seed + len(successes) rows.
            assert n == len(successes), (
                f"row count mismatch: {n} rows vs {len(successes)} successes"
            )
        finally:
            pool.close()


def test_pool_pool_grows_up_to_max_connections():
    """Concurrent acquirers block (timeout) when pool is exhausted."""
    from chormanager.data.database import ConnectionPool
    with tempfile.TemporaryDirectory() as tmp:
        # max=1, but 3 concurrent acquirers \u2192 1 success, 2 timeouts.
        pool = _make_pool(Path(tmp), max_connections=1)
        try:
            errors: list = []
            successes: list = []
            held = threading.Event()
            release = threading.Event()
            def worker() -> None:
                try:
                    with pool.connection(timeout=0.3) as c:
                        successes.append(threading.get_ident())
                        # Hold until release event.
                        held.set()
                        release.wait(timeout=2.0)
                except ConnectionError as e:
                    errors.append(e)
            threads = [threading.Thread(target=worker) for _ in range(3)]
            for t in threads: t.start()
            held.wait(timeout=1.0)
            # Give the other workers enough time to hit their
            # 0.3s timeout.
            time.sleep(0.5)
            # Let the held worker release.
            release.set()
            for t in threads: t.join()
            # At least one ConnectionError expected (2 of 3 time out).
            assert len(errors) >= 1, (
                f"expected at least 1 timeout, got {len(errors)}"
            )
            assert len(successes) >= 1, (
                f"at least one worker should have acquired, got {len(successes)}"
            )
        finally:
            pool.close()
