# ChorManager - Benutzerhandbuch

## Inhalt
1. [Installation](#1-installation)
2. [Oberfläche](#2-oberfläche)
3. [Projekte verwalten](#3-projekte-verwalten)
4. [Sänger verwalten](#4-sänger-verwalten)
5. [Besetzungen](#5-besetzungen)
6. [Termine und Verfügbarkeit](#6-termine-und-verfugbarkeit)
7. [Choraufstellung](#7-choraufstellung)
8. [Repertoire](#8-repertoire)
9. [Daten exportieren](#9-daten-exportieren)
10. [Einstellungen](#10-einstellungen)

---

## 1. Installation

ChorManager läuft unter Linux (Ubuntu/Mint).

```bash
./run.sh
```

Beim ersten Start wird automatisch:
- ein Virtual Environment erstellt
- die Datenbank angelegt (`~/.local/share/chormanager/chor.db`)
- ein Backup erstellt

### Portabler Modus (USB-Stick)

Sie möchten die Daten auf einem USB-Stick speichern?

1. Menü: **Extras → Einstellungen**
2. "Datenpfad" auf Ihren USB-Stick ändern
3. Fertig - alle Daten werden dort gespeichert

---

## 2. Oberfläche

### Seitenleiste (links)

Klicken Sie auf einen Menüpunkt, um den Tab zu wechseln:
- **Projekte** - Projektverwaltung
- **Sänger** - Sängerdaten
- **Besetzungen** - Sänger-Lineups
- **Termine** - Proben und Auftritte
- **Aufstellung** - Choraufstellung-Planung
- **Repertoire** - Notenverwaltung

### Context-Toolbar (oben)

Je nach Tab werden verschiedene Aktionen angeboten:
- **Hinzufügen** - Neuen Eintrag erstellen
- **Aktualisieren** - Daten neu laden
- **Bearbeiten** - Eintrag ändern
- **Löschen** - Eintrag löschen
- **Als aktiv setzen** - Projekt/Besetzung aktivieren

### Schnellsuche

Oben rechts in jedem Tab: Suchfeld für schnelle Filterung.

### Sortierung

Viele Tabellen können sortiert werden:
- **Klick auf Spaltenüberschriften** (falls implementiert)
- **Dropdown-Menüs** in der Toolbar für:
  - Sortierfeld auswählen (z.B. "Name", "Datum", "Komponist")
  - Sortierreihenfolge: Aufsteigend oder Absteigend

---

## 3. Projekte verwalten

Ein Projekt fasst alles zusammen, was zu einer Produktion gehört (z.B. "Hoffmann OKO 2026").

### Neues Projekt erstellen

1. Tab **Projekte** öffnen
2. Toolbar: **Hinzufügen** klicken
3. Felder ausfüllen:
   - **Name** (Pflichtfeld, z.B. "Hoffmann OKO 2026")
   - **Spielzeit** (z.B. "2025/26")
   - **Beschreibung** (ca. 10 Zeilen sichtbar)
4. **Speichern**

### Projekt bearbeiten

1. Projekt in der Liste auswählen
2. Toolbar: **Bearbeiten** oder Doppelklick
3. Im Dialog können Sie auch die **Repertoire-Stücke** sehen:
   - Tabelle am Ende des Dialogs
   - Zeigt: Komponist, Titel, Besetzung
   - Nur Stücke, die diesem Projekt zugeordnet sind
4. Änderungen vornehmen und **Speichern**

### Aktives Projekt setzen

Ein Projekt als "aktiv" markieren:

1. Projekt in der Liste auswählen
2. Toolbar: **Als aktives Projekt setzen**

Das aktive Projekt filtert automatisch:
- Termine im Tab **Termine**
- Sänger im Tab **Sänger** (falls projektbezogen)
- Verfügbarkeit

### Projekt duplizieren

1. Projekt auswählen
2. Rechtsklick → **Duplizieren**
3. Neues Projekt wird mit "(Kopie)" erstellt

---

## 4. Sänger verwalten

### Sänger hinzufügen

1. Tab **Sänger** öffnen
2. Toolbar: **Hinzufügen** klicken
3. Felder ausfüllen:
   - **Name** (Pflichtfeld)
   - **Kurzname** (z.B. "M. Müller")
   - **Stimmgruppe**: Sopran 1, Sopran 2, Alt 1, Alt 2, Tenor 1, Tenor 2, Bass 1, Bass 2
   - **E-Mail**, **Telefon** (optional)
   - **Adresse**: Straße, PLZ, Stadt (optional)
   - **Geburtsdatum** (für Altersberechnung)
   - **Guardien** (für Minderjährige)
   - **Beitrittsdatum**: Jahr und Monat
4. **Speichern**

### Sänger bearbeiten

1. Sänger in der Liste auswählen
2. Toolbar: **Bearbeiten** oder Doppelklick
3. Änderungen vornehmen
4. **Speichern**

**Spezialfunktion - Affinität:**
- Feld "Affinität" mit Sänger verknüpfen
- Bei Änderung wird die Verknüpfung automatisch bidirektional aktualisiert

### Filterung

- **Stimmgruppe**: Dropdown oben im Tab
- **Status**: Alle/Aktive/Minderjährige/U16
- **Suche**: Nach Name, Kurzname, E-Mail

### Sänger löschen

1. Sänger auswählen
2. Toolbar: **Löschen**
3. Bestätigen

---

## 5. Besetzungen

Eine Besetzung ist eine feste Liste von Sängern für ein Projekt.

### Neue Besetzung erstellen

1. Tab **Besetzungen** öffnen
2. Toolbar: **Hinzufügen** klicken
3. Namen eingeben (z.B. "Konzertbesetzung")
4. Sänger auswählen (Checkbox-Liste mit Name, Kurzname, Stimmgruppe, Alter)
5. **Speichern**

### Als aktiv setzen

Die aktive Besetzung wird an anderen Stellen verwendet:

1. Besetzung in der Liste auswählen
2. Toolbar: **Als aktiv setzen**

### Besetzung bearbeiten

1. Besetzung auswählen
2. Toolbar: **Bearbeiten** oder Doppelklick
3. Sänger anpassen
4. **Speichern**

### Besetzung duplizieren

1. Besetzung auswählen
2. Rechtsklick → **Duplizieren**

---

## 6. Termine und Verfügbarkeit

### Termin erstellen

1. Tab **Termine** öffnen
2. Toolbar: **Hinzufügen** klicken
3. Felder ausfüllen:
   - **Name** (z.B. "1. Generalprobe")
   - **Datum/Zeit**
   - **Typ**: 
     - GP (Generalprobe)
     - OP (Orchesterprobe)
     - SOFA (Solo/Finale/Anders)
     - Probe
     - Konzert
     - Auftritt
   - **Ort** (optional)
   - **Beschreibung** (optional)
   - **Projekt**: Automatisch auf aktives Projekt gesetzt
4. **Speichern**

### Verfügbarkeit erfassen

Für jeden Termin können Sie angeben, wer kommt:

1. Termin auswählen
2. Toolbar: **Verfügbarkeit erfassen**
3. Dialog zeigt alle Sänger mit:
   - **Schnellsuche** (Kurzname)
   - **Stimmgruppe-Filter**
   - **Sortierung** (Kurzname oder Stimmgruppe)
4. Für jeden Sänger Status wählen:
   - ✓ **Verfügbar / Zusage** (yes)
   - ✗ **Nicht verfügbar / Absage** (no)
   - ○ **Keine Rückmeldung** (none)
   - ✓? **Zusage unter Vorbehalt** (conditional)
   - ? **Weiß nicht** (unknown)
   - ~ **Vielleicht** (maybe)
5. Änderungen werden **automatisch gespeichert**

### Zusammenfassung

Im Verfügbarkeits-Dialog wird automatisch zusammengefasst:
- Anzahl pro Stimmgruppe
- Nach Status (Zusagen, Absagen, etc.)

### Verfügbarkeit exportieren

Im Verfügbarkeits-Dialog:
1. Button **Exportieren**
2. Format wählen: PDF, LibreOffice Writer, LibreOffice Calc, CSV
3. Felder auswählen: Kurzname, Stimmgruppe, Status
4. Datei wird erstellt

---

## 7. Choraufstellung

Die Choraufstellung ist ein separates Plugin zur Planung der Sängerpositionen.

### Neue Aufstellung erstellen

1. Tab **Aufstellung** öffnen
2. Toolbar: **Neue Aufstellung** klicken
3. Termin auswählen (automatisch nach aktivem Projekt gefiltert)
4. Die Choraufstellung-App öffnet sich mit den Sängern, die zugesagt haben

### Aufstellung bearbeiten

1. Datei in der Liste auswählen
2. Toolbar: **Bearbeiten** klicken
3. Choraufstellung-App öffnet die Datei

### Choraufstellung-App nutzen

- **Drag & Drop**: Sänger in die Raster ziehen
- **Rubber-Band**: Mehrere Sänger auswählen
- **Optimieren**: Automatische Platzierung
- **PDF-Export**: Druckfertige Auffstellung
- **Theming**: Hell-/Dunkelmodus

---

## 8. Repertoire

Verwalten Sie Ihr Notenarchiv.

### Stück hinzufügen

1. Tab **Repertoire** öffnen
2. Toolbar: **Hinzufügen** klicken
3. Felder ausfüllen:
   - **Komponist**: Name des Komponisten
   - **Titel**: Titel des Stücks (Pflichtfeld)
   - **Lebensdaten**: Geburts- und Sterbejahr (z.B. "1756-1791")
   - **Land**: Nationalität (z.B. "Österreich")
   - **Verlag**: Notenverlag
   - **Besetzung**: z.B. "Gemischter Chor", "SATB"
   - **Standort**: Wo sind die Noten? (z.B. "Regal A3")
   - **Programm**: Dropdown mit allen Projekten (Konzertprogrammen)
4. **Speichern**

### Programm verknüpfen

Das Feld **Programm** enthält eine Dropdown-Liste aller Konzertprogramme (Projekte):
- Wählen Sie das Projekt aus, zu dem das Stück gehört
- Das Stück erscheint dann im Projekt-Dialog unter "Stücke in diesem Programm"

### Stück bearbeiten

1. Stück in der Tabelle auswählen
2. Toolbar: **Bearbeiten** oder Doppelklick
3. Änderungen vornehmen
4. **Speichern**

### Sortierung im Repertoire-Tab

Oben in der Toolbar können Sie sortieren:
- **Sortieren nach**: Komponist, Land, Standort
- **Reihenfolge**: Aufsteigend (A-Z) oder Absteigend (Z-A)
- **Standard**: Sortiert nach Komponist, aufsteigend

### Suche im Repertoire

- Suchfeld oben rechts: Durchsucht alle Felder inklusive Programm-Namen
- Echtzeit-Filterung während der Eingabe

---

## 9. Daten exportieren

### CSV-Export

1. Menü: **Projekt → Export → CSV exportieren**
2. Felder auswählen (Name, Kurzname, Stimmgruppe, etc.)
3. Datei speichern (.csv mit Semikolon-Trennung)

### PDF-Export

Für Termine und Verfügbarkeit:

1. Menü: **Termine → Export → PDF exportieren**
2. Programm wählen (falls gefiltert)
3. PDF wird erstellt (A4, druckfertig)

### LibreOffice Export

1. Menü: **Projekt → Export → LibreOffice Writer/Spreadsheet**
2. Format wählen:
   - **Writer (.odt)**: Formattierter Text mit Tabellen
   - **Calc (.ods)**: Tabellenkalkulation
3. Datei speichern

### JSON-Sync (für Choraufstellung)

Exportiert Daten im JSON-Format für die Choraufstellung-App:
- Sänger mit Zusagen
- Termin- und Projektdaten
- Automatisch im `choraufstellung/data/`-Ordner gespeichert

### Daten-Backup

**Automatisch:**
- Bei jedem Programmstart
- Vor kritischen Speicheroperationen

**Manuell:**
1. Menü: **Extras → Backup erstellen**
2. ZIP-Datei wird erstellt mit:
   - `chor.db` (Datenbank)
   - `config/` (Einstellungen)
   - `choraufstellung/data/` (Aufstellungen)

### Daten importieren (von USB/anderem PC)

1. Menü: **Extras → Backup wiederherstellen**
2. ZIP-Backupdatei auswählen
3. Alle Daten werden überschrieben

---

## 10. Einstellungen

### Theme ändern

1. Menü: **Extras → Einstellungen**
2. **Theme**: Hell oder Dunkel wählen
3. Oberfläche wird sofort umgeschaltet

### Datenpfad ändern

1. Menü: **Extras → Einstellungen**
2. **Datenpfad**: Neuen Ordner wählen (z.B. USB-Stick)
3. Alle Daten werden dorthin verschoben

### Logging

- Log-Dateien in: `~/.local/share/chormanager/logs/`
- Automatische Rotation bei 1 MB
- Maximal 5 Backup-Logs

---

## Tastenkombinationen

| Taste | Funktion |
|-------|----------|
| `Strg+N` | Neuer Eintrag |
| `Strg+S` | Speichern |
| `Strg+Z` | Rückgängig |
| `Strg+Y` | Wiederholen |
| `F5` | Aktualisieren |

---

## Context-Menü (Rechtsklick)

In den meisten Tabellen können Sie mit **Rechtsklick** weitere Aktionen aufrufen:
- **Hinzufügen**
- **Bearbeiten**
- **Duplizieren** (falls unterstützt)
- **Löschen**
- **Umbenennen** (Besetzungen)
- **Als aktiv setzen** (Projekte, Besetzungen)

---

## Problemlösung

### App startet nicht

```bash
./run.sh
```

Falls Fehler:
- Python 3.8+ und PyQt6 erforderlich
- Virtual Environment wird automatisch erstellt

### Datenbank fehlt

Beim ersten Start wird automatisch eine neue Datenbank erstellt.

### Backup wiederherstellen

1. Menü: **Extras → Backup wiederherstellen**
2. Backup-Datei (.zip) auswählen
3. App wird neu gestartet

### "Programm" im Repertoire zeigt falsche Projekte

- Stellen Sie sicher, dass das Projekt in der Projektverwaltung existiert
- Die Verknüpfung erfolgt über die Projekt-ID (intern), nicht über den Namen
- Bei Umbenennen eines Projekts bleiben die Verknüpfungen erhalten

---

## Chordirektion-Tipps

### Effiziente Arbeitsweise

1. **Projekt zuerst**: Immer zuerst das Projekt erstellen und als aktiv setzen
2. **Sänger filtern**: Nutzen Sie die Stimmgruppe-Filter für schnelle Übersicht
3. **Verfügbarkeit erfassen**: Nutzen Sie den Verfügbarkeits-Dialog mit Zusammenfassung
4. **Repertoire verknüpfen**: Verknüpfen Sie Stücke direkt mit dem Projekt
5. **Backups**: Lassen Sie automatische Backups eingeschaltet

### Choraufstellung optimal nutzen

- Exportieren Sie die Verfügbarkeit, um zusagen zu sehen
- Nutzen Sie die "Als aktiv setzen"-Funktion für Besetzungen
- Die Choraufstellung-App arbeitet mit den Daten der aktiven Besetzung

---

## Lizenz

MIT License

---

**Version**: 1.1 (2026-04-30)  
**ChorManager Version**: 0.4  
**Neu in dieser Version**:
- Repertoire: Programm-Verknüpfung mit Dropdown
- Repertoire: Sortierung nach Komponist, Land, Standort
- Projekt-Dialog: Repertoire-Stücke am Ende angezeigt
- Projekt-Dialog: Beschreibungsfeld auf 10 Zeilen vergrößert
- Verbesserte Benutzeroberfläche und Fehlerbehebungen
