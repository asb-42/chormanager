"""M1 writes (1/2): token auth + singer CRUD.

Plan ref: Analyse §3.1/§3.4 (Single-User + Token; Rollen-Reserve),
m0_erd-openapi §3. Reads bleiben offen; Writes brauchen
``Authorization: Bearer <CHORMANAGER_API_TOKEN>``. Ohne gesetztes
Token (Dev-Default) ist alles offen. Gültiges Token ⇒ Rolle
``chorleiter`` (Reserve für Sänger-Portal, §3.4).
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
    conn.execute(
        """CREATE TABLE availability (id TEXT PRIMARY KEY,
            singer_id TEXT NOT NULL, event_id TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(singer_id, event_id))"""
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, short_name, voice_group,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("s-1", "Anna Muster", "Anna", "Sopran 1",
          "2026-01-01", "2026-01-01")],
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


def test_reads_stay_open(client):
    assert client.get("/api/singers").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_write_without_token_rejected(client):
    response = client.post("/api/singers", json={"full_name": "X"})
    assert response.status_code in (401, 403)


def test_write_with_wrong_token_rejected(client):
    response = client.post(
        "/api/singers",
        json={"full_name": "X"},
        headers={"Authorization": "Bearer falsch"},
    )
    assert response.status_code in (401, 403)


def test_create_singer(client):
    response = client.post(
        "/api/singers",
        json={"full_name": "Clara Neu", "short_name": "Clara",
              "voice_group": "Alt 1", "height": 172},
        headers=_auth(),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["id"]
    assert payload["short_name"] == "Clara"
    assert client.get(f"/api/singers/{payload['id']}").status_code == 200


def test_create_singer_requires_name(client):
    response = client.post("/api/singers", json={}, headers=_auth())
    assert response.status_code == 422


def test_update_singer(client):
    response = client.put(
        "/api/singers/s-1", json={"height": 171}, headers=_auth()
    )
    assert response.status_code == 200
    assert response.json()["height"] == 171
    assert response.json()["full_name"] == "Anna Muster"


def test_update_singer_not_found(client):
    response = client.put(
        "/api/singers/nope", json={"height": 1}, headers=_auth()
    )
    assert response.status_code == 404


def test_delete_singer(client):
    response = client.delete("/api/singers/s-1", headers=_auth())
    assert response.status_code == 204
    assert client.get("/api/singers/s-1").status_code == 404


def test_delete_singer_not_found(client):
    response = client.delete("/api/singers/nope", headers=_auth())
    assert response.status_code == 404


def test_open_mode_without_token_env(tmp_path, monkeypatch):
    """Ohne CHORMANAGER_API_TOKEN (Dev-Default): alles offen."""
    db_path = str(tmp_path / "open.db")
    _seed_db(db_path)
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("CHORMANAGER_API_TOKEN", raising=False)
    from app.main import create_app
    from app import deps

    deps.get_engine.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/singers", json={"full_name": "Offen"}
            )
            assert response.status_code == 201
    finally:
        deps.get_engine.cache_clear()
