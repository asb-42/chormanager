# AGENTS.md — chormanager/history/

## Purpose
**Undo/Redo history service**: command-based, protocol-driven.
Each domain mutation goes through a ``Command`` whose ``undo`` /
``redo`` are reversible.

## Ownership
Owned by the project. Used by MainWindow's central
``HistoryService`` (a wrapper around the command list).

## Local Contracts

* **Command pattern.** Every undoable action is a ``Command``
  with ``undo()`` and ``redo()``. New undoable actions follow
  this pattern; do not bypass it with raw mutations.
* **max_entries cap.** ``HistoryService.__init__(max_entries=100)``
  keeps the last 100 commands; older ones are dropped silently.
  Do not raise on overflow.
* **No Qt in core.** The ``Command`` Protocol is
  ``chormanager/history/service.py``-level and does not depend
  on PyQt6. ``chormanager/choraufstellung/core/commands.py``
  provides the actual implementations and is Qt-free.

## Work Guidance

* When a new tab-level action becomes undoable, add the
  command to ``core/commands.py`` first, then wire it through
  ``HistoryService`` in this folder.
* Pure Python commands can be tested in
  ``tests/unit/test_history.py``. Qt-coupled commands (e.g.
  anything that touches ``QtUndoStack``) belong in the UI test
  suite.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_history.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
