# Code Review Report: ChorManager

**Date:** 2026-06-13
**Reviewer:** AI Code Review
**Scope:** Full Python/PyQt6 codebase (88 Python files, ~25,000 lines)

---

## Executive Summary

| Metric | Score | Trend | Notes |
|--------|-------|-------|-------|
| **Overall Quality** | 6/10 | → | Solid domain model, good test coverage at the unit level, but massive god modules and architectural duplication |
| **Maintainability** | 4/10 | ↓ | `choraufstellung/main.py` (1907 lines) is a critical problem; two parallel codebases for configuration |
| **Robustness** | 5/10 | → | Good db error handling, but GUI freezes on PDF/saves, no QThread usage, silent failures in duplicate DB wrapper |
| **Architecture** | 5/10 | ↑ | Repository pattern is clean; however, two ChorManagerDB classes exist in parallel, and the sub-app duplicates core app config |

The codebase works and has good tests (258 unit tests passing). The domain layer (`domain/models.py`, `domain/repository.py`) is well-structured. The main risks are the 1907-line god module, duplicate implementations of the same concept (two ChorManagerDB classes, two config systems), and GUI freezes from blocking operations.

---

## Major Findings

### 1. [CRITICAL] God Module: `choraufstellung/main.py` (1907 lines)

**Location:** `chormanager/choraufstellung/main.py`
**Severity:** Critical

**Explanation:** This single file contains 7 classes: `DraggableTableWidget`, `SingerTile`, `MoveSingerCommand`, `SwapSingersCommand`, `MoveGroupCommand`, `FormationGrid` (~300 lines), `SingerPool` (~150 lines), `AddSingerDialog`, `AffinityDialog`, `VoicingConfigDialog`, and `MainWindow` (~500 lines). The `AGENTS.md` rule "main.py ≤ 750 lines" exists precisely to prevent this.

**Risk:** Any change to this file risks breaking multiple unrelated features. New developers cannot navigate it effectively. Testing is near-impossible without mocking half the file.

**Recommended fix:** Split into modules:
- `ui/grid_widget.py` → `FormationGrid` (already exists in `ui/grid_widget.py` but duplicates)
- `ui/pool_widget.py` → `SingerPool` (already exists in `ui/pool_widget.py` but duplicates)  
- `ui/dialogs.py` → All dialog classes
- `ui/commands.py` → Undo command classes
- `app/main_window.py` → `MainWindow` (ideally ≤ 500 lines)

The modular versions in `ui/grid_widget.py` and `ui/pool_widget.py` are already used by `__init__.py`; the `main.py` versions should be removed in favor of imports.

---

### 2. [CRITICAL] Duplicate ChorManagerDB Classes

**Locations:**
- `chormanager/export/chormanager_db.py` (226 lines, 80% identical)
- `chormanager/choraufstellung/chormanager_db.py` (328 lines)

**Severity:** Critical

**Explanation:** Two files provide read-only access to the same SQLite database with almost identical code. The `choraufstellung/` version has a `set_singer_affinity()` method (line 207) that opens the connection in read-only mode (`?mode=ro` on line 49), then tries to write via `self._conn.execute("UPDATE singers SET affinity_uuid = ?...")`. This will **silently fail** because the connection is read-only — no exception is raised, no error is returned.

**Risk:** Data corruption from silent failures, maintenance burden of keeping two copies in sync, confusion about which version is canonical.

**Recommended fix:** Delete `chormanager/choraufstellung/chormanager_db.py` and route all callers through `chormanager/export/chormanager_db.py`. The `ChorAufstellungIntegration` class in `__init__.py` already imports from the canonical location.

---

### 3. [HIGH] Duplicate Arrangement Algorithms (bypassed refactoring)

**Location:** `chormanager/choraufstellung/main.py:485-620` (FormationGrid class)
**Severity:** High

**Explanation:** The previous refactoring (Category 6) created `core/arrangement.py` with pure functions and updated `ui/grid_widget.py` to use them. However, `main.py:FormationGrid` still has its own **inline implementations** of `auto_arrange_by_height`, `auto_arrange_men_outer`, `auto_arrange_satb`, etc. that do NOT use `core/arrangement.py`. The `_auto_arrange_by_groups` method (line 708) is also duplicated in spirit. When the `__init__.py` re-exports `FormationGrid` from `ui/grid_widget.py`, tests use the modular version, but the actual `main.py` at runtime uses its own inline version.

**Risk:** Fixes applied to `core/arrangement.py` don't take effect in the running application. Algorithms drift between the two implementations.

**Recommended fix:** Replace all inline arrangement methods in `main.py:FormationGrid` with delegation to `core/arrangement.py`, exactly as done in `ui/grid_widget.py`.

---

### 4. [HIGH] Main Thread Blocking Operations

**Locations:** 
- `main.py:1590` — `_autosave_check()` on main thread (I/O + JSON serialization)
- `main.py:1632` — `export_pdf()` on main thread (Full PDF generation)
- `main.py:1700` — `run_optimizer()` on main thread (computation-heavy)

**Severity:** High

**Explanation:** All three operations block the Qt event loop. PDF generation via ReportLab can take multiple seconds for large formations. The optimizer runs the full arrangement algorithm synchronously. The autosave runs every 120 seconds but does JSON serialization + file I/O on the main thread.

**Risk:** GUI freezes of 1-10 seconds visible to the user, especially on larger formations or slower disks.

**Recommended fix:** Use `QThread` + `QRunnable` for:
- PDF export (most impactful — users see an export dialog then a freeze)
- Optimizer execution
- Heavy file I/O (load/save/autosave)

---

### 5. [HIGH] Two Separate Configuration Systems

**Locations:**
- `chormanager/config.py` — YAML-based (canonical, `Config/config/`)
- `chormanager/choraufstellung/config.py` — JSON-based (deprecated wrapper)

**Severity:** High

**Explanation:** The canonical `chormanager/config.py` uses YAML via `safe_load()` and `lru_cache`, while the sub-app `choraufstellung/config.py` uses JSON files. The `__init__.py` re-exports from `chorafstellung/config.py` (line 31-34), meaning callers through the `__init__.py` API get the old JSON-based config. The `load_settings()` function reads from JSON files using `os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")` instead of the canonical XDG path.

**Risk:** Theme changes and config modifications through the sub-app don't persist to the canonical YAML config. Settings get lost.

**Recommended fix:** Remove re-exports of config functions from `__init__.py` and route all callers through `chormanager.config`. The `choraufstellung/config.py` should be marked deprecated and removed in a future release.

---

### 6. [HIGH] Potential SQL Injection in Repository Layer

**Location:** `chormanager/domain/repository.py` — all `create()` and `update()` methods
**Severity:** High (but limited attack surface)

**Explanation:** All repository `create()` methods use:
```python
columns = ", ".join(kwargs.keys())
placeholders = ", ".join(["?"] * len(kwargs))
self.db.execute(f"INSERT INTO singers ({columns}) VALUES ({placeholders})", ...)
```
While `kwargs` keys aren't directly user-controlled in current usage, the keys are dynamically constructed from `**kwargs` and concatenated into SQL strings. If any caller passes a field name that matches a malicious pattern, SQL injection is possible. The `update()` methods have the same pattern.

**Risk:** A caller passing an unexpected kwarg name could manipulate the SQL structure. While the current callers are internal, future development could expose this.

**Recommended fix:** Validate `kwargs` keys against an allowlist of known columns before constructing SQL. Or switch to ORM-style column-based builders.

---

### 7. [MEDIUM] Memory Leak in FormationGrid.refresh_grid()

**Location:** `chormanager/choraufstellung/main.py:580` (`FormationGrid.refresh_grid`)
**Severity:** Medium

**Explanation:** Every call to `refresh_grid()` does:
```python
for tile in list(self.tiles.values()):
    tile.deleteLater()
self.tiles.clear()
```
Then immediately recreates all tile widgets. However, `deleteLater()` doesn't free memory synchronously — it defers to the event loop. If `refresh_grid()` is called rapidly (e.g., during drag operations), old widgets accumulate as pending-delete objects. The row label `QLabel` and cell `QFrame` widgets also accumulate (`for label in list(self.findChildren(QLabel))` — this catches ALL labels, not just row labels, and `findChildren` is expensive).

**Risk:** Visible memory growth during rapid grid operations (drag, resize, auto-arrange).

**Recommended fix:** Use `setParent(None)` + `deleteLater()` in sequence, or reuse existing tiles by updating their data/position instead of recreating them. The modular `ui/grid_widget.py` has the same issue.

---

### 8. [MEDIUM] PDF Export Color Fallback Truncates Voice Group Names

**Location:** `chormanager/choraufstellung/pdf_export.py:172,221`
```python
vg_short = vg.split()[0] if vg else ""
...
bg_color = color_map.get(vg_short, colors.white)
```

**Severity:** Medium

**Explanation:** `VOICE_COLORS` maps "Sopran", "Alt", "Tenor", "Bass". Voice groups are "Sopran 1", "Alt 2", etc. The `split()[0]` extracts "Sopran" from "Sopran 1", which happens to work. But if a new voice group like "Mezzo-Sopran" is added, `split()[0]` returns "Mezzo-Sopran" which won't match and silently falls back to `colors.white`.

**Risk:** New voice groups get no color in PDF output. Fix is simple: use the canonical `get_voice_group_color()` from config.

**Recommended fix:** Replace the hardcoded `VOICE_COLORS` with calls to `chormanager.config.get_voice_group_color()` for theme-consistent colors.

---

### 9. [MEDIUM] Event CLI Parsing Splits Date at First `-` Character

**Location:** `chormanager/__main__.py` (implied from `event_date[:10]` patterns throughout)
**Evidence:** Multiple occurrences of `event_date[:10]` (e.g., main.py:1641, 1645, 1675)
**Severity:** Medium

**Explanation:** ISO dates like "2026-06-15" are 10 chars, so `[:10]` returns the full date. But any ISO datetime like "2026-06-15T14:30:00" is truncated to "2026-06-15" which discards time. If the event system sends timestamps, the time portion is lost. This is safe for dates but fragile.

**Risk:** If event dates ever carry timezone information ("2026-06-15+02:00"), the `[:10]` could truncate incorrectly (it works for "+02:00" because hour offsets are 6 chars, so [:10] still gets the date). Low risk but fragile.

**Recommended fix:** Use `datetime.fromisoformat(date).strftime("%Y-%m-%d")` for explicit date parsing.

---

### 10. [MEDIUM] Test Gaps in Critical Paths

**Locations:**
- No tests for `pdf_export.py` (0% coverage of PDF generation)
- No tests for `services/chor_manager_data_service.py`
- No tests for `export/chormanager_db.py` (0 tests for DB bridge)
- No tests for UI dialogs (AddSingerDialog, AffinityDialog, VoicingConfigDialog)
- No tests for `_load_from_chormanager()` in main.py (entire integration path)
- No tests for `_check_recovery()` autosave recovery
- No tests for theme switching or `_apply_theme()`

**Severity:** Medium

**Explanation:** The unit tests are good (258 passing) but focus on domain logic and repositories. The integration layer (DB bridge, PDF export, ChorManager data loading) has zero coverage. If the ChorManager DB schema changes, no test catches the regression.

**Recommended fix:** Add integration tests for `export/chormanager_db.py` against a real SQLite DB. Add unit tests for `pdf_export.py` that verify output without rendering. Add tests for `services/chor_manager_data_service.py`.

---

## Dead Code Findings

| File | Symbol | Reason Dead | Confidence |
|------|--------|-------------|------------|
| `choraufstellung/chormanager_db.py` | `ChorManagerDB` | Duplicate of `export/chormanager_db.py` with a broken write method | High |
| `choraufstellung/optimizer_dialog.py` | `OptimizerDialog` | `main.py:optimizer.py` imports from `ui.optimizer_dialog` via `__init__.py`, but the `main.py` file has its own try/except fallback | Medium |
| `choraufstellung/dependencies.py` | All functions | `main.py` uses direct imports with try/except fallbacks instead of this module | High |
| `choraufstellung/core/commands.py` | `SwapSingersCommand`, `MoveGroupCommand`, `MoveSingerCommand` | `main.py` has its own duplicate `SwapSingersCommand`, `MoveGroupCommand`, `MoveSingerCommand` at lines 38-84 | High |
| `choraufstellung/config.py` | `load_voice_groups_config()` | Deprecated in favor of `chormanager.config.get_voice_group_color()` | High |
| `choraufstellung/config.py` | `get_data_dir()` | Returns `os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")` — diverges from canonical | High |
| `choraufstellung/ui/grid_widget.py` | All arrangement methods | Currently used by `__init__.py` exports but NOT used by `main.py:FormationGrid` — effectively dead for runtime | Medium |
| `config/voice_groups.yaml` | Entire file | Superseded by `config/voice_groups.json` which has theme support | High |

## Fixed (previous PRs)

| Item | Fix |
|------|-----|
| PyQt5/6 compatibility shim | Removed from `main.py` |
| `qt_compat.py` wrapper | Deleted |
| `optimizer.py`, `optimizer_rules.py` (old) | Deleted |
| `ui_components.py` | Deleted |
| Autosave symlink → JSON index | Fixed in `storage.py` |
| `to_formation_singer()` / `from_domain_singer()` | Added to both Singer models |
| `get_voice_group_color()` canonical | Added to `chormanager/config.py` |

---

## Technology Stack Usage Assessment

### PyQt6 Usage: 6/10

**Good:**
- QSplitter for resizable panels
- QRubberBand for selection
- QUndoStack for undo/redo
- QGraphicsDropShadowEffect for visual polish

**Problems:**
- **Missing QThread usage**: All file I/O, PDF generation, and computation run on the main thread (Findings #4)
- **Widget recreation instead of reuse**: `FormationGrid.refresh_grid()` destroys and recreates all tiles instead of updating in place (Finding #7)
- **Hardcoded stylesheets**: Theme application uses massive inline string stylesheets (main.py:1715-1748) instead of QSS theme files
- **No QAbstractListModel/QAbstractTableModel**: Singer pool uses raw QTableWidget with manual item management instead of model-view architecture
- **Imperative signal wiring**: `menu()` method (main.py:1179) wires all actions imperatively instead of using `Qt.qt_connect()` or builder pattern

### SQLite Usage: 7/10

**Good:**
- Parameterized queries in repositories
- Context manager for transactions
- WAL-style connection handling

**Problems:**
- Dynamic column construction in `create()` methods (Finding #6)
- Direct `commit()` calls in repositories instead of using the `transaction()` context manager
- `ON DELETE CASCADE` for availability but no cascade for affinity references (orphaned `affinity_uuid` after singer deletion)
- No explicit foreign key enforcement check on connection (the `PRAGMA foreign_keys = ON` is correct, but connection reuse across threads could drop pragma settings)

### PyYAML Usage: 8/10

**Good:**
- `safe_load()` used everywhere
- `lru_cache` for config parsing
- Default dictionaries for missing keys

**Problems:**
- No schema validation — corrupt YAML silently returns empty defaults
- No config versioning — schema changes can silently introduce broken defaults

### ReportLab Usage: 5/10

**Good:**
- `SimpleDocTemplate` with proper page sizing
- Table-based layout
- Title/subtitle info extraction

**Problems:**
- Hardcoded color mapping instead of theme-aware config (Finding #8)
- `RotatedParagraph` class reinvents text rotation (ReportLab has built-in support via `TableStyle.ROTATE`)
- No error recovery — a ReportLab import fails catastrophically
- No test coverage at all
- Single-threaded generation on main thread

### pytest Usage: 7/10

**Good:**
- 258 unit tests passing
- Clear test structure (unit/integration/gui)
- Good fixture reuse via `conftest.py`
- `off-screen` mode for Qt tests
- Deterministic test ordering within classes

**Problems:**
- **Critical gaps**: No PDF, no DB bridge, no ChorManager data service tests
- Mock storage is a hand-coded class instead of using `unittest.mock`
- `test_arrangement_rules.py` has a `pytest.skip()` test that should either be fixed or removed
- Some integration tests skip with `pytest.skip()` when dependencies aren't available instead of providing fallback fixtures
- 2 pre-existing failures in `test_metadata_saving.py` (PyQt6 mismatch in test environment)

---

## Refactoring Opportunities

Ranked by expected maintenance benefit:

1. **Split MainWindow god module** (estimate: 4-6 hours) — Extract FormationGrid, SingerPool, dialogs, commands. Use existing `ui/grid_widget.py` and `ui/pool_widget.py`. Benefit: Eliminates duplication, makes all code paths consistent, enables testing.

2. **Delete duplicate ChorManagerDB** (estimate: 1 hour) — Remove `choraufstellung/chormanager_db.py`, route all callers through canonical `export/chormanager_db.py`. Benefit: Eliminates silent write failure, removes 328 lines of duplication.

3. **Use QThread for blocking operations** (estimate: 3-4 hours) — Wrap PDF export, optimizer, and autosave in `QRunnable`. Benefit: No more GUI freezes, professional responsiveness.

4. **Remove old arrangement code from main.py** (estimate: 1 hour) — Replace inline `auto_arrange_*` with delegation to `core/arrangement.py`. Benefit: Makes algorithm fixes effective at runtime, 150 lines removed.

5. **Unify config systems** (estimate: 2-3 hours) — Remove re-exports from `__init__.py`, make `choraufstellung/config.py` a thin wrapper calling canonical config. Benefit: Single source of truth for all settings.

6. **Use Model-View architecture for SingerPool** (estimate: 3-4 hours) — Replace raw QTableWidget with QTableView + QAbstractTableModel. Benefit: Separation of data and presentation, easier to test, less code.

7. **Add PDF export tests** (estimate: 2 hours) — Write tests that construct `PDFExporter`, call `export_formation()`, verify output is valid PDF (check header bytes), verify content for known input. Benefit: Prevents regression on all PDF changes.

8. **Replace widget recreation with in-place updates** (estimate: 2 hours) — Change `FormationGrid.refresh_grid()` to update existing tile data/position instead of destroying and recreating. Benefit: Eliminates memory leak, smoother drag operations.

9. **Validate kwargs keys in repository create/update** (estimate: 30 min) — Add allowlist check for column names. Benefit: Eliminates SQL injection surface.

10. **Extract theme QSS to files** (estimate: 1 hour) — Move hardcoded stylesheet strings from `_apply_theme()` into QSS files (like the existing `ui/themes/`). Benefit: Theme editing without code changes, consistent styling.

---

## Quick Wins (< 30 minutes each)

| # | Task | File | Effort |
|---|------|------|--------|
| 1 | Fix `[singer not in sorted_singers[:idx]]` bug in main.py auto_arrange_by_height (line 636) | main.py | 5 min |
| 2 | Replace hardcoded PDF colors with `get_voice_group_color()` | pdf_export.py | 10 min |
| 3 | Remove `dependencies.py` (replace direct imports) | choraufstellung/dependencies.py | 10 min |
| 4 | Fix `test_arrangement_rules.py` skipped test (fix or remove) | tests/unit/test_arrangement_rules.py | 5 min |
| 5 | Add `skipUnless` for reportlab in pdf_export imports | pdf_export.py | 5 min |
| 6 | Remove dead `config/voice_groups.yaml` | config/voice_groups.yaml | 2 min |
| 7 | Fix `event_date[:10]` → `fromisoformat` in PDF export | main.py:1641 | 10 min |

---

## Final Verdict

### Is the codebase production-ready?

**Conditionally yes.** The application works correctly for its core use case (258 unit tests pass). The domain layer and repository pattern are well-engineered. However, there are architectural issues that make it fragile and difficult to maintain.

### What are the biggest risks?

1. **Silent data issues from the duplicate ChorManagerDB** — the `set_singer_affinity()` method silently fails on read-only connections (Critical)
2. **Algorithm drift** — fixes to `core/arrangement.py` don't apply to the runtime `main.py` (High)
3. **GUI freezes** — PDF export and optimizer block the UI (High)
4. **1907-line god module** — every change risks regression in unrelated features (Critical for maintenance velocity)

### What should be fixed before the next release?

1. Delete duplicate `choraufstellung/chormanager_db.py` (1 hour)
2. Replace inline arrangement algorithms in `main.py:FormationGrid` with `core/arrangement.py` delegation (1 hour)
3. Fix PDF color fallback to use theme-aware config (10 min)
4. Remove `dependencies.py` dead code (10 min)

### What should be addressed before major new features are added?

1. Split `choraufstellung/main.py` into separate modules (4-6 hours, highest impact improvement)
2. Unify config systems to use `chormanager/config.py` as single source of truth (2-3 hours)
3. Add QThread support for PDF export and optimizer (3-4 hours)
4. Add tests for PDF export, DB bridge, and ChorManager data service (2-3 hours)
