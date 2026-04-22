# ChorManager

Desktop-Anwendung zur Verwaltung eines Chors für Linux Mint/Ubuntu.

## Features

### Stammdatenverwaltung
- **Sänger-Verwaltung**: Name, Kurzname, Stimmgruppe, E-Mail, Telefon, Adresse
- **Dynamische Felder**: Felder können über YAML-Konfiguration erweitert werden
- **Filter/Suche**: Suche nach Name, E-Mail, Telefon; Filter nach Stimmgruppe
- **Undo/Redo**: Vollständige Rückgängig/Wiederholen-Funktion
- **Automatische Backups**: Bei Start und vor dem Speichern

### Projekte & Termine
- **Projektverwaltung**: Projekte erstellen und verwalten (z.B. "Hoffmann OKO 2026")
- **Projekt-Filter**: Bei aktivem Projekt werden nur zugehörige Daten angezeigt
- **Projekt-Info**: Aktuelles Projekt wird im Header angezeigt
- **Terminverwaltung**: Termine erstellen mit Typ (GP, OP, SOFA, Probe, Konzert, Auftritt)
- **Termin-Projekt-Zuordnung**: Jeder Termin ist einem Projekt zugeordnet
- **Verfügbarkeit**: Verwaltung von Sänger-Verfügbarkeit für Termine
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
- Folgende Daten werden übertragen: singer_id, full_name, short_name, voice_group, affinity_uuid

**Aktuelle Limitierungen**:
- Die Integration ist **einweg**: Änderungen in Choraufstellung fließen **NICHT** zurück in die ChorManager-Datenbank
- Drag & Drop: Funktioniert abhängig von Event-Verfügbarkeitsdaten
- Speicherort: Alle Daten werden in `choraufstellung/data/` gespeichert (nicht im User-Home)

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
- **Tab-Interface**: Projekte, Sänger, Termine als separate Tabs
- **Sortierung**: Klick auf Spaltenüberschriften sortiert auf-/absteigend
- **Verfügbarkeits-Dialog**: Radio-Buttons für Status-Auswahl mit Zusammenfassungstabelle
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
│   ├── views/           # Hauptansichten (Sänger, Termine, Projekte)
│   └── dialogs/         # Dialoge (Event, Availability, Config, Selbstdarstellung)
├── export/              # Export-Logik (CSV, PDF, JSON, DB-Zugriff)
├── backup/              # Backup-Management
├── history/             # Undo/Redo mit Command Pattern
└── tests/               # pytest Test-Suite
```

## Änderungen

### Version 1.x (2026)

- Projektverwaltung hinzugefügt
- Tab-basierte UI mit Projekt-, Sänger- und Termine-Tabs
- Projekt-Filter für Sänger und Termine
- Verfügbarkeits-Dialog mit Radio-Buttons und Zusammenfassung nach Stimmgruppen
- Direkter DB-Zugriff für Choraufstellung (chormanager_db.py Modul)
- Choraufstellung-Menüintegration
- Selbstdarstellung (Marketing-Texte) im Menü
- Konfigurationsdialog für Pfade, Backup, Logging, Theme
- Erweiterte Tests für Project, Event, Availability Repository + Export-Modul
- **PyQt6-Portierung**: Alle Enums auf scoped format umgestellt (Qt6 compatibility)
- **Sängerpool laden**: Event-basierte Verfügbarkeit wird aus DB gelesen
- **Speicherort**: Alle Choraufstellung-Daten lokal im `data/`-Ordner

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

### Änderungen heute (2026-04-22)\n\n**UI/UX-Verbesserungen:**\n- Sidebar-Navigation mit Material Design Icons (📁 Projekte, 👤 Sänger, 📅 Termine, 🎵 Aufstellung)\n- Context Toolbar horizontal über Content-Bereich positioniert\n- Info-Bar unter Hauptmenü mit Projekt-/Termin-Status-Anzeige\n- Seitentitel für alle Tabs hinzugefügt\n- Suchfunktionalität in allen Tabs (inkl. neu hinzugefügter Suche in Choraufstellung)\n- Theme-Switching über Menü "Ansicht → Hell/Dunkel"\n\n**Theme-System überarbeitet:**\n- QDarkStyleSheet-Integration anstatt improvisierter Stylesheets\n- Professionelle 54KB Light/Dark-Themes\n- Material Design Icons integriert und heruntergeladen\n- PyQtDarkTheme durch QDarkStyle ersetzt (wegen Python 3.12-Kompatibilität)\n\n**Code-Verbesserungen:**\n- Duplicate Layout-Addition in singers_tab.py behoben\n- Tab-Switching-Logik korrigiert (self.tabs → self.content_stack)\n- Imports für QLabel und QIcon hinzugefügt\n- Dark Theme CSS für bessere Lesbarkeit optimiert\n\n**Dependencies:**\n- QDarkStyle zu requirements.txt hinzugefügt\n- Material Design Icons heruntergeladen in assets/icons/\n\n**Testing:**\n- Alle Unit-Tests erfolgreich (135 passed, 1 skipped)
