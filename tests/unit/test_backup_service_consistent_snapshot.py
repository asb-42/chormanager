"""TDD RED: Regression tests for m9-FIX-A — sqlite3.backup() in BackupService.

The old ``create_backup`` did a plain ``shutil.copy2`` of the SQLite file.
That snapshot can be **inconsistent** if the app is still writing while
copying. m9-FIX-A makes the backup consistent by using the SQLite
backup API (``Connection.backup``) so that we get a transactionally
consistent snapshot, even while the source DB is being modified.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from pathlib import Path

import pytest


def _create_sqlite_db(path: Path) -> None:
    """Create a tiny SQLite db with one row."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE kv (k TEXT PRIMARY KEY, v TEXT)")
        conn.execute("INSERT INTO kv VALUES ('hello', 'world')")
        conn.commit()
    finally:
        conn.close()


def _count_rows(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM kv")
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def test_create_backup_uses_sqlite_backup_api(tmp_path: Path):
    """Backup is produced via the SQLite backup API, not a plain file copy.

    The output file must be a valid SQLite db with the same content.
    """
    from chormanager.backup.service import BackupService

    src = tmp_path / "src.db"
    _create_sqlite_db(src)

    svc = BackupService(backup_dir=str(tmp_path / "backups"))
    out = svc.create_backup(str(src))

    assert os.path.exists(out)
    # The backup must be a valid SQLite db: open it, count rows.
    assert _count_rows(Path(out)) == 1


def test_create_backup_consistent_under_concurrent_writes(tmp_path: Path):
    """While we copy, another thread writes. The backup must NOT be corrupt.

    The SQLite ``Connection.backup`` API is transactional: the backup
    sees a consistent snapshot. A plain ``shutil.copy2`` may observe
    a half-written page and produce a corrupt file.
    """
    from chormanager.backup.service import BackupService

    src = tmp_path / "writer.db"
    _create_sqlite_db(src)

    # Background writer: insert rows as fast as possible while the
    # backup runs.
    stop = threading.Event()

    def writer() -> None:
        conn = sqlite3.connect(str(src), timeout=5.0)
        try:
            i = 0
            while not stop.is_set():
                conn.execute(
                    "INSERT OR REPLACE INTO kv VALUES (?, ?)",
                    (f"k{i}", f"v{i}"),
                )
                conn.commit()
                i += 1
        finally:
            conn.close()

    t = threading.Thread(target=writer, daemon=True)
    t.start()

    try:
        svc = BackupService(backup_dir=str(tmp_path / "backups"))
        out = svc.create_backup(str(src))
    finally:
        stop.set()
        t.join(timeout=2.0)

    # The backup must open cleanly. If the snapshot was inconsistent,
    # sqlite3.connect() would raise ``DatabaseError: database disk image is malformed``.
    conn = sqlite3.connect(str(out))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM kv")
        # Snapshot must contain at least the original row.
        n = int(cur.fetchone()[0])
        assert n >= 1
    finally:
        conn.close()


def test_create_backup_returns_string_path(tmp_path: Path):
    from chormanager.backup.service import BackupService

    src = tmp_path / "x.db"
    _create_sqlite_db(src)
    svc = BackupService(backup_dir=str(tmp_path / "backups"))
    out = svc.create_backup(str(src))
    assert isinstance(out, str)
    assert out.endswith(".db")


def test_create_backup_uses_sqlite_path_for_dot_db(tmp_path: Path, monkeypatch):
    """For ``*.db`` sources the implementation must take the SQLite branch.

    We assert this by patching ``BackupService._sqlite_backup`` with a
    recorder and confirming it was called (the original method is then
    called too, so the output is a real valid SQLite file).
    """
    from chormanager.backup.service import BackupService

    src = tmp_path / "spied.db"
    _create_sqlite_db(src)

    called = {"sqlite_backup": 0, "shutil_copy2": 0}
    real_sqlite_backup = BackupService._sqlite_backup
    real_copy2 = BackupService.__module__ and __import__(
        "shutil", fromlist=["copy2"]
    ).copy2

    def spy_sqlite_backup(s, d):
        called["sqlite_backup"] += 1
        return real_sqlite_backup(s, d)

    monkeypatch.setattr(BackupService, "_sqlite_backup", staticmethod(spy_sqlite_backup))

    svc = BackupService(backup_dir=str(tmp_path / "backups"))
    out = svc.create_backup(str(src))

    assert called["sqlite_backup"] == 1, (
        f"Expected _sqlite_backup to be called once, got {called['sqlite_backup']}"
    )
    assert os.path.exists(out)
    # The output must be a valid SQLite db.
    assert _count_rows(Path(out)) == 1


def test_create_backup_falls_back_to_shutil_for_non_sqlite(tmp_path: Path):
    """Non-SQLite sources still get a plain ``shutil.copy2`` backup."""
    from chormanager.backup.service import BackupService

    src = tmp_path / "config.json"
    src.write_text('{"app": "ChorManager"}', encoding="utf-8")

    svc = BackupService(backup_dir=str(tmp_path / "backups"))
    out = svc.create_backup(str(src))
    assert os.path.exists(out)
    assert Path(out).read_text(encoding="utf-8") == '{"app": "ChorManager"}'
