"""TDD RED: Regression tests for M-2 Schritt 7 -- AutoSaveController.

The choraufstellung ``MainWindow`` currently keeps a ``QTimer`` that
fires ``_autosave_check`` every 120 000 ms (2 minutes).  That method
checks ``is_modified`` and the current file path, builds a JSON
serialisation of the current grid state, and calls
``self.storage.save_autosave(data)``.

M-2 Schritt 7 extracts this into a dedicated ``AutoSaveController``
class in ``choraufstellung/autosave.py`` so the timer logic, the
save-decision, and the JSON-building can be unit-tested in isolation
and reused by future callers (e.g. a CLI batch mode).

The controller is designed to be a *delegate*, not a copy of the
window: the window still owns the source-of-truth flags
(``is_modified``, current file path, singers list, grid), and the
controller gets three small injection points:

  * ``is_modified()`` -> bool   -- should we save at all?
  * ``has_file()``    -> bool   -- is there a file to write to?
  * ``build_data()``  -> dict   -- what data should we save?

Plus a ``storage`` object that exposes ``save_autosave(data)`` (the
existing ``choraufstellung.storage.FormationStorage`` already has it).

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 7.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from unittest.mock import MagicMock

import pytest

# conftest.py already adds chormanager/choraufstellung/ to sys.path.


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------

class TestModuleShape:
    def test_autosave_module_exists(self):
        try:
            import autosave  # noqa: F401
        except ModuleNotFoundError as exc:
            pytest.fail(f"autosave module not yet created: {exc}")

    def test_autosave_module_exports_controller(self):
        from autosave import AutoSaveController
        assert AutoSaveController is not None


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

class _FakeWindow:
    """Stand-in for ``MainWindow`` -- exposes the three injection
    points the AutoSaveController needs.

    The flags and data are mutable so the test can simulate the
    user editing the grid (is_modified becomes True, the file path
    is set, build_data returns a snapshot).
    """

    def __init__(self, *, modified=False, has_file=True, data=None):
        self._modified = modified
        self._has_file = has_file
        self._data = data if data is not None else {
            "version": "1.0",
            "rows": 4,
            "cols": 5,
            "staggered": False,
            "singers": [],
            "placed": [],
        }

    def is_modified(self) -> bool:
        return self._modified

    def has_file(self) -> bool:
        return self._has_file

    def build_data(self) -> dict:
        return self._data


# ---------------------------------------------------------------------------
# Behaviour tests
# ---------------------------------------------------------------------------

class TestAutoSaveTimer:
    def test_starts_qtimer_with_default_interval(self, qtbot):
        """The controller must start a QTimer with the 120 000 ms
        default interval that the original MainWindow used."""
        from autosave import AutoSaveController
        from qt_compat import QTimer

        storage = MagicMock()
        win = _FakeWindow(modified=True, has_file=True)
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=120_000)
        try:
            assert isinstance(ctrl.timer, QTimer), \
                "AutoSaveController must own a QTimer"
            assert ctrl.timer.isActive(), \
                "QTimer must be running right after construction"
            assert ctrl.timer.interval() == 120_000, \
                f"default interval is {ctrl.timer.interval()}, " \
                f"expected 120000"
        finally:
            ctrl.stop()

    def test_custom_interval_is_honoured(self, qtbot):
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow()
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=5_000)
        try:
            assert ctrl.timer.interval() == 5_000
        finally:
            ctrl.stop()

    def test_stop_prevents_further_saves(self, qtbot):
        """``stop()`` halts the timer; a subsequent ``check()`` call
        must still work (manual trigger) but the timer must not fire
        on its own."""
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow(modified=True, has_file=True)
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        ctrl.stop()
        assert not ctrl.timer.isActive()
        # Manual check() still works after stop().
        ctrl.check()
        storage.save_autosave.assert_called_once()


class TestAutoSaveCheck:
    def test_check_skips_when_unmodified(self, qtbot):
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow(modified=False, has_file=True)
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        try:
            ctrl.check()
            storage.save_autosave.assert_not_called()
        finally:
            ctrl.stop()

    def test_check_skips_when_no_file(self, qtbot):
        """If the user has not saved yet, autosave must not write
        anything (the recovery check later uses the autosave
        directory's mtime to decide whether to offer a recovery
        -- bogus recovery offers would be terrible UX)."""
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow(modified=True, has_file=False)
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        try:
            ctrl.check()
            storage.save_autosave.assert_not_called()
        finally:
            ctrl.stop()

    def test_check_writes_when_modified_and_has_file(self, qtbot):
        from autosave import AutoSaveController
        storage = MagicMock()
        snapshot = {"version": "1.0", "rows": 2, "cols": 3,
                    "staggered": False, "singers": [], "placed": []}
        win = _FakeWindow(modified=True, has_file=True, data=snapshot)
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        try:
            ctrl.check()
            storage.save_autosave.assert_called_once_with(snapshot)
        finally:
            ctrl.stop()

    def test_check_passes_exact_data_from_window(self, qtbot):
        """The controller must NOT modify or reformat the dict the
        window hands back -- it's the window's job to produce a
        schema-stable snapshot."""
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow(modified=True, has_file=True, data={
            "version": "1.0", "custom_field": [1, 2, 3],
        })
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        try:
            ctrl.check()
            args, _ = storage.save_autosave.call_args
            assert args[0] == {
                "version": "1.0", "custom_field": [1, 2, 3],
            }
        finally:
            ctrl.stop()


class TestAutoSaveStartStop:
    def test_start_can_resume_a_stopped_timer(self, qtbot):
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow()
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        ctrl.stop()
        assert not ctrl.timer.isActive()
        ctrl.start()
        try:
            assert ctrl.timer.isActive()
        finally:
            ctrl.stop()

    def test_start_with_new_interval(self, qtbot):
        from autosave import AutoSaveController
        storage = MagicMock()
        win = _FakeWindow()
        ctrl = AutoSaveController(window=win, storage=storage,
                                  interval_ms=60_000)
        ctrl.start(interval_ms=10_000)
        try:
            assert ctrl.timer.interval() == 10_000
        finally:
            ctrl.stop()
