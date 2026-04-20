# ChorManager - Projektplan

## 1. Projektübersicht

Desktop-Anwendung zur Verwaltung eines Chors (ca. 50 Mitglieder) für Linux Mint/Ubuntu. Lokale Datenspeicherung aus Datenschutzgründen.

**Entwicklungsansatz**: TDD (Test Driven Development) - für jeden Feature-Schritt erst Tests schreiben, dann implementieren.

---

## 2. Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Sprache | Python 3.11+ |
| GUI-Framework | PyQt6 (moderne Qt-Bindings, gute Linux-Unterstützung) |
| Datenbank | SQLite3 (lokal, keine externen Dependencies) |
| Distribution | PyInstaller → AppImage/DEB |
| Testing | pytest |

**Begründung**:
- PyQt6: Professionelles GUI-Framework, nativ auf Linux, gute Dokumentation
- SQLite: Keine Installation nötig, ACID-konform, robust gegen Datenkorruption
- PyInstaller: Bewährte Lösung für Python-Distribution

---

## 3. Datenmodell

### 3.1 Konfigurationsdatei (JSON/YAML)
```
config/
├── voice_groups.yaml    # Stimmgruppen (Sopran 1, Sopran 2, Alt 1, Alt 2, Tenor 1, Tenor 2, Bass 1, Bass 2)
└── fields.yaml         # Felddefinitionen (erweiterbar)
```

### 3.2 Datenbank-Schema (SQLite)
```sql
CREATE TABLE singers (
    id TEXT PRIMARY KEY,           -- UUID
    full_name TEXT NOT NULL,
    short_name TEXT,
    birth_date TEXT,              -- ISO 8601 (YYYY-MM-DD)
    voice_group TEXT REFERENCES voice_groups(name),
    email TEXT,
    social_contacts TEXT,         -- JSON: {twitter, instagram, ...}
    joined_year INTEGER,
    joined_month INTEGER,
    left_year INTEGER,
    left_month INTEGER,
    affinity_uuid TEXT,            -- Reference to external app
    created_at TEXT,
    updated_at TEXT
);

-- Erweiterbar: Spalten werden dynamisch aus config geladen
```

### 3.3 Feld-Erweiterbarkeit
- Felder in `fields.yaml` definieren: Name, Typ, Pflicht/Optional, Validierung
- UI generiert Formulare dynamisch basierend auf Konfiguration
- Einfaches Hinzufügen neuer Felder ohne Code-Änderung

---

## 4. Architektur (Modular)

```
chormanager/
├── config/              # Konfigurationsmanagement
├── data/                # Datenbank-Layer (Repository Pattern)
├── domain/              # Geschäftslogik (Models, Services)
├── ui/                  # PyQt6 UI-Komponenten
│   ├── widgets/         # Wiederverwendbare Widgets
│   ├── views/           # Hauptansichten
│   └── dialogs/         # Dialoge
├── export/              # Export-Logik (CSV, PDF, ODT)
├── backup/              # Backup-Management
├── history/             # Undo/Redo mit Command Pattern
├── tests/               # pytest Test-Suite
└── main.py              # Application Entry Point
```

---

## 5. Features Ausbaustufe 1

### 5.1 Stammdatenverwaltung
- [ ] CRUD für Sänger (Create, Read, Update, Delete)
- [ ] Dynamische Feldgenerierung aus Konfiguration
- [ ] Dropdown für Stimmgruppen aus config/voice_groups.yaml

### 5.2 Listenansicht / Report
- [ ] Tabellenansicht mit Sortierung und Filterung
- [ ] Report-Generator: Feldauswahl für Ausdruck
- [ ] PDF-Export (PyPDF2 oder reportlab)
- [ ] LibreOffice Writer/Calc Export via subprocess (libreoffice --convert-to)

### 5.3 CSV-Export
- [ ] Export mit Feld-Auswahl
- [ ] Import mit Validierung

### 5.4 Datensicherheit (Non-negotiable)

#### Undo/Redo
- Command Pattern für alle Änderungen
- History-Stack (max. 100 Einträge, konfigurierbar)
- Tastenkürzel: Ctrl+Z / Ctrl+Shift+Z

#### Backup-System
- **Bei Start**: Automatisches Backup beim App-Start (konfigurierbar)
- **Vor Speichern**: Sicherungskopie mit Zeitstempel
- **Backup-Verzeichnis**: `~/.local/share/chormanager/backups/`
- **Aufbewahrung**: Konfigurierbare Anzahl (z.B. letzte 10)

#### Datenintegrität
- SQLite Transactions für atomare Änderungen
- Validierung vor dem Speichern
- Konsistenzprüfung beim Start

---

## 6. TDD-Workflow

```
1. Test schreiben (tests/test_singer_crud.py)
2. Test ausführen → FAIL (rot)
3. Minimalen Code implementieren
4. Test ausführen → PASS (grün)
5. Refactor wenn nötig
6. Nächster Test
```

**Test-Kategorien**:
- Unit Tests: Modelle, Services, Validierung
- Integration Tests: Datenbank-Operationen
- GUI Tests: PyQt6 Widget-Tests mit pytest-qt

---

## 7. Ausbaustufe 2 (Terminplanung)

**Konzeptuell vorgemerkt** (nicht in Phase 1):
- Proben/Konzert-Termine
- Teilnahme-Tracking (ja/nein/vielleicht)
- Integration mit Export.odt-Struktur

Datenmodell-Erweiterung:
```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    name TEXT,
    date TEXT,
    event_type TEXT,  -- probe, konzert
    description TEXT
);

CREATE TABLE availability (
    singer_id TEXT REFERENCES singers(id),
    event_id TEXT REFERENCES events(id),
    status TEXT  -- yes, no, maybe
);
```

---

## 8. Implementierungs-Reihenfolge (TDD)

### Phase 1: Foundation
1. [ ] Projekt-Struktur erstellen
2. [ ] Config-Loader (YAML)
3. [ ] Datenbank-Verbindung + Schema
4. [ ] Singer Model + Repository

### Phase 2: Core CRUD
5. [ ] SingerRepository Tests → Implementation
6. [ ] SingerService Tests → Implementation
7. [ ] Undo/Redo Service Tests → Implementation

### Phase 3: GUI
8. [ ] Hauptfenster + Tabellenansicht
9. [ ] Singer Bearbeiten Dialog
10. [ ] Konfigurierbare Felder in UI

### Phase 4: Export/Backup
11. [ ] CSV Export/Import
12. [ ] PDF Export
13. [ ] Backup Service
14. [ ] LibreOffice Export

### Phase 5: Polish
15. [ ] Filter/Sortierung
16. [ ] Keyboard-Shortcuts
17. [ ] Logging + Fehlerbehandlung

---

## 9. Offene Fragen

- [x] **GUI-Sprache**: Deutsch
- [x] **Datum-Format**: TT.MM.JJJJ (deutsches Format)
- [x] **Backup-Speicherort**: Standard ~/.local/share/chormanager/backups/
- [x] **Logging**: Ja, mit Rotation (Python logging.handlers.RotatingFileHandler)

---

## 10. Nächste Schritte

1. Projekt-Struktur initialisieren (Python + PyQt6 + pytest)
2. Config-System implementieren mit Tests
3. Datenbank-Layer mit Tests
4. REST folgt...

