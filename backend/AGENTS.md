# AGENTS.md — backend/

## Purpose
**Web backend** (FastAPI, M1+): REST-API über dem bestehenden
Datenbestand. Spiegelt die Kontrakte aus
``docs/plans/2026-09-26_m0_erd-openapi.md`` §3; läuft ab M5 per
Docker Compose (api + db + static-frontend).

## Ownership
Das Backend gehört der Web-Migration (Branch ``web-migration``).
Der Qt-Desktop auf ``main`` bleibt unberührt — das Backend liest
den Bestand zunächst nur (SQLite-Datei des Desktops).

## Local Contracts

* **Portable SQL only.** Nur ``String``/``Integer``-Spalten,
  keine Dialekt-Sondertypen (Analyse §5.6: SQLite heute,
  MariaDB morgen, kein Lock-in).
* **One module per resource.** ``app/routers/<name>.py`` je
  Ressource, Schemas in ``app/schemas.py``, Tabellen in
  ``app/tables.py`` (Spiegel von
  ``chormanager/data/database.py::create_tables``).
* **App factory.** ``app/main.py::create_app()`` baut die App;
  Tests nutzen ``TestClient(create_app())`` mit
  ``CHORMANAGER_DATABASE_URL`` auf Tmp-DB (kein Touch von
  ``data/chor.db``).
* **Python 3.11+.** Kein 3.9-Zwang hier (gilt nur für den
  Qt-Desktop, Analyse §5.5). Trotzdem `Optional[...]`-Stil
  statt PEP-604-Unions — konsistent zum Repo.

## Work Guidance

* Neue Endpunkte folgen den M0-Kontrakten
  (``docs/plans/2026-09-26_m0_erd-openapi.md`` §3); Abweichungen
  dort nachziehen.
* Lesende Endpunkte zuerst (Desktop-Parität prüfen), Writes +
  Auth danach.

## Verification

```bash
.venv/bin/python -m pytest backend/tests/ -q
```

## Child DOX Index

* ``app/`` — Factory, Deps, Schemas, Tabellen, Router
  (kein eigenes AGENTS.md; folgt diesem Doc).
* ``tests/`` — Backend-Tests (TestClient, Tmp-DB).
