"""Alembic 002: formations-Tabelle für Bestands-DBs nachziehen.

Befund (Klick-Test): Desktop-DBs kennen keine ``formations``-Tabelle;
``stamp head`` markiert nur, erzeugt aber nichts. Verfahren für
Bestands-DBs: ``stamp 001`` (Baseline passt), dann ``upgrade head``
(002 erzeugt formations idempotent). Frische DBs: 002 ist No-op.
"""
from __future__ import annotations

import sqlite3

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


def _legacy_db(db_path: str) -> None:
    """Desktop-DB ohne formations (nur Kern-Tabellen, eine Zeile)."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        "INSERT INTO singers (id, full_name, created_at, updated_at)"
        " VALUES ('s-1', 'Anna', '2026-01-01', '2026-01-01')"
    )
    conn.commit()
    conn.close()


def test_002_adds_formations_to_stamped_legacy_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "legacy.db")
    _legacy_db(db_path)
    cfg = _cfg(db_path, monkeypatch)
    command.stamp(cfg, "001")
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        names = set(inspect(engine).get_table_names())
        assert "formations" in names
        from sqlalchemy import text

        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM singers")).scalar()
        assert count == 1
    finally:
        engine.dispose()


def test_002_noop_on_fresh_upgrade(tmp_path, monkeypatch):
    db_path = str(tmp_path / "fresh.db")
    cfg = _cfg(db_path, monkeypatch)
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        names = set(inspect(engine).get_table_names())
        assert "formations" in names
    finally:
        engine.dispose()
