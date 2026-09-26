"""M4: formation grid PDF (§5.3) + version endpoint.

§5.3-Kriterien: Kurznamen horizontal + vertikal zentriert,
Stimmgruppen-Farben + Gruppen-Kurztext (S/W-lesbar), Kopf mit
Projekt/Termin/Datum, keine abgeschnittenen Kacheln (Fit-Skalierung),
Viewer-garantierte Schriften (reportlab Standard-14, Desktop-Parität).
"""
from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE formations (id TEXT PRIMARY KEY, name TEXT,
            rows INTEGER NOT NULL, cols INTEGER NOT NULL,
            staggered INTEGER DEFAULT 0, voicing_config TEXT,
            singers TEXT, placed TEXT, metadata TEXT, event_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    singers = [
        {"singer_id": "s-1", "name": "Anna", "voice_group": "Sopran 1",
         "height": 170, "affinity": ""},
    ]
    placed = [
        {"singer": {"singer_id": "s-2", "name": "Berta",
                    "voice_group": "Bass 2", "height": 185, "affinity": ""},
         "row": 0, "col": 1},
    ]
    metadata = {"project": "P", "event": "E", "event_date": "2026-09-26",
                "event_type": "Probe"}
    conn.execute(
        "INSERT INTO formations (id, name, rows, cols, staggered,"
        " voicing_config, singers, placed, metadata, event_id,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("f-1", "Probe", 4, 5, 0, "[]", json.dumps(singers),
         json.dumps(placed), json.dumps(metadata), "e-1",
         "2026-01-01", "2026-01-01"),
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


def test_formation_pdf(client):
    response = client.get("/api/formations/f-1/pdf")
    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_formation_pdf_not_found(client):
    assert client.get("/api/formations/nope/pdf").status_code == 404


def test_version_matches_desktop(client):
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json()["version"] == "0.1.0"
