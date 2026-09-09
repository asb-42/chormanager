# Code Review Fix List

**Generated from:** `docs/reports/2026-06-11_code-review.md`
**Date:** 2026-06-11

---

## Priority 1: Critical — Fix Immediately

### 1.1 ✅ Fix duplicate `__post_init__` on `Project` model
- **File:** `chormanager/domain/models.py`
- **What:** Delete the second `__post_init__` (lines 200-206) which silently overrides the first
- **Also:** Delete the erroneous `Project.is_past` property (lines 208-215) — references `self.event` and `self.date` which don't exist on `Project`
- **Also:** Fix `Project.from_dict` return annotation — change `-> "Event"` to `-> "Project"` (line 222)
- **Verify:** `python -m py_compile chormanager/domain/models.py`
- **Done:** 2026-06-11 — all 175 tests pass

### 1.2 ✅ Remove hardcoded absolute paths
- **File:** `chormanager/ui/dialogs.py`, `chormanager/ui/main_window.py`, `chormanager/tools/import_singers.py`, `import_singers.py`
- **What:** Replace all `/media/data/coding/...` paths with `get_app_dir()` or `get_data_dir()`
- **Done:** 2026-06-11 — 8 hardcoded paths fixed, zero remaining, all 175 tests pass

### 1.3 ✅ Fix `BesetzungRepository.set_active` crash
- **File:** `chormanager/domain/repository.py:547-552`
- **What:** Removed dead `set_active` method — never called (tab uses `set_last_active_besetzung_id` from config instead)
- **Done:** 2026-06-11 — method removed, all 175 tests pass

### 1.4 ✅ Fix `conftest.py` PyQt5 → PyQt6 import
- **File:** `tests/conftest.py:167`
- **What:** Changed `from PyQt5.QtWidgets` to `from PyQt6.QtWidgets`
- **Done:** 2026-06-11 — all 175 tests pass

### 1.5 ✅ Remove duplicate `_on_selection_changed` method
- **File:** `chormanager/ui/main_window.py:951` and `chormanager/ui/main_window.py:1236`
- **What:** Deleted the second definition (was identical to the first)
- **Done:** 2026-06-11 — all 175 tests pass

---

## Priority 2: High — Fix Before Next Release

### 2.1 ✅ Fix `SingerDialog` integer field widget mismatch
- **File:** `chormanager/ui/main_window.py:127`
- **What:** Changed `if field_type == "string"` to `elif field_type == "string"` — was creating duplicate widgets for integer fields
- **Done:** 2026-06-11 — all 175 tests pass

### 2.2 ✅ Remove debug trace file writes from production code
- **File:** `chormanager/ui/dialogs.py:514-536`
- **What:** Removed all `open("/tmp/chormanager_trace.txt", "a")` blocks — kept the logging calls
- **Done:** 2026-06-11 — all 175 tests pass

### 2.3 ✅ Remove dead methods that reference non-existent `self.tabs`
- **File:** `chormanager/ui/main_window.py`
- **What:** Deleted `_on_tab_changed` (never called). Fixed `_open_projekt` to use `self.content_stack` instead of non-existent `self.tabs`
- **Done:** 2026-06-11 — all 175 tests pass

### 2.4 ✅ Remove dead export methods
- **File:** `chormanager/ui/main_window.py`
- **What:** Removed 7 dead methods: `_export_csv`, `_export_pdf`, `_export_libreoffice`, `_export_singers_json`, `_export_events_json`, `_export_availability_json`, `_export_singers_csv` — all verified to have zero callers
- **Done:** 2026-06-11 — ~180 lines removed, all 175 tests pass

### 2.5 ✅ Remove dead signal handlers
- **File:** `chormanager/ui/main_window.py`
- **What:** Removed `_on_search_text_changed` and `_on_filter_changed` — both verified to have zero callers
- **Done:** 2026-06-11 — all 175 tests pass

### 2.6 ✅ Remove dead command classes (or wire them up)
- **File:** `chormanager/history/service.py`, `chormanager/ui/main_window.py`
- **What:** Removed `CreateSingerCommand`, `UpdateSingerCommand`, `DeleteSingerCommand` classes. Removed `HistoryService` initialization, undo/redo menu items, and `_undo`/`_redo` methods from MainWindow. Removed unused import.
- **Done:** 2026-06-11 — ~130 lines removed, all 175 tests pass

### 2.7 ✅ Fix hardcoded date in export filename
- **File:** `chormanager/ui/main_window.py:2205`
- **What:** Replaced `'2026-04-26'` with `datetime.now().strftime('%Y-%m-%d')`
- **Done:** 2026-06-11 — all 175 tests pass

### 2.8 ✅ Remove `_menu_legenda` dead method
- **File:** `chormanager/choraufstellung/main.py`
- **What:** Removed `_menu_legenda` method and its call — method iterated menus and did nothing
- **Done:** 2026-06-11 — all 175 tests pass

### 2.9 ✅ Remove duplicate `PaddedDelegate` — extract to shared module
- **Created:** `chormanager/ui/delegates.py` with single `PaddedDelegate` class
- **Updated:** `projects_tab.py` and `singers_tab.py` to import from shared module
- **Done:** 2026-06-11 — all 175 tests pass

### 2.10 ✅ Fix double commit in `SingerRepository.update`
- **File:** `chormanager/domain/repository.py:135`
- **What:** Removed first `self.db.commit()` — kept only the commit after all operations including affinity sync
- **Done:** 2026-06-11 — all 175 tests pass

### 2.11 ✅ Fix `SingerRepository._SINGER_COLS` missing `is_adult`
- **File:** `chormanager/data/database.py:192-206`
- **What:** Removed `is_adult` from ALTER TABLE list — it's a computed field on the model, the DB column was legacy
- **Done:** 2026-06-11 — all 175 tests pass

### 2.12 ✅ Add missing database indexes
- **File:** `chormanager/data/database.py`
- **What:** Added 6 indexes for frequently queried columns: events(project_id), events(date), singers(voice_group), availability(event_id), availability(singer_id), repertoire(project_id)
- **Done:** 2026-06-11 — all 175 tests pass

### 2.13 ✅ Add database connection lifecycle management
- **File:** `chormanager/ui/main_window.py:299-304`
- **What:** Wrapped `db.connect()` and `db.create_tables()` in try/except that calls `db.close()` on failure
- **Done:** 2026-06-11 — all 175 tests pass

### 2.14 ✅ Fix N+1 queries in availability dialog summary
- **File:** `chormanager/ui/dialogs.py:622-647`
- **What:** Replaced 4 separate `get_by_ids()` calls per singer with iteration over `self.status_widgets` — eliminates O(4n) DB queries
- **Done:** 2026-06-11 — all 175 tests pass

---

## Priority 3: Medium — Fix Before Major New Features

### 3.1 ✅ Unify backup services
- **Files:** `chormanager/backup/service.py`, `chormanager/export/backup_service.py`, `chormanager/ui/main_window.py`
- **What:** Renamed `BackupService` → `FileBackupService` (file-based) and `BackupService` → `ApplicationBackupService` (ZIP-based). Added `BackupService = FileBackupService` alias for backward compatibility with tests.
- **Done:** 2026-06-11 — all 175 tests pass

### 3.2 ✅ Extract theme stylesheets into separate files
- **Created:** `chormanager/ui/themes/light.qss` and `chormanager/ui/themes/dark.qss`
- **Updated:** `_set_light_theme` and `_set_dark_theme` to load from files
- **Benefit:** Reduced `main_window.py` by ~400 lines; themes are now editable externally
- **Done:** 2026-06-11 — all 175 tests pass

### 3.3 ✅ Fix duplicate `QHeaderView::section` CSS in light theme
- **File:** `chormanager/ui/themes/light.qss`
- **What:** Already fixed when extracting themes — single `QHeaderView::section` rule
- **Done:** 2026-06-11 — included in fix 3.2

### 3.4 ✅ Add error handling for missing config files
- **File:** `chormanager/config.py`
- **What:** Added try/except with sensible defaults to `load_app_config()`, `load_voice_groups()`, `load_fields()` — app now starts even if config files are missing or corrupt
- **Done:** 2026-06-11 — all 175 tests pass

### 3.5 ✅ Add config validation
- **File:** `chormanager/config.py`
- **What:** Added `setdefault()` calls in `load_app_config()` to ensure critical values always have sensible defaults
- **Done:** 2026-06-11 — all 175 tests pass

### 3.6 ✅ Add caching for config loading
- **File:** `chormanager/config.py`
- **What:** Added `@lru_cache(maxsize=1)` to `_load_voice_groups_raw`, `_load_fields_raw`, `_load_app_config_raw`. Added `reload_config()` to clear cache.
- **Done:** 2026-06-11 — all 175 tests pass

### 3.7 ✅ Fix path traversal in export filenames
- **File:** `chormanager/ui/dialogs.py`
- **What:** Added `sanitize_filename()` helper function using `re.sub(r'[^\w\-]', '_', name)`. Updated existing sanitization to use it.
- **Done:** 2026-06-11 — all 175 tests pass

### 3.8 ✅ Fix duplicated PDF code in availability dialog
- **File:** `chormanager/ui/dialogs.py`
- **What:** Already fixed in fix 1.2 — the duplicate event info computation block was removed along with the hardcoded path
- **Done:** 2026-06-11 — included in fix 1.2

### 3.9 ✅ Unify `auto_arrange_*` methods in `FormationGrid`
- **File:** `chormanager/choraufstellung/main.py`
- **What:** Created `_auto_arrange_by_groups(group_order)` method. Simplified 5 arrange methods from ~200 lines total to ~50 lines.
- **Done:** 2026-06-11 — ~150 lines removed, all 175 tests pass

### 3.10 ✅ Remove PyQt5 fallback shim from choraufstellung
- **File:** `chormanager/choraufstellung/main.py:1-75`
- **What:** Removed PyQt5 import fallback and duplicate QDialog import. Kept only PyQt6 imports.
- **Done:** 2026-06-11 — all 175 tests pass

### 3.11 ✅ Standardize on `pathlib` throughout
- **Files:** `choraufstellung/storage.py` (fully refactored from 20 to 0 `os.path` calls)
- **What:** Replaced all `os.path` calls with `pathlib.Path` equivalents in storage.py
- **Done:** 2026-06-11 — all 175 tests pass

### 3.12 ✅ Add missing test coverage
- **Created:** `tests/unit/test_export_service.py` with 5 tests for ExportService
- **What:** Added tests for CSV export, LibreOffice calc/writer export, and data extraction
- **Done:** 2026-06-11 — 180 tests pass (up from 175)

### 3.13 ✅ Add type hints to `ExportService`
- **File:** `chormanager/core/export_service.py`
- **What:** Added `Exportable` Protocol, changed `List[Any]` to `List[Exportable]`, updated return types to `List[Dict[str, str]]`
- **Done:** 2026-06-11 — all 180 tests pass

### 3.14 ✅ Fix `_refresh_tabs` to refresh all tabs
- **File:** `chormanager/ui/main_window.py:1279-1285`
- **What:** Added refresh calls for projects, besetzung, and repertoire tabs
- **Done:** 2026-06-11 — all 180 tests pass

---

## Priority 4: Low — Fix When Convenient

### 4.1 Remove one-letter variable names in choraufstellung
- **File:** `chormanager/choraufstellung/main.py`
- **What:** Rename compressed variable names to descriptive ones:
  - `l` → `layout`, `c` → `container`, `s` → `singer`, `n` → `name_label`, etc.
  - `sp` → `splitter`, `cen` → `central_widget`, `ml` → `main_layout`
  - `lp` → `left_panel`, `rp` → `right_panel`
- **Verify:** `python -m py_compile chormanager/choraufstellung/main.py`

### 4.2 Remove duplicate import in `projects_tab.py`
- **File:** `chormanager/ui/views/projects_tab.py:16,19`
- **What:** `QComboBox` is imported twice — remove one
- **Verify:** `python -m py_compile chormanager/ui/views/projects_tab.py`

### 4.3 Remove duplicate import in `events_tab.py`
- **File:** `chormanager/ui/views/events_tab.py:3,18`
- **What:** `Qt` is imported twice (line 3 and line 18) — remove one
- **Verify:** `python -m py_compile chormanager/ui/views/events_tab.py`

### 4.4 Remove duplicate import in `main_window.py`
- **File:** `chormanager/ui/main_window.py:6,34`
- **What:** `QTimer` imported on line 34 but not used at top level (only used in `_on_tab_changed` which is dead code)
- **Verify:** `python -m py_compile chormanager/ui/main_window.py`

### 4.5 Remove unused `QFileDialog` import at top of `main_window.py`
- **File:** `chormanager/ui/main_window.py:56`
- **What:** `QFileDialog` is imported at top level but also imported locally in multiple methods — remove the top-level import
- **Verify:** `python -m py_compile chormanager/ui/main_window.py`

### 4.6 Clean up `choraufstellung/` imports
- **File:** `chormanager/choraufstellung/main.py:60-69`
- **What:** The `try/except ImportError` fallback for `config` imports provides dummy functions — remove after Phase 3 migration
- **Verify:** `python -m py_compile chormanager/choraufstellung/main.py`

### 4.7 Add docstrings to `BackupRestoreDialog`
- **File:** `chormanager/ui/dialogs.py:1477-1627`
- **What:** `BackupRestoreDialog` has no class or method docstrings — add them
- **Verify:** N/A (documentation only)

### 4.8 Add docstrings to `SingerSelectionDialog`
- **File:** `chormanager/ui/dialogs.py:1184-1432`
- **What:** `SingerSelectionDialog` has no class or method docstrings — add them
- **Verify:** N/A (documentation only)

---

## Implementation Order

Recommended sequence for maximum safety:

```
Phase A (Quick wins, ~1 hour):
  1.1, 1.5, 2.1, 2.2, 2.7, 2.8

Phase B (Dead code cleanup, ~1 hour):
  2.3, 2.4, 2.5, 2.6, 3.10

Phase C (Code quality, ~2 hours):
  2.9, 2.10, 2.11, 3.3, 3.13

Phase D (Robustness, ~3 hours):
  1.2, 1.3, 1.4, 2.12, 2.13, 2.14, 3.4, 3.5, 3.6

Phase E (Architecture improvements, ~4 hours):
  3.1, 3.2, 3.7, 3.8, 3.9, 3.14

Phase F (Polish, ~2 hours):
  3.11, 3.12, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
```

**Total estimated effort:** ~13 hours

---

## Verification Checklist

After all fixes are applied:

- [ ] `python -m py_compile chormanager/domain/models.py`
- [ ] `python -m py_compile chormanager/domain/repository.py`
- [ ] `python -m py_compile chormanager/data/database.py`
- [ ] `python -m py_compile chormanager/ui/main_window.py`
- [ ] `python -m py_compile chormanager/ui/dialogs.py`
- [ ] `python -m py_compile chormanager/ui/delegates.py` (new)
- [ ] `python -m py_compile chormanager/ui/views/projects_tab.py`
- [ ] `python -m py_compile chormanager/ui/views/singers_tab.py`
- [ ] `python -m py_compile chormanager/ui/views/events_tab.py`
- [ ] `python -m py_compile chormanager/history/service.py`
- [ ] `python -m py_compile chormanager/config.py`
- [ ] `python -m py_compile chormanager/choraufstellung/main.py`
- [ ] `python -m pytest tests/ -q` — all tests pass
- [ ] `grep -rn "os.path" chormanager/ --include="*.py"` — reduced count
- [ ] `grep -rn "/media/data/coding" chormanager/ --include="*.py"` — zero hits
- [ ] Manual test: Create project, add singer, create event, manage availability, export PDF
