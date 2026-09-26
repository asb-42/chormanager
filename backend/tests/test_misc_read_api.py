"""M1 increment 2c: Besetzung/Repertoire/Selbstdarstellung read API.

Plan ref: docs/plans/2026-09-26_m0_erd-openapi.md §3.
``singer_ids`` kommt geparst als Liste (Fallback ``[]`` bei
korruptem JSON); leere Selbstdarstellung liest sich als
``{"id": None, "content": ""}`` statt 404.
"""
from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient


def _seed_db(path: str, with_selbstdarstellung: bool = True) -> None:
    conn = sqlite3.connect(path)
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
        "INSERT INTO besetzung (id, name, project_id, singer_ids,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("b-1", "Stamm", "p-1", json.dumps(["s-1", "s-2"]),
          "2026-01-01", "2026-01-01"),
         ("b-2", "Gäste", "p-2", "kein-json{{{",
          "2026-01-01", "2026-01-01")],
    )
    conn.executemany(
        "INSERT INTO repertoire (id, composer, title, project_id,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        [("r-1", "Bach", "Motette", "p-1", "2026-01-01", "2026-01-01"),
         ("r-2", "Mozart", "Messe", "p-2", "2026-01-01", "2026-01-01")],
    )
    if with_selbstdarstellung:
        conn.execute(
            "INSERT INTO selbstdarstellung (id, content, updated_at)"
            " VALUES (?, ?, ?)",
            ("d-1", "Wir sind der Chor.", "2026-01-01"),
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


def test_list_besetzungen(client):
    response = client.get("/api/besetzungen")
    assert response.status_code == 200
    by_id = {b["id"]: b for b in response.json()}
    assert set(by_id) == {"b-1", "b-2"}
    assert by_id["b-1"]["singer_ids"] == ["s-1", "s-2"]
    # Korruptes JSON fällt auf [] zurück statt zu crashen.
    assert by_id["b-2"]["singer_ids"] == []


def test_list_besetzungen_project_filter(client):
    response = client.get("/api/besetzungen", params={"project_id": "p-1"})
    assert [b["id"] for b in response.json()] == ["b-1"]


def test_besetzung_carries_updated_at(client):
    response = client.get("/api/besetzungen/b-1")
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2026-01-01"


def test_get_besetzung_not_found(client):
    assert client.get("/api/besetzungen/nope").status_code == 404


def test_list_repertoire_project_filter(client):
    response = client.get("/api/repertoire", params={"project_id": "p-2"})
    payload = response.json()
    assert [r["id"] for r in payload] == ["r-2"]
    assert payload[0]["composer"] == "Mozart"


def test_list_repertoire_search_and_sort(client):
    found = client.get("/api/repertoire", params={"search": "moz"}).json()
    assert [r["id"] for r in found] == ["r-2"]
    by_composer = client.get(
        "/api/repertoire", params={"sort": "composer", "direction": "desc"}
    ).json()
    assert [r["id"] for r in by_composer] == ["r-2", "r-1"]
    bad = client.get("/api/repertoire", params={"sort": "hacker"})
    assert bad.status_code == 422


def test_get_repertoire_not_found(client):
    assert client.get("/api/repertoire/nope").status_code == 404


def test_get_selbstdarstellung(client):
    response = client.get("/api/selbstdarstellung")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "d-1"
    assert payload["content"] == "Wir sind der Chor."


def test_get_selbstdarstellung_empty(tmp_path, monkeypatch):
    from app.main import create_app
    from app import deps

    db_path = str(tmp_path / "empty.db")
    _seed_db(db_path, with_selbstdarstellung=False)
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    deps.get_engine.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.get("/api/selbstdarstellung")
            assert response.status_code == 200
            assert response.json() == {"id": None, "content": ""}
    finally:
        deps.get_engine.cache_clear()
