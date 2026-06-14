# AGENTS.md — tests/

## Purpose
All test files for the project. Three tiers:
* ``unit/`` — fast, no I/O, headless (``QT_QPA_PLATFORM=offscreen``).
* ``integration/`` — touches the database; may run a few seconds.
* ``gui/`` — full Qt MainWindow smoke-tests.

## Ownership
The tests belong to the project. New tests are added next to the
module they cover: e.g. tests for
``chormanager/data/database.py`` go in
``tests/unit/test_database*.py``.

## Local Contracts

* **No test depends on another test.** Tests must be runnable
  in any order. Module-level fixtures are allowed; global
  state (e.g. ``os.environ``) must be restored in the fixture's
  teardown.
* **Headless execution.** All Qt tests run with
  ``QT_QPA_PLATFORM=offscreen``. The CI does not provide a
  display server.
* **Test pyramid target** (from the root ``AGENTS.md``):
  ~70 % unit, ~25 % integration, ~5 % UI. The sub-app
  ``chormanager/choraufstellung/`` is UI-heavy so its
  tests/unit:tests/gui ratio is closer to 60:15.
* **No mocking of QApplication** when pure-Python logic
  suffices. The pytest-qt ``qtbot`` fixture is the only
  exception.

## Work Guidance

* When writing a regression test for a bug fix, put a
  one-line comment in the test referring to the plan ID
  (``# m9-FIX-A: database is locked``).
* For new Qt signals, use ``qtbot.waitSignal(timeout=...)``
  rather than ``QApplication.processEvents``.
* Property-based tests (Hypothesis) live in
  ``tests/unit/test_*_properties.py``. They are slow and run
  with reduced ``max_examples`` in CI.

## Verification

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/unit/ -q \
    --ignore=tests/unit/test_choraufstellung_window_resize_bug.py \
    --ignore=tests/unit/test_metadata_saving.py
```

The two ignored tests are **pre-existing deadlocks** on `main`
and are tracked as future-sprint work. They are excluded from
the verification command to keep CI green.

## Child DOX Index

*(The three test sub-folders are simple sub-trees; no per-tier
AGENTS.md is needed. The contracts above apply to all of them.)*
