"""M1 increment 2b: availability matrix GET + bulk PUT (first write).

Plan ref: docs/plans/2026-09-26_m0_erd-openapi.md §3
(``/events/{id}/availability``). Desktop-Parität: Matrix mit allen
sechs Status (fehlende Zeile = ``none``); Bulk-Upsert nach m7
(UPDATE-first, dann INSERT — dialektneutral für SQLite + MariaDB).
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient


STATUSES = ("yes", "no", "none", "conditional", "unknown", "maybe")


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE events (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            date TEXT NOT NULL, event_type TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            short_name TEXT, voice_group TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE availability (id TEXT PRIMARY KEY,
            singer_id TEXT NOT NULL, event_id TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(singer_id, event_id))"""
    )
    conn.executemany(
        "INSERT INTO events (id, name, date, event_type,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("e-1", "Probe", "2026-09-01", "Probe", "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, short_name, voice_group,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("s-1", "Anna Muster", "Anna", "Sopran 1",
          "2026-01-01", "2026-01-01"),
         ("s-2", "Berta Beispiel", "Berta", "Bass 2",
          "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO availability (id, singer_id, event_id, status,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("a-1", "s-1", "e-1", "yes", "2026-01-01", "2026-01-01")],
    )
    conn.commit()
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient wired to a seeded tmp database."""
    db_path = str(tmp_path / "t.db")
    _seed_db(db_path)
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    from app.main import create_app
    from app import deps

    deps.get_engine.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    deps.get_engine.cache_clear()


def test_get_matrix(client):
    response = client.get("/api/events/e-1/availability")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"] == "e-1"
    by_singer = {e["singer_id"]: e for e in payload["entries"]}
    assert set(by_singer) == {"s-1", "s-2"}
    assert by_singer["s-1"]["status"] == "yes"
    # Missing row reads as "none" (keine Rückmeldung).
    assert by_singer["s-2"]["status"] == "none"
    assert by_singer["s-1"]["voice_group"] == "Sopran 1"


def test_get_matrix_unknown_event(client):
    assert client.get("/api/events/nope/availability").status_code == 404


def test_put_bulk_upserts_and_persists(client):
    response = client.put(
        "/api/events/e-1/availability",
        json={"entries": [
            {"singer_id": "s-1", "status": "no"},
            {"singer_id": "s-2", "status": "conditional"},
        ]},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 2
    matrix = client.get("/api/events/e-1/availability").json()
    by_singer = {e["singer_id"]: e for e in matrix["entries"]}
    assert by_singer["s-1"]["status"] == "no"
    assert by_singer["s-2"]["status"] == "conditional"
    # No duplicate rows: UNIQUE(singer_id, event_id) holds.
    assert len(matrix["entries"]) == 2


def test_put_bulk_rejects_bad_status(client):
    response = client.put(
        "/api/events/e-1/availability",
        json={"entries": [{"singer_id": "s-1", "status": "vielleicht"}]},
    )
    assert response.status_code == 422
    # Nothing persisted.
    matrix = client.get("/api/events/e-1/availability").json()
    by_singer = {e["singer_id"]: e for e in matrix["entries"]}
    assert by_singer["s-1"]["status"] == "yes"


def test_put_bulk_unknown_event(client):
    response = client.put(
        "/api/events/nope/availability",
        json={"entries": [{"singer_id": "s-1", "status": "yes"}]},
    )
    assert response.status_code == 404
