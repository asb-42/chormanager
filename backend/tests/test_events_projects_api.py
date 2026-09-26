"""M1 increment 2a: events + projects read API (inkl. Summary).

Plan ref: docs/plans/2026-09-26_m0_erd-openapi.md §3 (``/events``,
``/projects``, ``/projects/{id}/summary``). Desktop-Parität:
``EventsTab._load_events`` (Filter + Zusagen-Zählspalten).
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            description TEXT, is_active INTEGER DEFAULT 0, spielzeit TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE events (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            date TEXT NOT NULL, event_type TEXT NOT NULL, location TEXT,
            description TEXT, project_id TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            voice_group TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE availability (id TEXT PRIMARY KEY,
            singer_id TEXT NOT NULL, event_id TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.executemany(
        "INSERT INTO projects (id, name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?)",
        [("p-1", "Hoffmann", "2026-01-01", "2026-01-01"),
         ("p-2", "Anderes", "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO events (id, name, date, event_type, project_id,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("e-1", "Probe A", "2026-09-01", "Probe", "p-1",
          "2026-01-01", "2026-01-01"),
         ("e-2", "Konzert", "2026-10-01", "Konzert", "p-1",
          "2026-01-01", "2026-01-01"),
         ("e-3", "Fremd", "2026-11-01", "Probe", "p-2",
          "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, voice_group,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        [("s-1", "Anna", "Sopran 1", "2026-01-01", "2026-01-01"),
         ("s-2", "Berta", "Sopran 1", "2026-01-01", "2026-01-01"),
         ("s-3", "Clara", "Bass 2", "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO availability (id, singer_id, event_id, status,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("a-1", "s-1", "e-1", "yes", "2026-01-01", "2026-01-01"),
         ("a-2", "s-2", "e-1", "conditional", "2026-01-01", "2026-01-01"),
         ("a-3", "s-3", "e-1", "no", "2026-01-01", "2026-01-01"),
         ("a-4", "s-1", "e-2", "yes", "2026-01-01", "2026-01-01")],
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


def test_list_events_with_counts(client):
    response = client.get("/api/events")
    assert response.status_code == 200
    payload = {e["id"]: e for e in response.json()}
    assert set(payload) == {"e-1", "e-2", "e-3"}
    assert payload["e-1"]["yes_count"] == 1
    assert payload["e-1"]["conditional_count"] == 1
    assert payload["e-2"]["yes_count"] == 1
    assert payload["e-3"]["yes_count"] == 0


def test_list_events_project_filter(client):
    response = client.get("/api/events", params={"project_id": "p-1"})
    assert {e["id"] for e in response.json()} == {"e-1", "e-2"}


def test_list_events_search_and_type_filter(client):
    response = client.get("/api/events", params={"search": "konz"})
    assert [e["id"] for e in response.json()] == ["e-2"]
    response = client.get("/api/events", params={"event_type": "Probe"})
    assert {e["id"] for e in response.json()} == {"e-1", "e-3"}


def test_get_event_not_found(client):
    assert client.get("/api/events/nope").status_code == 404


def test_list_projects(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert {p["id"] for p in response.json()} == {"p-1", "p-2"}


def test_project_summary(client):
    response = client.get("/api/projects/p-1/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "p-1"
    by_event = {e["event_id"]: e for e in payload["events"]}
    assert by_event["e-1"]["yes"] == 1
    assert by_event["e-1"]["conditional"] == 1
    assert by_event["e-2"]["yes"] == 1
    assert "e-3" not in by_event
    vg = payload["by_voice_group"]
    assert vg["Sopran 1"]["yes"] == 2
    assert vg["Sopran 1"]["conditional"] == 1
    assert vg["Bass 2"]["yes"] == 0


def test_project_summary_not_found(client):
    assert client.get("/api/projects/nope/summary").status_code == 404
