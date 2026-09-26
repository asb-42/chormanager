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
