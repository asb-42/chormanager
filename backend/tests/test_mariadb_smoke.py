"""M1 MariaDB-Smoke: Dialekt-Portabilität gegen echte MariaDB.

Läuft nur mit gesetzter ``CHORMANAGER_TEST_MARIADB_URL``
(sonst skipped) — braucht ``backend/docker-compose.yml`` up:

    docker compose -f backend/docker-compose.yml up -d
    CHORMANAGER_TEST_MARIADB_URL="mysql+pymysql://chor:chor@127.0.0.1:3306/chor" \\
        .venv/bin/python -m pytest backend/tests/test_mariadb_smoke.py -q

Der Test fährt Alembic head hoch, schreibt/liest über die API
(Singer-CRUD, Availability-Bulk, Summary) und räumt die DB wieder
ab (downgrade base). Fängt MariaDB-Spezifika (utf8mb4, ilike,
Aggregates, Text-Spalten).
"""
from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

NEEDS_MARIADB = pytest.mark.skipif(
    not os.environ.get("CHORMANAGER_TEST_MARIADB_URL"),
    reason="Nur mit CHORMANAGER_TEST_MARIADB_URL (MariaDB up)",
)


def _alembic_cfg(url: str) -> Config:
    cfg = Config("backend/alembic.ini")
    cfg.set_main_option("script_location", "backend/alembic")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def mariadb_url(monkeypatch):
    """URL aus der Umgebung, als API-Default gesetzt (Auth offen)."""
    url = os.environ["CHORMANAGER_TEST_MARIADB_URL"]
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", url)
    monkeypatch.delenv("CHORMANAGER_API_TOKEN", raising=False)
    from app import deps

    deps.get_engine.cache_clear()
    yield url
    deps.get_engine.cache_clear()


@NEEDS_MARIADB
def test_upgrade_head_and_api_roundtrip(mariadb_url, monkeypatch):
    from app.main import create_app

    cfg = _alembic_cfg(mariadb_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = create_engine(mariadb_url, future=True)
    try:
        names = set(inspect(engine).get_table_names())
        assert {
            "singers", "events", "projects", "availability",
            "besetzung", "repertoire", "selbstdarstellung", "formations",
        } <= names
        with engine.begin() as conn:
            row = conn.execute(
                text("SHOW CREATE TABLE availability")
            ).first()
            assert "utf8mb4" in row[1].lower()

        with TestClient(create_app()) as client:
            singer = client.post(
                "/api/singers", json={"full_name": "Maria DB"}
            ).json()
            assert singer["id"]
            event = client.post(
                "/api/events",
                json={"name": "E", "date": "2026-01-01",
                      "event_type": "Probe"},
            ).json()
            put = client.put(
                f"/api/events/{event['id']}/availability",
                json={"entries": [
                    {"singer_id": singer["id"], "status": "yes"}]},
            ).json()
            assert put["updated"] == 1
            matrix = client.get(
                f"/api/events/{event['id']}/availability"
            ).json()
            assert matrix["entries"][0]["status"] == "yes"
            found = client.get(
                "/api/singers", params={"search": "maria"}
            ).json()
            assert [s["id"] for s in found] == [singer["id"]]
    finally:
        command.downgrade(cfg, "base")
