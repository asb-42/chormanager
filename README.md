# ChorManager

Desktop-Anwendung zur Verwaltung eines Chors für Linux Mint/Ubuntu.

> Änderungsverlauf: siehe [CHANGELOG.md](CHANGELOG.md)

## Features

### Aufgaben (Startansicht)
- **Aufgaben-Karten**: Leitfaden für Nicht-Techniker statt leerer Projekte-Tabelle; Fortschritt basiert auf offenen Vorbedingungen
- **Geführter Assistent (Wizard)**: Schritt-für-Schritt durch die Kern-Workflows
  - Aufstellung für einen Auftritt planen (Projekt → Termin → Besetzung → Zusagen → Aufstellung öffnen)
  - Neuen Termin eintragen
  - Zusagen und Absagen erfassen
  - Chormitglied aufnehmen
- Bestätigt erkannte Vorbedingungen, statt sie zu überspringen

### Stammdatenverwaltung
- **Sänger-Verwaltung**: Name, Kurzname, Stimmgruppe, Größe, E-Mail, Telefon, Adresse
- **Dynamische Felder**: Felder können über YAML-Konfiguration erweitert werden
- **Filter/Suche**: Suche nach Name, E-Mail, Telefon; Filter nach Stimmgruppe
- **Sortierung**: Nach Name, Stimmgruppe oder Größe sortierbar
- **Undo/Redo**: Vollständige Rückgängig/Wiederholen-Funktion
- **Automatische Backups**: Bei Start und vor dem Speichern
- **Auto-Reload**: Datenbank nach Backup-Wiederherstellung automatisch neu geladen

### Projekte & Termine
- **Projektverwaltung**: Projekte erstellen und verwalten (z.B. "Hoffmann OKO 2026")
- **Projekt-Filter**: Bei aktivem Projekt werden nur zugehörige Daten angezeigt
- **Projekt-Info**: Aktuelles Projekt wird im Header angezeigt
- **Terminverwaltung**: Termine erstellen mit Typ (GP, OP, SOFA, Probe, Konzert, Auftritt)
- **Termin-Projekt-Zuordnung**: Jeder Termin ist einem Projekt zugeordnet
- **Verfügbarkeit**: Verwaltung von Sänger-Verfügbarkeit für Termine
- **Verfügbarkeits-Button**: Schnellzugriff auf Verfügbarkeit im Termine-Tab
- **Sortierung**: Termine nach Datum, Name oder Typ sortierbar
- **Zusammenfassung**: Automatische Auswertung nach Stimmgruppen
- **Zusagen/Absagen-Liste**: Projekt-weite Rückmeldematrix aller Termine als PDF oder LibreOffice-Datei (Register-Summen inklusive)

### Verfügbarkeits-Status
- ✓ Verfügbar / Zusage (yes)
- ✗ Nicht verfügbar / Absage (no)
- ○ Keine Rückmeldung (none)
- ✓? Zusage unter Vorbehalt (conditional)
- ? Weiß nicht (unknown)
- ~ Vielleicht (maybe)

### Marketing
- **Selbstdarstellung**: Texte für Chor-Präsentation (Marketing-Menü)

### Exporte
- **CSV Export**: Export aller Sängerdaten
- **PDF Export**: Druckfertige Listen (via reportlab)
- **LibreOffice Export**: Writer und Calc Formate
- **JSON-Sync**: Export für Choraufstellung

### Integration
- **Choraufstellung-Integration**: Menü "Choraufstellung" → "In Choraufstellung öffnen..."
- **ChorManagerBridge**: Sänger-Zusagen werden bevorzugt über eine temporäre JSON-Datei (ENV `CHOR_EVENT_DATA`) übergeben; SQLite-Zugriff als Fallback
- Folgende Daten werden übertragen: singer_id, full_name, short_name, voice_group, height, affinity_uuid
- Metadaten: Projekt, Termin, Termin-Typ werden in JSON-Datei gespeichert

### Choraufstellung

Die Choraufstellung-App ist im `choraufstellung/` Verzeichnis enthalten und wird über das ChorManager-Menü (Choraufstellung → In Choraufstellung öffnen...) gestartet.

#### Integration ChorManager ↔ Choraufstellung

**Einweg-Integration** (ChorManager → Choraufstellung):
- Sänger mit Zusagen ("yes" oder "conditional") werden aus der ChorManager-Datenbank geladen
- Event-ID wird via Umgebungsvariable übergeben
- Folgende Daten werden übertragen: singer_id, full_name, short_name, voice_group, height, affinity_uuid
- Metadaten: Projekt, Termin, Termin-Typ werden in JSON-Datei gespeichert

**Aktuelle Limitierungen**:
- Die Integration ist **einweg**: Änderungen in Choraufstellung fließen **NICHT** zurück in die ChorManager-Datenbank
- Drag & Drop: Funktioniert abhängig von Event-Verfügbarkeitsdaten
- Speicherort: Alle Daten werden in `chormanager/choraufstellung/data/` gespeichert (nicht im User-Home)
- Auto-Save & Wiederherstellung: Automatische Zwischenspeicherung mit Rotation; beim Start wird angeboten, einen neueren Auto-Save wiederherzustellen

#### Choraufstellung Features

- **Optimieren**: Automatische Platzierung mit verschiedenen Regeln:
  - Nach Stimmgruppen sortiert
  - Nach Größe (Height) sortiert
  - Nähe (Singpartner) berücksichtigen
  - Stimmgruppen zusammenhaltend
- **PDF-Export**: Druckfertige Aufstellung
  - Konfigurationsdialog: Schriftgröße, Seitenrand, Schwarz-Weiß-Modus
  - Querformat-Automatik
  - Versetztes Raster unterstützt
- **Theming**: Hell-/Dunkelmodus
  - Stimmgruppen-Farben theme-aware (Hell/Dunkel)
  - Konfigurierbar in `config/voice_groups.json`
- **Nähe (Singpartner)**: Menüpunkt platziert Sänger mit Affinität zusammen

#### PyQt6

Die App nutzt PyQt6 mit **scoped Enums** (Qt6-Format), z.B.
`Qt.Orientation.Horizontal`, `QMessageBox.StandardButton.Save`,
`Qt.DropAction.CopyAction`, `e.globalPosition()`. (Historie der
Umbauten von Qt5-Konstanten: siehe CHANGELOG.)

### UI/UX
- **Theme**: Hell/Dunkel-Modus (via Konfigurationsdialog einstellbar)
- **Tab-Interface**: Aufgaben, Projekte, Sänger, Besetzungen, Termine, Aufstellung, Repertoire
- **Sortierung**: Dropdown-Sortierung in Sänger (Name, Stimmgruppe, Größe), Termine (Datum, Name, Typ), Aufstellung (Dateiname, Projekt, Datum)
- **Verfügbarkeits-Dialog**: Radio-Buttons für Status-Auswahl mit Zusammenfassungstabelle
- **Verfügbarkeits-Button**: Schnellzugriff im Termine-Tab
- **Konfigurationsdialog**: Einstellungen für Datenpfade, Backup, Logging, Choraufstellung

### Sonstiges
- **Logging**: Automatische Log-Dateien mit Rotation
- **Datenimport**: CSV + UUID aus externer JSON-Datei

## Installation

```bash
cd /media/data/coding/chormanager
./run.sh
```

Erstellt automatisch das Virtual Environment und installiert Dependencies.

## Datenstandort & Portabler Modus

### Standard-Speicherort

Die Datenbank liegt in:
```
~/.local/share/chormanager/chor.db
```

Backups werden erstellt in:
```
~/.local/share/chormanager/backups/
```

Logs werden erstellt in:
```
~/.local/share/chormanager/logs/
```

### Portabler Modus (USB-Stick / Wechsel zwischen Rechnern)

ChorManager kann alle Daten in **einem** Verzeichnis bündeln – ideal für USB-Stick oder Wechsel zwischen Rechnern:

1. **Konfigurationsdialog öffnen** (Extras → Einstellungen)
2. **Datenpfad** auf gewünschten Ordner setzen (z.B. USB-Stick)
3. Fertig – alle Daten werden jetzt dort gespeichert

### Daten exportieren / importieren

Um alle Daten auf einen anderen PC zu übertragen:

1. **Export**: Extras → Daten exportieren... → erstellt `chormanager_daten_2026-04-16.zip`
2. Auf USB-Stick sichern
3. **Import**: Auf dem anderen PC Extras → Daten importieren... → ZIP auswählen

Kein komplizierter technischer Vorgang – Chorleiter-gerecht!

## Konfiguration

Konfigurationsdateien befinden sich im `config/` Verzeichnis:
- `voice_groups.yaml` - Stimmgruppen-Konfiguration
- `fields.yaml` - Sänger-Felder
- `app.yaml` - App-Einstellungen

## Datenmodell

### Tabellen

- **singers**: Sänger-Stammdaten
- **events**: Termine
- **projects**: Projekte (inkl. `spielzeit`)
- **availability**: Verfügbarkeit pro Sänger/Termin
- **selbstdarstellung**: Marketing-Texte
- **besetzung**: Sänger-Lineups
- **repertoire**: Repertoire-Einträge

### Beziehungen

```
projects (1) → (n) events
projects (1) → (n) besetzung
projects (1) → (n) repertoire
events (1) → (n) availability
singers (1) → (n) availability
```

## Tests

```bash
cd /media/data/coding/chormanager
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
```

Die Suite umfasst über 1300 Tests (Unit, Integration, GUI) und läuft
headless — kein Display-Server nötig.

## Technologien

- **Python 3.9+**
- **PyQt6** (GUI; PyQt5 wird für Dual-Bind-Dialog-Tests zusätzlich benötigt)
- **SQLite** (Datenbank)
- **PyYAML** (Konfiguration)
- **reportlab** (PDF-Export)
- **pytest** (Tests; inkl. pytest-qt, hypothesis)

## Architektur

```
chormanager/
├── config/              # Konfigurationsmanagement
├── data/                # Datenbank-Layer
├── domain/              # Geschäftslogik (Models, Services)
├── ui/                  # PyQt6 UI-Komponenten
│   ├── views/           # Hauptansichten (Aufgaben, Sänger, Termine, Projekte, Repertoire, Aufstellung)
│   └── dialogs/         # Dialoge (Event, Availability, Config, Selbstdarstellung)
├── export/              # Export-Logik (CSV, PDF, JSON, DB-Zugriff)
├── backup/              # Backup-Management
├── history/             # Undo/Redo mit Command Pattern
├── tools/               # Hilfs-Skripte (z.B. import_singers.py)
├── core/                # Qt-freie Kernlogik (Optimizer, Response-Matrix, Export-Renderers)
├── chorAufstellung/    # Sub-App Aufstellungs-Editor (eigenständige QtWidgets-App)
│   ├── core/            # Regeln/Optimizer/Raster (Qt-frei)
│   ├── ui/ & widgets/   # Grid, Pool, Menüs
│   └── services/        # Autosave, Recovery, PDF, Bridge
└── tests/               # pytest Test-Suite (unit / integration / gui)
```

## Änderungsverlauf

Siehe [CHANGELOG.md](CHANGELOG.md).

