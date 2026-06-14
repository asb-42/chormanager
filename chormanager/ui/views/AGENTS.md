# AGENTS.md — chormanager/ui/views/

## Purpose
Per-tab Qt views (events, singers, projects, repertoire,
besetzung, choraufstellung). Each view is a ``QWidget`` that
hosts a ``QTableView`` and connects to the appropriate
repository.

## Ownership
Owned by the project. Views are tab-panes inside
``ChorManagerTabWidget`` (in ``chormanager/ui/main_window.py``).

## Local Contracts

* **One view per repository.** ``SingersTab`` wraps
  ``SingerRepository``; ``EventsTab`` wraps ``EventRepository``;
  etc. Do not cross-couple views.
* **TableModel + QTableView.** Views expose data through
  ``QAbstractTableModel`` subclasses (not direct
  ``QTableWidgetItem`` items, which scale poorly).
* **Selection signal contract.** Each view emits
  ``selection_changed`` via the shared ``TabSignals`` bus
  (``chormanager/ui/tab_signals.py``). New selection events
  must go through TabSignals, not through per-view pyqtSignals.

## Work Guidance

* The views are extracted from the original monolithic
  MainWindow (M-1 / M-2 refactor). When changing a view, run
  the targeted test file
  (``tests/unit/test_choraufstellung_*`` and
  ``tests/unit/test_chormanager_ui_*.py``).
* New views go here. Do not add views to the dialogs folder.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_choraufstellung_formation_grid.py \
    tests/unit/test_choraufstellung_singer_tile_pool.py \
    tests/unit/test_choraufstellung_pool_auto_shrink.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
