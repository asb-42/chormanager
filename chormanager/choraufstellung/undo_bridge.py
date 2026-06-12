"""Qt-aware bridge for the pure-Python :class:`core.commands.UndoStack`.

ChorAufstellung's :class:`choraufstellung.main.MainWindow` historically
used Qt's native ``QUndoStack`` / ``QUndoCommand``.  In M-2 Schritt 3
the undo logic itself was moved to a Qt-agnostic module
(``core.commands``) so it can be unit-tested headless.  This bridge
re-attaches the two Qt signals the UI cares about
(``canUndoChanged`` and ``canRedoChanged``) and exposes the same
``canUndo()`` / ``canRedo()`` / ``undo()`` / ``redo()`` / ``push()``
method names the existing call-sites already use.

The class is intentionally **not** a ``QUndoStack`` subclass — Qt's
``QUndoStack`` is tied to ``QUndoCommand``, and our commands are
plain ``core.commands.UndoCommand`` instances.  Instead, it is a thin
``QObject`` that holds a private :class:`core.commands.UndoStack` and
re-emits the change signals.

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 3.
"""
from __future__ import annotations

from typing import Optional

# We need a QObject + signals.  Try PyQt6 first, fall back to PyQt5 —
# the ChorAufstellung subshell is launched with whichever Qt is
# installed in the venv.
try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtCore import QObject, pyqtSignal

from core.commands import UndoStack, UndoCommand


class QtUndoStack(QObject):
    """``QObject`` wrapper around :class:`core.commands.UndoStack` that
    emits ``canUndoChanged`` / ``canRedoChanged`` whenever the
    underlying pure-Python stack's state changes.

    The signal names match ``QUndoStack``'s API so existing menu wiring
    (``stack.canUndoChanged.connect(...)``) keeps working unchanged.
    """

    # Emitted with no arguments whenever ``canUndo()`` flips.
    canUndoChanged = pyqtSignal()
    # Emitted with no arguments whenever ``canRedo()`` flips.
    canRedoChanged = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._stack = UndoStack()
        # Initial state is "no undo, no redo" — we only fire the
        # change signals on *transitions*, not on construction, so the
        # menu does not flash an update before any command is pushed.
        self._stack.on_can_undo_changed(self._on_can_undo_changed)
        self._stack.on_can_redo_changed(self._on_can_redo_changed)

    # -- public API mirroring QUndoStack ---------------------------------

    def push(self, command: UndoCommand) -> None:
        """Push a command onto the stack.  ``QUndoStack`` also
        auto-runs the command via ``redo()``; we do the same so the
        semantics are identical to the prior Qt-based implementation.
        """
        # Run the command first (this is what QUndoStack.push does)
        # then add it to the stack so undo/redo work in the right
        # order.
        command.redo()
        self._stack.push(command)

    def undo(self) -> bool:
        return self._stack.undo()

    def redo(self) -> bool:
        return self._stack.redo()

    def canUndo(self) -> bool:
        return self._stack.can_undo()

    def canRedo(self) -> bool:
        return self._stack.can_redo()

    def clear(self) -> None:
        self._stack.clear()

    def isClean(self) -> bool:
        return self._stack.is_clean()

    def setClean(self) -> None:
        self._stack.set_clean_state()

    def count(self) -> int:
        return self._stack.count()

    def index(self) -> int:
        return self._stack.index()

    def getCommand(self, idx: int) -> Optional[UndoCommand]:
        return self._stack.get_command(idx)

    # -- access to the underlying pure-Python stack ---------------------

    @property
    def core(self) -> UndoStack:
        """The wrapped :class:`core.commands.UndoStack` — useful for
        tests and for the few places that need the pure-Python API
        directly."""
        return self._stack

    # -- internal: signal hooks from the pure-Python stack --------------

    def _on_can_undo_changed(self, _value: bool) -> None:
        self.canUndoChanged.emit()

    def _on_can_redo_changed(self, _value: bool) -> None:
        self.canRedoChanged.emit()
