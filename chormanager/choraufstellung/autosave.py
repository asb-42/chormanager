"""ChorAufstellung :class:`AutoSaveController`.

M-2 Schritt 7: Extracted from ``choraufstellung/main.py``.  The
original code was a ``QTimer`` in ``MainWindow.__init__`` connected
to a private ``_autosave_check`` method.  Moving it into its own
class makes the timer behaviour unit-testable, keeps the
``MainWindow`` lean, and lets a future CLI / batch mode reuse the
controller with a different "window" object.

Design (a *delegate*, not a copy)
---------------------------------
The controller is intentionally tiny and dumb: it knows nothing
about singers, grids, or JSON schemas.  It asks the supplied
``window`` object for three pieces of state via small protocol
methods:

  * ``is_modified()`` -> ``bool``  -- should we save at all?
  * ``has_file()``    -> ``bool``  -- is there a file path to
                                       write the autosave next to?
  * ``build_data()``  -> ``dict``  -- what JSON snapshot should
                                       we hand to ``storage``?

The window stays the single source of truth for those flags; the
controller stays the single owner of the ``QTimer`` and the
save-decision logic.

The ``storage`` object is expected to expose
``save_autosave(data: dict) -> bool`` -- the existing
:class:`choraufstellung.storage.FormationStorage` already does.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol

from qt_compat import QObject, QTimer


# ---------------------------------------------------------------------------
# Window protocol (duck-typed so we don't import MainWindow)
# ---------------------------------------------------------------------------

class _AutoSaveWindow(Protocol):
    """Minimal protocol the controller relies on.

    Any object (real MainWindow, test double, future CLI wrapper)
    that exposes these three methods can be wrapped by
    ``AutoSaveController``.
    """

    def is_modified(self) -> bool: ...
    def has_file(self) -> bool: ...
    def build_data(self) -> Dict[str, Any]: ...


# ---------------------------------------------------------------------------
# AutoSaveController
# ---------------------------------------------------------------------------

class AutoSaveController:
    """Owns the autosave :class:`QTimer` and the save-decision logic.

    Default interval is 120 000 ms (2 minutes) -- the value the
    original ``MainWindow`` used.

    Public API
    ----------
    ``check()``
        Manually trigger the same logic the timer would.  Returns
        ``True`` if ``storage.save_autosave`` was actually called,
        ``False`` otherwise.  Used by ``closeEvent`` so a save
        happens on exit even if the timer hasn't fired yet.
    ``stop()``
        Halt the timer (used on close / app shutdown).
    ``start(interval_ms=None)``
        (Re)start the timer; optionally change the interval in
        the same call.
    """

    DEFAULT_INTERVAL_MS: int = 120_000

    def __init__(
        self,
        window: _AutoSaveWindow,
        storage: Any,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        parent: Optional[QObject] = None,
    ) -> None:
        self._window = window
        self._storage = storage
        # Parent the QTimer to the *window* when possible so its
        # lifetime matches the window's.  This is what
        # ``QTimer(self)`` did in the old ``MainWindow.__init__`` and
        # is critical for headless tests: as long as the timer has
        # a QObject parent, pytest-qt can tear down the QApplication
        # cleanly once the test is over.  An orphan QTimer would
        # keep the event loop busy forever.
        if parent is None and isinstance(window, QObject):
            parent = window
        self.timer: QTimer = QTimer(parent)
        self.timer.timeout.connect(self.check)
        self.timer.start(interval_ms)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> bool:
        """Decide whether to autosave right now and act on it.

        Returns ``True`` if a save was triggered, ``False`` if the
        controller decided to skip (because nothing was modified,
        or no file path is set).
        """
        if not self._window.is_modified():
            return False
        if not self._window.has_file():
            return False
        data = self._window.build_data()
        self._storage.save_autosave(data)
        return True

    def stop(self) -> None:
        """Halt the autosave timer.  ``check()`` still works manually."""
        self.timer.stop()

    def start(self, interval_ms: Optional[int] = None) -> None:
        """(Re)start the autosave timer.

        If ``interval_ms`` is given the new interval is applied
        first; otherwise the previously configured interval is
        reused (QTimer remembers it across ``stop``/``start``).
        """
        if interval_ms is not None:
            self.timer.setInterval(interval_ms)
        self.timer.start()
