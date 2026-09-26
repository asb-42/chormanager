"""SQLite → Ziel-DB importieren (Erstbefüllung MariaDB aus Desktop-DB).

Kopiert alle Tabellen aus ``app.tables.metadata``, die in der Quelle
existieren (Spaltenschnittmenge, fehlende Zielspalten bleiben NULL).
Ohne ``--force`` Abbruch bei nicht-leerem Ziel (kein versehentliches
Mischen, z. B. mit Smoke-Daten).

    .venv/bin/python backend/tools/import_sqlite.py data/chor.db \\
        --dst mysql+pymysql://chor:chor@127.0.0.1:3306/chor --force
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, delete, func, select  # noqa: E402

from app.tables import metadata  # noqa: E402


def _src_columns(src: sqlite3.Connection, table: str) -> list:
    """Spaltennamen der Quelltabelle in Reihenfolge."""
    return [row[1] for row in src.execute(f"PRAGMA table_info({table})")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", help="SQLite-Quelldatei (Desktop-DB)")
    parser.add_argument(
        "--dst",
        default=None,
        help="Ziel-URL (Default: CHORMANAGER_DATABASE_URL)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ziel-Tabellen vorher leeren",
    )
    args = parser.parse_args()

    dst_url = args.dst or os.environ.get("CHORMANAGER_DATABASE_URL")
    if not dst_url:
        print("Fehler: --dst oder CHORMANAGER_DATABASE_URL nötig")
        return 2
    src_path = Path(args.src)
    if not src_path.is_file():
        print(f"Fehler: Quelle fehlt: {src_path}")
        return 2

    src = sqlite3.connect(str(src_path))
    try:
        src_tables = {
            row[0]
            for row in src.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    except sqlite3.DatabaseError as exc:
        print(f"Fehler: Quelle unlesbar: {exc}")
        src.close()
        return 2

    engine = create_engine(dst_url, future=True)
    total = 0
    try:
        with engine.begin() as conn:
            for table in metadata.sorted_tables:
                if table.name not in src_tables:
                    print(f"skip {table.name} (nicht in Quelle)")
                    continue
                if args.force:
                    conn.execute(delete(table))
                else:
                    existing = conn.execute(
                        select(func.count()).select_from(table)
                    ).scalar()
                    if existing:
                        print(
                            f"Abbruch: {table.name} enthält {existing} "
                            f"Zeilen (nochmal mit --force)"
                        )
                        return 1
                common = [
                    col.name
                    for col in table.columns
                    if col.name in set(_src_columns(src, table.name))
                ]
                rows = src.execute(
                    f"SELECT {', '.join(common)} FROM {table.name}"
                ).fetchall()
                if rows:
                    conn.execute(
                        table.insert(),
                        [dict(zip(common, row)) for row in rows],
                    )
                print(f"{table.name}: {len(rows)} Zeilen")
                total += len(rows)
    finally:
        src.close()
        engine.dispose()
    print(f"fertig: {total} Zeilen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
