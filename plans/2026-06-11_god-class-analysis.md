# God Class & God Module Analysis

**Date:** 2026-06-11
**Status:** Post-refactoring (after P1-P4 fixes)

---

## Current Line Counts

| File | Before | After | Reduction | Status |
|------|-------:|------:|----------:|--------|
| `ui/main_window.py` | 2,925 | 2,193 | -732 (25%) | **Still God class** |
| `choraufstellung/main.py` | 2,180 | 2,032 | -148 (7%) | **Still God class** |
| `ui/dialogs.py` | 1,824 | 1,782 | -42 (2%) | **Still God module** |
| `choraufstellung/ui/grid_widget.py` | 778 | 778 | 0 | Large but focused |
| `choraufstellung/core/rules.py` | 668 | 668 | 0 | Acceptable |
| `domain/repository.py` | 655 | 647 | -8 (1%) | Acceptable (6 repos) |

---

## Detailed Breakdown

### 1. `ui/main_window.py` — 2,193 lines

**What it contains:**

| Section | Lines | Description |
|---------|------:|-------------|
| Imports | ~60 | PyQt6, domain, config imports |
| `get_icon()` | 20 | Icon helper function |
| `SingerDialog` | 220 | Singer CRUD dialog |
| `MainWindow.__init__` | 50 | Initialization |
| `_setup_ui` | 20 | UI setup orchestration |
| `_create_info_bar` | 80 | Info bar with project/event labels |
| `_create_menu_bar` | 280 | All menu definitions |
| `_create_tool_bar` | 5 | Empty toolbar |
| `_create_central_widget` | 130 | Sidebar + tab stack |
| `_switch_view` | 20 | Tab switching |
| `_emit_selection` | 50 | Selection propagation |
| `_update_context_toolbar` | 280 | Dynamic toolbar per tab |
| `_on_*` handlers | 100 | Event handlers |
| `_refresh_tabs` | 15 | Tab refresh |
| CRUD methods | 200 | Singer/Event/Project CRUD |
| `_set_light_theme` | 5 | Theme (extracted to .qss) |
| `_set_dark_theme` | 5 | Theme (extracted to .qss) |
| Export methods | 400 | CSV/PDF/LibreOffice/Sync exports |
| `_open_choraufstellung*` | 200 | Subprocess launch |
| `_open_backup_restore` | 30 | Backup dialog |
| `_reload_after_restore` | 50 | Post-restore reload |
| `_show_config/about` | 50 | Config/About dialogs |
| `VersionCheckDialog` | 100 | Version check dialog |
| `closeEvent` | 10 | Cleanup |

**Key problems:**
- `SingerDialog` (220 lines) should be in its own file
- `VersionCheckDialog` (100 lines) should be in its own file
- Export methods (400 lines) should be in a service
- Menu creation (280 lines) should be extracted
- Context toolbar logic (280 lines) should be extracted

### 2. `choraufstellung/main.py` — 2,032 lines

**What it contains:**

| Section | Lines | Description |
|---------|------:|-------------|
| Imports/compat | 80 | PyQt6 imports, fallback stubs |
| `DraggableListWidget` | 15 | Custom list widget |
| `DraggableTableWidget` | 25 | Custom table widget |
| `SingerTile` | 130 | Singer tile widget |
| `MoveSingerCommand` | 20 | Undo command |
| `SwapSingersCommand` | 20 | Undo command |
| `MoveGroupCommand` | 30 | Undo command |
| `FormationGrid` | 450 | Grid widget (core) |
| `SingerPool` | 130 | Pool widget |
| `AddSingerDialog` | 30 | Add singer dialog |
| `AffinityDialog` | 50 | Affinity dialog |
| `VoicingConfigDialog` | 30 | Config dialog |
| `MainWindow` | 750 | Standalone main window |
| `main()` | 25 | Entry point |

**Key problems:**
- Multiple widget classes in one file
- `MainWindow` (750 lines) duplicates main app functionality
- Dialogs mixed with widgets

### 3. `ui/dialogs.py` — 1,782 lines

**What it contains:**

| Section | Lines | Description |
|---------|------:|-------------|
| `sanitize_filename` | 15 | Helper function |
| `AvailabilityDelegate` | 25 | Custom delegate |
| `AvailabilityDialog` | 40 | Simple availability dialog |
| `EventDialog` | 100 | Event CRUD dialog |
| `EventListDialog` | 110 | Event list dialog |
| `EventAvailabilityDialog` | 350 | Complex availability manager |
| `ConfigDialog` | 130 | Config settings dialog |
| `SelbstdarstellungDialog` | 80 | Self-presentation dialog |
| `SingerSelectionDialog` | 250 | Singer selection dialog |
| `DropZone` | 35 | File drop zone |
| `BackupRestoreDialog` | 200 | Backup/restore dialog |
| `NewFormationDialog` | 80 | New formation dialog |
| `RepertoireDialog` | 110 | Repertoire CRUD dialog |

**Key problems:**
- 12 dialog classes in one file
- Each dialog should be in its own file
- `EventAvailabilityDialog` (350 lines) is particularly complex

---

## Recommended Refactoring Plan

### Phase 1: Extract Dialogs from `dialogs.py` (est. 4-6 hours)

Create individual files for each dialog:

```
chormanager/ui/dialogs/
├── __init__.py              # Export all dialogs
├── event_dialog.py          # EventDialog (100 lines)
├── event_list_dialog.py     # EventListDialog (110 lines)
├── event_availability.py    # EventAvailabilityDialog (350 lines)
├── config_dialog.py         # ConfigDialog (130 lines)
├── selbstdarstellung.py     # SelbstdarstellungDialog (80 lines)
├── singer_selection.py      # SingerSelectionDialog (250 lines)
├── backup_restore.py        # BackupRestoreDialog (200 lines)
├── new_formation.py         # NewFormationDialog (80 lines)
├── repertoire_dialog.py     # RepertoireDialog (110 lines)
├── availability.py          # AvailabilityDialog + Delegate (65 lines)
├── drop_zone.py             # DropZone (35 lines)
└── helpers.py               # sanitize_filename (15 lines)
```

### Phase 2: Extract from `main_window.py` (est. 6-8 hours)

```
chormanager/ui/
├── main_window.py           # Shell only (~500 lines)
├── singer_dialog.py         # SingerDialog (220 lines)
├── version_dialog.py        # VersionCheckDialog (100 lines)
├── menu_builder.py          # Menu creation (280 lines)
├── toolbar_builder.py       # Context toolbar logic (280 lines)
├── theme.py                 # Theme loading (10 lines)
└── export_handlers.py       # Export methods (400 lines)
```

### Phase 3: Refactor `choraufstellung/main.py` (est. 4-6 hours)

```
chormanager/choraufstellung/
├── widgets/
│   ├── __init__.py
│   ├── singer_tile.py       # SingerTile (130 lines)
│   ├── draggable_list.py    # DraggableListWidget (15 lines)
│   └── draggable_table.py   # DraggableTableWidget (25 lines)
├── dialogs/
│   ├── __init__.py
│   ├── add_singer.py        # AddSingerDialog (30 lines)
│   ├── affinity.py          # AffinityDialog (50 lines)
│   └── voicing_config.py    # VoicingConfigDialog (30 lines)
├── commands.py              # Undo commands (70 lines)
├── main_window.py           # Standalone MainWindow (750 lines)
└── main.py                  # Entry point (25 lines)
```

---

## Expected Results After Refactoring

| File | Current | Target | Reduction |
|------|-------:|-------:|----------:|
| `ui/main_window.py` | 2,193 | ~500 | -77% |
| `ui/dialogs.py` | 1,782 | ~0 (split) | -100% |
| `choraufstellung/main.py` | 2,032 | ~800 | -61% |
| **Total** | **6,007** | **~1,300** | **-78%** |

---

## Priority Assessment

| Priority | Task | Effort | Impact |
|:--------:|------|--------|--------|
| 1 | Extract dialogs from `dialogs.py` | 4-6h | High — 12 classes separated |
| 2 | Extract from `main_window.py` | 6-8h | High — God class eliminated |
| 3 | Refactor `choraufstellung/main.py` | 4-6h | Medium — cleaner plugin |
| 4 | Extract `SingerDialog` from main_window | 1h | Low — already self-contained |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Import cycles | Use lazy imports in `__init__.py` |
| Test breakage | Update imports in test files |
| Signal/slot connections | Verify all connections after move |
| PyQt6 parent-child | Ensure widget hierarchy preserved |

---

## Conclusion

The codebase has improved (reduced by ~900 lines total), but three files remain as God classes/modules:

1. **`main_window.py` (2,193 lines)** — Most critical. Contains dialogs, export logic, theme switching, and menu construction that should be separate modules.

2. **`choraufstellung/main.py` (2,032 lines)** — Second priority. Contains multiple widget classes and dialogs mixed with the main window.

3. **`dialogs.py` (1,782 lines)** — Third priority. Contains 12 dialog classes that should each be in their own file.

**Total estimated refactoring effort:** 14-20 hours for a senior developer.

**Recommendation:** Start with `dialogs.py` extraction (lowest risk, highest modularity gain), then tackle `main_window.py`.
