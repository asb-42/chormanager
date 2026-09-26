"""Import-Skript: sqlite→sqlite Roundtrip erhält alle Zeilen."""
from __future__ import annotations

import sqlite3
import subprocess
import sys


def test_import_roundtrip(tmp_path):
    src = tmp_path / "src.db"
    dst = tmp_path / "dst.db"
    conn = sqlite3.connect(str(src))
    conn.execute(
        """CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
            voice_group TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE events (id TEXT PRIMARY KEY, name TEXT NOT NULL,
            date TEXT NOT NULL, event_type TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    conn.executemany(
        "INSERT INTO singers (id, full_name, voice_group,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        [("s-1", "Anna", "Sopran 1", "2026-01-01", "2026-01-01"),
         ("s-2", "Berta", None, "2026-01-01", "2026-01-01")],
    )
    conn.execute(
        "INSERT INTO events (id, name, date, event_type,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("e-1", "Probe", "2026-09-01", "Probe", "2026-01-01", "2026-01-01"),
    )
    conn.commit()
    conn.close()

    # Ziel-DB: leere Hülle mit neuen Tabellen (simuliert frische Migration)
    from sqlalchemy import create_engine

    from app.tables import metadata

    engine = create_engine(f"sqlite:///{dst}")
    metadata.create_all(engine)
    engine.dispose()

    script = "backend/tools/import_sqlite.py"
    result = subprocess.run(
        [sys.executable, script, str(src),
         "--dst", f"sqlite:///{dst}", "--force"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    check = sqlite3.connect(str(dst))
    try:
        assert check.execute("SELECT COUNT(*) FROM singers").fetchone()[0] == 2
        assert check.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        row = check.execute(
            "SELECT full_name, voice_group FROM singers WHERE id='s-1'"
        ).fetchone()
        assert tuple(row) == ("Anna", "Sopran 1")
    finally:
        check.close()


def test_import_refuses_nonempty_without_force(tmp_path):
    import shutil

    src = tmp_path / "src.db"
    dst = tmp_path / "dst.db"
    conn = sqlite3.connect(str(src))
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
    shutil.copy(str(src), str(dst))

    script = "backend/tools/import_sqlite.py"
    result = subprocess.run(
        [sys.executable, script, str(src), "--dst", f"sqlite:///{dst}"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 1
    assert "Abbruch" in result.stdout
