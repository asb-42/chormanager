"""TDD RED: Regression tests for M-2 Schritt 3 — Undo-Commands in main.py.

The ACTIVE ``chormanager/choraufstellung/main.py`` still subclasses
``QUndoCommand`` directly and uses ``QUndoStack`` (Qt's native undo
framework).  This test module pins down the contract for replacing those
with the pure-Python ``core.commands.UndoStack`` / ``UndoCommand`` plus a
thin Qt-signal bridge.

It also documents and pins the (currently buggy) ``on_can_undo_changed``
and ``on_can_redo_changed`` callbacks of ``core.commands.UndoStack``.

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 3.
"""
from __future__ import annotations

from typing import List
import pytest

# Pure-Python implementation under test (already exists from partial
# migration in earlier session).
from core.commands import (
    UndoStack,
    UndoCommand,
    MoveSingerCommand,
    SwapSingersCommand,
    MoveGroupCommand,
    CommandResult,
)


# ---------------------------------------------------------------------------
# Test fixtures & helpers
# ---------------------------------------------------------------------------

class MockSinger:
    """Minimal stand-in for ``singer_model.Singer``."""

    def __init__(self, sid: str, row: int = -1, col: int = -1) -> None:
        self.singer_id = sid
        self.row = row
        self.col = col


def _make_get_singer(singers: dict) -> "callable":
    return lambda sid: singers.get(sid)


def _make_get_all(singers: dict) -> "callable":
    return lambda: list(singers.values())


# ---------------------------------------------------------------------------
# M-2 Schritt 3.1: UndoStack callbacks must FIRE on state change
# ---------------------------------------------------------------------------

class TestUndoStackCanUndoCallbackFires:
    """The pure-Python UndoStack exposes ``on_can_undo_changed`` / ...
    ``on_can_redo_changed`` setters.  Those callbacks MUST actually be
    invoked when the state changes — currently they are assigned but
    never called (bug in core/commands.py:202-206)."""

    def test_push_fires_can_undo_callback_when_first_command_pushed(self):
        stack = UndoStack()
        calls: List[bool] = []
        stack.on_can_undo_changed(lambda v: calls.append(v))

        singer = MockSinger("s1", 0, 0)
        cmd = MoveSingerCommand(
            "s1", 0, 0, 1, 1,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        stack.push(cmd)
        # Callback should have been called at least once.
        assert calls, "on_can_undo_changed callback was never fired on push"
        # The latest value must reflect that undo is now possible.
        assert calls[-1] is True

    def test_undo_fires_can_undo_callback_to_false(self):
        stack = UndoStack()
        singer = MockSinger("s1", 0, 0)
        cmd = MoveSingerCommand(
            "s1", 0, 0, 1, 1,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        stack.push(cmd)
        calls: List[bool] = []
        stack.on_can_undo_changed(lambda v: calls.append(v))
        stack.undo()
        # Callback should have fired with False (stack is now empty).
        assert calls, "on_can_undo_changed callback never fired on undo"
        assert calls[-1] is False

    def test_redo_fires_can_redo_callback(self):
        stack = UndoStack()
        singer = MockSinger("s1", 0, 0)
        cmd = MoveSingerCommand(
            "s1", 0, 0, 1, 1,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        stack.push(cmd)
        stack.undo()
        calls: List[bool] = []
        stack.on_can_redo_changed(lambda v: calls.append(v))
        stack.redo()
        assert calls, "on_can_redo_changed callback never fired on redo"
        assert calls[-1] is False  # nothing more to redo

    def test_clear_fires_both_callbacks(self):
        """Push two commands, undo once (so redo is possible), then
        clear — both callbacks must fire because both axes flip from
        True to False."""
        stack = UndoStack()
        singer = MockSinger("s1", 0, 0)
        cmd1 = MoveSingerCommand(
            "s1", 0, 0, 1, 1,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        cmd2 = MoveSingerCommand(
            "s1", 0, 0, 2, 2,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        stack.push(cmd1)
        stack.push(cmd2)
        # Undo once: can_undo=True (cmd1), can_redo=True (cmd2).
        stack.undo()
        undo_calls: List[bool] = []
        redo_calls: List[bool] = []
        stack.on_can_undo_changed(lambda v: undo_calls.append(v))
        stack.on_can_redo_changed(lambda v: redo_calls.append(v))
        stack.clear()
        # Both axes flip from True to False.
        assert undo_calls, "clear() did not fire on_can_undo_changed"
        assert redo_calls, "clear() did not fire on_can_redo_changed"
        assert undo_calls[-1] is False
        assert redo_calls[-1] is False


# ---------------------------------------------------------------------------
# M-2 Schritt 3.2: Qt signal bridge
# ---------------------------------------------------------------------------

class TestQtUndoStackBridge:
    """A thin Qt-aware wrapper around ``UndoStack`` must emit the same
    ``canUndoChanged`` / ``canRedoChanged`` signals that ``QUndoStack``
    emits, so the MainWindow can drive menu actions with the existing
    ``.setEnabled()`` pattern.

    NOTE: The bridge module lives at
    ``chormanager/choraufstellung/undo_bridge.py``.  The root test
    conftest puts the choraufstellung directory on ``sys.path`` so the
    module is importable as the top-level name ``undo_bridge`` from
    tests run with the project rootdir (matching the existing
    ``from core.commands import …`` pattern in
    ``test_undo_commands.py``)."""

    def test_bridge_module_exists(self):
        # Lazy import so an ImportError is reported per-test, not at
        # collection time.
        try:
            from undo_bridge import QtUndoStack  # noqa: F401
        except ModuleNotFoundError as exc:
            pytest.fail(
                f"undo_bridge.QtUndoStack not yet implemented: {exc}"
            )

    def test_bridge_subclasses_qobject(self):
        from PyQt6.QtCore import QObject
        from undo_bridge import QtUndoStack
        assert issubclass(QtUndoStack, QObject)

    def test_bridge_exposes_can_undo_can_redo(self, qtbot):
        from undo_bridge import QtUndoStack
        stack = QtUndoStack()
        assert stack.canUndo() is False
        assert stack.canRedo() is False

    def test_bridge_emits_can_undo_changed_on_push(self, qtbot):
        from undo_bridge import QtUndoStack
        stack = QtUndoStack()
        with qtbot.waitSignal(stack.canUndoChanged, timeout=500):
            singer = MockSinger("s1", 0, 0)
            cmd = MoveSingerCommand(
                "s1", 0, 0, 1, 1,
                _make_get_singer({"s1": singer}),
                lambda: None,
            )
            stack.push(cmd)
        assert stack.canUndo() is True

    def test_bridge_emits_can_redo_changed_on_undo(self, qtbot):
        from undo_bridge import QtUndoStack
        stack = QtUndoStack()
        singer = MockSinger("s1", 0, 0)
        cmd = MoveSingerCommand(
            "s1", 0, 0, 1, 1,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        stack.push(cmd)
        with qtbot.waitSignal(stack.canRedoChanged, timeout=500):
            stack.undo()
        assert stack.canRedo() is True

    def test_bridge_undo_and_redo_round_trip(self):
        from undo_bridge import QtUndoStack
        stack = QtUndoStack()
        singer = MockSinger("s1", 0, 0)
        cmd = MoveSingerCommand(
            "s1", 0, 0, 1, 1,
            _make_get_singer({"s1": singer}),
            lambda: None,
        )
        stack.push(cmd)
        assert stack.canUndo() is True
        assert stack.canRedo() is False
        assert stack.undo() is True
        assert stack.canUndo() is False
        assert stack.canRedo() is True
        assert stack.redo() is True
        assert singer.row == 1 and singer.col == 1


# ---------------------------------------------------------------------------
# M-2 Schritt 3.3: main.py backward-compat re-exports
# ---------------------------------------------------------------------------

class TestMainPyReExportsCoreCommands:
    """``main.py`` must continue to expose ``MoveSingerCommand``,
    ``SwapSingersCommand`` and ``MoveGroupCommand`` at module level for
    any external code (or the choraufstellung subshell) that still
    references them via ``from choraufstellung.main import ...``."""

    def test_main_module_exposes_move_singer_command(self):
        import sys
        # The subshell launches main.py as __main__; under pytest the
        # module is importable as choraufstellung.main.
        try:
            from choraufstellung import main as m
        except ImportError:
            pytest.skip("choraufstellung.main not on sys.path in this env")
        assert hasattr(m, "MoveSingerCommand")
        assert hasattr(m, "SwapSingersCommand")
        assert hasattr(m, "MoveGroupCommand")

    def test_main_move_singer_command_is_core_class(self):
        try:
            from choraufstellung import main as m
        except ImportError:
            pytest.skip("choraufstellung.main not on sys.path in this env")
        from core.commands import MoveSingerCommand as Core
        assert m.MoveSingerCommand is Core

    def test_main_swap_singers_command_is_core_class(self):
        try:
            from choraufstellung import main as m
        except ImportError:
            pytest.skip("choraufstellung.main not on sys.path in this env")
        from core.commands import SwapSingersCommand as Core
        assert m.SwapSingersCommand is Core

    def test_main_move_group_command_is_core_class(self):
        try:
            from choraufstellung import main as m
        except ImportError:
            pytest.skip("choraufstellung.main not on sys.path in this env")
        from core.commands import MoveGroupCommand as Core
        assert m.MoveGroupCommand is Core
