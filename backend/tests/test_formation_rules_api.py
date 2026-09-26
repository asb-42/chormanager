"""M1/M3: rule catalog for the optimizer dialog (read, open)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient wired to an empty tmp database (no token)."""
    import sqlite3

    db_path = str(tmp_path / "t.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE formations (id TEXT PRIMARY KEY, name TEXT,
            rows INTEGER NOT NULL, cols INTEGER NOT NULL,
            staggered INTEGER DEFAULT 0, voicing_config TEXT,
            singers TEXT, placed TEXT, metadata TEXT, event_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.commit()
    conn.close()
    monkeypatch.setenv("CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("CHORMANAGER_API_TOKEN", raising=False)
    from app.main import create_app
    from app import deps

    deps.get_engine.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    deps.get_engine.cache_clear()


def test_list_rules(client):
    response = client.get("/api/formations/rules")
    assert response.status_code == 200
    by_id = {rule["id"]: rule for rule in response.json()}
    assert {"height", "satb", "affinity"} <= set(by_id)
    assert by_id["height"]["primary"] is True
    assert by_id["affinity"]["primary"] is False
    assert by_id["height"]["name"]
