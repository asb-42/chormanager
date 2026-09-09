# Code Review Report — 2026-06-12

**Reviewer:** Senior-level automated code review
**Codebase:** ChorManager (chormanager)
**Stack:** Python 3.12, PyQt6, SQLite, PyYAML, ReportLab, pytest

---

## Executive Summary

| Metric | Score (1–10) | Rationale |
|--------|-------------|-----------|
| **Overall Code Quality** | 7 | Solid architecture with clear separation between core logic and UI, good test coverage, but significant issues in main.py (god module) and PyQt5/6 mixing |
| **Maintainability** | 6 | Core modules are well-tested and isolated, but main.py is 2000+ lines with too many responsibilities, duplicate Singer models, tight coupling in UI |
| **Robustness** | 7 | Good error handling in storage/DB, atomic writes, autosave/recovery, but PyQt5/6 compatibility layer is fragile, thread safety gaps |
| **Architecture** | 7 | Clear layering (core/ui/storage), but choraufstellung/main.py violates single-responsibility, two separate Singer models, config duplication |

---

## Major Findings

### 1. CRITICAL: `choraufstellung/main.py` is a God Module (2000+ lines)

**Location:** `chormanager/choraufstellung/main.py:1–2033`
**Severity:** CRITICAL

**Explanation:** This single file contains:
- `FormationGrid` widget (600+ lines) — grid rendering, drag/drop, selection, undo commands
- `SingerPool` widget (150+ lines) — singer list management
- `AddSingerDialog`, `AffinityDialog`, `VoicingConfigDialog` — multiple dialogs
- `MainWindow` class (800+ lines) — menu, file I/O, autosave, PDF export, optimizer integration, theme handling, ChorManager integration
- Business logic mixed with UI (auto-arrange algorithms, affinity logic)
- Direct SQLite access in `_load_from_chormanager()` (lines 1910–1980)

**Risk:** Impossible to test headlessly, violates AGENTS.md rule "main.py ≤ 750 lines", tight coupling prevents reuse, changes risk breaking unrelated features.

**Fix:** Split into:
- `ui/grid_widget.py` — FormationGrid + SingerTile + commands
- `ui/pool_widget.py` — SingerPool
- `ui/dialogs.py` — All dialogs
- `ui/main_window.py` — MainWindow only (wiring)
- Move auto-arrange logic to `core/arrangement.py`
- Move ChorManager loading to a service class

---

### 2. HIGH: Duplicate Singer Models (Two Different `Singer` Classes)

**Location:**
- `chormanager/choraufstellung/singer_model.py:18` (Singer with VoiceGroup enum, UUID, affinity)
- `chormanager/domain/models.py:10` (Singer with 35+ fields, flat structure, JSON social_contacts)

**Severity:** HIGH

**Explanation:** Two completely different `Singer` dataclasses with different fields, purposes, and serialization. The choraufstellung model has `voice_group: VoiceGroup`, `affinity`, `external_id`; the domain model has `full_name`, `short_name`, `birth_date`, `email`, `phone`, `address`, `guardian1`, `social_contacts`, etc.

**Risk:** Data conversion bugs, synchronization issues when loading from ChorManager DB, confusion about which model to use where.

**Fix:** Create a single canonical `Singer` model in `domain/models.py` with optional fields, or use adapter pattern with clear conversion functions.

---

### 3. HIGH: PyQt5/PyQt6 Compatibility Layer is Fragile

**Location:** `chormanager/choraufstellung/main.py:5–43`, `chormanager/choraufstellung/qt_compat.py`

**Severity:** HIGH

**Explanation:** The code uses monkey-patching to alias PyQt5 enums to PyQt6, but `pyproject.toml` declares `PyQt6>=6.5.0` only. Tests run with PyQt5 (`pytest-qt` uses PyQt5).

**Risk:** Runtime errors if enum values differ, maintenance burden, test environment mismatch, hidden bugs when Qt behavior differs.

**Fix:** Commit to PyQt6 only. Remove compatibility layer entirely. Use `QT_QPA_PLATFORM=offscreen` for headless tests.

---

### 4. HIGH: Direct SQLite Access in UI Layer

**Location:** `chormanager/choraufstellung/main.py:1910–1980` (`_load_from_chormanager`)

**Severity:** HIGH

**Explanation:** MainWindow directly opens SQLite connection, executes raw SQL with JOINs, maps rows to Singer objects. This bypasses the repository layer entirely.

**Risk:** Schema changes break UI, no transaction handling, violates layer separation, duplicates query logic.

**Fix:** Create a `ChorManagerDataService` that uses existing repositories.

---

### 5. MEDIUM: Two Separate Config Systems

**Location:**
- `chormanager/config.py` — YAML-based with `@lru_cache`
- `chormanager/choraufstellung/config.py` — JSON-based with theme-aware colors, global cache

**Severity:** MEDIUM

**Explanation:** Duplicate voice group definitions, different file formats (YAML vs JSON), different caching strategies, different paths.

**Risk:** Inconsistent voice group colors, config drift, confusion about which config to use.

**Fix:** Unify into single config system.

---

### 6. MEDIUM: Business Logic Embedded in UI Widgets

**Location:** `chormanager/choraufstellung/main.py:662–732`

**Severity:** MEDIUM

**Explanation:** Arrangement algorithms live in `FormationGrid` widget class, directly accessing `main_window.singers` via parent traversal.

**Risk:** Untestable without Qt, fragile parent-chain coupling, violates "core/ = headless logic" rule.

**Fix:** Move to `core/arrangement.py` as pure functions.

---

### 7. MEDIUM: Missing Thread Safety for Blocking Operations

**Location:** `chormanager/choraufstellung/main.py:1719–1738` (`export_pdf`)

**Severity:** MEDIUM

**Explanation:** PDF generation runs on main thread. For large choirs, `doc.build(story)` blocks UI.

**Risk:** GUI freezes during export.

**Fix:** Move PDF generation to `QRunnable`.

---

### 8. MEDIUM: Autosave Uses Symlinks (Platform Risk)

**Location:** `chormanager/choraufstellung/storage.py:136–139`

**Severity:** MEDIUM

**Explanation:** `os.symlink` requires admin rights on Windows. Fails silently on some filesystems.

**Fix:** Write `latest_autosave.json` as a regular JSON file.

---

### 9. MEDIUM: Incomplete Type Hints

**Location:** Throughout codebase

**Severity:** MEDIUM

**Explanation:** Many public methods lack type hints. Reduced IDE support, missed bugs.

**Fix:** Add type hints to all public APIs.

---

### 10. LOW: Magic Numbers in Grid Rendering

**Location:** `chormanager/choraufstellung/main.py:322–326`

**Severity:** LOW

**Explanation:** Hardcoded layout constants duplicated in `GridConfig` dataclass.

**Fix:** Use `GridConfig` consistently.

---

## Dead Code Findings

| File | Symbol | Reason | Confidence |
|------|--------|--------|------------|
| `choraufstellung/main.py` | `DraggableListWidget` (lines 85–98) | Never instantiated; `SingerPool` uses `DraggableTableWidget` | HIGH |
| `choraufstellung/main.py` | `OptimizeFormationCommand` (lines 9–55) | Duplicate of optimizer.py version | HIGH |
| `choraufstellung/core/commands.py` | Entire file | Exists but not imported anywhere | HIGH |
| `choraufstellung/ui/grid_widget.py` | Entire file | Exists but `FormationGrid` imported from main.py | HIGH |
| `choraufstellung/ui/pool_widget.py` | Entire file | Exists but `SingerPool` imported from main.py | HIGH |
| `choraufstellung/ui/optimizer_dialog.py` | Entire file | Exists but `OptimizerDialog` imported from main.py | HIGH |
| `domain/models.py` | `Singer.address` | Legacy field, marked deprecated | MEDIUM |
| `domain/models.py` | `Singer.social_contacts_dict` | Parses JSON but never called | MEDIUM |
| `data/database.py` | `ALTER TABLE repertoire RENAME COLUMN` | One-time migration, runs every startup | LOW |

---

## Technology Stack Usage Assessment

| Technology | Assessment | Issues |
|------------|------------|--------|
| **PyQt6** | ⚠️ Mixed with PyQt5 | Compatibility layer, PyQt5 in test env, monkey-patched enums |
| **SQLite** | ✅ Good | Parameterized queries, foreign keys, indexes, migrations |
| **PyYAML** | ✅ Good | `safe_load()` used, `@lru_cache`, validation defaults |
| **ReportLab** | ✅ Good | Isolated in `pdf_export.py`, handles color/bw modes, rotation |
| **pytest** | ✅ Good | 233 unit tests pass, integration tests pass |

---

## Refactoring Opportunities (Ranked by Maintenance Benefit)

1. Split `choraufstellung/main.py` into 5+ modules
2. Unify Singer models
3. Remove PyQt5/6 compatibility layer
4. Create `ChorManagerDataService` for loading event singers
5. Unify config systems
6. Move arrangement algorithms to `core/arrangement.py`
7. Add `QRunnable` for PDF export
8. Fix autosave symlink → regular JSON
9. Complete type hints on all public APIs
10. Delete dead code

---

## Quick Wins (< 30 min each)

1. Delete unused `DraggableListWidget` from main.py
2. Delete duplicate `OptimizeFormationCommand` from main.py
3. Fix `reload_config()` — returns undefined `config` variable
4. Remove `ALTER TABLE repertoire RENAME COLUMN` from `create_tables()`
5. Change autosave symlink to JSON file
6. Add type hints to key public APIs
7. Remove `Singer.address` legacy field
8. Use `GridConfig` in `FormationGrid` instead of duplicated constants
9. Delete unused `core/commands.py`
10. Delete unused `ui/grid_widget.py`, `ui/pool_widget.py`, `ui/optimizer_dialog.py`

---

## Final Verdict

**Is the codebase production-ready?**
Conditionally yes — for the ChorManager main app. The ChorAufstellung sub-app has critical architectural issues that should be fixed before relying on it for production data.

**Biggest Risks:**
1. Data loss/corruption risk from god module mixing UI, business logic, and raw SQL
2. Maintenance paralysis from 2000-line file
3. PyQt5/6 mismatch — tests on PyQt5, production on PyQt6
4. Singer model duplication causing sync bugs

**Must Fix Before Next Release:**
1. Split `choraufstellung/main.py` per AGENTS.md (≤750 lines)
2. Remove PyQt5/6 compatibility layer
3. Unify Singer models or add explicit adapter with tests
4. Move ChorManager DB loading to repository-based service

**Must Fix Before Major New Features:**
1. Unify config systems
2. Move arrangement algorithms to `core/`
3. Add threading for PDF export
4. Complete type hints
5. Clean up dead code
