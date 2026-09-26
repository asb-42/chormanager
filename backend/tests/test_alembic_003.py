"""Alembic 003: description → TEXT (läuft überall fehlerfrei durch)."""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _cfg(db_path: str, monkeypatch) -> Config:
    monkeypatch.setenv(
        "CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}"
    )
    cfg = Config("backend/alembic.ini")
    cfg.set_main_option("script_location", "backend/alembic")
    return cfg


def test_003_runs_clean_on_sqlite(tmp_path, monkeypatch):
    db_path = str(tmp_path / "t.db")
    cfg = _cfg(db_path, monkeypatch)
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        names = set(inspect(engine).get_table_names())
        assert {"projects", "events", "formations"} <= names
    finally:
        engine.dispose()
