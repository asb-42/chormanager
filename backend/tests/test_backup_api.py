"""M1/M4: backup create/list/restore/delete (SQLite-only).

Nutzt FileBackupService (Desktop). Restore disposed Engines vorher
(keine offenen Handles auf die DB-Datei). Nicht-SQLite-URLs
(MariaDB: DB-native Tools in M5) → 400 ohne Verbindungsversuch.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            short_name TEXT, birth_date TEXT, voice_group TEXT,
            height INTEGER, email TEXT, phone TEXT, street TEXT,
            postal_code TEXT, city TEXT, gender TEXT,
            guardian1 TEXT, guardian1_phone TEXT,
            guardian2 TEXT, guardian2_phone TEXT,
            social_contacts TEXT, joined_year INTEGER, joined_month INTEGER,
            left_year INTEGER, left_month INTEGER, affinity_uuid TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?)",
        [("s-1", "Anna", "2026-01-01", "2026-01-01")],
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient mit Tmp-DB + isoliertem Backup-Verzeichnis."""
    db_path = str(tmp_path / "t.db")
    _seed_db(db_path)
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CHORMANAGER_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("CHORMANAGER_API_TOKEN", raising=False)
    from app.main import create_app
    from app import deps

    deps.get_engine.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    deps.get_engine.cache_clear()


def test_list_empty(client):
    response = client.get("/api/backup")
    assert response.status_code == 200
    assert response.json() == []


def test_create_lists_and_restores(client):
    created = client.post("/api/backup")
    assert created.status_code == 201
    backup_id = created.json()["id"]
    assert backup_id

    listed = client.get("/api/backup").json()
    assert [b["id"] for b in listed] == [backup_id]
    assert listed[0]["size"] > 0

    # Restore auf die laufende DB (Engines werden disposed).
    response = client.post(f"/api/backup/{backup_id}/restore")
    assert response.status_code == 200
    assert len(client.get("/api/singers").json()) == 1

    assert client.delete(f"/api/backup/{backup_id}").status_code == 204
    assert client.get("/api/backup").json() == []


def test_restore_unknown_id_404(client):
    response = client.post("/api/backup/nope.json/restore")
    assert response.status_code == 404


def test_non_sqlite_rejected_without_connect(tmp_path, monkeypatch):
    from app.main import create_app
    from app import deps

    monkeypatch.setenv(
        "CHORMANAGER_DATABASE_URL", "mysql+pymysql://u:p@host/db"
    )
    deps.get_engine.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.get("/api/backup").status_code == 400
            assert client.post("/api/backup").status_code == 400
    finally:
        deps.get_engine.cache_clear()
