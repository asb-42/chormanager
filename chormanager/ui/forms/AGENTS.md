# AGENTS.md — chormanager/ui/forms/

## Purpose
Form widgets (singer dialog form, repertoire form, ...). Forms
are the inner data-entry widgets that the dialogs
(``chormanager/ui/dialogs/``) wrap in a ``QDialogButtonBox``.

## Ownership
Owned by the project. Forms are reusable; a form can be
embedded in a dialog OR used standalone.

## Local Contracts

* **Form owns its data, dialog owns its lifecycle.** A form
  exposes ``get_data()`` / ``set_data()`` / ``validate()``;
  the dialog wraps it, owns the accept/reject buttons, and
  translates the form's data to a domain object via a
  repository.
* **Validation is the form's job.** Forms report errors via
  signals (``validation_failed = pyqtSignal(str)``) so the
  dialog can show a ``QMessageBox`` without owning the form's
  internals.

## Work Guidance

* The forms are extracted from the original monolithic
  MainWindow (M-1 / M-2 refactor). When changing a form, run
  the targeted test file
  (``tests/unit/test_chormanager_ui_dialogs_*.py``).
* Forms are usually small (< 200 LOC). Keep them simple.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/unit/test_chormanager_ui_dialogs_singer_selection.py \
    -q
```

## Child DOX Index

*(This folder is a leaf in the DOX tree. No children.)*
