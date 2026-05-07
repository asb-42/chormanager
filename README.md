# ChorManager

Desktop-Anwendung zur Verwaltung eines Chors für Linux Mint/Ubuntu.

## Features

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
- **Direkter DB-Zugriff**: Choraufstellung kann die Datenbank readonly öffnen
- **Environment-Variablen**: Projekt- und Termin-Daten werden via ENV an Choraufstellung übergeben

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
- Speicherort: Alle Daten werden in `choraufstellung/data/` gespeichert (nicht im User-Home)

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

Die App使用的是 PyQt6 mit folgenden Enum-Änderungen:
- `Qt.Horizontal` → `Qt.Orientation.Horizontal`
- `Qt.AlignCenter` → `Qt.AlignmentFlag.AlignCenter`
- `QFrame.Panel` → `QFrame.Shape.Panel`
- `QMessageBox.Save` → `QMessageBox.StandardButton.Save`
- `Qt.CaseInsensitive` → `Qt.CaseSensitivity.CaseInsensitive`
- `QRubberBand.Rectangle` → `QRubberBand.Shape.Rectangle`
- `drag.exec(1)` → `drag.exec(Qt.DropAction.CopyAction)`
- `e.globalPos()` → `e.globalPosition()`

### UI/UX
- **Theme**: Hell/Dunkel-Modus (via Konfigurationsdialog einstellbar)
- **Tab-Interface**: Projekte, Sänger, Besetzungen, Termine, Aufstellung, Repertoire
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

### Portabler Modus (USB-Stick / Wechsel между компьютерами)

ChorManager kann alle Daten in **einem** Verzeichnis bündeln – ideal für USB-Stick oder Wechsel между PCs:

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
- **projects**: Projekte
- **availability**: Verfügbarkeit pro Sänger/Termin
- **selbstdarstellung**: Marketing-Texte

### Beziehungen

```
projects (1) → (n) events
events (1) → (n) availability
singers (1) → (n) availability
```

## Tests

```bash
cd /media/data/coding/chormanager
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit/ -v
```

## Technologien

- **Python 3.8+**
- **PyQt6** (GUI)
- **SQLite** (Datenbank)
- **PyYAML** (Konfiguration)
- **reportlab** (PDF-Export)
- **pytest** (Tests)

## Architektur

```
chormanager/
├── config/              # Konfigurationsmanagement
├── data/                # Datenbank-Layer
├── domain/              # Geschäftslogik (Models, Services)
├── ui/                  # PyQt6 UI-Komponenten
│   ├── views/           # Hauptansichten (Sänger, Termine, Projekte, Repertoire, Aufstellung)
│   └── dialogs/         # Dialoge (Event, Availability, Config, Selbstdarstellung)
├── export/              # Export-Logik (CSV, PDF, JSON, DB-Zugriff)
├── backup/              # Backup-Management
├── history/             # Undo/Redo mit Command Pattern
├── tools/               # Hilfs-Skripte (z.B. import_singers.py)
└── tests/               # pytest Test-Suite
```

## Änderungen

### Version 1.x (2026)

- Projektverwaltung hinzugefügt
- Tab-basierte UI mit Projekt-, Sänger-, Besetzung-, Termine-, Aufstellung- und Repertoire-Tabs
- Projekt-Filter für Sänger und Termine
- Verfügbarkeits-Dialog mit Radio-Buttons und Zusammenfassung nach Stimmgruppen
- Verfügbarkeits-Button für schnellen Zugriff
- Direkter DB-Zugriff für Choraufstellung (chormanager_db.py Modul)
- Choraufstellung-Menüintegration
- Selbstdarstellung (Marketing-Texte) im Menü
- Konfigurationsdialog für Pfade, Backup, Logging, Theme
- Erweiterte Tests für Project, Event, Availability Repository + Export-Modul
- **PyQt6-Portierung**: Alle Enums auf scoped format umgestellt (Qt6 compatibility)
- **Sängerpool laden**: Event-basierte Verfügbarkeit wird aus DB gelesen
- **Speicherort**: Alle Choraufstellung-Daten lokal im `data/`-Ordner
- **Sänger-Größe**: height-Feld für optimale Choraufstellung-Platzierung
- **Sortierung**: Dropdown-Sortierung in Sänger-, Termine- und Aufstellung-Tabs
- **Auto-Reload**: Datenbank nach Backup-Wiederherstellung automatisch neu geladen
- **Choraufstellung-Enhancements**:
  - PDF-Export mit Konfigurationsdialog
  - Nähe (Singpartner) Optimierung
  - Stimmgruppen-Farben (theme-aware)
  - Versetztes Raster im PDF-Export

### Version 0.x

- Ursprüngliche Version mit Sänger-Verwaltung

---

### Änderungen heute (2026-04-21)

**ChorManager → Choraufstellung Integration:**
- Neuer Tab "Aufstellung" zeigt alle JSON-Aufstellungsdateien
- Spalten: Dateiname, Dateigröße, Projekt, Termin (Datum), Typ (Event-Name), Gespeichert
- Automatischer Dateiname beim Speichern
- Metadaten in JSON: Projekt, Termin, Termin-Datum
- Tab-Refresh bei Rückkehr aus Choraufstellung
- Kontextmenü: "Bearbeiten", "Duplizieren"

**Choraufstellung App:**
- Optimiert aufstellen funktioniert wieder
- PDF-Export: Automatische Querformat-Erkennung
- PDF-Export: Versetztes Raster unterstützt
- Druck-Menü getrennt

**DB-Schema:**
- `address` ersetzt durch `street`, `postal_code`, `city`
- Tests aktualisiert

### Änderungen heute (2026-04-23)

**Besetzung Feature (neu):**
- Neuer Tab "Besetzungen" zur Verwaltung von Sänger-Lineups
- SingerSelectionDialog: Checkbox-Tabelle mit Name, Kurzname, Stimmgruppe, Alter
- Besetzungen persistent in Datenbank (`besetzung` Tabelle)
- "Als aktiv setzen" speichert aktive Besetzung sitzungsübergreifend
- Info-Bar zeigt aktive Besetzung an (zwischen Projekt und Termin)

**UI-Verbesserungen:**
- Context Toolbar mit vollständigen Aktionen für Besetzung-Tab
- Context Menu: Bearbeiten, Umbenennen, Als aktiv, Löschen
- Dunkeltheme: QCheckBox-Styling hinzugefügt
- Tab-Indizes korrigiert (0=Projekte, 1=Sänger, 2=Besetzung, 3=Termine, 4=Aufstellung, 5=Repertoire)
- Projekt-Dropdown aus Besetzung-Tab entfernt (verwendet aktives Projekt)
- Alter-Spalte in SingerSelectionDialog

**Besetzung-Verfügbarkeit Filter (nicht vollständig implementiert):**
- EventAvailabilityDialog mit besetzung_ids Parameter
- Filter-Logik in _load_availability()
- Kommunikation mit besetzung_tab nicht funktional

**Diverses:**
- SingerSelectionDialog: Klasse in dialogs.py definiert
- QDialog.DialogCode.Accepted für PyQt6-Kompatibilität
- Parent-Parameter für Theme-Vererbung

**Testing:**
- Alle Unit-Tests erfolgreich (135 passed, 1 skipped)

---

### Änderungen heute (2026-05-07)

**ChorManager Enhancements:**
- Sänger-Größe (height) Feld hinzugefügt für Choraufstellung-Optimierung
- Sortierung in Sänger-Tab: Nach Name, Stimmgruppe oder Größe sortierbar
- Sortierung in Termine-Tab: Dropdown für Datum, Name, Typ
- Verfügbarkeits-Button in Termine-Tab für schnellen Zugriff
- Auto-Reload: Datenbank nach Backup-Wiederherstellung automatisch neu geladen
- Repertoire: Projekt-Verknüpfung und Sortierung verbessert

**Choraufstellung Enhancements:**
- PDF-Export: Konfigurationsdialog (Schriftgröße, Seitenrand, Schwarz-Weiß-Modus)
- PDF-Export: Versetztes Raster und Querformat-Automatik
- 'Nähe (Singpartner)' Menü für Affinitäts-Optimierung
- Stimmgruppen-Farben: Theme-aware (Hell/Dunkel), konfigurierbar in `config/voice_groups.json`
- Arrangement-Regeln: S1S2A1A2, S1S2B1B2T1T2A1A2, VoiceGroupCohesion
- Auto-Arrange by Height: Sänger nach Größe automatisch platzieren
- Metadaten: Projekt, Termin, Termin-Typ in JSON-Datei gespeichert

**Testing:**
- Neue Tests: test_metadata_saving.py, test_arrangement_rules.py
- Alle Unit-Tests erfolgreich
