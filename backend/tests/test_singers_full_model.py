"""Vollständiges Sänger-Modell (20 Felder, Desktop-Parität) + Sortierung."""
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
    conn.commit()
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient ohne Token (offen)."""
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


FULL = {
    "full_name": "Max Muster",
    "short_name": "Max",
    "birth_date": "2010-05-01",
    "voice_group": "Sopran 1",
    "height": 150,
    "email": "max@example.org",
    "phone": "0123",
    "street": "Weg 1",
    "postal_code": "12345",
    "city": "Ort",
    "gender": "m",
    "guardian1": "Mutter",
    "guardian1_phone": "0111",
    "guardian2": "Vater",
    "guardian2_phone": "0222",
    "social_contacts": "threema: max",
    "joined_year": 2024,
    "joined_month": 9,
    "left_year": None,
    "left_month": None,
    "affinity_uuid": "aff-1",
}


def test_full_model_roundtrip(client):
    created = client.post("/api/singers", json=FULL)
    assert created.status_code == 201, created.text
    singer_id = created.json()["id"]
    fetched = client.get(f"/api/singers/{singer_id}").json()
    for key, value in FULL.items():
        assert fetched[key] == value, key
    updated = client.put(
        f"/api/singers/{singer_id}",
        json={"guardian1": "Oma", "joined_month": 10},
    )
    assert updated.status_code == 200
    assert updated.json()["guardian1"] == "Oma"
    assert updated.json()["joined_month"] == 10


def test_sorting(client):
    for name, voice in [("Zeta", "Bass 2"), ("Alpha", "Sopran 1")]:
        response = client.post(
            "/api/singers",
            json={"full_name": name, "voice_group": voice},
        )
        assert response.status_code == 201
    by_voice = client.get(
        "/api/singers", params={"sort": "voice_group", "direction": "desc"}
    ).json()
    assert [s["voice_group"] for s in by_voice] == ["Sopran 1", "Bass 2"]
    default = client.get("/api/singers").json()
    assert [s["full_name"] for s in default] == ["Alpha", "Zeta"]
    bad = client.get("/api/singers", params={"sort": "hacker"})
    assert bad.status_code == 422
