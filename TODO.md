# ChorManager - Offene Aufgaben

## Erledigt (Session 2026-04-16)

- [x] Projektverwaltung (ProjectsTab, Projekt-Filter, Projekt-Auswahl)
- [x] Events Tab (Tabellenansicht, Sortierung, Projekt-Filter, Verfügbarkeits-Anzeige)
- [x] Verfügbarkeits-Dialog (Radio-Buttons, Zusammenfassung nach Stimmgruppen)
- [x] Marketing-Menü: Selbstdarstellung
- [x] Konfigurationsdialog (Datenpfade, Backup, Logging, Theme, Choraufstellung)
- [x] Export-Modul (JSON/CSV Export)
- [x] DB-Zugriffsmodul für Choraufstellung (`chormanager_db.py`)
- [x] Choraufstellung-Menüintegration ("In Choraufstellung öffnen...")
- [x] Unit-Tests für Project, Event, Availability Repository + Export-Modul
- [x] README aktualisiert
- [x] Portabler Modus: Export/Import-Funktion (Extras-Menü), `portability.py` Modul
- [x] README: Portabler Modus dokumentiert

## Offene Aufgaben

### Hohe Priorität

- [ ] LSP-Type-Check-Fehler beheben (siehe README.md Warnungen)
- [ ] PyQt6-Kompatibilität für alle UI-Komponenten sicherstellen
- [ ] Logging进一步完善 (Konfiguration via GUI)

### Mittlere Priorität

- [ ] PDF-Export fertigstellen (reportlab-Integration prüfen)
- [ ] Weitere Unit-Tests für Domain-Layer
- [ ] Integrationstests für DB-Operationen
- [ ] UI-Tests mit pytest-qt

### Niedrige Priorität

- [ ] Dokumentation der Architektur ergänzen
- [ ] XDG-Standard für Konfigurationsdateien prüfen
- [ ] Automatisches Backup-Management via UI konfigurierbar machen
- [ ] Mehrsprachigkeit vorbereiten (i18n-Framework)

## Bekannte Probleme

1. **Type-Check-Warnungen**: LSP meldet mehrere Typ-Probleme in `models.py`, `repository.py`, `test_history.py`
2. **PyQt5/PyQt6-Mischung**: Choraufstellung verwendet PyQt5, ChorManager PyQt6
3. **Test-Coverage**: ~63 Tests vorhanden, Coverage sollte erhöht werden

## Integration mit Choraufstellung

Siehe `/media/data/coding/choraufstellung/INTEGRATION_TODO.md` für die Choraufstellung-Seite der Integration.