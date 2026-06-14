# AGENTS.md — chormanager/ui/dialogs/

## Purpose
Per-domain Qt dialogs (event, singer, repertoire, project,
selbstdarstellung, backup-restore, ...). Each dialog is a thin
wrapper around a form (``chormanager/ui/forms/``) plus a
``QDialogButtonBox``.

## Ownership
Owned by the project. The dialogs are stateless and survive
config changes via ``QSettings``.

## Local Contracts

* **Each dialog has a focused factory.** ``EventDialog``
  accepts a ``db`` and (optionally) an event id; on accept it
  commits via the appropriate repository. Do not couple
  dialogs to the MainWindow.
* **Validation at the boundary.** All inputs are validated
  before ``accept()`` runs; bad input must show a
  ``QMessageBox.warning`` and keep the dialog open.
* **No background work in dialogs.** Any long-running operation
  uses the ``SubprocessRunner`` (M-1) or a ``QThread`` worker
  (C-3). Dialogs never block their own event loop.

## Work Guidance

* The dialogs are extracted from the original monolithic
  MainWindow (M-1 / M-2 refactor). When changing a dialog, run
  the targeted test file
  (``tests/unit/test_chormanager_ui_dialogs_*.py``) and the
  relevant form test.
* Adding a new dialog: add the file, add a test, add a menu
  entry in MainWindow.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_chormanager_ui_dialogs_*.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
