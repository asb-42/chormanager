"""M1 formations: CRUD + placements + optimizer-preview (Kernstück).

Plan ref: m0_erd-openapi §3, Analyse §3.3 (Regeln server-seitig,
Preview ohne Persist; Übernahme per Placements-PUT).
``formations`` ist eine neue M1-Tabelle (kein Desktop-Vorgänger).
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE events (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            date TEXT NOT NULL, event_type TEXT NOT NULL,
            project_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            short_name TEXT, voice_group TEXT, height INTEGER,
            affinity_uuid TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE availability (id TEXT PRIMARY KEY,
            singer_id TEXT NOT NULL, event_id TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(singer_id, event_id))"""
    )
    conn.execute(
        """CREATE TABLE formations (id TEXT PRIMARY KEY, name TEXT,
            rows INTEGER NOT NULL, cols INTEGER NOT NULL,
            staggered INTEGER DEFAULT 0, voicing_config TEXT,
            singers TEXT, placed TEXT, metadata TEXT, event_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.executemany(
        "INSERT INTO events (id, name, date, event_type,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("e-1", "Probe", "2026-09-01", "Probe", "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, short_name, voice_group,"
        " height, affinity_uuid, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [("s-1", "Anna Muster", "Anna", "Sopran 1", 170, "",
          "2026-01-01", "2026-01-01"),
         ("s-2", "Berta Beispiel", "Berta", "Bass 2", 185, "",
          "2026-01-01", "2026-01-01"),
         ("s-3", "Clara X", "Clara", "Alt 1", 168, "",
          "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO availability (id, singer_id, event_id, status,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("a-1", "s-1", "e-1", "yes", "2026-01-01", "2026-01-01"),
         ("a-2", "s-2", "e-1", "conditional", "2026-01-01", "2026-01-01"),
         ("a-3", "s-3", "e-1", "no", "2026-01-01", "2026-01-01")],
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


def _create(client, **kwargs):
    payload = {"name": "F1", "rows": 4, "cols": 5, "event_id": "e-1"}
    payload.update(kwargs)
    response = client.post("/api/formations", json=payload, headers=_auth())
    assert response.status_code == 201, response.text
    return response.json()


def test_create_seeds_available_singers(client):
    doc = _create(client)
    assert doc["rows"] == 4
    assert doc["event_id"] == "e-1"
    assert {s["singer_id"] for s in doc["singers"]} == {"s-1", "s-2"}
    assert doc["placed"] == []
    assert doc["metadata"]["event"] == "Probe"


def test_create_unknown_event_404(client):
    response = client.post(
        "/api/formations",
        json={"rows": 4, "cols": 5, "event_id": "nope"}, headers=_auth(),
    )
    assert response.status_code == 404


def test_list_and_get_detail(client):
    doc = _create(client)
    listed = client.get("/api/formations").json()
    assert [f["id"] for f in listed] == [doc["id"]]
    detail = client.get(f"/api/formations/{doc['id']}").json()
    assert detail["singers"] == doc["singers"]
    assert client.get("/api/formations/nope").status_code == 404


def test_put_placements_persists(client):
    doc = _create(client)
    response = client.put(
        f"/api/formations/{doc['id']}/placements",
        json={"placements": [
            {"singer_id": "s-1", "row": 0, "col": 1},
            {"singer_id": "s-2", "row": 1, "col": 0},
        ]},
        headers=_auth(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert {(p["singer"]["singer_id"], p["row"], p["col"])
            for p in payload["placed"]} == {("s-1", 0, 1), ("s-2", 1, 0)}
    assert payload["singers"] == []
    # Omitted singers become unplaced.
    response = client.put(
        f"/api/formations/{doc['id']}/placements",
        json={"placements": [{"singer_id": "s-1", "row": 2, "col": 2}]},
        headers=_auth(),
    )
    assert {(p["singer"]["singer_id"], p["row"], p["col"])
            for p in response.json()["placed"]} == {("s-1", 2, 2)}
    assert {s["singer_id"] for s in response.json()["singers"]} == {"s-2"}


def test_put_placements_validates(client):
    doc = _create(client)
    fid = doc["id"]
    # Out of bounds.
    response = client.put(
        f"/api/formations/{fid}/placements",
        json={"placements": [{"singer_id": "s-1", "row": 9, "col": 0}]},
        headers=_auth(),
    )
    assert response.status_code == 422
    # Unknown singer.
    response = client.put(
        f"/api/formations/{fid}/placements",
        json={"placements": [{"singer_id": "s-x", "row": 0, "col": 0}]},
        headers=_auth(),
    )
    assert response.status_code == 422
    # Duplicate cell.
    response = client.put(
        f"/api/formations/{fid}/placements",
        json={"placements": [
            {"singer_id": "s-1", "row": 0, "col": 0},
            {"singer_id": "s-2", "row": 0, "col": 0}]},
        headers=_auth(),
    )
    assert response.status_code == 422
    # Nothing persisted by the rejected calls.
    assert client.get(f"/api/formations/{fid}").json()["placed"] == []


def test_put_placements_with_resize(client):
    doc = _create(client)
    response = client.put(
        f"/api/formations/{doc['id']}/placements",
        json={"rows": 2, "cols": 2, "placements": [
            {"singer_id": "s-1", "row": 1, "col": 1}]},
        headers=_auth(),
    )
    assert response.status_code == 200
    assert response.json()["rows"] == 2


def test_optimize_preview_without_persist(client):
    doc = _create(client)
    client.put(
        f"/api/formations/{doc['id']}/placements",
        json={"placements": [
            {"singer_id": "s-2", "row": 0, "col": 0},
            {"singer_id": "s-1", "row": 0, "col": 1}]},
        headers=_auth(),
    )
    response = client.post(
        f"/api/formations/{doc['id']}/optimize",
        json={"rule_ids": ["height"]},
        headers=_auth(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert {p["singer_id"] for p in payload["placements"]} == {"s-1", "s-2"}
    assert "swap_count" in payload
    # Preview only: stored placements unchanged.
    stored = client.get(f"/api/formations/{doc['id']}").json()
    assert {(p["singer"]["singer_id"], p["row"], p["col"])
            for p in stored["placed"]} == {("s-2", 0, 0), ("s-1", 0, 1)}


def test_optimize_unknown_rule_422(client):
    doc = _create(client)
    response = client.post(
        f"/api/formations/{doc['id']}/optimize",
        json={"rule_ids": ["nonsense"]},
        headers=_auth(),
    )
    assert response.status_code == 422


def test_delete_formation(client):
    doc = _create(client)
    assert client.delete(f"/api/formations/{doc['id']}",
                         headers=_auth()).status_code == 204
    assert client.get(f"/api/formations/{doc['id']}").status_code == 404


def test_writes_rejected_without_token(client):
    assert client.post("/api/formations", json={"rows": 1, "cols": 1}
                       ).status_code in (401, 403)
