# Fix Plan: 2026-06-13 Code Review

This plan is derived from the code review report at `docs/reports/2026-06-13_code-review.md`.
Items are grouped by category and ordered by priority within each category.

---

## Category C: Critical

### C1 — Delete duplicate ChorManagerDB class
- **Files:** `chormanager/choraufstellung/chormanager_db.py` (delete), `chormanager/export/chormanager_db.py` (keep)
- **Work:**
  - [ ] Delete `chormanager/choraufstellung/chormanager_db.py`
  - [ ] Update `chormanager/choraufstellung/__init__.py` to import from canonical location
  - [ ] Update `chormanager/choraufstellung/main.py` if it imports from the deleted file
  - [ ] Verify `ChorAufstellungIntegration.__init__.py:65-79` still works (uses `chormanager.export.chormanager_db`)
  - [ ] Run `pytest tests/ -q --ignore=tests/unit/test_event_list_dialog_dropdown.py` — expect 258 passed
- **Risk:** The `choraufstellung/chormanager_db.py` has `set_singer_affinity()` which silently fails on read-only connections. Deletion eliminates this bug.

### C2 — Align `main.py:FormationGrid` arrangement algorithms with `core/arrangement.py`
- **Files:** `chormanager/choraufstellung/main.py`
- **Work:**
  - [ ] Replace `FormationGrid.auto_arrange_by_height()` (main.py:485) with delegation to `core.arrangement.arrange_by_height()`
  - [ ] Replace `FormationGrid.auto_arrange_men_outer()` (main.py:510) with delegation to `core.arrangement.arrange_men_outer()`
  - [ ] Replace `FormationGrid.auto_arrange_satb()` (main.py:556) with delegation to `core.arrangement.arrange_satb()`
  - [ ] Replace `FormationGrid.auto_arrange_sbta()` (main.py:588) with delegation to `core.arrangement.arrange_sbta()`
  - [ ] Replace `FormationGrid.auto_arrange_s1s2b2b1t2t1a2a1()` (main.py:620) with delegation
  - [ ] Replace `FormationGrid._auto_arrange_by_groups()` (main.py:708) — used by SATB/SBTA/other — with core delegation
  - [ ] Update `auto_arrange_by_height` to not walk up to `main_window.singers` — use `self.singers` directly
  - [ ] Run `pytest tests/ -q` — expect no regressions
- **Verification:**
  - [ ] After fix, both `ui/grid_widget.py` and `main.py` delegate to the same `core/arrangement.py` functions
  - [ ] No duplicate arrangement logic remains

---

## Category H: High

### H1 — Add QThread for PDF export
- **Files:** `chormanager/choraufstellung/main.py`, `chormanager/choraufstellung/pdf_export.py`
- **Work:**
  - [ ] Create `PDFExportWorker(QRunnable)` in `pdf_export.py` or a new `pdf_export_worker.py`
  - [ ] Worker takes all export parameters and returns (success, path_or_error)
  - [ ] Connect `QThreadPool.globalInstance().start(worker)` in `MainWindow.export_pdf()`
  - [ ] Show progress/result via signals or callback on main thread
  - [ ] Disable export button during generation to prevent double-trigger
  - [ ] Run `pytest tests/ -q` — expect no regressions

### H2 — Unify config systems
- **Files:** `chormanager/choraufstellung/config.py`, `chormanager/choraufstellung/__init__.py`, `chormanager/choraufstellung/main.py`
- **Work:**
  - [ ] In `__init__.py`, remove re-exports from `choraufstellung.config` (lines 31-38)
  - [ ] In `__init__.py`, add re-exports from `chormanager.config`
  - [ ] Update `main.py` imports: replace `from config import ...` with `from chormanager.config import ...`
  - [ ] Update `main.py:try/except ImportError` fallback to use `chormanager.config` functions
  - [ ] Verify `load_settings()`, `save_settings()`, `get_voice_group_color()` work correctly
  - [ ] Run `pytest tests/ -q` — expect no regressions

### H3 — Fix memory leak in FormationGrid.refresh_grid()
- **Files:** `chormanager/choraufstellung/main.py`, `chormanager/choraufstellung/ui/grid_widget.py`
- **Work:**
  - [ ] In both `FormationGrid.refresh_grid()` implementations:
    - [ ] Replace `tile.deleteLater()` + `self.tiles.clear()` loop with: disconnect signals, set parent None, then deleteLater
    - [ ] Don't delete/recreate cell frames — mark/unmark them via visibility or style
    - [ ] Don't use `findChildren(QLabel)` for row labels — maintain a separate list
  - [ ] Run `pytest tests/ -q` — expect no regressions

### H4 — Fix PDF color mapping to use theme-aware config
- **Files:** `chormanager/choraufstellung/pdf_export.py`
- **Work:**
  - [ ] Remove hardcoded `VOICE_COLORS` class variable
  - [ ] In `_create_standard_grid()` and `_create_staggered_grid()`, replace `color_map.get(vg_short, colors.white)` with `get_voice_group_color(vg_short)`
  - [ ] Import `get_voice_group_color` from `chormanager.config` (with try/except fallback)
  - [ ] Run `pytest tests/ -q` — expect no regressions

### H5 — Fix missing QThread for autosave
- **Files:** `chormanager/choraufstellung/main.py`
- **Work:**
  - [ ] Create `AutosaveWorker(QRunnable)` that serializes + saves
  - [ ] Replace synchronous `_autosave_check()` with thread pool submission
  - [ ] Run `pytest tests/ -q` — expect no regressions

### H6 — Fix missing QThread for optimizer
- **Files:** `chormanager/choraufstellung/main.py`, `chormanager/choraufstellung/core/optimizer.py`
- **Work:**
  - [ ] Create `OptimizerWorker(QRunnable)` that runs `FormationOptimizer.run()`
  - [ ] Update `MainWindow.run_optimizer()` to use thread pool
  - [ ] Add progress indicator or disable UI during optimization
  - [ ] Run `pytest tests/ -q` — expect no regressions

### H7 — Validate kwargs keys in repository create/update
- **Files:** `chormanager/domain/repository.py`
- **Work:**
  - [ ] Add class-level `ALLOWED_COLUMNS` set to each repository
  - [ ] In `create()` and `update()`, filter kwargs keys against `ALLOWED_COLUMNS`
  - [ ] Raise `ValueError` for unknown columns (or silently drop)
  - [ ] Run `pytest tests/ -q` — expect no regressions

---

## Category M: Medium

### M1 — Split MainWindow god module
- **Files:** `chormanager/choraufstellung/main.py` (1907 lines)
- **Work:**
  - [ ] Remove duplicate `FormationGrid` class — use `ui/grid_widget.py:FormationGrid`
  - [ ] Remove duplicate `SingerPool` class — use `ui/pool_widget.py:SingerPool`
  - [ ] Extract `AddSingerDialog` → `ui/dialogs.py`
  - [ ] Extract `AffinityDialog` → `ui/dialogs.py`
  - [ ] Extract `VoicingConfigDialog` → `ui/dialogs.py`
  - [ ] Extract `DraggableTableWidget` → `ui/pool_widget.py` (already exists there? Check)
  - [ ] Extract `SingerTile` class → `ui/grid_widget.py`
  - [ ] Extract undo commands → `core/commands.py` (remove duplicates)
  - [ ] Ensure `MainWindow` only imports from these modules
  - [ ] Run `pytest tests/ -q` — expect no regressions
- **Target:** `main.py` ≤ 750 lines

### M2 — Add PDF export tests
- **Files:** `tests/unit/test_pdf_export.py` (new)
- **Work:**
  - [ ] Create `test_pdf_export_returns_true_for_valid_data`
  - [ ] Create `test_pdf_export_creates_file_with_expected_header` (check `%PDF-1.4` magic bytes)
  - [ ] Create `test_pdf_export_handles_empty_singers`
  - [ ] Create `test_pdf_export_handles_staggered_grid`
  - [ ] Create `test_pdf_export_handles_color_and_bw_modes`
  - [ ] Create `test_pdf_export_handles_rotated_text`
  - [ ] Run `pytest tests/unit/test_pdf_export.py -v` — expect all passed
  - [ ] Run `pytest tests/ -q` — expect no regressions

### M3 — Add tests for chor_manager_data_service
- **Files:** `tests/unit/test_chor_manager_data_service.py` (new)
- **Work:**
  - [ ] Create `test_load_singers_from_event_data_file_valid_json`
  - [ ] Create `test_load_singers_from_event_data_file_missing_file_returns_none`
  - [ ] Create `test_load_singers_from_event_data_file_invalid_json_returns_none`
  - [ ] Create `test_load_singers_from_db_valid_path`
  - [ ] Create `test_load_singers_from_db_nonexistent_path_returns_none`
  - [ ] Create `test_parse_singer_from_db_row` (verify fields mapped correctly)
  - [ ] Run `pytest tests/unit/test_chor_manager_data_service.py -v` — expect all passed

### M4 — Replace hardcoded event_date[:10] with fromisoformat
- **Files:** `chormanager/choraufstellung/main.py:1641,1645,1675`, `chormanager/choraufstellung/main.py:1586`
- **Work:**
  - [ ] Replace all `event_date[:10]` with `datetime.fromisoformat(event_date).strftime("%Y-%m-%d")`
  - [ ] Wrap in try/except with fallback to original value
  - [ ] Run `pytest tests/ -q` — expect no regressions

### M5 — Extract theme QSS to .qss files
- **Files:** `chormanager/choraufstellung/main.py:1715-1748`
- **Work:**
  - [ ] Move hardcoded dark stylesheet string to `chormanager/ui/themes/dark.qss`
  - [ ] Move hardcoded light stylesheet string to `chormanager/ui/themes/light.qss`
  - [ ] In `_apply_theme()`, load QSS from file
  - [ ] Fall back to inline strings if file not found
  - [ ] Run `pytest tests/ -q` — expect no regressions

---

## Category L: Low

### L1 — Remove dead code
- **Files:**
  - [ ] Delete `chormanager/choraufstellung/dependencies.py`
  - [ ] Delete `config/voice_groups.yaml` (superseded by voice_groups.json)
  - [ ] Remove `dependencies` import from any remaining callers
- **Verification:** `python3 -m py_compile chormanager/**/*.py` (check all files compile)

### L2 — Fix/remove skipped test in test_arrangement_rules.py
- **File:** `tests/unit/test_arrangement_rules.py`
- **Work:**
  - [ ] Either implement `test_cost_function_compute_cost_sum` or remove it
  - [ ] Run `pytest tests/unit/test_arrangement_rules.py -v` — expect 0 skipped

### L3 — Add skipUnless for reportlab in pdf_export
- **File:** `chormanager/choraufstellung/pdf_export.py`
- **Work:**
  - [ ] Move `from reportlab.lib import colors` etc into lazy import or add try/except
  - [ ] Make `PDFExporter` raise `ImportError` at construction time rather than module load time
  - [ ] Update `main.py` import fallback to catch this

### L4 — Verify all integration tests pass
- **Files:** `tests/integration/`
- **Work:**
  - [ ] Run `python3 -m pytest tests/integration/ -v --tb=short`
  - [ ] Fix any failures
  - [ ] Ensure `test_storage_corruption_handling` tests don't skip (they skip when dependencies not available)

### L5 — Run full test suite and document expectations
- **Work:**
  - [ ] Run `python3 -m pytest tests/ -q --ignore=tests/unit/test_event_list_dialog_dropdown.py 2>&1 | tee /tmp/test_output.txt`
  - [ ] Document known failures (currently 2 pre-existing in test_metadata_saving.py)
  - [ ] Check all tests deterministic

---

## Summary

| Priority | Items | Estimated Effort |
|----------|-------|-----------------|
| Critical | 2 | 2-3 hours |
| High | 7 | 8-12 hours |
| Medium | 5 | 10-14 hours |
| Low | 5 | 2-3 hours |
| **Total** | **19** | **22-32 hours** |

## Commit Strategy

1. Commit C1 + C2 together: `fix: align arrangement algorithms and remove duplicate DB class`
2. Commit H1 + H5 + H6 together: `feat: add QThread workers for PDF/optimizer/autosave`
3. Commit H2: `refactor: unify config systems`
4. Commit H3: `fix: memory leak in FormationGrid.refresh_grid()`
5. Commit H4: `fix: PDF color mapping use theme-aware config`
6. Commit M1 separately (largest refactor): `refactor: split main.py into modules`
7. Commit M2 + M3 together: `test: add PDF export and data service tests`
8. Remaining items as small individual commits
