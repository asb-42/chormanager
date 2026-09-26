"""M1 Alembic: Baseline-Revision über alle 8 Tabellen.

Plan ref: M1 (Alembic-Migrationen aus database.py-Schema + neue
M1-Tabellen). Upgrade head auf leerer SQLite-DB erzeugt alle
Tabellen (7 Desktop + formations); Downgrade base räumt ab.
Dialektneutral formuliert (SQLite heute, MariaDB morgen, §5.6).
"""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

EXPECTED_TABLES = {
    "singers",
    "events",
    "projects",
    "selbstdarstellung",
    "availability",
    "besetzung",
    "repertoire",
    "formations",
}


def _cfg(db_path: str, monkeypatch) -> Config:
    monkeypatch.setenv(
        "CHORMANAGER_DATABASE_URL", f"sqlite:///{db_path}"
    )
    cfg = Config("backend/alembic.ini")
    cfg.set_main_option("script_location", "backend/alembic")
    return cfg


def test_upgrade_head_creates_all_tables(tmp_path, monkeypatch):
    db_path = str(tmp_path / "mig.db")
    command.upgrade(_cfg(db_path, monkeypatch), "head")
    names = set(inspect(create_engine(f"sqlite:///{db_path}"))
                .get_table_names())
    assert EXPECTED_TABLES <= names
    assert "alembic_version" in names


def test_downgrade_base_removes_all_tables(tmp_path, monkeypatch):
    db_path = str(tmp_path / "mig.db")
    cfg = _cfg(db_path, monkeypatch)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    names = set(inspect(create_engine(f"sqlite:///{db_path}"))
                .get_table_names())
    assert EXPECTED_TABLES.isdisjoint(names)
