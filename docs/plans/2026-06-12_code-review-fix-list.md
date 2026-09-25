# Code Review Fix List — 2026-06-12

Granular, actionable tasks grouped by priority category.
Each task includes: description, file(s) affected, estimated effort.

---

## Category 1: CRITICAL — Dead Code Cleanup & Bug Fixes (Quick Wins)

- [ ] **1.1** Delete unused `DraggableListWidget` from `chormanager/choraufstellung/main.py` (lines 85–98)
- [ ] **1.2** Delete duplicate `OptimizeFormationCommand` from `chormanager/choraufstellung/main.py` (lines 9–55)
- [ ] **1.3** Delete dead file `chormanager/choraufstellung/core/commands.py`
- [ ] **1.4** Delete dead file `chormanager/choraufstellung/ui/grid_widget.py` (shadows main.py's FormationGrid)
- [ ] **1.5** Delete dead file `chormanager/choraufstellung/ui/pool_widget.py` (shadows main.py's SingerPool)
- [ ] **1.6** Delete dead file `chormanager/choraufstellung/ui/optimizer_dialog.py` (shadows main.py's OptimizerDialog)
- [ ] **1.7** Fix `reload_config()` in `chormanager/config.py:213` — returns undefined `config` variable
- [ ] **1.8** Remove `ALTER TABLE repertoire RENAME COLUMN program TO project_id` migration from `chormanager/data/database.py:create_tables()`

---

## Category 2: HIGH — PyQt5/6 Standardization

- [ ] **2.1** Remove `chormanager/choraufstellung/main.py` PyQt5-to-Python6 compatibility shim (lines 27–43, the `QFrame.Panel = ...` etc. monkey-patches)
- [ ] **2.2** Remove `chormanager/choraufstellung/qt_compat.py` `exec_qt` import block (lines 5–12)
- [ ] **2.3** Update `tests/conftest.py` to use PyQt6 (if PyQt5-specific fixtures exist)
- [ ] **2.4** Remove PyQt6 references from `tests/gui/` files that currently use PyQt5 patterns
- [ ] **2.5** Ensure `tests/unit/test_event_list_dialog_dropdown_ui.py` imports from PyQt6 correctly (currently skips)
- [ ] **2.6** Verify all PyQt6 enum usage is correct (no PyQt5 aliases needed)

---

## Category 3: HIGH — ChorManager DB Loading via Repository

- [ ] **3.1** Create `chormanager/choraufstellung/services/__init__.py`
- [ ] **3.2** Create `chormanager/choraufstellung/services/chor_manager_data_service.py` with `load_singers_for_event()` using `SingerRepository` + `AvailabilityRepository`
- [ ] **3.3** Refactor `chormanager/choraufstellung/main.py:_load_from_chormanager()` to use `ChorManagerDataService` instead of raw SQLite
- [ ] **3.4** Add unit tests for `ChorManagerDataService` in `tests/unit/test_chor_manager_data_service.py`

---

## Category 4: HIGH — Unify Singer Models

- [ ] **4.1** Add `singer_id` field to `chormanager/domain/models.py:Singer` (already has `id`, keep it)
- [ ] **4.2** Add `affinity_uuid` field to `chormanager/domain/models.py:Singer` (already has it)
- [ ] **4.3** Add `to_formation_singer()` method on `domain/models.py:Singer` that returns a `choraufstellung/singer_model.py:Singer`
- [ ] **4.4** Add `from_domain_singer()` classmethod on `choraufstellung/singer_model.py:Singer`
- [ ] **4.5** Update `chormanager/choraufstellung/main.py:_load_from_chormanager()` to use the adapter
- [ ] **4.6** Add unit tests for Singer model conversion in `tests/unit/test_singer_conversion.py`
- [ ] **4.7** Remove `Singer.address` legacy field from `chormanager/domain/models.py:Singer`

---

## Category 5: MEDIUM — Unify Config Systems

- [ ] **5.1** Add `get_voice_group_color(voice_group_id, theme=None)` to `chormanager/config.py`
- [ ] **5.2** Add theme-aware caching to `chormanager/config.py` for voice group colors
- [ ] **5.3** Update `chormanager/choraufstellung/singer_model.py:voice_group_color()` to use `chormanager/config.py`
- [ ] **5.4** Update `chormanager/choraufstellung/main.py` to use `chormanager/config.py` for voice group colors
- [ ] **5.5** Mark `chormanager/choraufstellung/config.py:load_voice_groups_config()` as deprecated
- [ ] **5.6** Add tests for new `config.py:get_voice_group_color()`

---

## Category 6: MEDIUM — Move Arrangement Algorithms to core/

- [ ] **6.1** Create `chormanager/choraufstellung/core/arrangement.py`
- [ ] **6.2** Move `auto_arrange_by_height()` logic from FormationGrid to `core/arrangement.py:arrange_by_height()`
- [ ] **6.3** Move `auto_arrange_men_outer()` logic to `core/arrangement.py:arrange_men_outer()`
- [ ] **6.4** Move `auto_arrange_satb()` etc. to `core/arrangement.py`
- [ ] **6.5** Update FormationGrid methods to call core functions
- [ ] **6.6** Add unit tests for all arrangement algorithms in `tests/unit/test_arrangement.py`
- [ ] **6.7** Update main.py menu actions to use the new arrangement functions

---

## Category 7: MEDIUM — Fix Autosave Symlink

- [ ] **7.1** Update `chormanager/choraufstellung/storage.py:save_autosave()` to write `latest_autosave.json` as regular JSON instead of symlink
- [ ] **7.2** Update `chormanager/choraufstellung/storage.py:get_latest_autosave_path()` to read JSON index file
- [ ] **7.3** Update `chormanager/choraufstellung/storage.py:delete_latest_autosave()` to handle JSON index
- [ ] **7.4** Add tests for autosave without symlinks in `tests/unit/test_autosave.py`

---

## Category 8: LOW — Type Hints & Cleanup

- [ ] **8.1** Add type hints to `FormationGrid.place_singer()`, `FormationGrid.place_singer_at()`
- [ ] **8.2** Add type hints to `SingerPool.update_singers()`, `SingerPool.add_singer()`
- [ ] **8.3** Add type hints to `MainWindow._load_from_chormanager()`
- [ ] **8.4** Add type hints to `MainWindow._save_file()`
- [ ] **8.5** Remove `Singer.social_contacts_dict` if unused
- [ ] **8.6** Update `chormanager/choraufstellung/main.py` `FormationGrid` constants to use `GridConfig` dataclass

---

## Verification Checklist

After all categories are implemented:

- [ ] `python3 -m pytest tests/unit/ -q` passes (≥233 unit tests)
- [ ] `python3 -m pytest tests/integration/ -q` passes (≥21 integration tests)
- [ ] `python3 -m py_compile chormanager/choraufstellung/main.py` succeeds
- [ ] `python3 -m py_compile chormanager/config.py` succeeds
- [ ] No new PyQt5 imports in production code
- [ ] No new raw SQL in UI layer
- [ ] All dead files deleted
