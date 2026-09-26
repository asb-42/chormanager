# ChorManager Backend (M1+)

FastAPI-API über dem bestehenden SQLite-Bestand (später MariaDB).
Python 3.11+ (Analyse §5.5); läuft in der Repo-`.venv`.

## Start (Dev)

```bash
# DB: Default ist <repo>/data/chor.db, sonst Env:
export CHORMANAGER_DATABASE_URL="sqlite:////pfad/chor.db"
# später: export CHORMANAGER_DATABASE_URL="mysql+pymysql://user:pw@host/chor"

.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
# Docs: http://localhost:8000/docs
```

## Tests

```bash
.venv/bin/python -m pytest backend/tests/ -q
```

## Migrationen (Alembic)

```bash
# Neue leere DB aufsetzen:
CHORMANAGER_DATABASE_URL="sqlite:////pfad/neu.db" \
  .venv/bin/alembic -c backend/alembic.ini upgrade head

# Bestands-DB (Desktop-Schema, kennt nur die 7 Desktop-Tabellen):
# 1. Baseline stempeln (Schema passt bereits, nichts läuft),
# 2. upgrade head (Revision 002 zieht NUR die neue formations-Tabelle
#    idempotent nach, Daten bleiben unangetastet).
# NICHT "stamp head" — das würde formations nie erzeugen!
CHORMANAGER_DATABASE_URL="sqlite:////pfad/chor.db" \
  .venv/bin/alembic -c backend/alembic.ini stamp 001
CHORMANAGER_DATABASE_URL="sqlite:////pfad/chor.db" \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
```

Folge-Revisionen (z. B. `formations`-Tabelle für gestempelte
Bestands-DBs, `users`/`roles` mit dem Portal) kommen als `002+`.

## MariaDB (M1-Abschluss, verifiziert)

```bash
docker compose -f backend/docker-compose.yml up -d
CHORMANAGER_DATABASE_URL="mysql+pymysql://chor:chor@127.0.0.1:3306/chor" \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
CHORMANAGER_TEST_MARIADB_URL="mysql+pymysql://chor:chor@127.0.0.1:3306/chor" \
  .venv/bin/python -m pytest backend/tests/test_mariadb_smoke.py -q
```

Der Smoke-Test fährt head hoch, prüft utf8mb4, dreht eine
API-Runde (CRUD, Bulk, ilike-Suche) und räumt per Downgrade ab.
Credentials für Prod aus der Umgebung (M5); alle Typen portabel
(Analyse §5.6).

## Erstbefüllung aus der Desktop-DB

```bash
.venv/bin/python backend/tools/import_sqlite.py data/chor.db \
  --dst "mysql+pymysql://chor:chor@127.0.0.1:3306/chor" --force
```

Ohne `--force` Abbruch bei nicht-leerem Ziel. Lange Texte
(`description`) sind TEXT-Spalten (Revision 003) — VARCHAR würde
echte Projektbeschreibungen kappen.

## Auth (Single-User-Stufe)

Reads sind offen. Writes brauchen ohne gesetztes Token nichts
(Dev-Default); mit gesetztem Token einen Bearer:

```bash
export CHORMANAGER_API_TOKEN="..."
# Header: Authorization: Bearer ...
```

Gültiges Token ⇒ Rolle `chorleiter` (Reserve für Portal-Rollen,
Analyse §3.4; `users`-Tabelle kommt mit dem Portal-Meilenstein).

## Stand (M1-Inkremente 1–3)

- `GET /api/health`, `GET /api/singers[?search=&voice_group=]`,
  `GET /api/singers/{id}` (lesend, SQLAlchemy Core, portable Typen)
- Nächste Inkremente: restliche Router (M0-Kontrakte
  `docs/plans/2026-09-26_m0_erd-openapi.md` §3), Writes + Auth,
  Alembic-Baseline, MariaDB-Umstellung.
