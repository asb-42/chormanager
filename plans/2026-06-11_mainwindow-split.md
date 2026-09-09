# Plan: Split MainWindow God Module

**Date:** 2026-06-11
**Source:** `chormanager/choraufstellung/main.py` (1872 lines, lines 1056-1848 are `MainWindow`)
**Target:** `main.py` ≤ 500 lines after all extractions

---

## 1. Current Architecture Analysis

### Structure of main.py (1872 lines)

| Section | Lines | Class / Scope | Notes |
|---------|-------|---------------|-------|
| Imports + Fallbacks | 1-57 | module-level | 3 import blocks: stdlib, PyQt6, app modules |
| DraggableTableWidget | 59-81 | class | Drag source for singer table — **duplicate** of `ui/pool_widget.py` (line 444) |
| SingerTile | 83-206 | class | Grid tile widget — **duplicate** of `ui/grid_widget.py` (line 63) |
| MoveSingerCommand | 208-228 | class (QUndoCommand) | **Duplicate** of `core/commands.py` (line 36) |
| SwapSingersCommand | 229-246 | class (QUndoCommand) | **Duplicate** of `core/commands.py` (line 63) |
| MoveGroupCommand | 248-274 | class (QUndoCommand) | **Duplicate** of `core/commands.py` (line 102) |
| FormationGrid | 276-775 | class (QWidget) | **Duplicate** of `ui/grid_widget.py` (line 20) |
| SingerPool | 777-932 | class (QWidget) | **Duplicate** of `ui/pool_widget.py` (line 20) |
| AddSingerDialog | 934-962 | class (QDialog) | Dialog — can extract to `ui/dialogs.py` |
| AffinityDialog | 964-1015 | class (QDialog) | Dialog — can extract to `ui/dialogs.py` |
| VoicingConfigDialog | 1017-1054 | class (QDialog) | Dialog — can extract to `ui/dialogs.py` |
| MainWindow.__init__ | 1056-1105 | constructor | ~50 lines of state + wiring |
| setup_ui() | 1107-1151 | method | ~45 inline layout — **extract to builder** |
| menu() | 1153-1232 | method | ~80 lines — **extract to builder** |
| add_to_grid / place_all / update_grid_count | 1234-1256 | 3 methods | Singer grid management |
| _check_grid_capacity / _show_resize / _reset_excess | 1258-1309 | 3 methods | Grid resize logic |
| upd_grid / on_raster_mode_changed | 1311-1333 | 2 methods | Grid dimension changes |
| undo/redo/swap_action | 1335-1350 | 5 methods | Undo/redo wiring |
| reset_formation / apply_all_affinity | 1352-1390 | 2 methods | Formation operations |
| new_f / open_f / _open_file | 1392-1428 | 3 methods | File I/O — **extract to service** |
| save_f / save_as_f / _save_file | 1430-1504 | 3 methods | File I/O — **extract to service** |
| generate_filename | 1506-1518 | 1 method | File naming — **extract to service** |
| _autosave_check | 1520-1541 | 1 method | Autosave — **extract to service** |
| _check_recovery | 1543-1564 | 1 method | Recovery — **extract to service** |
| export_pdf / _on_pdf_done/error | 1565-1642 | 3 methods | PDF export — partially extracted (workers exist) |
| run_optimizer / _on_opt_done/error | 1644-1667 | 3 methods | Optimizer — partially extracted (workers exist) |
| show_cfg / _apply_theme | 1669-1719 | 2 methods | Theme + config — **extract theme** |
| add_singer_via_menu / edit_singer / affinity / removed | 1721-1741 | 4 methods | Singer CRUD |
| do_quick_search / upd_leg | 1743-1768 | 2 methods | Search + legend |
| show_about / closeEvent | 1770-1784 | 2 methods | Misc |
| _load_from_chormanager | 1786-1820 | 1 method | ChorManager integration — **extract to service** |
| _load_formation_data | 1822-1848 | 1 method | Internal loader — **extract to service** |
| main() | 1850-1872 | function | Entry point |

### Key Findings

1. **5 classes in main.py are duplicates** of already-extracted modules in `ui/` and `core/`:
   - `DraggableTableWidget` → `ui/pool_widget.py` (line 444)
   - `SingerTile` → `ui/grid_widget.py` (line 63)
   - `FormationGrid` → `ui/grid_widget.py` (with different undo mechanism)
   - `SingerPool` → `ui/pool_widget.py`
   - All 3 `QUndoCommand` subclasses → `core/commands.py`

2. **The `ui/` versions are not stubs** — they are full implementations. However they use
   `core/commands.py` (`UndoCommand` + `UndoStack` — pure Python) instead of PyQt6's `QUndoCommand`/`QUndoStack`.
   This is the main API gap preventing a drop-in replacement.

3. **No tests exist** for the duplicate classes in main.py — only `tests/gui/` tests exist for
   the `ui/grid_widget.py` version, and they import via `__init__.py` which also exports the `ui/` version.

---

## 2. Migration Strategy: Two-Phase Approach

### Philosophy

Rather than creating yet-another-new-file, we **remove duplicates** and **wire to existing files**.
This reduces total lines-of-code and eliminates the bug-prone "two implementations" problem.

### Phase I: Extract isolated MainWindow methods into new service/builder modules

Low-risk extractions that don't change how FormationGrid / SingerPool / commands work:

| Target file | Content | Lines saved |
|-------------|---------|-------------|
| `ui/dialogs.py` | AddSingerDialog, AffinityDialog, VoicingConfigDialog | ~120 |
| `ui/menu_builder.py` | `MainWindow.menu()` logic | ~80 |
| `services/formation_file_service.py` | `new_f, open_f, _open_file, save_f, save_as_f, _save_file, generate_filename, _autosave_check, _check_recovery, export_pdf, _on_pdf_export_done/error, run_optimizer, _on_optimizer_done/error` | ~180 |
| `ui/theme_manager.py` | `_apply_theme, upd_leg, clear_color_cache` usage | ~60 |
| `services/formation_loader.py` | `_load_from_chormanager, _load_formation_data` | ~70 |

**Total Phase I reduction: ~510 lines → main.py ≈ 1362 lines**

### Phase II: Remove duplicate classes, wire main.py to existing ui/ modules

Higher risk — requires API compatibility between main.py usage and ui/ module APIs:

| Change | Details | Lines saved |
|--------|---------|-------------|
| Remove `DraggableTableWidget` | Import from `ui/pool_widget` | ~20 |
| Remove `SingerTile` | Import from `ui/grid_widget` | ~125 |
| Remove undo `QUndoCommand` classes | Import from `core/commands` | ~65 |
| Remove `FormationGrid` | Import from `ui/grid_widget` + adapt undo | ~500 |
| Remove `SingerPool` | Import from `ui/pool_widget` | ~155 |

**Total Phase II reduction: ~865 lines → main.py ≈ 497 lines** (≤500 target met)

---

## 3. Detailed Migration — Phase I (Low Risk)

### I-A: Extract `ui/dialogs.py`

**What:** Move 3 dialog classes from main.py out of MainWindow scope.

| Class | main.py lines | Dependencies |
|-------|---------------|--------------|
| `AddSingerDialog` | 934-962 | VoiceGroup enum, Singer model |
| `AffinityDialog` | 964-1015 | Singer model, QCompleter |
| `VoicingConfigDialog` | 1017-1054 | `load_voice_groups_config()` from config |

**Pattern:**
```python
# ui/dialogs.py
class AddSingerDialog(QDialog):
    """..."""  # exactly as in main.py
class AffinityDialog(QDialog):
    """..."""
class VoicingConfigDialog(QDialog):
    """..."""
```

**Changes to main.py:**
```python
# Remove class definitions (lines 934-1054)
# Add import:
from ui.dialogs import AddSingerDialog, AffinityDialog, VoicingConfigDialog
```

**Risk:** None — pure extract + import.

---

### I-B: Extract `ui/menu_builder.py` (or reuse existing)

**What:** Extract `MainWindow.menu()` into a builder function.

The existing `ui/menu_builder.py` (7622 bytes at `chormanager/ui/menu_builder.py`) may already have
a version of this. Check first — if so, adapt it; if not, create it.

```python
# ui/menu_builder.py
def build_main_menu(main_window, formation_grid, pool, swap_action, undo_action, redo_action):
    """Build the complete menu bar for MainWindow."""
    m = main_window.menuBar()
    # ... all menu items ...
```

**Changes to main.py:**
```python
# Replace ~80 lines with:
from ui.menu_builder import build_main_menu
# In setup_ui() or __init__:
build_main_menu(self, self.grid, self.pool, self.swap_action, self.undo_action, self.redo_action)
```

**Risk:** Low — pure extraction of menu creation.

---

### I-C: Extract `services/formation_file_service.py`

**What:** Extract all file I/O, autosave, PDF export, and optimizer methods.

These methods access `self.storage`, `self.pdf`, `self.grid`, `self.singers`, `self.file`,
and `self.is_modified`. Need a service class that receives MainWindow as a parent reference.

```python
# services/formation_file_service.py
class FormationFileService:
    def __init__(self, main_window):
        self.mw = main_window
        self.storage = main_window.storage
        self.pdf = main_window.pdf

    def new_file(self):
        mw = self.mw
        if mw.is_modified:
            # ... check save dialog ...
        mw.grid.singers = []
        mw.grid.refresh_grid()
        mw.singers = []
        mw.file = None
        mw.is_modified = False
        mw.update_grid_count()

    def open_file(self, filepath=None):
        # ...
    # etc for all 13 methods
```

**Changes to main.py:**
```python
# Remove ~180 lines of methods
# In __init__, add:
self.file_service = FormationFileService(self)
# Replace method calls:
#   self.new_f()  →  self.file_service.new_file()
#   self.save_f() →  self.file_service.save_file()
# etc.
```

**Risk:** Low-Medium — each method call must be updated in menus and signal handlers.

---

### I-D: Extract `ui/theme_manager.py`

**What:** Extract theme application and legend building.

```python
# ui/theme_manager.py
def apply_theme(main_window, theme):
    """Load QSS file or fallback for the given theme."""
    # ... current _apply_theme logic ...

def build_legend(parent_layout, voice_groups):
    """Build the voice group color legend."""
    # ... current upd_leg logic ...
```

**Changes to main.py:**
```python
# Remove lines 1674-1768 of _apply_theme and upd_leg
from ui.theme_manager import apply_theme, build_legend

# In __init__:
apply_theme(self, current_theme)
# ... 
build_legend(self.llay, self.cfg)
```

**Risk:** Low.

---

### I-E: Extract `services/formation_loader.py`

**What:** Extract ChorManager data loading and recovery.

```python
# services/formation_loader.py
class FormationLoader:
    def __init__(self, main_window):
        self.mw = main_window

    def load_from_chormanager(self):
        # ... current _load_from_chormanager logic ...

    def load_formation_data(self, data):
        # ... current _load_formation_data logic ...

    def check_recovery(self):
        # ... current _check_recovery logic ...
```

**Changes to main.py:**
```python
self.loader = FormationLoader(self)
# In __init__:
if self.chormanager_mode:
    self.loader.load_from_chormanager()
else:
    self.loader.check_recovery()
```

**Risk:** Low.

---

## 4. Detailed Migration — Phase II (Higher Risk)

### II-A: Standardize undo mechanism

**Problem:** `main.py` uses `QUndoCommand`/`QUndoStack` (PyQt6). `ui/grid_widget.py` + `core/commands.py`
use pure-Python `UndoCommand`/`UndoStack`. These are incompatible.

**Solution Option A (Recommended):** Make `ui/grid_widget.py` accept an optional `QUndoStack` while
keeping `core/commands.py` for headless use.

```python
# ui/grid_widget.py changes:
class FormationGrid(QWidget):
    def __init__(self, rows=4, cols=5, parent=None):
        # ...
        self.undo_stack = QUndoStack(self)  # default for Qt use
        # ... also keep set_undo_stack for compatibility
```

This way `main.py` can instantiate `FormationGrid` normally and get `QUndoStack` support.
The `core/commands.py` path remains available for headless testing.

**Solution Option B:** Switch `main.py` to use `core/commands.py`'s UndoStack. This requires
changing all undo/redo calls (canUndo → can_undo, etc.) and removing QUndoStack dependency
from main.py. Feasible but more invasive.

**Recommendation:** Option A — it's backward-compatible and requires minimal changes.

---

### II-B: Remove duplicate `DraggableTableWidget`

**What:** `main.py` line 59-81 has its own `DraggableTableWidget` that is identical in purpose
to `ui/pool_widget.py` line 444's `DraggableTableWidget`.

**Changes:**
1. Remove `DraggableTableWidget` class from main.py (lines 59-81)
2. In `main.py:SingerPool`, change: `self.table = DraggableTableWidget()` to import from `ui.pool_widget`
   — but this whole class will be removed in II-D anyway.

So this is a sub-step of II-D.

---

### II-C: Remove duplicate `SingerTile`

**What:** `main.py` lines 83-206 has its own `SingerTile` class that is very similar to
`ui/grid_widget.py` lines 63-208's `SingerTile`.

**Changes:**
1. Remove `SingerTile` class from main.py (lines 83-206)
2. Update `main.py:FormationGrid` to import from `ui.grid_widget` — but this whole class will
   be removed in II-E anyway.

So this is a sub-step of II-E.

---

### II-D: Migrate `SingerPool` → use `ui/pool_widget.py`

**What:** Replace main.py's local `SingerPool` (lines 777-932) with `ui/pool_widget.py`'s version.

**API differences to resolve:**

| main.py SingerPool | ui/pool_widget.py SingerPool |
|--------------------|------------------------------|
| `place_all_requested = pyqtSignal()` | **Missing** — needs to be added |
| `update_singers(singers, placed_ids)` | `update_singers(singers, placed_ids)` — same signature ✅ |
| `update_placed_singers(placed_ids)` | **Missing** — needs to be added |
| `add_singer(s)` | Has `_on_singer_list_changed` instead |
| `add_dialog(singer=None)` | `add_dialog(parent, singer=None)` — different signature ❌ |
| `set_affinity(singer)` | **Missing** — needs to be added |
| `remove_sel()` | Has `remove_selected_singer()` — same purpose, different name |
| Does NOT emit `singer_added` | Emits `singer_added` ✅ |
| Does NOT emit `singer_edit_requested` | Emits `singer_edit_requested` ✅ |

**Work:**
1. Add `place_all_requested` signal to `ui/pool_widget.py:SingerPool`
2. Add `update_placed_singers()` method
3. Add `set_affinity()` method
4. Add `add_dialog()` without `parent` param (or make `parent` optional)
5. Ensure signals match: `singer_selected`, `singer_added`, `singer_edit_requested`, `place_all_requested`

---

### II-E: Migrate `FormationGrid` → use `ui/grid_widget.py`

**What:** Replace main.py's local `FormationGrid` (lines 276-775) with `ui/grid_widget.py`'s version.

**API differences to resolve:**

| main.py FormationGrid | ui/grid_widget.py FormationGrid |
|-----------------------|---------------------------------|
| `undo_stack = QUndoStack(self)` | `undo_stack = None` (injected) |
| Commands: `MoveSingerCommand(QUndoCommand)` | Commands: `MoveSingerCommand(UndoCommand)` |
| `show_grid_context_menu(pos)` | → `contextMenuEvent` (reuse) |
| `set_dimensions(r, c)` | → `set_grid_size(r, c)` |
| `set_staggered(v)` | ✅ same name |
| `update_selection_visuals()` | ✅ same name |
| `highlight_singer(singer, parent_window)` | ✅ same name |
| `_pulse_step(tile, parent)` | ✅ same |
| `_restore_tile_style(tile)` | ✅ same |
| `clear_search_highlight()` | ✅ same name |
| `mousePressEvent` | ✅ same |
| `mouseMoveEvent` | ✅ same |
| `mouseReleaseEvent` | ✅ same |
| `swap_selected_singers()` | ✅ same name |
| `apply_affinity_proximity(singer)` | ✅ same name |
| `refresh_grid()` | ✅ same name |
| `place_singer(singer)` | ✅ same name |
| `place_singer_at(singer, r, c)` | ✅ same name |
| `is_occupied(r, c)` | ✅ same name |
| `get_singer_at(r, c)` | ✅ same name |
| `on_tile_removed(tile)` | ✅ same name |
| `on_tile_edit_requested(tile)` | ✅ same name |
| `on_tile_affinity_requested(tile)` | ✅ same name |
| `get_placed_singers()` | ⚠️ Returns different format |
| `get_placed_singer_ids()` | ✅ same name |
| `auto_arrange_by_height()` | ✅ same name + delegates to core/arrangement |
| `auto_arrange_men_outer()` | ✅ same name |
| `auto_arrange_satb()` | ✅ same name |
| `auto_arrange_sbta()` | ✅ same name |
| `auto_arrange_s1s2b2b1t2t1a2a1()` | ✅ same name |
| `auto_arrange_s1s2a1a2t1t2b1b2()` | ✅ same name |
| `auto_arrange_s1s2b1b2t1t2a1a2()` | ✅ same name |
| `optimize(primary, refinement)` | ✅ same name |
| `dragMoveEvent` | ✅ same |
| `dragEnterEvent` | ✅ same |
| `dropEvent` | ⚠️ same signature, verify implementation matches |
| `undo_stack.canUndoChanged` signal | ⚠️ Missing — needs `QUndoStack.canUndoChanged` signal |
| `undo_stack.canRedoChanged` signal | ⚠️ Missing |

**Key gaps:**
1. Need `QUndoStack` + `canUndoChanged`/`canRedoChanged` signals in `ui/grid_widget.py`
2. May need `set_undo_stack()` to accept `QUndoStack`

**Recommendation:** Make undo stack configurable in `ui/grid_widget.py`:
```python
class FormationGrid(QWidget):
    def __init__(self, rows=4, cols=5, parent=None):
        # ...
        self.undo_stack = QUndoStack(self)  # default for Qt
        # ...

    def set_undo_stack(self, stack):
        """Connect undo signals. Called when injecting external QUndoStack."""
        self.undo_stack = stack
        stack.canUndoChanged.connect(...)
        stack.canRedoChanged.connect(...)
```

This way both `main.py` and headless tests get what they expect.

---

## 5. Files to Create / Modify

### New files:
| File | Content | Est. lines |
|------|---------|------------|
| `chormanager/choraufstellung/ui/dialogs.py` | AddSingerDialog, AffinityDialog, VoicingConfigDialog | 120 |
| `chormanager/choraufstellung/ui/theme_manager.py` | apply_theme(), build_legend() | 80 |
| `chormanager/choraufstellung/services/formation_file_service.py` | FormationFileService class | 180 |
| `chormanager/choraufstellung/services/formation_loader.py` | FormationLoader class | 80 |

### Modified files:
| File | Changes | Est. delta |
|------|---------|------------|
| `main.py` | Remove duplicates, import from new files | −1375 lines |
| `ui/dialogs.py` | **(if exists)** Append 3 dialog classes | +120 lines |
| `ui/grid_widget.py` | Add QUndoStack default, signals, verify API parity | +30 lines |
| `ui/pool_widget.py` | Add place_all_requested signal, set_affinity(), add_dialog() | +50 lines |
| `ui/menu_builder.py` | **(if exists)** Adapt for MainWindow or create | +80 lines |

### Delated files:
(none — main.py remains as entry-point + slim MainWindow)

---

## 6. Risk Assessment

| Risk | Phase | Impact | Mitigation |
|------|-------|--------|------------|
| Missing method in ui/grid_widget.py | II-E | MainWindow doesn't compile | Verify full API parity before merging |
| QUndoStack signal wiring wrong | II-E | Undo/redo buttons don't update | Test manually + update `tests/gui/` |
| File service method signature mismatch | I-C | Caller in menu hander breaks | Extract methods one-by-one, compile test each |
| AffinityDialog different import pattern | I-A | ImportError | Keep exact class signature |
| Theme file path resolution | I-D | QSS not found | Use same os.path logic as current code |

---

## 7. Verification Plan

After each extraction (or batch of extractions):

```bash
# 1. Compile check
python3 -m py_compile chormanager/choraufstellung/main.py
python3 -m py_compile chormanager/choraufstellung/ui/dialogs.py
# ... etc for all new/modified files

# 2. Unit tests (headless)
python3 -m pytest tests/unit/ --ignore=tests/unit/test_event_list_dialog_dropdown.py -q

# 3. Integration tests
python3 -m pytest tests/integration/ -q

# 4. GUI tests (if Qt offscreen available)
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/gui/ -q

# 5. Manual smoke test
python3 -c "
import sys
sys.path.insert(0, 'chormanager/choraufstellung')
from main import MainWindow
# verify it instantiates without error
"
```

---

## 8. File Dependency Graph (Post-Split)

```
main.py (400-500 lines)
├── ui/dialogs.py         ← AddSingerDialog, AffinityDialog, VoicingConfigDialog
├── ui/pool_widget.py     ← SingerPool (with DraggableTableWidget inside)
├── ui/grid_widget.py     ← FormationGrid (with SingerTile inside)
│   └── core/commands.py  ← MoveSingerCommand, SwapSingersCommand, MoveGroupCommand
├── ui/theme_manager.py   ← apply_theme(), build_legend()
├── ui/menu_builder.py    ← build_main_menu()
├── services/formation_file_service.py  ← file/PDF I/O
├── services/formation_loader.py        ← DB/JSON loading
├── core/arrangement.py   ← arrangement algorithms
├── core/optimizer.py     ← optimization
├── workers.py            ← PDFExportWorker, OptimizerWorker, AutosaveWorker
└── storage.py            ← FormationStorage
```

No cycles. Clean dependency direction: `main.py → ui/ → core/` (leaf).
