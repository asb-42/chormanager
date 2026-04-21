# UX/Usability Audit — ChorManager v0.1

**Audit-Datum:** 2026-04-21  
** Auditor:** Frontend Specialist (UX/Usability-Fokus)  
**Status:** Kritisches Review – Phase 0.1 (halbwegs funktional, aber UX nicht berücksichtigt)

---

## 📋 Executive Summary

ChorManager ist eine PyQt6-Desktop-App zur Chorverwaltung mit vier Tabs (Projekte, Sänger, Termine, Aufstellung). Kernfunktionen funktionieren grundsätzlich, jedoch wurden UX-Prinzipien (Accessibility, Feedback, Validation, Error Handling) quasi ignoriert. Dieses Audit identifiziert **kritische Bugs**, ** usability-Schwächen** und **technische Schulden** mit priorisierten Lösungsvorschlägen.

**Gesamtbewertung:**  
🔴 **P0-Kritisch:** 4 sofortige Fixes (Stability)  
🟠 **P1-Hoch:** 8 Usability-Verbesserungen (UX-Feedback, Validation)  
🟡 **P2-Mittel:** 5 Design/Performance (Modernisierung, Accessibility)  
🟢 **P3-Niedrig:** 6 Nice-to-have (Polish, Consistency)

---

## 🔴 P0 – Kritische Bugs (Showstopper)

### 1. `_delete_singer()` ist kaputt – **BLOCKIEREND**
**Datei:** `chormanager/ui/views/singers_tab.py` Zeilen 247–255

**Problem:**
```python
def _delete_singer(self):
    """Delete selected singer."""
    from PyQt6.QtWidgets import QMessageBox

    current_row = self.table.currentRow()
    # FEHLER: `reply` wird deklariert, aber nie zugewiesen (QMessageBox nicht aufgerufen)
    # FEHLER: `singer_id` ist nicht definiert
    if reply == QMessageBox.StandardButton.Yes:
        self.singer_repo.delete(singer_id)
        self._load_singers()
```

**Impact:** Nutzer können keine Sänger löschen → Dead Code, frustrierend, generates false expectations.

**Fix:**
```python
def _delete_singer(self):
    """Delete selected singer."""
    from PyQt6.QtWidgets import QMessageBox

    current_row = self.table.currentRow()
    if current_row < 0:
        QMessageBox.information(self, "Information", "Bitte wählen Sie einen Sänger aus")
        return

    item = self.table.item(current_row, 0)
    singer_id = item.data(Qt.ItemDataRole.UserRole)

    reply = QMessageBox.question(
        self, "Löschen",
        "Möchten Sie diesen Sänger wirklich löschen?\n\n"
        "Alle Verknüpfungen (Verfügbarkeiten) werden ebenfalls gelöscht.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    if reply == QMessageBox.StandardButton.Yes:
        self.singer_repo.delete(singer_id)
        self._load_singers()
```

---

### 2. `ConfigDialog._load_config()` ist leer – **Einstellungen werden nie geladen/gespeichert**
**Datei:** `chormanager/ui/dialogs.py` Zeilen 641–643

**Problem:** Dialog zeigt hartkodierte Defaults (`"./data"`), aber beim Öffnen werden aktuelle Config-Werte **nicht** geladen. Bei "OK" wird `get_config()` aufgerufen, die aber nirgends persisted wird → Benutzer-Änderungen sind wirkungslos.

**Impact:** Konfigurationsdialog ist komplett broken. Ändert man Datenpfad, Backup-Pfad etc., wird nichts gespeichert. Nutzer glauben, App sei kaputt.

**Fix:**
```python
def _load_config(self):
    """Load current configuration."""
    from ..config import load_app_config, get_data_dir
    
    config = load_app_config()
    data_dir = get_data_dir()
    
    self.data_dir_input.setText(str(data_dir))
    self.db_filename_input.setText(config.get("database", {}).get("filename", "chor.db"))
    self.backup_dir_input.setText(config.get("backup", {}).get("backup_dir", "./data/backups"))
    self.backup_count_input.setText(str(config.get("backup", {}).get("backup_count", 10)))
    self.log_level_input.setCurrentText(config.get("logging", {}).get("level", "INFO"))
    self.log_file_input.setText(config.get("logging", {}).get("file", "./data/logs/chormanager.log"))
    self.choraufstellung_path_input.setText(config.get("choraufstellung", {}).get("path", "/media/data/coding/choraufstellung"))

def accept(self):
    """Save config and close."""
    config = self.get_config()
    # Write to config/app.yaml (oder state.json, je nach Design)
    from ..config import save_app_config
    save_app_config(config)  # Muss in config.py implementiert werden
    super().accept()
```
**Zusätzlich:** `config.py` muss `save_app_config()` + persistence-Logik erhalten (YAML schreiben).

---

### 3. Exporte blockieren UI (PDF, LibreOffice, CSV)
**Dateien:** `main_window.py` Methoden `_export_csv`, `_export_pdf`, `_export_libreoffice`, `_export_data`

**Problem:** Alle Exporte laufen synchron im Main Thread. Bei großen Datenmengen (>1000 Sänger) oder langsamen LibreOffice-Conversion friert UI für 5–30 Sekunden.

**Code-Beispiel (`_export_pdf`, Zeilen 561–619):**
```python
def _export_pdf(self):
    from PyQt6.QtWidgets import QFileDialog
    from reportlab.lib.pagesizes import A4
    # ... 40 Zeilen ReportLab-Code, alles synchron ...
    doc.build(elements)  # Blocking
    self.statusBar().showMessage(f"Exportiert nach {filename}")
```

**Impact:** UI reagiert nicht, Nutzer denken App abgestürzt.

**Fix-Strategie:**  
Einfache Lösung: `QThread` + `Worker` + `QProgressDialog`  
```python
from PyQt6.QtCore import QThread, pyqtSignal

class ExportWorker(QThread):
    finished = pyqtSignal(str)   # filename bei Erfolg
    error = pyqtSignal(str)      # error message

    def __init__(self, export_type, singers, filename):
        super().__init__()
        self.export_type = export_type
        self.singers = singers
        self.filename = filename

    def run(self):
        try:
            if self.export_type == "pdf":
                self._export_pdf()
            # ...
            self.finished.emit(self.filename)
        except Exception as e:
            self.error.emit(str(e))

# In _export_pdf():
worker = ExportWorker("pdf", singers, filename)
# ProgressDialog mit Cancel-Button verknüpfen
progress = QProgressDialog("Exportiere...", "Abbrechen", 0, 0, self)
progress.setWindowModality(Qt.WindowModality.WindowModal)
worker.finished.connect(progress.accept)
worker.error.connect(lambda msg: QMessageBox.warning(self, "Fehler", msg))
worker.start()
```

---

### 4. Choraufstellung-Start blockiert & Debug-Dialog unsauber
**Datei:** `main_window.py` Zeilen 1019–1121

**Problem:** 
- `subprocess.run([sys.executable, main_py], ...)` ist synchron → blockiert bis Choraufstellung beendet wird
- Debug-Dialog wird **danach** angezeigt, also nur nach Prozess-Ende →Nutzer sieht erst Debug-Info, wenn App bereits geschlossen wurde
- Fehler: `"choraufstellung_path"` Variable wird im QMessageBox f-string nicht expandiert (Zeile 1031)

```python
# Zeile 1029-1032
QMessageBox.warning(
    self, "Fehler",
    f"Choraufstellung nicht gefunden unter:\n choraufstellung_path"  # Bug hier!
)
```

Fix: `f"... unter:\n{choraufstellung_path}"`

---

## 🟠 P1 – Usability & UX-Feedback

### 5. **Kein visuelles Feedback während Ladevorgängen**
**Betroffene Methoden:** Alle `_load_*` Methoden in Tabs.

**Beobachtung:**
- `SingersTab._load_singers()` (Zeilen 118–181): Holt alle Sänger aus DB, filtert client-side, setzt RowCount, füllt Tabelle, `resizeColumnsToContents()`. Bei 500+ Sängern spürbare Verzögerung, aber **kein Cursor-Change**, **kein Busy-Indikator**.
- `EventAvailabilityDialog._load_availability()` (Zeilen 348–410): Erzeugt 8 RadioButtons pro Sänger → bei 50 Sängern 400 Widgets. Kann >1s dauern, UI hängt.

**Lösung:**
1. `QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)` vor Load, `restoreOverrideCursor()` nach Load.
2. Für große Tabellen: `QProgressDialog` während des Ladens.
3. Optional: `QTimer.singleShot(0, ...)` + `QApplication.processEvents()` für UI-Refresh bereits während des Ladens.
4. **Besser:** Model/View-Architektur (`QTableView` + `QAbstractTableModel`) asynchron mit `QThreadPool` + `QRunnable`.

---

### 6. **Fehlende Validierung in Formularen**
**Dateien:** `SingerDialog`, `EventDialog`, `ProjectDialog`

**Beispiel `SingerDialog` (main_window.py, Zeilen 162–200):**
```python
def get_data(self):
    data = {}
    for name, widget in self.inputs.items():
        if isinstance(widget, QLineEdit):
            value = widget.text().strip()
            if not value:
                data[name] = None   # Kein Hinweis, dass Feld required ist!
            # ...
```

**Probleme:**
- Pflichtfeld `full_name` wird erst im `_add_singer()` geprüft (Zeile 192): `if not data.get("full_name"): return` → Dialog schließt stumm, keine Fehlermeldung.
- Andere required fields (aus `fields.yaml`) werden ignoriert.
- Keine visuelle Markierung (rote Umrandung, Tooltip).
- Nutzer weiß nicht, was falsch war.

**Lösung:**
```python
def accept(self):  # Statt OK-Button direkt mit self.accept verbinden
    data = self.get_data()
    errors = []
    
    required_fields = load_required_fields()  # Aus config
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} ist ein Pflichtfeld")
    
    if errors:
        QMessageBox.warning(self, "Validierungsfehler", "\n".join(errors))
        return  # Dialog bleibt offen
    
    super().accept()
```
**Zusätzlich:** `QLineEdit.setStyleSheet("border: 2px solid red;")` für fehlende Felder, `setToolTip()`.

---

### 7. **EventAvailabilityDialog – Radio-Buttons in Tabelle sind unbedienbar**
**Datei:** `dialogs.py` Zeilen 329–346, 348–386

**Layout:**
- Tabelle mit 6 Spalten: Kurzname, Stimmgruppe, dann 6 Radio-Button-Spalten für Status.
- Radio-Buttons sind tiny targets (ca. 16×16 px) in enger Zelle → schwer zu treffen.
- Keine Tastaturbedienung möglich (Focus auf Tabelle, aber Radio-Buttons darin nicht tab-fokusbar).
- Bei 50 Sängern: 300 Radio-Widgets → Performance + Usability Horror.

**Alternative UX:**
1. **Combo-Box pro Zeile** statt 6 Radio-Buttons: Ein Klick, Dropdown öffnet sich. Platzsparend, bedienbar.
2. **Links-Klick toggle** durch Status-Zyklus: Zelle klicken → wechselt `none → yes → no → ...`. Visuelles Feedback via Hintergrundfarbe/Icon.
3. **Zwei-Button-Layout** pro Zeile: "✓" und "✗" Buttons, daneben Dropdown für andere Status.

**Empfohlen:**
```python
# Spalten: Kurzname, Stimmgruppe, Status [ComboBox]
self.table.setColumnCount(3)
self.table.setHorizontalHeaderLabels(["Kurzname", "Stimmgruppe", "Status"])

for row, singer in enumerate(singers):
    # ...
    status_combo = QComboBox()
    status_combo.addItems(["✓ Ja", "✗ Nein", "○ Offen", "✓? Vorbehalt", "? Unklar", "~ Vielleicht"])
    # Setze aktuellen Status
    status_map = {"yes":0, "no":1, "none":2, "conditional":3, "unknown":4, "maybe":5}
    status_combo.setCurrentIndex(status_map.get(current_status, 2))
    self.table.setCellWidget(row, 2, status_combo)
```
**Vorteil:** 50 Widgets statt 300, einfacher zu klicken, Tastatur bedienbar.

---

### 8. **Keine Bestätigung nach Speichern/Löschen (außer Statusbar)**
**Beispiel:** Nach Sänger speichern (SingersTab Zeile 196): `self._load_singers()` → Tabelle refreshed, aber kein "Gespeichert"-Toast. Statusbar zeigt "Bereit" oder nächste Aktion überschreibt.

**Lösung:**
- Kurzes Toast-Notification (1–2s) über der Tabelle oder in Statusbar mit Timer-Reset.
- Oder: `QMessageBox.information` mit kurzem Text und Auto-Close nach 1.5s (nicht modal).

---

### 9. **Validation-Fehler werden nicht visuell kommuniziert**
**Singer Dialog:** Wenn Geburtsdatum ungültig → Alter berechnet sich nicht → Feld bleibt leer. Kein Hinweis.

**Solution Pattern:** Validierung in Echtzeit `textChanged.connect(self._validate)` oder beim Verlassen des Feldes `editingFinished`. Visuell: rot, Tooltip.

---

### 10. **Tabellen-Sortierung inkonsistent**
- **ProjectsTab:** Sorting enabled, SortIndicator auf Spalte 3 (Anzahl Termine) gesetzt (Zeile 126).
- **EventsTab:** `self.table.setSortingEnabled(False)` (Zeile 99) → Warum? Sortierung wird manuell per `sorted(events, key=lambda e: e.date or "")` gemacht (Zeile 141). Inconsistent.
- **SingersTab:** Sorting enabled (Zeile 109), aber keine initiale Sort-Spalte.

**Empfehlung:** Konsistent auf `setSortingEnabled(True)` setzen und Default-Spalte (z.B. Name) mit `sortByColumn()` festlegen. Zusätzlich: SortIndicator-Shown auf allen Tabs.

---

## 🟡 P2 – Design & Accessibility

### 11. **Hardcoded Stylesheets – kein zentrales Theme-System**
**Datei:** `main_window.py` Zeilen 689–816 (`_set_light_theme` / `_set_dark_theme`)

**Problem:** Farben als Magic Strings in Python-Code. Bei Design-Änderungen muss man 2x 100+ Zeilen CSS editing durchführen. Keine CSS-Variablen (Qt-Stylesheet-Properties), keine Trennung von Struktur/Farbe.

**Lösung:** Stylesheet in externe `.qss` Datei auslagern und mit Platzhaltern (Python f-string) versehen:
```python
# themes/light.qss
$primary-color: #4a90d9;
QLabel#projectInfoLabel {
    background-color: $primary-color;
}
```
Oder Qt Property verwenden:
```python
self.setProperty("themeColorPrimary", QColor("#4a90d9"))
```
**Vorteil:** Einmalige Design-Änderungen, einfache Wartung.

---

### 12. **Keyboard Navigation: Nicht existent**
**Tabelle-Navigation:**
- Enter-Taste löst keine Aktion aus (editieren).
- Ctrl+A (Select All) funktioniert nicht.
- Entf-Taste löscht nicht (obwohl Delete-Button existiert).
- F2 zum Editieren? Fehlt.
- Esc schließt Dialoge? Ja, aber nur weil default.

**Menüs:**
- Alle Menüs haben Mnemonics? Nein. Nur "&Datei", "&Bearbeiten" (Zeilen 264, 285) – aber Untermenüs ohne `&`.

**Lösung:**
```python
# In Tab-Initialisierung:
self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

# Shortcuts:
delete_shortcut = QShortcut(QKeySequence.Delete, self.table)
delete_shortcut.activated.connect(self._delete_singer)
edit_shortcut = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_E), self.table)
edit_shortcut.activated.connect(self._edit_singer)
# Oder F2
edit_shortcut2 = QShortcut(QKeySequence(Qt.Key_F2), self.table)
edit_shortcut2.activated.connect(self._edit_singer)
```

---

### 13. **Screen-Reader Support: 0%**
Keine `setAccessibleName()`, `setAccessibleDescription()` auf irgendwelchen Widgets. Keine Text-to-Speech Unterstützung.

---

### 14. **Dialog-Größen sind starr**
SingerDialog: `setMinimumWidth(400)` → bei vielen Feldern muss gescrollt werden (aber kein ScrollArea!). Besser: `QScrollArea` für Formulare mit >10 Feldern.

---

### 15. **Tab-Reihenfolge nicht definiert**
Standard-Reihenfolge basiert auf Hinzufüge-Reihenfolge. Wird bei dynamischen Layouts chaotisch. Explizit setzen via `setTabOrder(widget1, widget2)`.

---

## 🟢 P3 – Polish & Konsistenz

### 16. **Statusbar-Nachrichten überschreiben sich gegenseitig**
**Code:** Überall `self.statusBar().showMessage("...")` → bei schnellen Aktionen ist lesen unmöglich.

**Better:** Statusbar mit Timer, der nach 3s auf "Bereit" zurücksetzt ODER Queue von Messages.

---

### 17. **Project-Tab: "Aktiv"-Spalte zeigt ✓, aber keine Erklärung**
Tooltip fehlt. Nutzer wissen nicht, was "Aktiv" bedeutet (Projektfilter).  
**Fix:** `self.table.setItem(row, 2, QTableWidgetItem("✓")).setToolTip("Aktives Projekt (filtert Sänger/Termine)")`

---

### 18. **Event-Typ-Labels sind redundant**
EventsTab Zeilen 163–171: Mapping von codes zu Labels. Besser: aus Config (`events.yaml`) laden oder in DB als display_name speichern.

---

### 19. **Keine Icons**
Alle Buttons sind Text-only. icons aus Qt-Standard (`QStyle.StandardPixmap`) würden UI professionalisieren (Hinzufügen: `QStyle.StandardPixmap.SP_FileIcon`, Bearbeiten: `SP_FileDialogDetailedView`, Löschen: `SP_TrashIcon`).

---

### 20. **Export-Pfade: kein Default-Verzeichnis**
`QFileDialog.getSaveFileName(self, "Als CSV exportieren", "", "CSV Dateien (*.csv)")` → startet im home-Verzeichnis, nicht im Datenverzeichnis.  
**Fix:** Start-Verzeichnis aus `config.get_data_dir()` ableiten.

---

## 📊 Performance Issues

### 21. **`_load_singers()` filtert client-side, holt ALLE Sänger**
**SingersTab Zeilen 118–156:**
```python
singers = self.singer_repo.get_all()  # Holt alle Sänger aus DB
if self.project_filter:
    # Filtert client-side
    singers = [s for s in singers if ...]
if search_text or voice_filter:
    filtered = []
    for s in singers:
        # Python-loop über alle
```
**Impact:** Mit 1000 Sängern ~10–50ms pro Abfrage + Python-Filter → spürbar.

**Fix:** Filter in SQL (WHERE-Klauseln) via Repository-Methoden:
```python
singers = self.singer_repo.get_filtered(
    search_text=search_text,
    voice_group=voice_filter,
    project_id=self.project_filter.id if self.project_filter else None
)
```

---

### 22. **`resizeColumnsToContents()` in EVERY load**
Wird in jedem `_load_*` aufgerufen → teuer, besonders bei großen Tabellen.  
**Fix:** Einmal nach Initialisierung aufrufen + `horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)` für ausgewählte Spalten.

---

## 🐛 Weitere Bugs & Inkonsistenzen

### 23. **Event-Tab Sortierung deaktiviert, aber manuelle Sortierung fehlerhaft**
Zeile 99: `self.table.setSortingEnabled(False)` + manuelle Sortierung per `sorted(events, key=lambda e: e.date or "")`.  
Problem: Wenn Nutzer auf Spaltenkopf klickt, passiert nichts. Kein User-Expectation-Match.

---

### 24. **Context-Menu in SingersTab unvollständig**
Code Zeilen 235–245: Nur "Bearbeiten". ProjectsTab und EventsTab haben "Bearbeiten" + "Duplizieren".  
Inkonsistenz → Nutzer erwartet gleiches Verhalten.

---

### 25. **Singer-Alter wird als String gespeichert, nicht berechnet**
SingersTab Zeile 165–170: `is_adult` Spalte wird gefüllt mit `str(age)` (String), aber Model definiert `is_adult` als `Optional[int]` (models.py Zeile 28 `_is_adult`). Inkonsistente Datentypen.

---

### 26. **EventAvailabilityDialog: Zähler-Reset-Knopf fehlt**
Wie ConfigDialog Reset-Buttons hätte, um Zähler (Ja/Vorbehalt) zurückzusetzen? Nicht nötig, aber inkonsistent zu Config-Dialog.

---

### 27. **Projekt-Filter in SingersTab: Code-Doppelung**
Zeilen 127–136: Project-Filter-Logik wird in SingersTab dupliziert statt zentral in Repository.  
Wartbarkeit leidet.

---

### 28. **Choraufstellung-Tab: Button "Aus ChorManager laden" ruft redundante Methode auf**
Zeilen 77–96: Ruft `main_window._open_choraufstellung()` auf, die komplett eigenen Code hat. Doppelte Logik → Wartung 2x.

---

### 29. **EventListDialog (dialogs.py Zeilen 191–277): UI unvollständig**
Dialog "Verfügbarkeit verwalten" zeigt Liste nur als Text, keine Tabelle, keine Sortierung, kein Edit. Nutzer kann nur auswählen, dann OK – aber keine Änderung möglich!  
**Bug:** Dialog ist **read-only**?! Sollte zumindest Double-Click auf Zeile → AvailabilityDialog öffnen.

---

### 30. **SelbstdarstellungDialog: Keine Formatierung-Toolbar**
Nur plain `QTextEdit`. Nutzer erwartet zumindest basic formatting (bold, italic, lists) für Marketing-Texte.

---

## ✅ Positiv erwähnenswerte Best Practices

- **Undo/Redo** via `HistoryService` + `QUndoCommand` (wenn auch nicht vollständig im Code sichtbar)
- **Backup-Service** beim Start/Beenden
- **Projekt-Filter-Konzept**: Gute Idee, Umsetzung ausbaufähig
- **Dark/Light Theme** bereits vorhanden (wenn auch hardcoded)
- **Context Menus** in Projects/Events vorhanden
- **YAML-Konfiguration** für Felder/Stimmgruppen → erweiterbar
- **Export-Formate** vielfältig (CSV, PDF, LibreOffice, JSON)
- **Clean Architecture Anlag** (`domain/`, `ui/`, `data/`)

---

## 🛠️ Lösungsvorschläge & Refactoring-Roadmap

### Phase 1: Stabilität (P0) – 1 Tag
1. `SingersTab._delete_singer()` Bugfix
2. `ConfigDialog` load/save + `config.py` persistence
3. Exporte asynchron (minimal: `QThread` für PDF/CSV)
4. Choraufstellung-Start non-blocking + Path-Bugfix

### Phase 2: Usability-Feedback (P1) – 2–3 Tage
5. Lade-Indikatoren (Wait-Cursor + optional ProgressDialog)
6. Formular-Validierung visuell + Messages
7. EventAvailabilityDialog: Radio-Button-Tabelle → ComboBox-Pattern
8. Toast/Notification-System (kurze non-modal Messages)
9. Tastatur-Shortcuts (Delete, F2, Ctrl+E)

### Phase 3: Modernisierung (P2) – 1 Woche
10. Zentrales Theme-System (CSS-Dateien + Variablen)
11. Accessibility: AccessibleNames, Tab-Order, Screen-Reader-Tags
12. Model/View für große Tabellen (`QAbstractTableModel`)
13. Icons via Qt-Standard oder FontAwesome-SVG
14. Performance: SQLilter statt client-side, `resizeColumnsToContents` optimieren

### Phase 4: Polish (P3) – 1–2 Tage
15. Tooltips für Header/Buttons
16. Default-Pfade in Export-Dialogen
17. Kontextmenü in SingersTab um "Duplizieren" erweitern
18. SingerDialog in Sections/Tabs gruppieren oder ScrollArea
19. EventListDialog editierbar machen
20. Statusbar Message-Queue

---

## 📋 Priorisierte Task-Liste für Entwicklung

```
[ ] P0-Bug1: SingersTab._delete_singer korrigieren
[ ] P0-Bug2: ConfigDialog.load/save implementieren
[ ] P0-Bug3: Exporte in QThread auslagern + ProgressDialog
[ ] P0-Bug4: Choraufstellung-Pfad-Bugfix + non-blocking start
[ ] P1-Task1: Wait-Cursor beim Laden aller Tabs
[ ] P1-Task2: Formular-Validierung mit visueller Rückmeldung
[ ] P1-Task3: EventAvailabilityDialog Radio-Buttons durch ComboBox ersetzen
[ ] P1-Task4: Toast/Notification-System (z.B. Statusbar mit Auto-Reset)
[ ] P1-Task5: Tastatur-Shortcuts (Del, F2, Ctrl+E)
[ ] P2-Task1: Externe Stylesheets (themes/light.qss, dark.qss)
[ ] P2-Task2: Accessibility: setAccessibleName auf allen interaktiven Widgets
[ ] P2-Task3: Repository-Filter-Methoden für SingersTab
[ ] P3-Task1: Icons für Buttons
[ ] P3-Task2: Export-Dialoge starten in get_data_dir()
```

---

## 🔍 Code-Qualitäts-Metriken (Quick Scan)

| Metrik | Status | Note |
|--------|--------|------|
| Type Hints | Teilweise | Fehlt in UI-Code oft |
| Docstrings | Gut | Dialoge haben Docstrings, Views weniger |
| Error Handling | Schlecht | Viele `except: pass` oder keine try/except |
| Magic Numbers | Viele | Zeilenhöhen, Spaltenbreiten hardcoded |
| Duplicate Code | Hoch | `_load_*` Muster ähnlich, aber nicht DRY |
| Global State | Mittel | `config` global, `db` wird durchgereicht |
| Testabdeckung | Unbekannt | `tests/gui/` existiert, aber Ausführung nicht geprüft |

---

## 📚 Empfohlene Ressourcen

- **Qt6 Accessibility:** https://doc.qt.io/qt-6/accessibility-qt6-index.html
- **PyQt6 Threading:** https://www.pythonguis.com/tutorials/multithreading-pyqt6/
- **Model/View Programming:** https://doc.qt.io/qt-6/model-view-programming.html
- **Qt Stylesheets Reference:** https://doc.qt.io/qt-6/stylesheet-reference.html

---

**Audit abgeschlossen.**  
Nächster Schritt: P0-Bugfixes priorisieren, dann UX-Feedback-System aufbauen.
