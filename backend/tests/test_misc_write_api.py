"""M1 writes (2/2): events/projects/besetzung/repertoire/selbstdarstellung.

Auth wie Singer-CRUD (Bearer ⇒ chorleiter). Semantik wie
Desktop-Schema: Event-Delete kaskadiert Availability;
Project-Delete setzt Kinder-``project_id`` auf NULL (explizites
SET NULL, dialektneutral); Selbstdarstellung-PUT ist Upsert.
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
            description TEXT, project_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE availability (id TEXT PRIMARY KEY,
            singer_id TEXT NOT NULL, event_id TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(singer_id, event_id))"""
    )
    conn.execute(
        """CREATE TABLE besetzung (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            project_id TEXT, singer_ids TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE repertoire (id TEXT PRIMARY KEY, composer TEXT,
            title TEXT NOT NULL, dates TEXT, country TEXT, publisher TEXT,
            arrangement TEXT, location TEXT, project_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE selbstdarstellung (id TEXT PRIMARY KEY,
            content TEXT, updated_at TEXT NOT NULL)"""
    )
    conn.executemany(
        "INSERT INTO projects (id, name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?)",
        [("p-1", "P1", "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO events (id, name, date, event_type, project_id,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("e-1", "Probe", "2026-09-01", "Probe", "p-1",
          "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?)",
        [("s-1", "Anna", "2026-01-01", "2026-01-01")],
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
    """TestClient with token auth enabled."""
    db_path = str(tmp_path / "t.db")
    _seed_db(db_path)
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CHORMANAGER_API_TOKEN", "secret-123")
    from app.main import create_app
    from app import deps

    deps.get_engine.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    deps.get_engine.cache_clear()


def _auth():
    return {"Authorization": "Bearer secret-123"}


def test_event_crud(client):
    created = client.post(
        "/api/events",
        json={"name": "Neu", "date": "2026-12-01", "event_type": "Probe",
              "project_id": "p-1"},
        headers=_auth(),
    )
    assert created.status_code == 201
    eid = created.json()["id"]
    assert created.json()["yes_count"] == 0
    updated = client.put(
        f"/api/events/{eid}", json={"location": "Saal"}, headers=_auth()
    )
    assert updated.status_code == 200
    assert updated.json()["location"] == "Saal"
    assert client.put("/api/events/nope", json={}, headers=_auth()
                      ).status_code == 404
    assert client.delete(f"/api/events/{eid}", headers=_auth()
                         ).status_code == 204
    assert client.get(f"/api/events/{eid}").status_code == 404


def test_event_create_requires_fields(client):
    response = client.post("/api/events", json={"name": "Ohne Rest"},
                           headers=_auth())
    assert response.status_code == 422


def test_event_delete_cascades_availability(client):
    assert client.delete("/api/events/e-1", headers=_auth()
                         ).status_code == 204
    matrix = client.get("/api/events/e-1/availability")
    assert matrix.status_code == 404


def test_project_crud_and_set_null(client):
    created = client.post(
        "/api/projects", json={"name": "Neu", "spielzeit": "26/27"},
        headers=_auth(),
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    assert client.put(f"/api/projects/{pid}", json={"description": "D"},
                      headers=_auth()).json()["description"] == "D"
    assert client.delete(f"/api/projects/{pid}", headers=_auth()
                         ).status_code == 204
    # Bestandskinder von p-1 behalten, verlieren aber die Zuordnung.
    assert client.delete("/api/projects/p-1", headers=_auth()
                         ).status_code == 204
    assert client.get("/api/projects/p-1").status_code == 404
    event = client.get("/api/events/e-1").json()
    assert event["project_id"] is None


def test_besetzung_crud(client):
    created = client.post(
        "/api/besetzungen",
        json={"name": "Stamm", "project_id": "p-1",
              "singer_ids": ["s-1"]},
        headers=_auth(),
    )
    assert created.status_code == 201
    assert created.json()["singer_ids"] == ["s-1"]
    bid = created.json()["id"]
    updated = client.put(
        f"/api/besetzungen/{bid}", json={"singer_ids": []}, headers=_auth()
    )
    assert updated.json()["singer_ids"] == []
    assert client.delete(f"/api/besetzungen/{bid}", headers=_auth()
                         ).status_code == 204
    assert client.get(f"/api/besetzungen/{bid}").status_code == 404


def test_repertoire_crud(client):
    created = client.post(
        "/api/repertoire", json={"title": "Motette", "composer": "Bach"},
        headers=_auth(),
    )
    assert created.status_code == 201
    rid = created.json()["id"]
    assert client.put(f"/api/repertoire/{rid}", json={"dates": "2026"},
                      headers=_auth()).json()["dates"] == "2026"
    assert client.post("/api/repertoire", json={}, headers=_auth()
                       ).status_code == 422
    assert client.delete(f"/api/repertoire/{rid}", headers=_auth()
                         ).status_code == 204


def test_selbstdarstellung_put_upsert(client):
    first = client.put(
        "/api/selbstdarstellung", json={"content": "Hallo"},
        headers=_auth(),
    )
    assert first.status_code == 200
    assert first.json()["content"] == "Hallo"
    second = client.put(
        "/api/selbstdarstellung", json={"content": "Welt"},
        headers=_auth(),
    )
    assert second.json()["content"] == "Welt"
    assert second.json()["id"] == first.json()["id"]
    assert client.get("/api/selbstdarstellung").json()["content"] == "Welt"


def test_writes_rejected_without_token(client):
    assert client.post("/api/events", json={}).status_code in (401, 403)
    assert client.delete("/api/projects/p-1").status_code in (401, 403)
