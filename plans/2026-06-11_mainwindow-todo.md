# Fine-Grained TODO List: Split MainWindow God Module

**Source:** `chormanager/choraufstellung/main.py` (1872 lines)
**Target:** `main.py` ≤ 500 lines

---

## Phase I: Extract Isolated Functionality (Steps 1–7)

### Step 1 — Extract dialogs to `ui/dialogs.py`

**Diff:** `main.py` −120 lines, `ui/dialogs.py` +120 lines

- [ ] 1.1 Create `chormanager/choraufstellung/ui/dialogs.py` with:
  - [ ] 1.1a `class AddSingerDialog(QDialog)` — copy from main.py lines 934-962 exactly
  - [ ] 1.1b `class AffinityDialog(QDialog)` — copy from main.py lines 964-1015 exactly
  - [ ] 1.1c `class VoicingConfigDialog(QDialog)` — copy from main.py lines 1017-1054 exactly
- [ ] 1.2 Remove lines 934-1054 from main.py (the 3 dialog class definitions)
- [ ] 1.3 Add `from ui.dialogs import AddSingerDialog, AffinityDialog, VoicingConfigDialog` to main.py imports
- [ ] 1.4 **Verify:** `python3 -m py_compile chormanager/choraufstellung/main.py`
- [ ] 1.5 **Verify:** `python3 -m pytest tests/unit/ -q --ignore=tests/unit/test_event_list_dialog_dropdown.py`
- [ ] 1.6 **Verify:** `python3 -m pytest tests/integration/ -q`
- [ ] 1.7 **Commit:** `refactor: extract AddSingerDialog, AffinityDialog, VoicingConfigDialog to ui/dialogs.py`

---

### Step 2 — Extract theme management to `ui/theme_manager.py`

**Diff:** `main.py` −80 lines, `ui/theme_manager.py` +80 lines

- [ ] 2.1 Create `chormanager/choraufstellung/ui/theme_manager.py` with:
  - [ ] 2.1a `def apply_theme(widget, theme)` — copy from main.py lines 1674-1719
    - [ ] Pass `widget` (MainWindow) instead of `self`
    - [ ] Keep QSS file loading with inline fallback
    - [ ] Call `clear_color_cache()`, `widget.grid.refresh_grid()`, `widget.pool.update_singers()`
  - [ ] 2.1b `def build_legend(voice_groups, layout)` — copy from main.py lines 1753-1768
    - [ ] Accept `voice_groups` and `layout` as explicit params
- [ ] 2.2 Remove main.py lines 1674-1768 (`_apply_theme`, `upd_leg`, the QSS hardcoded strings)
- [ ] 2.3 Add import `from ui.theme_manager import apply_theme, build_legend`
- [ ] 2.4 Replace `self._apply_theme(current_theme)` in `__init__` with `apply_theme(self, current_theme)`
- [ ] 2.5 Replace `self.upd_leg()` in `setup_ui()` with `build_legend(self.cfg, self.llay)`
- [ ] 2.6 **Verify:** compile + unit tests + integration tests
- [ ] 2.7 **Commit:** `refactor: extract theme management and legend to ui/theme_manager.py`

---

### Step 3 — Extract menu building to `ui/menu_builder.py`

**Diff:** `main.py` −80 lines, `ui/menu_builder.py` +80 lines

- [ ] 3.1 Check if `chormanager/ui/menu_builder.py` already has MainWindow-compatible menu builder
  - [ ] If yes: adapt it (add missing actions if needed)
  - [ ] If no: create `chormanager/choraufstellung/ui/menu_builder.py` with:
    - [ ] `def build_main_menu(main_window, grid, pool, swap_action, undo_action, redo_action)` 
    - [ ] Copy menu logic from main.py lines 1153-1232
    - [ ] Return the action references (swap_action, undo_action, redo_action) or set them as attrs
- [ ] 3.2 Remove lines 1153-1232 from main.py (`menu()` method)
- [ ] 3.3 Add `from ui.menu_builder import build_main_menu` to main.py
- [ ] 3.4 In `setup_ui()`, replace `self.menu()` with `build_main_menu(self, self.grid, self.pool, self.swap_action, self.undo_action, self.redo_action)`
- [ ] 3.5 **Verify:** compile + unit tests + integration tests
- [ ] 3.6 **Commit:** `refactor: extract menu building to ui/menu_builder.py`

---

### Step 4 — Extract file I/O to `services/formation_file_service.py`

**Diff:** `main.py` −180 lines, `services/formation_file_service.py` +180 lines

- [ ] 4.1 Create `chormanager/choraufstellung/services/formation_file_service.py` with:
  - [ ] 4.1a `class FormationFileService:` that takes `main_window` in constructor
  - [ ] 4.1b Method `new_file()` — from main.py `new_f()` (lines 1392-1404)
  - [ ] 4.1c Method `open_file(filepath=None)` — from main.py `open_f()` + `_open_file()` (lines 1406-1428)
  - [ ] 4.1d Method `save_file()` — from main.py `save_f()` (lines 1430-1454)
  - [ ] 4.1e Method `save_as_file()` — from main.py `save_as_f()` (lines 1456-1489)
  - [ ] 4.1f Method `_save_to_path(fp, metadata)` — from main.py `_save_file()` (lines 1491-1504)
  - [ ] 4.1g Method `generate_filename(event_date, event_name)` — from main.py (lines 1506-1518)
  - [ ] 4.1h Method `autosave_check()` — from main.py `_autosave_check()` (lines 1520-1541)
  - [ ] 4.1i Method `check_recovery()` — from main.py `_check_recovery()` (lines 1543-1564)
  - [ ] 4.1j Method `export_pdf()` — from main.py `export_pdf()` (lines 1565-1627)
    - [ ] Emit `pdf_done(success, message)` signal or keep callbacks on main_window
  - [ ] 4.1k Method `run_optimizer()` — from main.py `run_optimizer()` (lines 1644-1656)
    - [ ] Same — keep callbacks on main_window or emit signals
- [ ] 4.2 Remove the following methods from MainWindow:
  - `new_f()` (lines 1392-1404)
  - `open_f()` + `_open_file()` (lines 1406-1428)
  - `save_f()` (lines 1430-1454)
  - `save_as_f()` (lines 1456-1489)
  - `_save_file()` (lines 1491-1504)
  - `generate_filename()` (lines 1506-1518)
  - `_autosave_check()` (lines 1520-1541)
  - `_check_recovery()` (lines 1543-1564)
  - `export_pdf()` (lines 1565-1627)
  - `_on_pdf_export_done()` (lines 1629-1638)
  - `_on_pdf_export_error()` (lines 1640-1642)
  - `run_optimizer()` (lines 1644-1656)
  - `_on_optimizer_done()` (lines 1658-1663)
  - `_on_optimizer_error()` (lines 1665-1667)
- [ ] 4.3 Add `from services.formation_file_service import FormationFileService` + `self.file_service = FormationFileService(self)` in `__init__`
- [ ] 4.4 Update the `autosave_timer` connection: `self.autosave_timer.timeout.connect(self.file_service.autosave_check)`
- [ ] 4.5 Update menu action connections to point to `self.file_service.open_file()` etc.
- [ ] 4.6 **Verify:** compile + unit tests + integration tests
- [ ] 4.7 **Commit:** `refactor: extract file I/O, autosave, PDF export, optimizer to FormationFileService`

---

### Step 5 — Extract ChorManager data loading to `services/formation_loader.py`

**Diff:** `main.py` −70 lines, `services/formation_loader.py` +70 lines

- [ ] 5.1 Create `chormanager/choraufstellung/services/formation_loader.py` with:
  - [ ] 5.1a `class FormationLoader:` taking `main_window` in constructor
  - [ ] 5.1b Method `load_from_chormanager()` — from main.py `_load_from_chormanager()` (lines 1786-1820)
  - [ ] 5.1c Method `load_formation_data(data)` — from main.py `_load_formation_data()` (lines 1822-1848)
- [ ] 5.2 Remove main.py `_load_from_chormanager()` (lines 1786-1820)
- [ ] 5.3 Remove main.py `_load_formation_data()` (lines 1822-1848)
- [ ] 5.4 Add `from services.formation_loader import FormationLoader` + `self.loader = FormationLoader(self)` in `__init__`
- [ ] 5.5 In `__init__`, replace calls:
  - `self._load_from_chormanager()` → `self.loader.load_from_chormanager()`
  - `self._check_recovery()` → `self.loader.check_recovery()`
  - `self._load_formation_data(data)` → `self.loader.load_formation_data(data)` (in `check_recovery`)
- [ ] 5.6 **Verify:** compile + unit tests + integration tests
- [ ] 5.7 **Commit:** `refactor: extract ChorManager data loading to FormationLoader`

---

### Step 6 — Remove duplicate undo command classes, use `core/commands.py`

**Diff:** `main.py` −65 lines, `core/commands.py` +0 (already exists)

- [ ] 6.1 Remove main.py lines 208-274 (MoveSingerCommand, SwapSingersCommand, MoveGroupCommand)
- [ ] 6.2 Update main.py:FormationGrid to import from `core/commands`:
  - [ ] Change `MoveGroupCommand(group_ids, delta_col, delta_row, self)` → use `core/commands` version
  - [ ] Change `MoveSingerCommand(dragged_singer, old_row, old_col, ...)` → use `core/commands` version
  - [ ] Change `SwapSingersCommand(singer1, singer2, self)` → use `core/commands` version
- [ ] 6.3 Check if `core/commands.py` constructors match; if not:
  - [ ] **Option A:** Update calls in main.py to match core/commands.py signatures
  - [ ] **Option B:** Add backward-compat constructors to core/commands.py
- [ ] 6.4 Update the `self.undo_stack` usage: `core/commands.UndoStack` ≠ `QUndoStack`
  - [ ] **Decision:** Keep `QUndoStack` for Qt integration, but create wrapper commands
  - [ ] Implementation: Create `QtMoveSingerCommand(QUndoCommand)` that wraps `core.commands.MoveSingerCommand`
  - [ ] Or: Make `core/commands.py` commands inherit from `QUndoCommand` when Qt is available
- [ ] 6.5 **Verify:** compile + unit tests + integration tests + manual undo/redo
- [ ] 6.6 **Commit:** `refactor: consolidate undo commands, use core/commands.py`

---

## Phase II: Remove Duplicate Widgets (Steps 7–9)

### Step 7 — Migrate `SingerPool` to `ui/pool_widget.py`

**Diff:** `main.py` −155 lines, `ui/pool_widget.py` +50 lines

- [ ] 7.1 Audit `ui/pool_widget.py:SingerPool` for missing API compared to main.py version:
  - [ ] 7.1a Verify `place_all_requested` signal exists; add if missing
  - [ ] 7.1b Verify `update_placed_singers()` method exists
  - [ ] 7.1c Verify `set_affinity(singer)` method exists
  - [ ] 7.1d Verify `add_dialog(singer=None)` works without `parent` arg (make parent optional)
  - [ ] 7.1e Verify `singer_selected`, `singer_added`, `singer_edit_requested` signals match
- [ ] 7.2 Add `class DraggableTableWidget` to `ui/pool_widget.py` if not already there
  - [ ] OR remove from main.py and update references to use the one in `ui/pool_widget.py`
- [ ] 7.3 Remove main.py SingerPool class (lines 777-932)
  - [ ] Also remove main.py DraggableTableWidget class (lines 59-81) — it's only used by SingerPool
- [ ] 7.4 Add `from ui.pool_widget import SingerPool` to main.py
- [ ] 7.5 In `setup_ui()`, ensure `self.pool = SingerPool()` still works
- [ ] 7.6 **Verify:** compile + unit tests + integration tests + user flow (add singer, place, remove)
- [ ] 7.7 **Commit:** `refactor: migrate SingerPool to ui/pool_widget.py`

---

### Step 8 — Migrate `FormationGrid` to `ui/grid_widget.py`

**Diff:** `main.py` −500 lines, `ui/grid_widget.py` +30 lines

- [ ] 8.1 Audit `ui/grid_widget.py:FormationGrid` for API parity:
  - [ ] 8.1a `set_dimensions(r, c)` vs `set_grid_size(r, c)` — align names
  - [ ] 8.1b `undo_stack = QUndoStack(self)` — add as default, with signal forwarding
  - [ ] 8.1c `canUndoChanged` / `canRedoChanged` signals — wire from QUndoStack
  - [ ] 8.1d `show_grid_context_menu(pos)` — ensure exists
  - [ ] 8.1e `get_placed_singers()` — check return format (list of tuples vs list of Singer)
  - [ ] 8.1f **Copy** any methods present in main.py but missing in ui/grid_widget.py:
    - `set_staggered(v)` ✅ exists
    - `update_selection_visuals()` ✅ exists
    - `highlight_singer()` ✅ exists
    - `_pulse_step()` ✅ exists
    - `_restore_tile_style()` ✅ exists
    - `clear_search_highlight()` ✅ exists
    - `mousePressEvent` ✅ exists
    - `mouseMoveEvent` ✅ exists
    - `mouseReleaseEvent` ✅ exists
    - `swap_selected_singers()` ✅ exists
    - `apply_affinity_proximity()` ✅ exists
    - `refresh_grid()` ✅ exists
    - `place_singer()` ✅ exists
    - `place_singer_at()` ✅ exists
    - `is_occupied()` ✅ exists
    - `get_singer_at()` ✅ exists
    - `on_tile_removed()` ✅ exists
    - `on_tile_edit_requested()` ✅ exists
    - `on_tile_affinity_requested()` ✅ exists
    - `get_placed_singers()` — check return type
    - `get_placed_singer_ids()` ✅ exists
    - `auto_arrange_by_height` etc. ✅ exists
    - `optimize()` ✅ exists
    - `dragMoveEvent` / `dragEnterEvent` / `dropEvent` ✅ exists
- [ ] 8.2 Remove main.py FormationGrid class (lines 276-775)
  - [ ] Also remove main.py SingerTile class (lines 83-206) — only used by FormationGrid
- [ ] 8.3 Remove main.py undo command classes if not already done in Step 6 (lines 208-274)
- [ ] 8.4 Add `from ui.grid_widget import FormationGrid` to main.py
- [ ] 8.5 In `setup_ui()`, ensure `self.grid = FormationGrid(4, 5)` works:
  - [ ] Signal connections: `singer_removed_from_grid`, `singer_edit_requested`, `singer_affinity_requested`
  - [ ] `undo_stack.canUndoChanged`, `undo_stack.canRedoChanged`
  - [ ] `selection_changed`
- [ ] 8.6 **Verify:** compile + unit tests + integration tests
- [ ] 8.7 **Manual verification (critical):** Start the app, test:
  - [ ] Grid renders with correct dimensions
  - [ ] Drag & drop from pool to grid works
  - [ ] Drag & drop within grid works (move + group move)
  - [ ] Rubber band selection works
  - [ ] Undo/redo works (Ctrl+Z/Ctrl+Y)
  - [ ] Right-click context menu works
  - [ ] Affinity proximity works
  - [ ] Auto-arrange buttons work (all 7 arrangements)
  - [ ] Grid resize (rows/cols combos) works
  - [ ] Staggered/normal toggle works
- [ ] 8.8 **Commit:** `refactor: migrate FormationGrid to ui/grid_widget.py`

---

### Step 9 — Cleanup and final trimming

**Diff:** `main.py` −50 lines of various inline helpers

- [ ] 9.1 Remove `__init__` lines that set duplicates:
  - `self.pool.placed_singer_ids = set()` — verify ui/pool_widget does this
  - `self.pool.singers = self.singers` — verify wire-up still works
- [ ] 9.2 Simplify `setup_ui()`:
  - [ ] Move layout constants to top of method or a config
  - [ ] Extract inline lambda connections to named methods
- [ ] 9.3 Remove the `try/except ImportError` fallback block (lines 18-57) IF all modules
      are guaranteed available at this point. Otherwise keep for safety.
- [ ] 9.4 Count lines: `wc -l main.py` — target should be **≤500 lines**
- [ ] 9.5 **Verify:** full test suite
- [ ] 9.6 **Commit:** `refactor: final cleanup after MainWindow split`

---

## Acceptance Criteria

### Checklist — all must pass before declaring done:

| # | Criteria | How to verify |
|---|----------|--------------|
| 1 | `main.py` ≤ 500 lines | `wc -l main.py` |
| 2 | No duplicate class definitions | `grep -c "class FormationGrid" main.py` → 0 |
| 3 | No duplicate SingerTile | `grep -c "class SingerTile" main.py` → 0 |
| 4 | No duplicate SingerPool | `grep -c "class SingerPool" main.py` → 0 |
| 5 | No undo commands in main.py | `grep -c "class.*Command.*QUndo" main.py` → 0 |
| 6 | No dialog classes in main.py | `grep -c "class.*Dialog" main.py` → 0 (only import) |
| 7 | All 273 unit tests pass | `python3 -m pytest tests/unit/ -q --ignore=tests/unit/test_event_list_dialog_dropdown.py` |
| 8 | All integration tests pass | `python3 -m pytest tests/integration/ -q` |
| 9 | App starts without error | `QT_QPA_PLATFORM=offscreen python3 -c "..."` smoke test |
| 10 | Undo/redo works | Manual: place singer, move, Ctrl+Z, Ctrl+Y |
| 11 | Drag & drop works | Manual: drag from pool to grid |
| 12 | File save/load works | Manual: Ctrl+S, Ctrl+O |

---

## Estimated Effort

| Step | Description | Est. time |
|------|-------------|-----------|
| 1 | Extract dialogs | 15 min |
| 2 | Extract theme manager | 15 min |
| 3 | Extract menu builder | 15 min |
| 4 | Extract file service | 45 min |
| 5 | Extract formation loader | 20 min |
| 6 | Consolidate undo commands | 30 min |
| 7 | Migrate SingerPool | 45 min |
| 8 | Migrate FormationGrid | 90 min ⚠️ |
| 9 | Final cleanup | 30 min |
| **Total** | | **~5 hours** |

**Risk estimate:** Steps 6+7+8 are the high-risk zone (~3 hours). They involve API alignment
between the two widget implementations. Plan for 1-2 extra hours of debugging during these steps.
