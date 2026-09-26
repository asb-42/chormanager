# M0: ERD + API-Kontrakte (Stand 2026-09-26, Branch `web-migration`)

**Status:** Kontrakt-Entwurf, keine Implementierung. Quelle: `chormanager/data/database.py:186-295`
(`Database.create_tables`), Eigner-Vorgaben 2026-09-26 (§5.1–§5.9 der Web-Migrationsanalyse).
**Ziel-DB:** MariaDB InnoDB utf8mb4 (s. Analyse §5.6). SQL portabel halten (keine PG-Typen).

## 1. ERD (Ist-Schema, 7 Tabellen)

```mermaid
erDiagram
    PROJECTS ||--o{ EVENTS : "project_id (SET NULL)"
    PROJECTS ||--o{ BESETZUNG : "project_id (SET NULL)"
    PROJECTS ||--o{ REPERTOIRE : "project_id (SET NULL)"
    SINGERS ||--o{ AVAILABILITY : "singer_id (CASCADE)"
    EVENTS ||--o{ AVAILABILITY : "event_id (CASCADE)"
    SINGERS {
        text id PK "UUID"
        text full_name
        text short_name
        text birth_date "ISO"
        text voice_group "Sopran 1..Bass 2"
        int height
        text email
        text phone
        text street
        text postal_code
        text city
        text gender
        text guardian1
        text guardian1_phone
        text guardian2
        text guardian2_phone
        text social_contacts
        int joined_year
        int joined_month
        int left_year
        int left_month
        text affinity_uuid "Sitzpartner"
        text created_at
        text updated_at
    }
    EVENTS {
        text id PK
        text name
        text date "ISO"
        text event_type "GP/OP/SOFA/Probe/Konzert/Auftritt"
        text location
        text description
        text project_id FK
        text created_at
        text updated_at
    }
    PROJECTS {
        text id PK
        text name
        text description
        int is_active
        text spielzeit
        text created_at
        text updated_at
    }
    SELBSTDARSTELLUNG {
        text id PK
        text content
        text updated_at
    }
    AVAILABILITY {
        text id PK
        text singer_id FK
        text event_id FK
        text status "yes/no/none/conditional/unknown/maybe"
        text created_at
        text updated_at
    }
    BESETZUNG {
        text id PK
        text name
        text project_id FK
        text singer_ids "JSON-Array als TEXT"
        text created_at
        text updated_at
    }
    REPERTOIRE {
        text id PK
        text composer
        text title
        text dates
        text country
        text publisher
        text arrangement
        text location
        text project_id FK
        text created_at
        text updated_at
    }
```

**Auffälligkeiten für M1:**
- `UNIQUE(singer_id, event_id)` auf `availability` existiert bereits — trägt das Concurrent-Write-Modell der Sänger-Reserve (§3.4).
- `besetzung.singer_ids` ist ein JSON-Array in TEXT — aus Paritätsgründen in M1 unverändert übernehmen, Normalisierung (Join-Tabelle) erst bei Bedarf.
- IDs sind TEXT-UUIDs, Daten ISO-TEXT — MariaDB-Mapping 1:1 möglich (`TEXT`, `INT`, `DATETIME` für neue Zeitspalten).
- `spielzeit` + Adress-/Guardian-Spalten kamen per `ALTER TABLE`-Migration dazu (`database.py:297+`) — Alembic-Baseline in M1 muss den **migrierten** Endstand abbilden, nicht nur `create_tables`.

## 2. Geplante neue Tabellen (M1, noch nicht im Desktop)

| Tabelle | Zweck | Quelle |
|---|---|---|
| `formations` | Ersatz für Formations-JSONs in `choraufstellung/data/` (`rows`, `cols`, `staggered`, `voicing_config`, `placements` als JSON, `metadata`) | Analyse §7 |
| `voice_groups` | Eine Quelle für Stimmgruppen-Farben hell/dunkel (löst `voice_groups.yaml`+`.json`-Duplikat auf) | Analyse §5.4, §7 |
| `users` + `roles` | **Reserve, minimal befüllt:** genau 1 Chorleiter-User; Sänger-Portal später (§3.4) | Analyse §3.4, §5.8 |

## 3. API-Kontrakte (OpenAPI-Draft für M1, Gruppierung = Router)

```text
/singers                 GET (Liste+Filter), POST
/singers/{id}            GET, PUT, DELETE
/events                  GET (Projekt-Filter), POST
/events/{id}             GET, PUT, DELETE
/events/{id}/availability GET (Matrix), PUT (Bulk)
/projects                GET, POST
/projects/{id}           GET, PUT, DELETE
/projects/{id}/summary   GET (Zusagen-Auswertung je Stimmgruppe)
/besetzungen             GET, POST
/besetzungen/{id}        GET, PUT, DELETE
/repertoire              GET, POST
/repertoire/{id}         GET, PUT, DELETE
/selbstdarstellung       GET, PUT
/formations              GET, POST
/formations/{id}         GET, PUT, DELETE
/formations/{id}/placements PUT (Bulk, Autosave-Ziel)
/formations/{id}/optimize   POST (rule_ids -> Diff+Vorschau, s. §3.3)
/export/singers.csv      GET
/export/zusagen.pdf      GET (reportlab, Qualitätskriterien §5.3)
/export/zusagen.odt      GET
/export/sync.json        GET (Choraufstellung-Format, kompatibel)
/backup                  POST (anlegen), GET (Liste)
/backup/{id}/restore     POST
/config/voice-groups     GET, PUT (Admin)
/me/availability/{event_id} PUT (RESERVE Sänger-Portal, idempotent)
```

Konventionen: UUIDs als Pfad-IDs, ISO-8601-Daten, Bulk-Endpoints für Matrix/Placements,
`ETag`/`If-Match` (Revisions-Check Single-Editor, §5.2), Fehlerformat `{"detail": ...}` (FastAPI-Standard).

## 4. E2E-Basis (Playwright, implementiert in M3/M4, hier nur festgelegt)

- Smoke 1 (MS3): Login → Formation öffnen → Kachel per Drag verschieben → Undo → Optimizer-Diff übernehmen.
- Smoke 2 (MS4): Termin anlegen → Verfügbarkeiten bulk setzen → Zusagen-PDF laden (Status 200, `%PDF`-Header).
- Abnahmegerät: Notebook mit Maus/Trackpad (§5.1). Kein Mobile-Smoke in M0–M5.
