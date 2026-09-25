# Choraufstellung Plugin Migration Plan

**Date:** 2026-06-11
**Status:** Proposed
**Scope:** Integrate the `choraufstellung/` sub-app as an embedded plugin in the main ChorManager application

---

## Problem Statement

The `choraufstellung/` component is the most important feature of the application — it provides the interactive choir formation grid with drag-and-drop placement, optimizer rules, undo/redo, and PDF export. However, it currently runs as a **standalone subprocess** launched from the main app, communicating through:

- Temp JSON files (`CHOR_EVENT_DATA` environment variable)
- Environment variables (`CHOR_EVENT_DATE`, `CHOR_PROJECT`, etc.)
- Direct SQLite access (opens its own `sqlite3` connection)
- `subprocess.run()` launching a separate Python process

This architecture causes:

1. **Two separate Python processes** — no shared memory, no shared Qt event loop
2. **Duplicated models** — `choraufstellung/singer_model.py` vs `domain/models.py`
3. **Duplicated configuration** — `choraufstellung/config.py` vs `config.py`
4. **Duplicated voice group definitions** — hardcoded in multiple places
5. **Fragile communication** — temp files can be stale, env vars can be lost
6. **UI freezes** — main app blocks while subprocess runs
7. **2,180-line god-class** — `choraufstellung/main.py:MainWindow` duplicates much of the main app's UI scaffolding

The goal is to embed the plugin as a `QWidget` inside the main app's tab system, sharing models, configuration, and database connection.

---

## Architecture Overview

### Current Architecture

```
┌─────────────────────────────────────────────────┐
│  Main App (MainWindow)                          │
│                                                 │
│  ┌──────────────────┐    ┌───────────────────┐  │
│  │ ChorAufstellungTab│───>│ subprocess.run()  │  │
│  │ (file list only)  │    │                   │  │
│  └──────────────────┘    │ ┌───────────────┐ │  │
│                          │ │ Standalone     │ │  │
│  writes temp JSON ──────>│ │ MainWindow     │ │  │
│  sets env vars     ──────>│ │ (2,180 lines)  │ │  │
│                          │ │               │ │  │
│                          │ │ own Singer    │ │  │
│                          │ │ own Config    │ │  │
│                          │ │ own DB conn   │ │  │
│                          │ └───────────────┘ │  │
│                          └───────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Target Architecture

```
┌─────────────────────────────────────────────────┐
│  Main App (MainWindow)                          │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │ ChorAufstellungTab                       │   │
│  │                                          │   │
│  │  ┌────────────────────────────────────┐  │   │
│  │  │ FormationEditorWidget              │  │   │
│  │  │                                    │  │   │
│  │  │  ┌──────────┐  ┌───────────────┐  │  │   │
│  │  │  │SingerPool│  │FormationGrid  │  │  │   │
│  │  │  │          │  │               │  │  │   │
│  │  │  │uses shared│  │uses shared    │  │  │   │
│  │  │  │Singer model│ │Singer model   │  │  │   │
│  │  │  └──────────┘  └───────────────┘  │  │   │
│  │  │                                    │  │   │
│  │  │  toolbar: arrange, optimize, etc.  │  │   │
│  │  └────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  Shared: Database, SingerRepository, Config     │
└─────────────────────────────────────────────────┘
```

---

## Phase 1: Unify the Singer Model

**Goal:** Eliminate `choraufstellung/singer_model.py` by extending the shared `domain/models.py` Singer with formation-specific fields.

**Effort:** Medium (~2 hours)
**Risk:** Low — additive change, no existing behavior broken

### Current State

Two separate Singer classes exist:

| Field | `domain/models.py:Singer` | `choraufstellung/singer_model.py:Singer` |
|-------|:---:|:---:|
| `id` / `singer_id` | `id` (str) | `singer_id` (str) |
| `full_name` / `name` | `full_name` (str) | `name` (str) |
| `voice_group` | `str` (e.g. `"Sopran 1"`) | `VoiceGroup` enum |
| `row` | - | `int` (-1 = unplaced) |
| `col` | - | `int` (-1 = unplaced) |
| `affinity` | `affinity_uuid` (str) | `affinity` (str) |
| `height` | `Optional[int]` | `int` (default 0) |
| DB fields | birth_date, email, phone, etc. | - |
| `external_id` | - | `str` |

### Plan

1. **Add formation fields to `domain/models.py:Singer`:**

```python
@dataclass
class Singer:
    # ... existing DB fields (id, full_name, voice_group, etc.) ...
    
    # Formation-specific fields (used by choraufstellung plugin)
    row: int = -1
    col: int = -1
    affinity: str = ""
```

The `affinity` field already exists as `affinity_uuid` — rename or alias it. The `row`/`col` fields are transient (not stored in DB) and only used during formation editing.

2. **Add a `from_formation_dict` class method** to convert from the choraufstellung JSON format:

```python
@classmethod
def from_formation_dict(cls, data: dict) -> "Singer":
    """Create Singer from choraufstellung formation JSON."""
    return cls(
        id=data.get("singer_id", ""),
        full_name=data.get("name", ""),
        voice_group=data.get("voice_group", ""),
        height=data.get("height", 0),
        row=data.get("row", -1),
        col=data.get("col", -1),
        affinity=data.get("affinity", ""),
    )
```

3. **Update `to_dict`** to include formation fields when present (for JSON export).

4. **Delete `choraufstellung/singer_model.py`** — all references updated to use `domain/models.py:Singer`.

5. **Update `choraufstellung/core/rules.py`** — `SingerRef` dataclass can be replaced with the shared `Singer` model, or kept as a lightweight projection if the full model is too heavy for rule evaluation.

6. **Update `choraufstellung/storage.py`** — use `Singer.from_formation_dict()` instead of local `Singer.from_dict()`.

### Files Changed

| File | Change |
|------|--------|
| `domain/models.py` | Add `row`, `col`, `affinity` fields; add `from_formation_dict()` |
| `choraufstellung/singer_model.py` | **DELETE** |
| `choraufstellung/storage.py` | Update imports, use shared Singer |
| `choraufstellung/main.py` | Update imports (remove fallback chain) |
| `choraufstellung/core/rules.py` | Update SingerRef or replace with Singer |
| `tests/conftest.py` | Update sample_singers fixture |

### Verification

- All existing tests pass (especially `test_singer.py`, `test_grid_engine.py`, `test_arrangement_rules.py`)
- Formation save/load round-trips correctly with the shared model
- Voice group enum handling works for both string and enum inputs

---

## Phase 2: Embed the Plugin as a Widget

**Goal:** Replace the subprocess-based integration with an embedded `QWidget` inside `ChorAufstellungTab`.

**Effort:** Large (~6-8 hours)
**Risk:** Medium — UI rework, but isolated to one tab

### Step 2.1: Extract `FormationEditorWidget` from `choraufstellung/main.py`

Create a new file `choraufstellung/editor_widget.py` containing a `FormationEditorWidget(QWidget)` class. This class extracts the core functionality from `choraufstellung/main.py:MainWindow` (lines 1313-2155) minus the standalone scaffolding (menu bar, QApplication setup, subprocess handling).

**What to extract:**

| Source (`choraufstellung/main.py`) | Target (`editor_widget.py`) |
|---|---|
| `MainWindow.setup_ui()` (lines 1362-1406) | `FormationEditorWidget._setup_ui()` |
| `MainWindow.add_to_grid()` | `FormationEditorWidget.add_to_grid()` |
| `MainWindow.place_all_singers()` | `FormationEditorWidget.place_all_singers()` |
| `MainWindow.upd_grid()` | `FormationEditorWidget.upd_grid()` |
| `MainWindow.reset_formation()` | `FormationEditorWidget.reset_formation()` |
| `MainWindow.apply_all_affinity_proximity()` | `FormationEditorWidget.apply_all_affinity_proximity()` |
| `MainWindow.run_optimizer()` | `FormationEditorWidget.run_optimizer()` |
| `MainWindow.undo_last_action()` / `redo_last_action()` | `FormationEditorWidget.undo/redo` |
| `MainWindow.do_quick_search()` | `FormationEditorWidget.do_quick_search()` |
| `MainWindow._autosave_check()` | `FormationEditorWidget._autosave_check()` |
| `MainWindow._save_file()` | `FormationEditorWidget.save_formation()` |
| `MainWindow._load_formation_data()` | `FormationEditorWidget.load_formation()` |

**What to remove (standalone-only):**

- `MainWindow.menu()` — menu bar creation (main app provides menus)
- `MainWindow._apply_theme()` — theme switching (main app handles themes)
- `MainWindow.show_about()` — about dialog (main app handles this)
- `MainWindow.closeEvent()` — unsaved changes prompt (main app handles this)
- `MainWindow._load_from_chormanager()` — env var / temp file loading (replaced by direct data passing)
- `MainWindow.__init__` env var parsing (lines 1314-1340)

**What to add (new interface):**

```python
class FormationEditorWidget(QWidget):
    """Embedded choir formation editor widget."""
    
    formation_changed = pyqtSignal()  # Emitted when formation is modified
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.singer_repo = SingerRepository(db)
        # ... setup UI ...
    
    def load_singers(self, singers: list[Singer]):
        """Load singers into the pool from external source."""
        self.singers = singers
        self.pool.update_singers(singers, set())
    
    def load_formation(self, filepath: str):
        """Load a saved formation from JSON file."""
        # ... existing load logic ...
    
    def save_formation(self, filepath: str = None) -> bool:
        """Save current formation to JSON file."""
        # ... existing save logic ...
    
    def get_placed_singers(self) -> list[tuple[Singer, int, int]]:
        """Get all placed singers with their grid positions."""
        return self.grid.get_placed_singers()
    
    def clear(self):
        """Reset all singers back to pool."""
        # ... existing reset logic ...
```

### Step 2.2: Update `ChorAufstellungTab` to Embed the Widget

Modify `ui/views/choraufstellung_tab.py` to:

1. Replace the file-list-only view with an embedded `FormationEditorWidget`
2. Provide methods to load singer data from the database
3. Keep the file list as a secondary feature (open/save formations)

```python
class ChorAufstellungTab(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.event = None
        self.project = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar for file operations
        toolbar = QHBoxLayout()
        self.open_btn = QPushButton("Aufstellung öffnen...")
        self.open_btn.clicked.connect(self._open_formation)
        self.save_btn = QPushButton("Speichern")
        self.save_btn.clicked.connect(self._save_formation)
        toolbar.addWidget(self.open_btn)
        toolbar.addWidget(self.save_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Embedded formation editor
        self.editor = FormationEditorWidget(self.db, parent=self)
        layout.addWidget(self.editor)
    
    def set_event(self, event):
        """Load singers available for this event into the editor."""
        self.event = event
        if event:
            singers = self._get_available_singers(event)
            self.editor.load_singers(singers)
    
    def set_project(self, project):
        self.project = project
    
    def _get_available_singers(self, event) -> list[Singer]:
        """Get singers with availability=yes or conditional for event."""
        singer_repo = SingerRepository(self.db)
        avail_repo = AvailabilityRepository(self.db)
        
        all_singers = singer_repo.get_active()
        available = []
        for singer in all_singers:
            avail = avail_repo.get_by_ids(singer.id, event.id)
            if avail and avail.status in ("yes", "conditional"):
                available.append(singer)
        return available
```

### Step 2.3: Remove Subprocess Launch from MainWindow

Delete or gut the following methods from `ui/main_window.py`:

- `_open_choraufstellung_for_event` (lines 1352-1443) — replace with:
  ```python
  def _open_choraufstellung_for_event(self, event):
      self.content_stack.setCurrentIndex(4)
      self.choraufstellung_tab.set_event(event)
  ```

- `_open_choraufstellung_file` (lines 2321-2398) — replace with:
  ```python
  def _open_choraufstellung(self):
      self.content_stack.setCurrentIndex(4)
  ```

- All temp JSON file creation, env var setting, and `subprocess.run()` calls.

### Step 2.4: Update Context Toolbar for Formation Tab

In `_update_context_toolbar` (line 1180-1208), update the formation tab actions to use the embedded editor:

```python
elif tab_index == 4:  # Aufstellung
    new_action = QAction("Neue Aufstellung", self)
    new_action.triggered.connect(self.choraufstellung_tab.editor.new_formation)
    self.context_toolbar.addAction(new_action)
    
    if selection:
        edit_action = QAction("Bearbeiten", self)
        edit_action.triggered.connect(self.choraufstellung_tab.editor.toggle_edit_mode)
        self.context_toolbar.addAction(edit_action)
        # ... etc
```

### Files Changed

| File | Change |
|------|--------|
| `choraufstellung/editor_widget.py` | **NEW** — `FormationEditorWidget` class |
| `choraufstellung/__init__.py` | Export `FormationEditorWidget` |
| `ui/views/choraufstellung_tab.py` | Embed editor, add singer loading |
| `ui/main_window.py` | Remove subprocess launch, simplify formation methods |
| `choraufstellung/main.py` | Keep for standalone mode (optional), but not used by main app |

### Verification

- Launch main app, navigate to Aufstellung tab
- Select an event → singers with availability load into pool
- Drag singers to grid → placement works
- Save/load formations to JSON → round-trip works
- Undo/redo works
- Optimizer runs
- PDF export works
- No subprocess launched, no temp files created

---

## Phase 3: Share Configuration

**Goal:** Eliminate duplicated config loading by having the plugin use the main app's configuration.

**Effort:** Small (~1 hour)
**Risk:** Low

### Current Duplication

| Config | Main App | Plugin |
|--------|----------|--------|
| Voice groups | `config/load_voice_groups()` → `config/voice_groups.yaml` | `choraufstellung/config.py:load_voice_groups_config()` → local YAML or hardcoded |
| Voice group colors | Not centralized | `choraufstellung/config.py:get_voice_group_color()` → local config or fallback |
| Theme | `config.get_theme()` / `config.set_theme()` | `choraufstellung/config.py:load_settings()` / `save_settings()` → local JSON |
| Data directory | `config.get_data_dir()` → `./data` | `choraufstellung/storage.py:_get_data_dir()` → `./choraufstellung/data` |

### Plan

1. **Add `color` field to `config/voice_groups.yaml`:**

```yaml
voice_groups:
  - name: "Sopran 1"
    short: "S1"
    order: 1
    color: "#FFB3BA"  # ADD
  - name: "Sopran 2"
    short: "S2"
    order: 2
    color: "#FFDFBA"  # ADD
  # ... etc
```

2. **Add `get_voice_group_color()` to main app's `config.py`:**

```python
def get_voice_group_color(voice_group_name: str) -> str:
    """Get hex color for a voice group."""
    groups = load_voice_groups()
    for g in groups:
        if g["name"] == voice_group_name:
            return g.get("color", "#cccccc")
    return "#cccccc"
```

3. **Update `choraufstellung/singer_model.py:voice_group_color()`** (or its replacement after Phase 1) to use the shared config:

```python
def voice_group_color(voice_group) -> str:
    from chormanager.config import get_voice_group_color
    vg_str = voice_group.value if hasattr(voice_group, 'value') else str(voice_group)
    return get_voice_group_color(vg_str)
```

4. **Delete `choraufstellung/config.py`** — all its functions are replaced by the main app's `config.py`.

5. **Update `choraufstellung/storage.py:_get_data_dir()`** to use `config.get_data_dir()` from the main app.

### Files Changed

| File | Change |
|------|--------|
| `config/voice_groups.yaml` | Add `color` field to each group |
| `config.py` | Add `get_voice_group_color()` |
| `choraufstellung/config.py` | **DELETE** |
| `choraufstellung/singer_model.py` | Update `voice_group_color()` to use shared config |
| `choraufstellung/storage.py` | Update `_get_data_dir()` to use shared config |
| `choraufstellung/main.py` | Remove config imports/fallbacks |

### Verification

- Voice group colors display correctly in the formation grid
- Theme switching works from both main app and formation editor
- Data directory is consistent between main app and plugin

---

## Phase 4: Remove Subprocess Communication Layer

**Goal:** Delete all temp file, env var, and subprocess communication code.

**Effort:** Medium (~2 hours)
**Risk:** Low — deletes dead code after Phase 2

### Code to Delete

| Location | What | Lines |
|----------|------|------:|
| `choraufstellung/main.py` | `MainWindow.__init__` env var parsing | 1314-1340 |
| `choraufstellung/main.py` | `_load_from_chormanager()` — reads temp JSON, opens own DB | 2008-2128 |
| `main_window.py` | `_open_choraufstellung_for_event()` — writes temp JSON, sets env vars, subprocess | 1352-1443 |
| `main_window.py` | `_open_choraufstellung_file()` — same pattern | 2321-2398 |
| `main_window.py` | `_open_choraufstellung()` — delegates to above | 2317-2319 |
| `choraufstellung/main.py` | `main()` function — standalone entry point (keep if standalone mode desired) | 2158-2181 |

### Code to Simplify

| Location | What |
|----------|------|
| `main_window.py:2317-2319` | `_open_choraufstellung` → just switch to tab index 4 |
| `main_window.py:1352-1443` | `_open_choraufstellung_for_event` → call `tab.set_event(event)` |

### Files Changed

| File | Change |
|------|--------|
| `ui/main_window.py` | Delete subprocess methods, simplify formation navigation |
| `choraufstellung/main.py` | Delete `_load_from_chormanager`, delete env var parsing in `__init__` |

### Verification

- No temp files created in `/tmp/` when using formation editor
- No `CHOR_EVENT_DATA` or similar env vars set
- No subprocess launched
- Formation editor works entirely within the main app's process

---

## Phase 5: Clean Up Plugin Structure

**Goal:** Reorganize `choraufstellung/` to reflect its role as an embedded plugin.

**Effort:** Medium (~2 hours)
**Risk:** Low — file reorganization

### Target Structure

```
choraufstellung/
├── __init__.py              # Public API: FormationEditorWidget
├── editor_widget.py         # Main embedded widget (NEW, from Phase 2)
├── core/
│   ├── __init__.py
│   ├── grid_engine.py       # Grid math and configuration (KEEP)
│   ├── optimizer.py         # Formation optimizer (KEEP)
│   ├── rules.py             # Optimization rules (KEEP, update SingerRef)
│   └── commands.py          # QUndoCommand subclasses (KEEP)
├── ui/
│   ├── __init__.py
│   ├── grid_widget.py       # FormationGrid widget (KEEP)
│   ├── pool_widget.py       # SingerPool widget (KEEP)
│   ├── optimizer_dialog.py  # Optimizer dialog (KEEP)
│   └── print_preview.py     # Print preview (KEEP)
├── storage.py               # Formation JSON persistence (KEEP)
└── pdf_export.py            # PDF generation (KEEP)
```

### Files to Delete

| File | Reason |
|------|--------|
| `main.py` | 2,180-line standalone MainWindow — replaced by `editor_widget.py` |
| `singer_model.py` | Replaced by shared `domain/models.py` |
| `config.py` | Replaced by main app's `config.py` |
| `dependencies.py` | Only used by old standalone path |
| `qt_compat.py` | PyQt5 compatibility shim — no longer needed |
| `__main__.py` | Standalone entry point — keep only if standalone mode desired |

### Files to Keep (unchanged)

| File | Lines | Purpose |
|------|------:|---------|
| `core/grid_engine.py` | 131 | Grid math, coordinate calculations |
| `core/optimizer.py` | 94 | Hill-climb formation optimizer |
| `core/rules.py` | 668 | Optimization rule definitions |
| `core/commands.py` | 205 | QUndoCommand subclasses |
| `ui/grid_widget.py` | 778 | FormationGrid QWidget |
| `ui/pool_widget.py` | 463 | SingerPool QWidget |
| `ui/optimizer_dialog.py` | 163 | Optimizer rule selection dialog |
| `ui/print_preview.py` | 358 | Print preview widget |
| `storage.py` | 207 | Formation JSON save/load |
| `pdf_export.py` | 257 | PDF generation |

### Files to Update

| File | Change |
|------|--------|
| `__init__.py` | Export `FormationEditorWidget`, remove old imports |
| `core/rules.py` | Update `SingerRef` to use shared `Singer` model (or keep as lightweight projection) |
| `storage.py` | Update imports to use shared Singer model |
| `ui/grid_widget.py` | Update imports to use shared Singer model |
| `ui/pool_widget.py` | Update imports to use shared Singer model |

### Verification

- All imports resolve correctly
- No circular dependencies
- Formation save/load works with the new structure
- Tests pass

---

## Migration Order and Dependencies

```
Phase 1: Unify Singer Model
    │
    ▼
Phase 2: Embed as Widget ──────────────────────┐
    │                                           │
    ▼                                           ▼
Phase 3: Share Configuration          Phase 4: Remove Subprocess
    │                                           │
    └───────────────────┬───────────────────────┘
                        │
                        ▼
                Phase 5: Clean Up
```

- **Phase 1** must come first (other phases depend on the shared model)
- **Phases 2, 3, 4** can be done in parallel after Phase 1
- **Phase 5** comes last (cleanup after everything else is stable)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking formation save/load | Keep `storage.py` unchanged initially; test round-trip after each phase |
| Breaking optimizer rules | `core/rules.py` and `core/optimizer.py` are untouched until Phase 5 |
| Breaking PDF export | `pdf_export.py` is untouched; test export after Phase 2 |
| Breaking standalone mode | Keep `main.py` as optional standalone entry point; delete only in Phase 5 |
| Test regressions | Run full test suite after each phase; add integration tests for embedded widget |

---

## Success Criteria

After all phases are complete:

1. **No subprocess launched** when opening the formation editor
2. **No temp files** created in `/tmp/`
3. **No env vars** needed for communication
4. **Shared Singer model** between main app and plugin
5. **Shared configuration** (voice groups, colors, theme)
6. **Single database connection** shared across all components
7. **Plugin structure** is clean and self-contained under `choraufstellung/`
8. **All existing tests pass**
9. **Formation save/load** works identically to before
10. **PDF export** works identically to before
