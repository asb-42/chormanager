"""M1 export/config: CSV, Sync-JSON, Zusagen-PDF, Voice-Groups.

Plan ref: m0_erd-openapi §3. Desktop-Parität: CSV/Sync-Shapes aus
``export/sync.py``, Zusagen-PDF via ``core/response_matrix`` +
``core/response_render_pdf`` (reportlab, server-seitig §3.1),
Voice-Groups aus YAML (Gruppen) + JSON (Theme-Farben) gemergt.
Reads sind offen (kein Token nötig).
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE events (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            date TEXT NOT NULL, event_type TEXT NOT NULL, description TEXT,
            project_id TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            short_name TEXT, voice_group TEXT, affinity_uuid TEXT,
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
        "INSERT INTO projects (id, name, created_at, updated_at)"
        " VALUES (?, ?, ?, ?)",
        [("p-1", "Hoffmann", "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO events (id, name, date, event_type, description,"
        " project_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [("e-1", "Probe", "2026-09-01", "Probe", "", "p-1",
          "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, short_name, voice_group,"
        " affinity_uuid, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("s-1", "Anna Muster", "Anna", "Sopran 1", "",
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
    """TestClient wired to a seeded tmp database (no token)."""
    db_path = str(tmp_path / "t.db")
    _seed_db(db_path)
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("CHORMANAGER_API_TOKEN", raising=False)
    from app.main import create_app
    from app import deps

    deps.get_engine.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    deps.get_engine.cache_clear()


def test_singers_csv(client):
    response = client.get("/api/export/singers.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == ["singer_id", "name", "voice_group", "affinity"]
    assert rows[1] == ["s-1", "Anna", "Sopran 1", ""]


def test_sync_json_compat_shapes(client):
    response = client.get("/api/export/sync.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["singers"][0] == {
        "singer_id": "s-1", "name": "Anna",
        "voice_group": "Sopran 1", "affinity": "",
    }
    assert payload["events"][0]["event_id"] == "e-1"
    matrix = payload["availability"][0]
    assert matrix["event_id"] == "e-1"
    assert matrix["availability"][0]["status"] == "yes"


def test_zusagen_pdf(client):
    response = client.get(
        "/api/export/zusagen.pdf", params={"project_id": "p-1"}
    )
    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert response.content.startswith(b"%PDF")


def test_zusagen_pdf_unknown_project(client):
    response = client.get(
        "/api/export/zusagen.pdf", params={"project_id": "nope"}
    )
    assert response.status_code == 404


def test_voice_groups_merged(client):
    response = client.get("/api/config/voice-groups")
    assert response.status_code == 200
    by_id = {g["id"]: g for g in response.json()}
    assert by_id, "Gruppenliste darf nicht leer sein"
    sopran = by_id["Sopran 1"]
    assert sopran["short"] == "S1"
    assert sopran["color_light"].startswith("#")
    assert sopran["color_dark"].startswith("#")
