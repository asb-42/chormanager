# ChorManager Code Review

**Date:** 2026-06-11
**Reviewer:** MiMoCode (Senior-level Review)
**Scope:** Full codebase (~20,700 lines Python, PyQt6/SQLite/PyYAML/ReportLab/pytest)
**Project:** ChorManager — choir management desktop application

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Major Findings](#major-findings)
3. [Dead Code Findings](#dead-code-findings)
4. [Technology Stack Usage Assessment](#technology-stack-usage-assessment)
5. [Refactoring Opportunities](#refactoring-opportunities-ranked-by-benefit)
6. [Quick Wins](#quick-wins--30-minutes-each)
7. [Final Verdict](#final-verdict)

---

## Executive Summary

| Metric | Score (1-10) |
|--------|:---:|
| **Overall Code Quality** | 4/10 |
| **Maintainability** | 3/10 |
| **Robustness** | 4/10 |
| **Architecture** | 4/10 |

The application is a functional choir management desktop tool with good features, but suffers from two parallel codebases (the main app and the `choraufstellung/` sub-app), massive god-classes, numerous correctness bugs, hardcoded paths, and significant dead code.

---

## Major Findings

### 1. CRITICAL: Duplicate `__post_init__` on `Project` model

- **Severity:** Critical (data loss risk)
- **Location:** `chormanager/domain/models.py:186-206`
- **Explanation:** `Project` defines `__post_init__` twice. The second definition (lines 200-206) silently overrides the first (lines 186-198). The first version generates a UUID for new projects; the second does not. Additionally, the first version references `self.event` which doesn't exist on `Project`, and references `self.date` in `is_past` which doesn't exist.
- **Risk:** New projects may be created with empty `id`, and the `is_past` property will crash with `AttributeError`.
- **Fix:** Remove duplicate `__post_init__`, remove the erroneous `is_past` method from `Project` (it belongs on `Event`), fix return type annotation `from_dict` says `-> "Event"` instead of `-> "Project"`.

### 2. CRITICAL: Duplicate `_on_selection_changed` method

- **Severity:** Critical
- **Location:** `chormanager/ui/main_window.py:951` and `chormanager/ui/main_window.py:1236`
- **Explanation:** `MainWindow._on_selection_changed` is defined twice with identical signatures. The second definition silently overrides the first. While the logic is the same, this indicates copy-paste error and will confuse future maintenance.
- **Risk:** Any bug fix in one copy won't apply to the other.

### 3. CRITICAL: Hardcoded absolute paths

- **Severity:** Critical
- **Location:** `chormanager/ui/dialogs.py:742-744,775-777`, `chormanager/ui/dialogs.py:1064-1071`
- **Explanation:** Export paths are hardcoded to `/media/data/coding/chormanager/workdir`. The "Choraufstellung-Integration" config dialog defaults to `/media/data/coding/choraufstellung`.
- **Risk:** Application will fail on any machine other than the original developer's. This is a deployment blocker.

### 4. HIGH: EventAvailabilityDialog._load_availability — N+1 queries with trace file leak

- **Severity:** High
- **Location:** `chormanager/ui/dialogs.py:508-678`
- **Explanation:**
  - Lines 514-536 write debug traces to `/tmp/chormanager_trace.txt` unconditionally — debug code left in production.
  - Lines 635-660 call `self.avail_repo.get_by_ids()` 4 times per singer (once for each count check), resulting in O(4n) database queries where n is the number of singers. This could be a single query.
- **Risk:** UI freezes for large choirs; debug files accumulate on disk.

### 5. HIGH: Duplicate `PaddedDelegate` class

- **Severity:** High (maintainability)
- **Location:** `chormanager/ui/views/projects_tab.py:29-38` and `chormanager/ui/views/singers_tab.py:22-30`
- **Explanation:** Identical `PaddedDelegate` implementations exist in two files.
- **Risk:** Changes to one won't propagate to the other.

### 6. HIGH: Database migration uses raw string formatting

- **Severity:** High (security/correctness)
- **Location:** `chormanager/data/database.py:204`
- **Explanation:** `f"ALTER TABLE singers ADD COLUMN {col} {typ}"` uses string interpolation for SQL DDL. While the column names are hardcoded, this pattern is dangerous and sets a bad precedent.

### 7. HIGH: Missing database connection lifecycle management

- **Severity:** High
- **Location:** `chormanager/ui/main_window.py:308-309`
- **Explanation:** `Database` is created and connected in `MainWindow.__init__` but relies entirely on `closeEvent` for cleanup. If `MainWindow` construction fails or the app crashes, the connection leaks. The `Database` class supports context manager usage but it's never used.
- **Risk:** Database corruption if app is killed.

### 8. HIGH: HistoryService undo/redo commands never used in main app

- **Severity:** High (dead code)
- **Location:** `chormanager/history/service.py` entire file, `chormanager/ui/main_window.py:1457-1469`
- **Explanation:** `HistoryService` is initialized at `main_window.py:313` but `CreateSingerCommand`, `UpdateSingerCommand`, `DeleteSingerCommand` are never pushed onto the stack. The undo/redo menu items are wired but will never do anything because no commands are ever added.
- **Risk:** Undo/Redo is non-functional.

### 9. MEDIUM: Two completely separate BackupService implementations

- **Severity:** Medium
- **Location:** `chormanager/backup/service.py` (file-based backup) and `chormanager/export/backup_service.py` (ZIP-based backup)
- **Explanation:** `backup/service.py` is a simple file-copy backup. `export/backup_service.py` is a ZIP-based full application backup. They share the name `BackupService` but have completely different APIs. `main_window.py:2400` uses the ZIP one, while `main_window.py:314-317` uses the file-copy one.
- **Risk:** Confusion about which backup is active; potential data loss.

### 10. MEDIUM: `conftest.py` imports PyQt5 instead of PyQt6

- **Severity:** Medium (test reliability)
- **Location:** `tests/conftest.py:167-171`
- **Explanation:** `mock_qapp` fixture imports `from PyQt5.QtWidgets import QApplication` but the project uses PyQt6.
- **Risk:** Tests will fail if PyQt5 is not installed alongside PyQt6.

### 11. MEDIUM: `SingerDialog` integer field widget mismatch

- **Severity:** Medium
- **Location:** `chormanager/ui/main_window.py:122-125`
- **Explanation:** When `field_type == "integer"`, a `QLineEdit` is created and added to `self.inputs[name]`, but the `elif` chain immediately falls through to `if field_type == "string"` which also creates a `QLineEdit`. The integer field gets overwritten or duplicated in the form.
- **Fix:** Change `if field_type == "integer"` to `elif field_type == "integer"` (it's currently using `if` instead of `elif` after `elif field_type == "computed"`).

### 12. MEDIUM: `from_dict` return type annotation wrong on `Project`

- **Severity:** Medium
- **Location:** `chormanager/domain/models.py:222`
- **Explanation:** `Project.from_dict` has return annotation `-> "Event"` instead of `-> "Project"`.

### 13. MEDIUM: No `is_adult` column in `_SINGER_COLS`

- **Severity:** Medium
- **Location:** `chormanager/domain/repository.py:13-38`
- **Explanation:** `SingerRepository._SINGER_COLS` omits `is_adult` (filtered in `_cols`), but `database.py:192-206` adds the column via ALTER TABLE. The `is_adult` field on `Singer` is `_is_adult` (private) with a method `is_adult()`. This inconsistency means the DB column exists but is never read or written through the repository.

### 14. MEDIUM: `BesetzungRepository.set_active` references non-existent column

- **Severity:** Medium
- **Location:** `chormanager/domain/repository.py:547-552`
- **Explanation:** `set_active` tries to set `is_active = 1` on the `besetzung` table, but this column doesn't exist in the schema (`database.py:158-166`). Will crash with `sqlite3.OperationalError`.

### 15. MEDIUM: Hardcoded date in export default filename

- **Severity:** Low (maintainability)
- **Location:** `chormanager/ui/main_window.py:2542`
- **Explanation:** `default_name = f'2026-04-26-{tab_file}.{ext}'` has a hardcoded date.

### 16. MEDIUM: Double commit in `SingerRepository.update`

- **Severity:** Low
- **Location:** `chormanager/domain/repository.py:135` and `chormanager/domain/repository.py:159`
- **Explanation:** `commit()` is called at line 135 after the UPDATE, then again at line 159 after the affinity sync. The second commit is redundant and wraps unrelated affinity operations in the same transaction boundary.

---

## Dead Code Findings

| File | Symbol | Reason It Appears Dead | Confidence |
|------|--------|------------------------|:---:|
| `chormanager/history/service.py` | `CreateSingerCommand` | Never instantiated anywhere in the codebase | 100% |
| `chormanager/history/service.py` | `UpdateSingerCommand` | Never instantiated anywhere in the codebase | 100% |
| `chormanager/history/service.py` | `DeleteSingerCommand` | Never instantiated anywhere in the codebase | 100% |
| `chormanager/history/service.py` | `HistoryService` instance in MainWindow | Commands are never pushed onto it; undo/redo is non-functional | 95% |
| `chormanager/ui/main_window.py` | `_on_tab_changed` (line 1303) | Never called (no tab widget with this signal) | 90% |
| `chormanager/ui/main_window.py` | `_on_search_text_changed` (line 1321) | Never connected to any signal | 90% |
| `chormanager/ui/main_window.py` | `_on_filter_changed` (line 1325) | Never connected to any signal | 90% |
| `chormanager/ui/main_window.py` | `_export_csv` (line 1471) | Never called (replaced by `_export_tab_generic` flow) | 85% |
| `chormanager/ui/main_window.py` | `_export_pdf` (line 1501) | Never called (replaced by `_export_tab_generic` flow) | 85% |
| `chormanager/ui/main_window.py` | `_export_libreoffice` (line 1570) | Never called (replaced by `_export_tab_generic` flow) | 85% |
| `chormanager/ui/main_window.py` | `_export_singers_json` (line 2120) | Never connected to any menu/toolbar action | 85% |
| `chormanager/ui/main_window.py` | `_export_events_json` (line 2145) | Never connected to any menu/toolbar action | 85% |
| `chormanager/ui/main_window.py` | `_export_availability_json` (line 2170) | Never connected to any menu/toolbar action | 85% |
| `chormanager/ui/main_window.py` | `_export_singers_csv` (line 2197) | Never connected to any menu/toolbar action | 85% |
| `chormanager/ui/main_window.py` | `_on_tab_changed` (line 1303) | References `self.tabs` which doesn't exist (should be `self.content_stack`) | 95% |
| `chormanager/ui/main_window.py` | `_open_projekt` (line 2267) | References `self.tabs` which doesn't exist | 100% |
| `chormanager/ui/dialogs.py` | `AvailabilityDialog` (line 79) | Creates its own `Database()` connection ignoring the one passed; never used (replaced by `EventAvailabilityDialog`) | 80% |
| `chormanager/ui/dialogs.py` | `EventListDialog` (line 255) | Similar to `EventAvailabilityDialog`; may be dead | 70% |
| `chormanager/domain/models.py` | `Project.is_past` | References `self.event` and `self.date` which don't exist on `Project` | 100% |
| `chormanager/choraufstellung/main.py` | `_menu_legenda` (line 1984) | Iterates menus looking for items to do nothing | 100% |
| `chormanager/choraufstellung/main.py` | `_load_formation_data` (line 2130) | Only called from `_check_recovery` path (not dead, but narrow) | Low |

### Safe Removal Strategy

**High confidence dead code (can be deleted immediately):**

- `CreateSingerCommand`, `UpdateSingerCommand`, `DeleteSingerCommand` in `history/service.py` — remove the classes; keep `HistoryService` if undo/redo will be implemented later, or remove the entire file if not planned.
- `_on_tab_changed` in `main_window.py` — references non-existent `self.tabs`; delete entirely.
- `_open_projekt` in `main_window.py` — references non-existent `self.tabs`; delete the method and its menu connection.
- `Project.is_past` in `models.py` — delete the property (it will crash anyway).
- `_menu_legenda` in `choraufstellung/main.py` — delete the method and its call at line 1486.

**Medium confidence (review before removal):**

- `_export_csv`, `_export_pdf`, `_export_libreoffice` in `main_window.py` — grep the codebase for callers before removing; they appear superseded by `_export_tab_generic`.
- `_export_singers_json`, `_export_events_json`, `_export_availability_json`, `_export_singers_csv` — check if any menu items or toolbar actions reference these.
- `_on_search_text_changed`, `_on_filter_changed` — verify no signal connections exist.

---

## Technology Stack Usage Assessment

### PyQt6 — Grade: C-

**Strengths:**
- Proper use of signals/slots throughout
- QStackedWidget used effectively for sidebar navigation
- QToolBar provides context-sensitive actions
- QUndoStack integrated in FormationGrid for formation operations
- Drag and drop implemented for singer placement
- Two themes (light/dark) with full stylesheet support

**Weaknesses:**
- **God classes:** `MainWindow` is 2,925 lines. `dialogs.py` is 1,824 lines. `choraufstellung/main.py` is 2,180 lines. This makes maintenance extremely difficult.
- **No threading:** All database operations, PDF generation, file I/O, and LibreOffice conversions run on the main thread, blocking the UI.
- **Inline stylesheets:** ~200 lines of light theme and ~200 lines of dark theme are embedded as string literals in `main_window.py`.
- **PyQt5 fallback shim in choraufstellung/main.py:** Lines 1-75 contain a PyQt5 compatibility layer that is dead code since `pyproject.toml` requires PyQt6.
- **Duplicate dialog implementations:** `EventAvailabilityDialog` and `EventListDialog` overlap significantly. `AvailabilityDialog` creates its own `Database()` connection.
- **Manual state synchronization:** Tab views reload the entire database on every change rather than using Qt models or incremental updates.

### SQLite — Grade: C

**Strengths:**
- Foreign keys enabled via `PRAGMA foreign_keys = ON`
- All queries use parameterized statements (no SQL injection)
- Proper use of `sqlite3.Row` for dict-like row access
- Transaction context manager available in `Database` class

**Weaknesses:**
- **No migration framework:** Schema changes happen in `create_tables()` on every startup via `ALTER TABLE ... ADD COLUMN` wrapped in try/except. This is fragile and untraceable.
- **Missing indexes:** No indexes beyond primary keys. Searches by `voice_group`, `event_type`, `project_id`, etc. do full table scans.
- **N+1 query patterns:** `EventAvailabilityDialog._load_availability` calls `get_by_ids()` 4 times per singer for the summary statistics (yes, no, none, conditional counts).
- **String interpolation in DDL:** `f"ALTER TABLE singers ADD COLUMN {col} {typ}"` is used in `database.py:204`.
- **Schema inconsistencies:** `besetzung` table has no `is_active` column but `BesetzungRepository.set_active` tries to write it. `is_adult` column exists in DB but is never read/written through the repository.
- **Double commit pattern:** `SingerRepository.update()` commits twice — once after the main update, once after affinity sync.

### PyYAML — Grade: B

**Strengths:**
- `safe_load()` used consistently across all config loading
- Clean separation of concerns: `app.yaml`, `fields.yaml`, `voice_groups.yaml`
- Field definitions are data-driven and extensible
- Voice groups are configurable per installation

**Weaknesses:**
- No validation of configuration values (e.g., no check that `backup.max_backups` is a positive integer)
- No error handling for missing/invalid YAML files — the app will crash on startup if any config file is corrupt
- No configuration versioning or migration support
- `load_fields()` is called repeatedly (on every dialog open, every form render) without caching

### ReportLab — Grade: C

**Strengths:**
- Basic PDF generation works correctly
- Uses `SimpleDocTemplate` for proper page flow
- Unicode handling works (German characters render correctly)

**Weaknesses:**
- **Scattered implementation:** PDF generation logic exists in three places: `main_window.py` (lines 1501-1568), `dialogs.py` (lines 704-866), and `choraufstellung/pdf_export.py`.
- **No page overflow handling:** Tables will overflow page boundaries without proper splitting.
- **Hardcoded coordinates:** Column widths, font sizes, and spacing are hardcoded throughout.
- **Duplicated PDF code:** The availability PDF export in `dialogs.py` has duplicated logic for computing event info and filename (lines 718-777 duplicate lines 754-777).
- **No common base class or utility:** Each PDF export reimplements table styling, paragraph formatting, and document building.
- **No error handling:** If PDF generation fails (e.g., font issues, disk full), the exception propagates unhandled.

### pytest — Grade: B-

**Strengths:**
- Good test file organization: `tests/unit/`, `tests/integration/`, `tests/gui/`
- Appropriate fixtures in `conftest.py` for temporary directories, sample data, mock storage
- Core business logic tests are well-written (grid_engine, rules, commands, affinity)
- `QT_QPA_PLATFORM=offscreen` set for headless testing

**Weaknesses:**
- **PyQt5 import in conftest:** `mock_qapp` fixture imports `from PyQt5.QtWidgets` — will fail without PyQt5 installed.
- **Sparse GUI tests:** Only 2 test files in `tests/gui/` totaling ~127 lines. No tests for any dialog class.
- **Missing critical test coverage:**
  - `ExportService` — no tests
  - `BackupService` (both implementations) — no tests
  - `BackupRestoreDialog` — no tests
  - `ConfigDialog` — no tests
  - `SelbstdarstellungDialog` — no tests
  - `HistoryService` — no tests for the command classes
  - `MainWindow` — no tests
- **No integration tests for database migrations** — the schema evolution logic in `create_tables()` is untested.
- **No edge case testing** for corrupt files, permission errors, or concurrent access.

---

## Refactoring Opportunities (Ranked by Benefit)

| # | Refactor | Expected Benefit | Effort |
|---|----------|------------------|--------|
| 1 | **Extract `MainWindow` into smaller classes:** Split 2,925-line god-class into separate controller modules per domain (ProjectManager, SingerManager, EventManager, FormationManager) | High: reduces cognitive load, enables focused testing, makes navigation tractable | Large |
| 2 | **Delete or properly integrate `choraufstellung/` as standalone sub-app:** Currently it's a separate app with its own models, configs, and UI — duplicating much of the main app's functionality. Either integrate it as a module or extract it into a separate package. | High: eliminates dual codebase confusion, reduces maintenance burden | Large |
| 3 | **Remove dead commands/history integration or wire it up properly:** The undo/redo system is initialized but non-functional. Either implement it fully (push commands on every mutation) or remove it to reduce confusion. | Medium: cleaner codebase, removes false expectations | Medium |
| 4 | **Extract theme stylesheets into separate resource files or a theme service:** Move ~400 lines of CSS into dedicated `.qss` files loaded at runtime. | Medium: reduces `main_window.py` by ~400 lines, enables external theme customization | Small |
| 5 | **Unify backup services into a single `BackupService` class:** Merge `backup/service.py` and `export/backup_service.py` into one service with a clear API for both file-level and application-level backups. | Medium: eliminates confusion about which backup is active | Medium |
| 6 | **Create a proper database migration system:** Implement a version table and ordered SQL migration scripts. Replace the current `ALTER TABLE` try/except pattern. | Medium: reliable schema evolution, testable migrations | Medium |
| 7 | **Extract `PaddedDelegate` into a shared `ui/delegates.py` module:** Eliminate duplicate implementations across `projects_tab.py` and `singers_tab.py`. | Low: eliminates duplication, single source of truth | Small |
| 8 | **Move PDF export logic into a dedicated `export/pdf_export.py` service:** Consolidate scattered PDF generation code into one service with proper error handling. | Medium: separates concerns, enables unit testing of PDF logic | Medium |
| 9 | **Replace `QTableWidget` with `QAbstractTableModel` for data-heavy views:** Use Qt's model/view architecture for better performance and cleaner separation of data from presentation. | Medium: better performance for large datasets, cleaner code | Large |
| 10 | **Add type hints throughout (~40% coverage currently):** Add type annotations to all public APIs, repository methods, and dialog constructors. | Medium: catch bugs at dev time, improve IDE support | Medium |

---

## Quick Wins (< 30 minutes each)

1. **Fix `Project.__post_init__` duplicate** — delete the second definition (lines 200-206), remove the erroneous `is_past` property
2. **Fix `SingerDialog` integer field** — change `if field_type == "integer"` to `elif field_type == "integer"` at line 122
3. **Fix `Project.from_dict` return annotation** — change `-> "Event"` to `-> "Project"` at line 222
4. **Remove debug trace file writes** from `EventAvailabilityDialog._load_availability` (lines 514-536)
5. **Fix hardcoded date** in `main_window.py:2542` — replace `'2026-04-26'` with `datetime.now().strftime('%Y-%m-%d')`
6. **Remove duplicate `_on_selection_changed`** method in `MainWindow` (delete lines 1236-1243)
7. **Fix `conftest.py` PyQt5 → PyQt6** import at line 167
8. **Fix `BesetzungRepository.set_active`** — either add `is_active` column to the `besetzung` schema or remove the method entirely
9. **Remove `_on_tab_changed`** dead method (lines 1303-1308) that references non-existent `self.tabs`
10. **Fix `_open_projekt`** (lines 2267-2272) that references `self.tabs` — should be `self.content_stack`, or remove entirely since it's dead code
11. **Remove `_menu_legenda`** dead method in `choraufstellung/main.py` (line 1984) and its call at line 1486
12. **Remove `Project.is_past`** property (lines 208-215) which references non-existent `self.event` and `self.date`

---

## 1. Project Organization & Architecture

### Layer Separation

The project has a reasonable layered architecture:

```
chormanager/
├── config/          # YAML configuration files
├── data/            # Database layer (SQLite)
├── domain/          # Models and repository layer
├── core/            # Business logic services
├── history/         # Undo/redo command pattern
├── backup/          # File-level backup service
├── export/          # Export services (CSV, LibreOffice, ZIP backup)
├── ui/              # PyQt6 UI layer
│   ├── main_window.py
│   ├── dialogs.py
│   ├── export_dialog.py
│   └── views/       # Tab-based views
├── choraufstellung/ # Standalone sub-app (SEPARATE codebase)
│   ├── core/        # Grid engine, optimizer, rules
│   ├── ui/          # Grid widget, pool widget, dialogs
│   ├── singer_model.py
│   ├── storage.py
│   ├── pdf_export.py
│   └── main.py      # 2,180-line standalone main
└── tools/           # Import utilities
```

**Issues with the architecture:**

- **Two parallel codebases:** The `choraufstellung/` sub-app has its own `Singer` model (`singer_model.py`), its own `MainWindow` (2,180 lines), its own config system, and its own storage. It duplicates much of the main app's functionality and creates confusion about which code is authoritative.
- **No service layer between UI and repositories:** UI tabs directly instantiate repository objects and call database methods. A service layer would decouple business logic from both UI and persistence.
- **`dialogs.py` is a 1,824-line catch-all:** It contains `EventDialog`, `EventListDialog`, `EventAvailabilityDialog`, `ConfigDialog`, `SelbstdarstellungDialog`, `SingerSelectionDialog`, `BackupRestoreDialog`, `NewFormationDialog`, `RepertoireDialog`, and `DropZone`. These should be split into separate files.
- **`main_window.py` handles everything:** At 2,925 lines, it manages menu creation, toolbar creation, sidebar navigation, info bar, all CRUD operations, all exports, all theme switching, and all cross-tab coordination.
- **No clear feature-based organization:** The code is organized by technical layer (ui, domain, data) rather than by feature. This makes it hard to find all code related to a single feature (e.g., "availability management" touches `dialogs.py`, `events_tab.py`, `main_window.py`, `repository.py`, `database.py`).

### File and Module Names

- Most names are meaningful and consistent (e.g., `SingerRepository`, `EventDialog`, `FormationGrid`)
- The `choraufstellung/` naming is German ("choir formation") while the rest of the app uses English module names — inconsistent
- `tools/` contains only `import_singers.py` — unclear purpose without documentation

### Responsibility Separation

- **Good:** Domain models (`models.py`) are pure dataclasses. Repository classes encapsulate database access. Config loading is centralized.
- **Bad:** UI code directly manipulates database objects (e.g., `SelbstdarstellungDialog._save` executes raw SQL). Export logic is scattered across multiple files. The main window handles all cross-cutting concerns.

---

## 2. PyQt6 Usage Review

### UI Design

**Strengths:**
- Logical sidebar navigation with `QStackedWidget`
- Context toolbar updates based on active tab and selection
- Info bar provides at-a-glance status
- Proper use of `QFormLayout` for dialogs
- `QSplitter` for resizable panels

**Weaknesses:**
- Hardcoded minimum sizes (`setMinimumWidth(400)`, `setMinimumSize(600, 400)`, etc.) instead of using size policies
- Info bar uses hardcoded background colors in stylesheet instead of palette-based colors (breaks custom themes)
- Duplicate `QHeaderView::section` CSS blocks in light theme (lines 1678-1694 overlap with 1686-1694)
- Sidebar fixed width of 140px doesn't adapt to content

### Signals and Slots

**Strengths:**
- Signals properly defined with `pyqtSignal`
- No duplicate signal connections detected
- Proper use of lambda captures for parameter passing

**Weaknesses:**
- `lambda: self.singers_tab._add_singer() if hasattr(self, "singers_tab") else None` pattern used for menu actions (lines 542-552) — fragile and verbose. Should use direct method references after UI is fully initialized.
- `currentIndexChanged` connected to `_load_events` which rebuilds the entire table — could be optimized with incremental updates

### Threading

**Critical issue:** No threading is used anywhere in the application. The following operations block the main thread:

- Database queries (all repository calls)
- PDF generation (`SimpleDocTemplate.build()`)
- LibreOffice conversion (`subprocess.run` with `timeout=30`)
- File I/O (backup creation, JSON export)
- YAML config loading (on every dialog open)

**Impact:** For a choir of 100+ singers, the availability dialog will freeze during loading (N+1 queries × 4 count checks). PDF export will freeze for complex formations. LibreOffice conversion blocks for up to 30 seconds.

**Recommendation:** Use `QThread` or `QRunnable` for PDF generation, LibreOffice conversion, and bulk database operations. Use `QApplication.processEvents()` as a minimal improvement for long-running synchronous operations.

### Resource Management

- **Dialog lifecycle:** Dialogs are created with `parent=self` which is correct for memory management
- **Widget ownership:** No obvious memory leaks detected — Qt's parent-child ownership is used consistently
- **Repeated widget creation:** `EventAvailabilityDialog._load_availability` recreates all `QComboBox` widgets on every filter change instead of updating existing ones

---

## 3. SQLite Usage Review

### Connection Management

- Single connection per application instance (created in `MainWindow.__init__`)
- `Database` class supports context manager but it's never used
- `PRAGMA foreign_keys = ON` is set correctly
- Connection is closed in `closeEvent` but not in error paths

### Query Safety

**Good:** All queries use parameterized statements (`?` placeholders). No string-formatted SQL for data queries.

**Bad:** `database.py:204` uses `f"ALTER TABLE singers ADD COLUMN {col} {typ}"` for DDL. While the values are from a hardcoded list, this pattern should be avoided.

### Schema Design

**Issues:**
- `besetzung.singer_ids` stores a JSON array as TEXT — violates first normal form. A junction table would be more appropriate.
- `availability` has a composite UNIQUE constraint `(singer_id, event_id)` which is good
- Missing indexes on frequently queried columns: `events.project_id`, `events.date`, `singers.voice_group`, `availability.event_id`
- `selbstdarstellung` table has only one row (`id = 'main'`) — should be a key-value store or config entry instead

### Error Handling

- `create_tables()` uses try/except for ALTER TABLE to handle "column already exists" — acceptable pattern but fragile
- No error handling for database corruption scenarios
- No error handling for locked database (concurrent access)

### Performance

- **N+1 in availability dialog:** 4 queries per singer for summary stats
- **Repeated full-table scans:** `SingerRepository.get_all()` called in multiple places without filtering at the database level
- **No pagination:** All data loaded at once for every view

---

## 4. PyYAML Usage Review

### Safety

- `safe_load()` used consistently — no `yaml.load()` with unsafe loaders detected
- No `yaml.dump()` with `allow_pickle=True` detected

### Configuration Design

**Strengths:**
- `fields.yaml` provides a data-driven form definition system
- `voice_groups.yaml` is cleanly structured
- `app.yaml` has sensible defaults

**Weaknesses:**
- No validation of configuration values
- No default value fallbacks for required keys
- Config is re-read from disk on every call to `load_fields()`, `load_voice_groups()`, `load_app_config()`

### Robustness

- No error handling for missing config files — `FileNotFoundError` will crash the app on startup
- No error handling for invalid YAML syntax — `yaml.YAMLError` will crash the app
- No recovery behavior for corrupt configuration

---

## 5. ReportLab Usage Review

### Separation of Concerns

- PDF generation is scattered across `main_window.py`, `dialogs.py`, and `choraufstellung/pdf_export.py`
- Each location reimplements table styling, paragraph formatting, and document building
- Business logic (e.g., availability computation, singer filtering) is mixed with PDF layout code

### Robustness

- No page overflow handling — large tables will extend beyond page boundaries
- No empty data handling — if no singers exist, an empty PDF is generated
- No font management — relies on ReportLab's default Helvetica, which may not support all Unicode characters

### Layout Quality

- Hardcoded column widths (`5 * cm`, `3 * cm`, etc.)
- No multi-page support for long singer lists
- Inconsistent formatting across different export locations

---

## 6. Python Code Quality

### Readability

- **Naming:** Generally good. Domain models, repositories, and services have clear names.
- **Variable names:** Mostly clear. Some one-letter variables in `choraufstellung/main.py` (`l`, `c`, `s`, `n`, `v`, `h`, `d`, `r`, `f`, `e`, `a`, `k`, `m`, `sp`, `cen`, `ml`, `lp`, `ll`, `rp`, `rl`, `gh`, `gc`, `gc`, `sr`, `sc`, `sb`).
- **Method names:** Clear and descriptive in the main app. Compressed in `choraufstellung/main.py` (`upd_grid`, `upd_leg`, `show_cfg`, `new_f`, `open_f`, `save_f`, `save_as_f`).

### Complexity

- **Deep nesting:** `EventAvailabilityDialog._load_availability` has 5+ levels of nesting
- **Long methods:**
  - `_export_termine`: 86 lines
  - `_export_aufstellung`: 105 lines
  - `_load_availability` in `EventAvailabilityDialog`: 170 lines
  - `_setup_ui` in `MainWindow`: called from constructor, sets up entire application
- **Long classes:**
  - `MainWindow`: 2,925 lines
  - `dialogs.py` total: 1,824 lines
  - `choraufstellung/main.py`: 2,180 lines

### Maintainability

- **Repeated logic:** Export flow is duplicated 5+ times across different menu actions
- **Copy-paste patterns:** `auto_arrange_*` methods in `FormationGrid` are nearly identical (~60 lines each, 7 variants)
- **Magic strings:** Voice group names (`"Sopran 1"`, `"Alt 2"`, etc.) appear as string literals throughout the codebase instead of using constants or the `VoiceGroup` enum
- **Magic numbers:** Grid dimensions, timeouts, max counts used without named constants

### Type Safety

- Type hints present on repository methods and some domain models
- Missing type hints on:
  - Most UI methods
  - All dialog classes
  - `ExportService` methods (parameter types are vague `List[Any]`)
  - `FormationGrid` and `SingerPool` methods

### Modern Python Practices

- **Dataclasses:** Used correctly for domain models
- **pathlib:** Used in some places but `os.path` still dominates
- **Context managers:** `Database` supports it but is never used as one
- **Enums:** `VoiceGroup` enum exists in `choraufstellung/singer_model.py` but the main app uses string-based voice groups
- **`dataclasses.asdict`:** Used for model serialization — good
- **f-strings:** Used consistently — good

---

## 7. Robustness & Failure Handling

### File Operations

- **Missing files:** No error handling for missing config files on startup
- **Permission errors:** No handling for read-only database files or restricted directories
- **Corrupted files:** JSON formation files are loaded with `try/except Exception` that silently returns `None` — user gets no feedback about what went wrong

### Database Failures

- **Locked database:** No handling for `sqlite3.OperationalError: database is locked`
- **Corruption:** No integrity checks beyond foreign keys
- **Missing schema:** `create_tables()` handles this via `CREATE TABLE IF NOT EXISTS`

### User Input

- **Invalid values:** Integer fields in `SingerDialog` will silently set `None` on invalid input (line 268-270)
- **Empty required fields:** `EventDialog` doesn't validate required fields before accepting
- **Edge cases:** No validation for future dates on events, negative heights on singers, or invalid email formats

### Application Startup

- **Missing config:** App will crash if any YAML config file is missing or corrupt
- **Invalid config:** No validation of config values (e.g., negative `max_backups`)
- **Missing database:** New database is created automatically (good)
- **Missing resources:** No handling for missing voice group definitions

### Shutdown

- **Database close:** Connection is closed in `closeEvent` (good)
- **Backup on close:** `backup_before_save` is called (good)
- **Unsaved changes:** Formation sub-app checks for unsaved changes; main app does not

---

## 8. Correctness Review

### Logic Errors

1. **`Project.__post_init__` (models.py:186-206):** Duplicate method — second version overrides first, losing UUID generation.
2. **`Project.is_past` (models.py:208-215):** References `self.event` and `self.date` which don't exist on `Project`.
3. **`SingerDialog` integer handling (main_window.py:122-125):** Uses `if` instead of `elif`, causing duplicate widget creation.
4. **`_open_projekt` (main_window.py:2267-2272):** References `self.tabs` which doesn't exist.
5. **`_on_tab_changed` (main_window.py:1303-1308):** References `self.tabs` which doesn't exist.
6. **`BesetzungRepository.set_active` (repository.py:547-552):** References non-existent `is_active` column.
7. **`SingerRepository._SINGER_COLS` (repository.py:13-38):** Omits `is_adult` but the column exists in the database schema.

### Data Integrity

- **Lost updates:** Affinity sync in `SingerRepository.update` has a race condition — if two singers update their affinity simultaneously, the bidirectional sync could create inconsistencies
- **Invalid state transitions:** No validation that events can't be created with past dates, or that singers can't be added to multiple voice groups

### UI Correctness

- **Selection issues:** After loading events, the active event selection may not be restored correctly if the event list has changed
- **Refresh issues:** `_refresh_tabs` only refreshes singers and events, not projects, besetzung, or repertoire

---

## 9. Security Review

### SQLite

- All queries are parameterized — no SQL injection risk
- Foreign keys are enforced

### YAML

- `safe_load()` used consistently — no unsafe deserialization

### File Handling

- **Path traversal:** Export filenames are derived from user input (event names, singer names) without sanitization. An event named `../../etc/passwd` could cause path traversal in export paths.
- **User-controlled paths:** The config dialog allows users to set arbitrary paths for data directory and backup directory — this is expected for a desktop app but should validate paths exist and are writable.

### PDF Generation

- Singer names and event descriptions are passed directly to ReportLab paragraphs — if a singer name contains HTML/XML tags, it could be interpreted as markup. ReportLab's `Paragraph` class uses a limited HTML subset, but this should be sanitized.

### Logging

- No sensitive information logged (no passwords, no full email addresses in logs)

---

## 10. Linux Desktop Integration

### Path Handling

- **Mixed approach:** Some code uses `pathlib.Path` (config, export), some uses `os.path` (choraufstellung, dialogs). Should standardize on `pathlib`.
- **No XDG compliance:** Config and data are stored in `./data/` relative to the app directory instead of `~/.local/share/chormanager/` or `~/.config/chormanager/`. This makes the app non-portable and violates Linux filesystem conventions.

### File Permissions

- No explicit file permission management — relies on umask
- SQLite database created with default permissions

### Packaging Readiness

- `pyproject.toml` is present with proper metadata
- `run.sh` handles virtual environment creation
- No `setup.py` or `Makefile` for installation
- No `.desktop` file for desktop integration
- No icon file for the application
- No AppImage, Flatpak, or Snap packaging

### Compatibility

- Requires Python >= 3.11
- Requires PyQt6 >= 6.5.0
- No testing on different Linux distributions documented
- Hardcoded paths make it non-portable

---

## 11. Technical Debt Assessment

### Critical (Fix Immediately)

| Item | Impact |
|------|--------|
| Hardcoded absolute paths | Deployment blocker |
| `Project.__post_init__` duplicate | Data corruption risk |
| `BesetzungRepository.set_active` crash | Runtime error |
| `conftest.py` PyQt5 import | Test suite broken on PyQt6-only systems |

### High (Fix Before Release)

| Item | Impact |
|------|--------|
| Two parallel codebases (main + choraufstellung) | Maintenance nightmare |
| No database migration framework | Schema evolution impossible |
| Dead undo/redo commands | False feature expectation |
| N+1 queries in availability dialog | Performance degradation |
| Missing database connection lifecycle | Corruption on crash |

### Medium (Fix Before Major Features)

| Item | Impact |
|------|--------|
| God classes (MainWindow, dialogs) | Impossible to navigate or test |
| No threading for blocking operations | UI freezes |
| Duplicated `PaddedDelegate` | DRY violation |
| Inconsistent voice group handling (string vs enum) | Confusion and bugs |
| No test coverage for export/backup/dialogs | Regression risk |

### Low (Fix When Convenient)

| Item | Impact |
|------|--------|
| Hardcoded date in export filename | Cosmetic |
| Double commit in SingerRepository.update | Minor inefficiency |
| One-letter variable names in choraufstellung/main.py | Readability |
| Missing type hints | IDE support |

---

## Appendix A: File Line Counts

| File | Lines | Assessment |
|------|------:|------------|
| `ui/main_window.py` | 2,925 | **God class** — should be split |
| `choraufstellung/main.py` | 2,180 | **God class** — standalone sub-app |
| `ui/dialogs.py` | 1,824 | **God module** — should be split by dialog |
| `choraufstellung/ui/grid_widget.py` | 778 | Large but focused |
| `choraufstellung/core/rules.py` | 668 | Acceptable for rule definitions |
| `domain/repository.py` | 655 | Acceptable for 6 repository classes |
| `choraufstellung/ui/pool_widget.py` | 463 | Large but focused |
| `ui/views/events_tab.py` | 425 | Acceptable |
| `choraufstellung/optimizer_rules.py` | 407 | Acceptable |
| `ui/views/projects_tab.py` | 405 | Acceptable |
| `ui/views/singers_tab.py` | 390 | Acceptable |
| `tests/integration/test_storage_regression.py` | 385 | Good test coverage |
| `ui/views/choraufstellung_tab.py` | 367 | Acceptable |
| `choraufstellung/ui/print_preview.py` | 358 | Acceptable |
| `choraufstellung/chormanager_db.py` | 327 | Acceptable |
| `domain/models.py` | 324 | Acceptable |
| `tests/unit/test_arrangement_rules.py` | 329 | Good test coverage |
| `tests/unit/test_metadata_saving.py` | 283 | Good test coverage |
| `tests/unit/test_undo_commands.py` | 276 | Good test coverage |
| `choraufstellung/pdf_export.py` | 257 | Acceptable |
| `data/database.py` | 242 | Acceptable |
| All other files | < 250 each | Acceptable |

---

## Appendix B: Test Coverage Summary

| Test File | Lines | Covers |
|-----------|------:|--------|
| `test_arrangement_rules.py` | 329 | Grid arrangement rules |
| `test_metadata_saving.py` | 283 | Formation metadata persistence |
| `test_undo_commands.py` | 276 | Undo/redo command pattern |
| `test_storage_regression.py` | 385 | Storage save/load regression |
| `test_grid_engine.py` | 252 | Grid engine calculations |
| `test_storage.py` | 252 | Storage operations |
| `test_singer.py` | 228 | Singer model |
| `test_event.py` | 225 | Event model |
| `test_export.py` | 157 | Export service |
| `test_history.py` | 156 | History service |
| `test_config.py` | 92 | Configuration loading |
| `test_affinity.py` | 131 | Affinity pairing |
| `test_database.py` | 113 | Database operations |
| `test_backup.py` | 135 | Backup operations |
| `test_project.py` | 135 | Project model |
| `test_main_window.py` | 64 | Main window (minimal) |
| `test_events.py` | 63 | Events (minimal) |

**Missing test coverage:**
- `ExportService` (CSV, LibreOffice, Writer)
- `BackupService` (both implementations)
- `BackupRestoreDialog`
- `ConfigDialog`
- `SelbstdarstellungDialog`
- `SingerSelectionDialog`
- `RepertoireDialog`
- `NewFormationDialog`
- `MainWindow` (only 64 lines of tests)
- Database migrations
- PDF generation
- Theme switching
