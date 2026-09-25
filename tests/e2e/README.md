# E2E-Tier (Web): Gerüst, aktiv ab M3/M4

## Status (M0)

Gerüst only: `conftest.py` (Fixtures + Vertrag), zwei Spec-Dateien mit
übersprungenen Schritt-Tests. Kein `playwright`-Paket, keine Browser —
Installation erst in M3, wenn es eine App zum Testen gibt.

## Ausführen

```bash
# E2E einsammeln (alles skipped bis M3/M4):
python -m pytest tests/e2e/ -q

# Nur E2E:
python -m pytest tests/ -q -m e2e

# Desktop-Suite ohne E2E (Standard):
python -m pytest tests/ -q -m "not e2e"
```

## Aktivierungs-Checkliste (M3/M4)

1. `playwright` + Browser installieren (`pip install playwright`,
   `playwright install chromium`).
2. `WEB_BASE_URL` auf die laufende App zeigen lassen
   (Default `http://localhost:8000`).
3. `seeded_formation` + `web_page` in `conftest.py` echt
   implementieren (Seed via Backend-API, Login-Flow).
4. `pytestmark.skip` in den Spec-Dateien entfernen.
5. `data-testid`-Selektoren im Frontend (M2/M3) nach den
   Schritt-Docstrings vergeben.
