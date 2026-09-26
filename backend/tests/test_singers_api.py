"""M1 increment 1: backend skeleton + singers read API.

Plan ref: docs/plans/2026-09-25_web-migration-analyse.md (M1),
docs/plans/2026-09-26_m0_erd-openapi.md §3 (``/singers`` contracts).

Run from repo root with the project venv::

    .venv/bin/python -m pytest backend/tests/ -q
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
        "INSERT INTO singers (id, full_name, short_name, voice_group,"
        " height, email, street, city, affinity_uuid,"
        " created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("s-1", "Anna Muster", "Anna", "Sopran 1", 170,
             "anna@example.org", "Weg 1", "Ort", "", "2026-01-01", "2026-01-01"),
            ("s-2", "Berta Beispiel", "Berta", "Bass 2", 185,
             None, None, None, "", "2026-01-01", "2026-01-01"),
        ],
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


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_singers(client):
    response = client.get("/api/singers")
    assert response.status_code == 200
    payload = response.json()
    assert [s["id"] for s in payload] == ["s-1", "s-2"]
    assert payload[0]["short_name"] == "Anna"
    assert payload[0]["voice_group"] == "Sopran 1"


def test_list_singers_search_filter(client):
    response = client.get("/api/singers", params={"search": "bert"})
    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == ["s-2"]


def test_list_singers_search_address(client):
    response = client.get("/api/singers", params={"search": "weg"})
    assert response.status_code == 200
    assert [s["id"] for s in response.json()] == ["s-1"]


def test_list_singers_voice_group_filter(client):
    response = client.get("/api/singers", params={"voice_group": "Bass 2"})
    assert [s["id"] for s in response.json()] == ["s-2"]


def test_get_singer(client):
    response = client.get("/api/singers/s-1")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Anna Muster"


def test_get_singer_not_found(client):
    response = client.get("/api/singers/nope")
    assert response.status_code == 404
