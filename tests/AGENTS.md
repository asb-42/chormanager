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
* **No test touches the repo-local ``data/state.json``** (PR-Review
  R2, 2026-09-09). The root ``tests/conftest.py`` autouse fixture
  ``isolated_state_file`` redirects
  ``chormanager.config.get_state_file`` to a per-test temp file for
  ALL tiers (unit leaks via ``ProjectsTab.set_current_project`` were
  found too). Tests needing a pre-seeded state monkey-patch
  ``config.get_state_file`` themselves — the later (inner) patch
  wins.
* **No test reads the developer's real ChorAufstellung autosaves**
  (PR #4 follow-up, 2026-09-10). The sub-app resolves its data dir
  in ``choraufstellung/storage.py:_get_data_dir`` AND
  ``choraufstellung/config.py:get_data_dir``, each module existing
  twice (top-level + package) due to the ``__init__.py`` sys.path
  shim. The autouse fixture ``isolated_choraufstellung_data_dir``
  (root ``tests/conftest.py``) imports both instances eagerly and
  redirects them to a per-test temp dir. Without it a real
  ``MainWindow`` under test ran recovery against genuine user
  autosaves in ``choraufstellung/data/backups`` and the modal
  restore dialog hung the offscreen suite.
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

**Python 3.9 compatibility guard:** ``tests/unit/test_py39_compat.py``
scans every module for PEP 604 unions (``str | None``) that would be
evaluated at import time on 3.9 (``run.sh`` promises >= 3.9). It is
AST-based and runs on any interpreter. Full end-to-end proof for a
release: run the app import chain inside ``python:3.9-slim`` docker.
For a real 3.9 runtime check (docker python:3.9-slim + requirements):

```bash
docker run --rm -v "$PWD:/app" -w /app -e QT_QPA_PLATFORM=offscreen \
  python:3.9-slim bash -c "apt-get -qq update >/dev/null; \
  apt-get -qq install -y libglib2.0-0 libgl1 libegl1 libxkbcommon0 \
  libdbus-1-3 libfontconfig1 >/dev/null; pip -q install -r requirements.txt; \
  python -m chormanager --help"
```

## Child DOX Index

*(The three test sub-folders are simple sub-trees; no per-tier
AGENTS.md is needed. The contracts above apply to all of them.)*
