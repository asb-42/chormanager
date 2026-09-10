# Changelog

Alle nennenswerten Änderungen an ChorManager. Die Einträge folgen
[Keep a Changelog](https://keepachangelog.com/de/) in Kurzform —
user-facing Änderungen und wichtige interne Fixes, gruppiert nach
Datum (neueste zuerst).

## 2026-09-09

### Hinzugefügt
- **Aufgaben-Ansicht mit geführtem Assistent**: Neue Startansicht
  (erster Sidebar-Eintrag) mit Aufgaben-Karten und Schritt-für-Schritt-
  Wizard für die Kern-Workflows:
  - „Eine Aufstellung für einen Auftritt planen" (Projekt → Termin →
    Besetzung → Zusagen → Aufstellung öffnen)
  - „Einen neuen Termin eintragen"
  - „Zusagen und Absagen erfassen"
  - „Ein Chormitglied aufnehmen"
  - Karten zeigen Fortschritt anhand **offener Vorbedingungen**;
    der Wizard bestätigt erkannte Vorbedingungen, statt sie zu
    überspringen. Dunkles Theme wird unterstützt.
- **Projekt-weite Zusagen/Absagen-Liste** (Response-Matrix) als
  PDF oder LibreOffice-Datei, inkl. Register-Summen
  (Sopran/Alti/Tenor/Bass) im Verfügbarkeits-Export.

### Behoben
- `closeEvent`-Hänger in ChorAufstellung: `is_modified` wurde als
  Bound Method (immer truthy) statt als Funktionsaufruf ausgewertet —
  der „Änderungen speichern?"-Dialog erschien auch bei unmodifizierten
  Fenstern und blockierte offscreen dauerhaft.
- `save_state` legt fehlendes `data/`-Verzeichnis an (frühe State-Writes
  auf jungfräulichem Clone liefen vorher in `FileNotFoundError`).
- Löschen von Projekt/Termin/Besetzung räumt verwaiste Aktiv-IDs in
  `state.json` auf („Aktiv-Parameter verschwinden"-Bug).
- Besetzungs-Label in der Info-Bar bleibt konsistent, wenn die
  aktive Besetzung wechselt.
- `_restore_active_event` wirft keinen `NameError` mehr bei
  gelöschten Terminen; verwaiste IDs werden still bereinigt.
- Wizard-Abschluss synchronisiert den gepinnten Termin für alle Tasks;
  „Aktives Projekt" wird einheitlich aus der UI-Quelle (Config) gelöst.
- Hardcoded-Pfad in `_show_about` entfernt (`__file__`-basiert).

### Intern
- Integration der 71 Upstream-Commits (M-1-Mixin-Architektur,
  M-2-ChorAufstellung-Services: autosave, recovery, theme, undo_bridge,
  PDF-Export-Integration, ChorManager-Bridge) — `chormanager_db.py`
  und parallele Lokal-Strukturen wurden als superseded entfernt.
- `spielzeit`-DB-Migration (`ALTER TABLE projects ADD COLUMN spielzeit`)
  für Datenbanken vor dem Feature.
- Test-Isolation: keine Suite schreibt mehr in die echte
  `data/state.json`; ChorAufstellung-Recovery liest keine echten
  User-Autosaves mehr (Suite: 1324 passed, 5 skipped, 0 failed —
  sowohl im frischen Clone als auch mit vorhandenen Userdaten).
- Repositories in `domain/repositories/` aufgeteilt (Shim in
  `repository.py` hält die alte Import-Schnittstelle stabil).

## 2026-05-07

### Hinzugefügt
- Sänger-Größe (`height`) für Choraufstellung-Optimierung.
- Dropdown-Sortierung in Sänger- und Termine-Tab.
- Verfügbarkeits-Button im Termine-Tab für schnellen Zugriff.
- Auto-Reload der Datenbank nach Backup-Wiederherstellung.
- Repertoire: Projekt-Verknüpfung und verbesserte Sortierung.

### Choraufstellung
- PDF-Export: Konfigurationsdialog (Schriftgröße, Seitenrand,
  Schwarz-Weiß), versetztes Raster, Querformat-Automatik.
- „Nähe (Singpartner)"-Menü für Affinitäts-Optimierung.
- Theme-aware Stimmgruppen-Farben (konfigurierbar in
  `config/voice_groups.json`).
- Arrangement-Regeln: S1S2A1A2, S1S2B1B2T1T2A1A2, VoiceGroupCohesion;
  Auto-Arrange by Height.
- Metadaten (Projekt, Termin, Termin-Typ) in der JSON-Datei.

## 2026-04-23

### Hinzugefügt
- **Besetzungen**: Neuer Tab zur Verwaltung von Sänger-Lineups
  (Checkbox-Auswahl, persistent in `besetzung`-Tabelle, „Als aktiv
  setzen" sitzungsübergreifend, Info-Bar-Anzeige).
- Context Toolbar + Kontextmenü (Bearbeiten, Umbenennen, Als aktiv,
  Löschen) für Besetzung-Tab.
- Dunkeltheme: QCheckBox-Styling.

### Behoben
- Tab-Indizes korrigiert (0=Projekte, 1=Sänger, 2=Besetzung,
  3=Termine, 4=Aufstellung, 5=Repertoire).

## 2026-04-21

### Hinzugefügt
- Neuer Tab „Aufstellung": zeigt alle JSON-Aufstellungsdateien
  (Dateiname, -größe, Projekt, Termin, Typ, Gespeichert-am).
- Automatischer Dateiname beim Speichern; Metadaten in JSON;
  Tab-Refresh bei Rückkehr aus Choraufstellung; Kontextmenü
  (Bearbeiten, Duplizieren).

### Behoben
- ChorAufstellung: „Optimiert aufstellen" funktioniert wieder;
  PDF-Export mit automatischer Querformat-Erkennung und versetztem
  Raster; Druck-Menü getrennt.

### Geändert
- DB-Schema: `address` ersetzt durch `street`, `postal_code`, `city`.

## Version 1.x (2026-04 bis 2026-06)

- Projektverwaltung und tab-basierte UI (Projekt-, Sänger-,
  Besetzung-, Termine-, Aufstellung-, Repertoire-Tabs).
- Projekt-Filter für Sänger und Termine.
- Verfügbarkeits-Dialog mit Radio-Buttons und Zusammenfassung nach
  Stimmgruppen.
- ChorAufstellung-Menüintegration („In Choraufstellung öffnen...").
- Selbstdarstellung (Marketing-Texte) im Menü.
- Konfigurationsdialog für Pfade, Backup, Logging, Theme.
- PyQt6-Portierung (alle Enums auf scoped Format).
- Undo/Redo mit Command Pattern; automatische Backups bei Start und
  vor dem Speichern.

## Version 0.x

- Ursprüngliche Version mit Sänger-Verwaltung.
