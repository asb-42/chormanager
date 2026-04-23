# Bekannte UX-Probleme

Diese Datei dokumentiert UX-Probleme, die entweder nicht behoben werden konnten oder
noch nicht implementiert wurden.

## Nicht behoben

### 1. Tabellenzellen-Padding
**Status**: Bereits 12px Padding in CSS
**Problem**: Text wird trotzdem abgeschnitten
**Grund**: CSS `QTableWidget::item { padding }` wird nicht korrekt angewendet
**Aufwand**: Hoch - requires deep CSS debugging

### 2. Sidebar Icons (leere Rechtecke)
**Status**: Emoji-Icons funktionieren nicht
**Workaround**: Verwende Buchstaben (P, S, B, T, A)
**Grund**: Material Icons Font lädt nicht inoffscreen mode

### 3. Context Toolbar Icons
**Status**: Nur Text, keine Icons
**Problem**: QAction Icons werden nicht angezeigt
**Grund**: PyQt6 Toolbar mit ToolButtonTextBesideIcon Style
**Workaround**: Unicode-Zeichen im Text (➕, ✏️, etc.)

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