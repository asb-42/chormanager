# Bekannte UX-Probleme

Diese Datei dokumentiert UX-Probleme, die entweder nicht behoben werden konnten oder
noch nicht implementiert wurden.

### 1. Aktives Projekt kann nicht gesetzt werden
**Status**: "Als aktives Projekt setzen" fehlt in Context-Toolbar und Rechtsklick-Menü
**Problem**: 
- `set_last_active_project_id()` wird nicht in `_on_project_changed()` aufgerufen
- Context-Toolbar wird nicht mit `current_project` aktualisiert nach Restore
- Rechtsklick-Menü kann nicht erweitert werden (Code-Logik fehlt)
**Aufwand**: Mittel - `set_last_active_project_id()` in `_on_project_changed()` hinzufügen

### 2. Tabellenzellen zu eng
**Status**: 12px Padding in CSS, aber Zellen wirken gedrängt
**Problem**: CSS `QTableWidget::item { padding }` wirkt nicht korrekt
**Aufwand**: Hoch - requires deep CSS debugging
**Workaround**: Reduziert auf 6px in `QTableWidget::item`

### 1. Tabellenzellen-Padding
**Status**: Bereits 12px Padding in CSS
**Problem**: Text wird trotzdem abgeschnitten
**Grund**: CSS `QTableWidget::item { padding }` wird nicht korrekt angewendet
**Aufwand**: Hoch - requires deep CSS debugging

### 2. Context Toolbar Icons
**Status**: Nur Text, keine Icons
**Problem**: QAction Icons werden nicht angezeigt
**Grund**: PyQt6 Toolbar mit ToolButtonTextBesideIcon Style
**Workaround**: Unicode-Zeichen im Text (➕, ✏️, etc.)

### 3. Sidebar Icons (leere Rechtecke)
**Status**: Emoji-Icons funktionieren nicht
**Workaround**: Verwende Buchstaben (P, S, B, T, A)
**Grund**: Material Icons Font lädt nicht inoffscreen mode

## Nicht implementiert

### 4. Besetzung: Aktives Projekt nicht vorbelegt
**Status**: Beim Klick auf "Neue Besetzung" erscheint "Bitte wählen Sie zuerst ein Projekt"
**Problem**: Das aktive Projekt wird nicht automatisch erkannt
**Aufwand**: Mittel - Logik muss angepasst werden

### 5. Besetzung: Aufstellung-Integration
**Status**: Singer pool kommt aus Verfügbarkeit
**Problem**: Sollte aus aktiver Besetzung kommen
**Aufwand**: Hoch - requires API-Änderungen

### 6. Besetzung-Verfügbarkeit Filter
**Status**: Konnte nicht vollständig implementiert werden
**Problem**: 
- Active Besetzung wird sitzungsübergreifend gespeichert (config.py)
- Beim Öffnen von "Verfügbarkeit erfassen" kann `besetzung_tab` nicht zugegriffen werden
- Filter greift nicht - alle 67 Sänger werden angezeigt statt nur Besetzungs-Sänger
**Aufwand**: Unbekannt -Debug-Ausgabe erscheint nicht im Terminal

### 7. Aktualisieren-Button
**Status**: ✅ In Context-Toolbar bei Sänger, Termine, Besetzung

## Bereits behoben

- Infoleiste Dark Theme: word-wrap entfernt, size policy gesetzt
- Seitentitel Dark Theme: pageTitle CSS hinzugefügt
- Feste Breite Labels: QSizePolicy.Minimum gesetzt
- Aktualisieren-Dopplung: eine Instanz entfernt