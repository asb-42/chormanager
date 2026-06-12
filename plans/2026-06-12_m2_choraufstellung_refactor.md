# Plan: M-2 — Aufteilung `chormanager/choraufstellung/main.py`

> **Hinweis zum Pfad:** Diese Datei referenziert Python-Modul-Pfade
> (relativ zum **Package-Root** `chormanager/`, d.h. dem inneren
> `chormanager/`-Verzeichnis im Repo). Im Filesystem entspricht das
> dem absoluten Pfad `<repo-root>/chormanager/choraufstellung/main.py`.
> Mit dem Repo-Namen `chormanager` ergibt das ab dem App-Root
> `/media/data/coding/` den vollständigen Pfad
> `chormanager/chormanager/choraufstellung/main.py`. Die "doppelte"
> `chormanager/`-Komponente kommt vom Repo-Namen + Python-Package-Namen.

**Datum:** 2026-06-12
**Vorgänger:** M-1 (siehe `plans/2026-06-12_m1_main_window_refactor.md`, abgeschlossen)
**Code-Review:** `docs/reports/2026-06-12_code-review.md` Abschnitt M-2 + R-2
**Severity:** 🔴 Hoch (P0)
**Ziel-Datei (absolut):** `/media/data/coding/chormanager/chormanager/choraufstellung/main.py` (2 180 LOC, 12 Klassen).
**Ziel-Datei (relativ zum Package-Root):** `chormanager/choraufstellung/main.py` (so in diesem Plan-Dokument verwendet).
**Ziel-Datei (relativ zum Repo-Root):** `chormanager/chormanager/choraufstellung/main.py` (vom App-Root aus gesehen).
**Subshell-Status:** Subapp wird per `subprocess.run` aus
[`chormanager.ui.choraufstellung_launcher`](chormanager/ui/choraufstellung_launcher.py) gestartet — eigenständiger Prozess, **nicht** durch `chormanager.ui.main_window` abgedeckt.

## 🎯 Ziel

`chormanager/choraufstellung/main.py` (2 181 LOC, **12 Klassen in einer Datei**)
in mehrere Module aufteilen, sodass:
- jede Verantwortlichkeit in einer eigenen Datei lebt,
- jede Klasse in einem eigenen Modul **unit-testbar** ist,
- `MainWindow` selbst nur noch Window-Lifecycle + Menü/Toolbar-Wiring enthält
  (vergleichbar mit M-1 Schritt 1–8 der Hauptapp),
- Auto-Save-Timer, Undo-Stack, Optimizer-Bridge als klare Subsysteme sichtbar
  werden (R-2 aus dem Code-Review).

Erwartete Reduktion: `main.py` 2 181 → **~600 LOC** (Window-Lifecycle + Menü/Toolbar),
neue Module mit jeweils **< 500 LOC**.

## 📊 Bestandsaufnahme

### 12 Klassen in `chormanager/choraufstellung/main.py` (Z. 88–2 181)

| Z.       | Klasse                     | Verantwortlichkeit                 | LOC | Risiko |
|----------|----------------------------|------------------------------------|-----|--------|
| 88–104   | `Singer` (Fallback)        | Dataclass-Fallback in `try/except` | 17  | 🟢 Niedrig (wird nur importiert, wenn PyQt fehlt) |
| 99–104   | `OptimizerDialog` (Fallback) | PyQt-Fallback                     | 6   | 🟢 Niedrig |
| 103–104  | `GridEngine` (Stub)        | Engine-Fallback in `try/except`    | 2   | 🟢 Niedrig |
| 106–118  | `DraggableListWidget`      | Drag&Drop-Widget                   | 13  | 🟢 Niedrig |
| 120–142  | `DraggableTableWidget`     | Drag&Drop-Widget                   | 23  | 🟢 Niedrig |
| 144–267  | `SingerTile`               | UI-Kachel                          | 124 | 🟡 Mittel |
| 269–288  | `MoveSingerCommand`        | Undo-Command                       | 20  | 🟢 Niedrig |
| 290–307  | `SwapSingersCommand`       | Undo-Command                       | 18  | 🟢 Niedrig |
| 309–335  | `MoveGroupCommand`         | Undo-Command                       | 27  | 🟢 Niedrig |
| 337–1 032| `FormationGrid`            | Haupt-Grid-Widget (Drag/Drop/Auto-Arrange/Optimize) | 696 | 🔴 Hoch |
| 1 034–1 189| `SingerPool`             | Singer-Pool-Widget                 | 156 | 🟡 Mittel |
| 1 191–1 219| `AddSingerDialog`       | Dialog                             | 29  | 🟢 Niedrig |
| 1 222–1 272| `AffinityDialog`         | Dialog                             | 51  | 🟢 Niedrig |
| 1 274–1 311| `VoicingConfigDialog`    | Dialog                             | 38  | 🟢 Niedrig |
| 1 313–2 156| `MainWindow`             | **God-Class** (Setup, Menu, File-IO, Auto-Save, Optimizer, PDF-Export, Chormanager-Bridge, Theme, Close) | **844** | 🔴 Hoch |

Plus:
- Z. 1–86: PyQt5/PyQt6-Cross-Compat-`try/except` (86 LOC) — **separat zu extrahieren in `qt_compat.py`**
- Z. 2 158–2 181: `def main()` Entry-Point (24 LOC)

### Bestehende Tests

- `tests/unit/test_metadata_saving.py` — testet bereits `MainWindow` aus `chormanager.choraufstellung.main` (für Storage-Metadata-Contract)
- `tests/unit/test_dependencies_except_fallback.py` — testet `chormanager.choraufstellung.dependencies` (für `try/except`-Fix)
- `tests/integration/test_storage_regression.py:304–305` — **bereits übersprungen** mit Hinweis "main.py moved to choraufstellung module" → Refactor ist überfällig
- `tests/conftest.py:12–14` — `sys.path.insert(0, ...choraufstellung)` für Subshell-Import-Pattern

**Test-Suite-Status:** 518 passed, 4 skipped (nach M-1).

## 🏗️ Vorgeschlagene neue Modulstruktur

```
chormanager/choraufstellung/
├── __init__.py
├── __main__.py                  # Entry-Point (unverändert)
├── chormanager_db.py            # (unverändert)
├── config.py                    # (unverändert)
├── dependencies.py              # (unverändert)
├── optimizer.py                 # (unverändert)
├── optimizer_rules.py           # (unverändert)
├── optimizer_dialog.py          # (unverändert)
├── pdf_export.py                # (unverändert)
├── pdf_export_dialog.py         # (unverändert)
├── qt_compat.py                 # (unverändert) — aber in main.py entfällt der try/except
├── singer_model.py              # (unverändert)
├── storage.py                   # (unverändert)
├── ui_components.py             # (unverändert)
│
├── core/                        # (bestehend, bleibt)
│   ├── commands.py              # (unverändert)
│   ├── grid_engine.py           # (unverändert)
│   ├── optimizer.py             # (unverändert)
│   └── rules.py                 # (unverändert)
│
├── ui/                          # bestehend, bleibt
│   ├── grid_widget.py           # (unverändert)
│   ├── optimizer_dialog.py      # (unverändert)
│   ├── pool_widget.py           # (unverändert)
│   └── print_preview.py         # (unverändert)
│
├── widgets/                     # NEU: kleine UI-Widgets
│   ├── __init__.py
│   ├── draggable_list.py        # DraggableListWidget, DraggableTableWidget
│   ├── singer_tile.py           # SingerTile (~124 LOC)
│   ├── formation_grid.py        # FormationGrid (~696 LOC, siehe unten)
│   ├── singer_pool.py           # SingerPool (~156 LOC)
│   └── dialogs.py               # AddSingerDialog, AffinityDialog, VoicingConfigDialog (~118 LOC)
│
├── undo/                        # NEU: Undo-Stack als Subsystem
│   ├── __init__.py
│   ├── commands.py              # MoveSingerCommand, SwapSingersCommand, MoveGroupCommand (~65 LOC)
│   └── stack.py                 # NEU: dünner Wrapper um QUndoStack + Setup-Helfer
│
├── autosave.py                  # NEU: AutoSaveController (~120 LOC, _autosave_check + Timer)
│
├── file_io.py                   # NEU: File-IO-Logik (new_f, open_f, save_f, save_as_f, _save_file, generate_filename) (~120 LOC)
│
├── pdf_export_integration.py    # NEU: PDF-Export-Bridge (export_pdf-Methode) (~75 LOC)
│
├── chormanager_bridge.py        # NEU: _load_from_chormanager + _load_formation_data (~150 LOC)
│
├── recovery.py                  # NEU: _check_recovery (Auto-Save-Recovery beim Start) (~70 LOC)
│
├── theme.py                     # NEU: _apply_theme + style-Auswahl (~30 LOC, sehr klein)
│
├── main_window.py               # NEU: nur noch Window-Lifecycle + Menu/Toolbar-Wiring (~600 LOC, siehe Schritt 6)
│
└── main.py                      # VERBLEIBT: nur noch re-Export + `def main()` (~40 LOC)
```

### Wichtige Design-Entscheidungen

1. **Mixins NICHT** wie in M-1. Die Choraufstellung-Subapp ist **kleiner und einfacher** als die Hauptapp, und die 12 Klassen sind **bereits sauber abgegrenzt**. Statt Mixin-Pattern: **Composition über Aggregation**.
2. **Auto-Save als eigene Klasse** ([`autosave.py`](chormanager/choraufstellung/autosave.py)) statt Methode — testbar in Isolation, Timer sauber gekapselt.
3. **Undo als Subsystem** mit eigenem Modul-Pfad — `QUndoStack` wird im `MainWindow.__init__` instanziiert und an `commands.py` weitergegeben.
4. **PyQt5/PyQt6-Cross-Compat**: Der `try/except`-Block (Z. 1–86) wird in `qt_compat.py` ausgelagert (existiert bereits). `main.py` macht dann **nur noch** `from qt_compat import exec_qt` ohne Fallback.
5. **`from .module import …` Re-Exports** in `main.py` für **Backward-Compat** — die Subshell und Tests dürfen weiterhin `from chormanager.choraufstellung.main import MainWindow` machen.

## 🪜 Extraktions-Reihenfolge (kleinster Eingriff zuerst)

Jeder Schritt = 1 eigener Commit + Push, max. 200 LOC Δ pro Schritt, mit **TDD RED→GREEN→REFACTOR**.

### Schritt 1: PyQt-Cross-Compat in `qt_compat.py` konsolidieren (🟢 Niedrig)

**Ziel:** Z. 1–86 in `main.py` durch `from qt_compat import exec_qt` ersetzen. `qt_compat.py` existiert bereits, muss aber um die Klassen-Fallbacks (`Singer`, `OptimizerDialog`, `GridEngine`) erweitert werden.

**TDD:** 1 Test in `tests/unit/test_qt_compat_fallbacks.py` für jeden Fallback.

**Verifikation:** 518+1 passed, `py_compile` OK, `FormationGrid`-Smoke-Test (1 Test) grün.

**Risiko:** Niedrig. Fallbacks werden nur aktiv, wenn PyQt fehlt — und PyQt6 ist Pflicht (siehe `pyproject.toml`).

### Schritt 2: `DraggableListWidget` + `DraggableTableWidget` → [`widgets/draggable_list.py`](chormanager/choraufstellung/widgets/draggable_list.py) (🟢 Niedrig)

**Ziel:** Z. 106–142 in eigene Datei.

**TDD:** Smoke-Test: `QListWidget`/`QTableWidget` mit `startDrag()` Mock aufrufen, prüfen dass `QDrag` gestartet wird.

**Re-Export in `main.py`:** `from .widgets.draggable_list import DraggableListWidget, DraggableTableWidget  # noqa: F401`

**Verifikation:** 518+2 passed, `py_compile` OK.

### Schritt 3: Undo-Commands → [`undo/commands.py`](chormanager/choraufstellung/undo/commands.py) (🟢 Niedrig)

**Ziel:** Z. 269–335 in eigene Datei (alle 3 QUndoCommand-Klassen).

**TDD:** 3 Tests in `tests/unit/test_choraufstellung_undo_commands.py`:
- `MoveSingerCommand.undo/redo` setzt Sänger zurück
- `SwapSingersCommand.undo/redo` tauscht zurück
- `MoveGroupCommand.undo/redo` bewegt Gruppe zurück

**Re-Export in `main.py`:** `from .undo.commands import MoveSingerCommand, SwapSingersCommand, MoveGroupCommand  # noqa: F401`

**Verifikation:** 518+5 passed, `py_compile` OK.

### Schritt 4: 3 Dialoge → [`widgets/dialogs.py`](chormanager/choraufstellung/widgets/dialogs.py) (🟢 Niedrig)

**Ziel:** Z. 1 191–1 311 (`AddSingerDialog`, `AffinityDialog`, `VoicingConfigDialog`) in eigene Datei.

**TDD:** 3 Smoke-Tests, die zeigen, dass die Dialoge mit `parent=None` und Default-Args instantiierbar sind.

**Verifikation:** 518+8 passed, `py_compile` OK.

### Schritt 5: `SingerTile` + `SingerPool` → [`widgets/singer_tile.py`](chormanager/choraufstellung/widgets/singer_tile.py) + [`widgets/singer_pool.py`](chormanager/choraufstellung/widgets/singer_pool.py) (🟡 Mittel)

**Ziel:** Z. 144–267 (SingerTile) + Z. 1 034–1 189 (SingerPool) in eigene Dateien.

**TDD:**
- `test_singer_tile_init`: SingerTile mit Fake-Singer → hat korrekten Text + kann Signale senden
- `test_singer_pool_add_dialog_returns_singer`: AddSingerDialog-Mock, prüfen dass Pool richtig reagiert

**Re-Export in `main.py`:** beide Klassen re-exportieren.

**Verifikation:** 518+10 passed, `py_compile` OK.

### Schritt 6: `FormationGrid` → [`widgets/formation_grid.py`](chormanager/choraufstellung/widgets/formation_grid.py) (🔴 Hoch)

**Ziel:** Z. 337–1 032 in eigene Datei. Das ist der **größte Brocken** (696 LOC).

**TDD:**
- `test_formation_grid_init_with_default_4x5`: Smoke-Test
- `test_formation_grid_place_singer_at_unoccupied_cell`: Sänger platzieren, dann Zelle prüfen
- `test_formation_grid_swap_selected_singers`: 2 Sänger platzieren, swap, Reihenfolge prüfen
- `test_formation_grid_auto_arrange_satb_keeps_voice_groups_in_correct_rows`: Auto-Arrange mit 8 Sängern (2 SATB), prüfen dass Reihen stimmen
- `test_formation_grid_emit_singer_removed_from_grid`: Sänger platzieren, entfernen, Signal empfangen

**Re-Export in `main.py`:** `from .widgets.formation_grid import FormationGrid  # noqa: F401`

**Verifikation:** 518+15 passed, `py_compile` OK, **Smoke-Test manuell**: `FormationGrid(4,5)` zeigt Grid mit 20 leeren Zellen.

### Schritt 7: `AutoSave` als Klasse → [`autosave.py`](chormanager/choraufstellung/autosave.py) (🟡 Mittel)

**Ziel:** Die `_autosave_check`-Logik (Z. 1 770–1 810, ~40 LOC) in eine eigene `AutoSaveController`-Klasse extrahieren, plus die Timer-Logik aus `__init__` (Z. 1 341–1 343).

**Design:**
```python
class AutoSaveController:
    def __init__(self, parent_window, storage, interval_ms=120000):
        self._window = parent_window
        self._storage = storage
        self._timer = QTimer(parent_window)
        self._timer.timeout.connect(self._check)
        self._timer.start(interval_ms)
    def _check(self): ...   # ehemals _autosave_check
    def stop(self): self._timer.stop()
    def start(self, interval_ms=None): ...
```

**TDD:**
- `test_autosave_timer_fires_after_interval`: QTimer mit 100 ms, Signal mocken
- `test_autosave_check_writes_when_modified`: `is_modified=True`, prüfen dass `save_autosave` aufgerufen wird
- `test_autosave_check_skips_when_unmodified`: `is_modified=False`, prüfen dass `save_autosave` **nicht** aufgerufen wird
- `test_autosave_stop_prevents_further_writes`: stop() aufrufen, dann 200 ms warten, prüfen dass `save_autosave` nicht aufgerufen wird

**Im MainWindow:** `self.autosave = AutoSaveController(self, self.storage, 120000)` — der Aufruf der ursprünglichen `_autosave_check` (in `closeEvent`) wird zu `self.autosave._check()`.

**Verifikation:** 518+19 passed, `py_compile` OK.

### Schritt 8: File-IO-Logik → [`file_io.py`](chormanager/choraufstellung/file_io.py) (🟡 Mittel)

**Ziel:** `new_f`, `open_f`, `save_f`, `save_as_f`, `_save_file`, `generate_filename` (Z. 1 648–1 768, ~120 LOC) in eine eigene Klasse `FormationFileIO`.

**Design:**
```python
class FormationFileIO:
    def __init__(self, storage): self._storage = storage
    def new(self, parent, is_modified) -> bool: ...   # Prompt + Reset
    def open(self, parent) -> Optional[dict]: ...     # FileDialog + load
    def save(self, parent, grid) -> bool: ...        # save oder save_as fallback
    def save_as(self, parent, grid) -> bool: ...
    def _save_to_path(self, path, grid, metadata) -> bool: ...
    def generate_filename(self, event_date, event_name=None) -> str: ...
```

**TDD:**
- 6 Tests für jeden Pfad (mit `monkeypatch` auf `QFileDialog`)
- `test_save_to_atomic_path`: prüfen, dass Schreiben + `os.replace`-Pattern verwendet wird
- `test_open_with_invalid_json_shows_warning`: korruptes JSON → `QMessageBox.warning`

**Im MainWindow:** `self.file_io = FormationFileIO(self.storage)`; Menu-Actions rufen `self.file_io.save(...)` etc.

**Verifikation:** 518+25 passed, `py_compile` OK.

### Schritt 9: PDF-Export-Bridge → [`pdf_export_integration.py`](chormanager/choraufstellung/pdf_export_integration.py) (🟡 Mittel)

**Ziel:** `export_pdf` (Z. 1 812–1 878, ~66 LOC) in eine eigene Funktion/Klasse.

**TDD:**
- `test_export_pdf_writes_file`: `PDFExportDialog`-Mock, prüfen dass `pdf.export` aufgerufen wird
- `test_export_pdf_with_cancelled_dialog_is_noop`: Dialog gibt `None` zurück → keine Datei
- `test_export_pdf_error_shows_critical`: `pdf.export` raises → `QMessageBox.critical`

**Im MainWindow:** `self.pdf_exporter = PDFExportBridge(self.pdf, self.grid, self._loaded_metadata)`; Menu-Action ruft `self.pdf_exporter.export()`.

**Verifikation:** 518+28 passed, `py_compile` OK.

### Schritt 10: ChorManager-Bridge → [`chormanager_bridge.py`](chormanager/choraufstellung/chormanager_bridge.py) (🟡 Mittel)

**Ziel:** `_load_from_chormanager` (Z. 2 008–2 128) + `_load_formation_data` (Z. 2 130–2 156) in eine eigene `ChorManagerBridge`-Klasse.

**TDD:**
- `test_load_from_event_data_file_reads_json`: Temp-JSON mit `{"event": {...}, "singers": [...]}`, prüfen dass `MainWindow.singers` korrekt gefüllt ist
- `test_load_from_event_data_file_missing_keeps_state`: `CHOR_EVENT_DATA` zeigt auf nicht-existenten Pfad → keine Exception
- `test_load_formation_data_restores_grid`: data-Dict mit `rows=4, cols=5, singers=[...]`, prüfen dass Grid neu aufgebaut wird
- `test_chormanager_mode_triggers_bridge`: `chormanager_mode=True` in `__init__`, prüfen dass `_load_from_chormanager` aufgerufen wird

**Im MainWindow:** `self.cm_bridge = ChorManagerBridge(self)`; `chormanager_mode=True` ruft `self.cm_bridge.load_from_env()`.

**Verifikation:** 518+32 passed, `py_compile` OK.

### Schritt 11: Recovery-Logik → [`recovery.py`](chormanager/choraufstellung/recovery.py) (🟡 Mittel)

**Ziel:** `_check_recovery` (Z. 1 790–1 809, ~20 LOC) + Integration mit `FormationStorage.get_latest_autosave_path` in eigene `RecoveryController`-Klasse.

**TDD:**
- `test_check_recovery_offers_restore_when_autosave_exists`: `get_latest_autosave_path` gibt Pfad → `QMessageBox.question` aufgerufen
- `test_check_recovery_silent_when_no_autosave`: `None` zurück → kein Dialog
- `test_recovery_user_yes_restores_state`: User klickt Yes → `_load_formation_data` aufgerufen
- `test_recovery_user_no_skips_silently`: User klickt No → kein Restore

**Im MainWindow:** `self.recovery = RecoveryController(self.storage, self._load_formation_data, parent=self)`; `__init__` ruft `self.recovery.check()` statt `_check_recovery()`.

**Verifikation:** 518+36 passed, `py_compile` OK.

### Schritt 12: Theme → [`theme.py`](chormanager/choraufstellung/theme.py) (🟢 Niedrig)

**Ziel:** `_apply_theme` (Z. 1 894–1 933, ~40 LOC) in eigene `ThemeApplier`-Klasse oder Funktion.

**TDD:**
- `test_apply_light_theme_sets_stylesheet`: Prüfen, dass `setStyleSheet` mit Light-Stylesheet aufgerufen wird
- `test_apply_dark_theme_sets_stylesheet`: dito für Dark
- `test_apply_theme_persists_to_settings`: prüfen, dass `save_settings` aufgerufen wird

**Im MainWindow:** `self.theme_applier = ThemeApplier(self)`; `__init__` ruft `self.theme_applier.apply(current_theme)`.

**Verifikation:** 518+39 passed, `py_compile` OK.

### Schritt 13: `MainWindow` schlanker machen — Menu/Toolbar-Wiring (🟡 Mittel)

**Ziel:** Der `MainWindow` in `main.py` enthält jetzt nur noch:
- `__init__` (~30 LOC, ohne Auto-Save-Timer, ohne Engine-Setup)
- `setup_ui` (~50 LOC, Grid + Pool + Splitter)
- `menu` (~250 LOC, **bleibt hier** — Menu-Wiring ist zentral)
- `closeEvent` (~20 LOC)
- `update_grid_count` und andere kleine UI-Methoden (~50 LOC)

Insgesamt ~600 LOC. **Menu bleibt im MainWindow**, weil es das gesamte Wiring bündelt.

**TDD:**
- 1 Smoke-Test: `MainWindow` mit `chormanager_mode=False` startet, hat alle Attribute (grid, pool, menu, toolbar, statusbar)
- 1 Test: `closeEvent` mit `is_modified=True` zeigt `QMessageBox.question`

**Verifikation:** 518+41 passed, `py_compile` OK, manueller Smoke-Test: Subshell startet und lädt/leert Formation.

### Schritt 14: Finale `main.py` (🟢 Niedrig)

**Ziel:** `main.py` enthält nur noch:
- Alle Re-Exports für Backward-Compat (ca. 15 Zeilen)
- `def main()` Entry-Point (24 LOC, unverändert)

Insgesamt ~40 LOC.

**Re-Exports:**
```python
# Backward-compat: Tests und Subshell importieren weiterhin
# 'from chormanager.choraufstellung.main import MainWindow'.
from .main_window import MainWindow              # noqa: F401
from .widgets.formation_grid import FormationGrid  # noqa: F401
from .widgets.singer_tile import SingerTile        # noqa: F401
from .widgets.singer_pool import SingerPool        # noqa: F401
from .widgets.dialogs import (                     # noqa: F401
    AddSingerDialog, AffinityDialog, VoicingConfigDialog
)
from .undo.commands import (                       # noqa: F401
    MoveSingerCommand, SwapSingersCommand, MoveGroupCommand
)
from .widgets.draggable_list import (              # noqa: F401
    DraggableListWidget, DraggableTableWidget
)


def main():
    # ... unverändert
```

**Verifikation:** 518+41 passed, **Smoke-Test manuell**: Subshell via `python -m chormanager.choraufstellung` startet.

## ⚠️ Risiko-Bewertung

### Risiko 1: PyQt5/PyQt6-Cross-Compat bricht (Schritt 1)
- **Mitigation:** qt_compat existiert bereits und ist in `dependencies.py` etabliert. Schritt 1 erweitert es nur.
- **Fallback:** Schritt 1 wird **zuletzt** in `main.py` aktiv, also re-aktivierbar via Re-Export.

### Risiko 2: `QUndoStack`-Reihenfolge ändert sich (Schritt 3)
- **Mitigation:** `MoveSingerCommand` etc. sind reine Dataclass-Klassen; das `QUndoStack` lebt im `MainWindow` und reicht das `grid` per Konstruktor durch. Keine globale State-Änderung.

### Risiko 3: Auto-Save-Timer feuert zu früh / zu spät (Schritt 7)
- **Mitigation:** Tests verwenden `interval_ms=100` statt 120 000 ms. Behavior byte-für-byte identisch, nur Timer-Setup anders.

### Risiko 4: Tests für `chormanager.choraufstellung.main.MainWindow` müssen angepasst werden
- **Mitigation:** Schritt 14 hält alle Re-Exports. `test_metadata_saving.py:180, 241` läuft unverändert weiter.

### Risiko 5: Manuelle Subshell-Smoke-Tests sind nötig
- Da die Subshell per `subprocess.run` startet, ist automatisierte Test-Schicht **unzureichend**. Jeder Schritt 7–13 erfordert einen **manuellen Smoke-Test** (5 Min).

### Risiko 6: `chormanager_mode=True` Initialisierung ist fragil (Schritt 10)
- **Mitigation:** Schritt 10 ist byte-für-byte; die Logik liegt in `chormanager_bridge.py`, aber der Aufruf passiert weiterhin in `__init__`.

## ✅ Erfolgs-Kriterien

- `main.py` reduziert von **2 181 → ~40 LOC** (Re-Exports + `def main()`)
- Alle 12 Klassen in eigenen Modulen (jeweils < 700 LOC)
- Mindestens **+41 neue Unit-Tests** in `tests/unit/test_choraufstellung_*.py`
- 559+ passed, 4 skipped, 0 failed
- `python -m py_compile chormanager/choraufstellung/main.py` muss fehlerfrei durchlaufen
- `python -m chormanager.choraufstellung` (Subshell) startet manuell ohne Fehler
- Launcher aus Hauptapp (`_open_choraufstellung_file`) startet die Subshell unverändert

## 🚫 Was dieser Plan NICHT macht

- Keine Änderung an `chormanager.choraufstellung.core/*` (Optimizer-Logik bleibt)
- Keine Änderung an `chormanager.choraufstellung.ui/*` (bestehende UI-Module bleiben)
- Keine Migration `os.path` → `pathlib` (M-7 aus Code-Review, separater Plan)
- Keine Behebung der `except:`-Klauseln (M-4, separater Plan)
- Keine `QThread`/`QProcess`-Migration für `subprocess.run` (M-5, separater Plan)
- Keine `pyproject.toml`/`conftest.py`-Änderung (außer minimale Anpassungen wenn nötig)

## 📅 Reihenfolge der Commits

| Commit | Schritt | LOC-Δ | Neue Tests | Risiko |
|--------|---------|-------|------------|--------|
| M-2.1  | qt_compat erweitern | -86 | +1 | 🟢 |
| M-2.2  | Draggable-Widgets | -36 | +2 | 🟢 |
| M-2.3  | Undo-Commands | -65 | +3 | 🟢 |
| M-2.4  | 3 Dialoge | -118 | +3 | 🟢 |
| M-2.5  | SingerTile + SingerPool | -280 | +2 | 🟡 |
| M-2.6  | FormationGrid | -696 | +5 | 🔴 |
| M-2.7  | AutoSaveController | -80 | +4 | 🟡 |
| M-2.8  | FormationFileIO | -120 | +6 | 🟡 |
| M-2.9  | PDFExportBridge | -66 | +3 | 🟡 |
| M-2.10 | ChorManagerBridge | -150 | +4 | 🟡 |
| M-2.11 | RecoveryController | -50 | +4 | 🟡 |
| M-2.12 | ThemeApplier | -40 | +3 | 🟢 |
| M-2.13 | MainWindow schlanker | -300 | +1 | 🟡 |
| M-2.14 | main.py = nur Re-Exports + main() | -560 | 0 | 🟢 |
| **Σ**  | **14 Schritte** | **-2 141 LOC** | **+41 Tests** | |

Erwartete Endgröße: `main.py` 40 LOC + 12 neue Module (Ø 180 LOC).

## 🔗 Bezug zum Code-Review

- **M-2** (God-Class, 🔴 Hoch) — **vollständig adressiert**.
- **R-2** (Window + Undo + Optimizer-Bridge) — **vollständig adressiert**.
- **R-3** (`dialogs.py` 1 824 LOC) — **NICHT** in diesem Plan, separater M-3-Plan.
- **M-4** (`except:`-Klauseln) — **NICHT** in diesem Plan, separater Plan.

## 🚀 Nächste Schritte (nach User-Freigabe dieses Plans)

1. **Schritt 1** starten (TDD RED → GREEN → REFACTOR)
2. Pro Schritt: ein Commit mit detaillierter Message + Push
3. Nach Schritt 6 (`FormationGrid`): **Zwischen-Review** durch User
4. Nach Schritt 14: manueller Smoke-Test der Subshell + End-Review
