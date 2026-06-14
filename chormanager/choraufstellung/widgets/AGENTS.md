# AGENTS.md — chormanager/choraufstellung/widgets/

## Purpose
The **legacy** Qt widgets of ChorAufstellung: ``FormationGrid``,
``SingerPool``, ``SingerTile``, drag-and-drop helpers, context
menus. These predate the M-1 / M-2 refactor and are still the
production widgets in the stand-alone mode.

## Ownership
The widgets are coupled to the MainWindow tab event model
(``TabSignals`` in ``chormanager/ui/tab_signals.py``). They emit
singer-affinity / drag-drop signals; consumers (e.g. the
context-menu) connect to them.

## Local Contracts

* **Drag-and-drop must not break.** ``FormationGrid`` exposes
  ``dragEnterEvent`` / ``dropEvent`` / ``mousePressEvent`` etc.
  Any change to the mouse / drag pipeline must keep the round-trip
  intact (test in ``tests/unit/test_choraufstellung_draggable_widgets.py``).
* **Single-pulse search timer.** ``FormationGrid.highlight_singer``
  must reuse the timer that was created in ``__init__``
  (CC4). A new ``QTimer`` per call leaks and was the original
  bug.
* **Row-label tile cache.** ``FormationGrid.refresh_grid`` iterates
  ``self._row_labels`` rather than walking the children tree
  with ``findChildren(QLabel)`` (m5). New code must follow this
  pattern.

## Work Guidance

* The widgets are large (the file is 800+ LOC). When changing
  one, run the **whole** unit test suite afterwards, not just
  the targeted test.
* New widgets here should expose the same ``pyqtSignal``
  contract as the existing ones (``singer_removed_from_grid``,
  ``singer_edit_requested``, ``singer_affinity_requested``).
* The migration plan is to eventually move everything to
  ``chormanager/choraufstellung/ui/`` (see the A-1 sub-plan).
  Until then, this folder is the **source of truth** for
  the widgets.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_choraufstellung_formation_grid.py \
    tests/unit/test_choraufstellung_singer_tile_pool.py \
    tests/unit/test_choraufstellung_pool_auto_shrink.py \
    tests/unit/test_choraufstellung_draggable_widgets.py \
    tests/unit/test_choraufstellung_singleton_pulse_timer.py \
    tests/unit/test_choraufstellung_viewport_resize.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
