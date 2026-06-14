"""Recovery-Controller for ChorAufstellung (M-2 Schritt 11).

Encapsulates the autosave-recovery flow that was previously inlined in
:meth:`MainWindow._check_recovery` (Z. 697–717 in the legacy main.py).

The controller:

1. Asks :class:`FormationStorage` for the latest autosave path.
2. Compares its mtime to ``host.last_manual_save_mtime``; skips when
   the autosave is missing or not newer than the manual save.
3. Shows a "Wiederherstellen?" question (only when a Qt event loop
   is running — the dialog call is mocked in unit tests).
4. On "Yes", calls back into ``host._load_formation_data`` and
   marks the formation as modified.

Design
------
* **Lazy-Qt:** :class:`QMessageBox` is looked up via the module-level
  ``QMessageBox`` handle so tests can monkey-patch it.
* **Pure-Python decision:** the "should we ask?" logic does not
  touch Qt, so it is unit-tested with a fake storage and a fake host.
* **No exceptions:** any failure inside ``storage.load_formation``
  results in a ``False`` return value; the host is never left in
  a half-restored state.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    pass


# Module-level handle so tests can monkey-patch the dialog class.
QMessageBox: Any = None


def _resolve_qmessagebox() -> Any:
    """Lazy lookup of :class:`QMessageBox` (cached in module globals)."""
    global QMessageBox
    if QMessageBox is None:
        from PyQt6.QtWidgets import QMessageBox as _QMB  # type: ignore
        QMessageBox = _QMB
    return QMessageBox


class RecoveryController:
    """Orchestrates the autosave-recovery prompt."""

    DIALOG_TITLE: str = "Wiederherstellen"
    DIALOG_TEXT: str = (
        "Es wurde eine automatisch gespeicherte Aufstellung gefunden, "
        "die neuer ist als Ihre letzte manuelle Speicherung.\n\n"
        "Möchten Sie die automatisch gespeicherte Version wiederherstellen?\n"
        "(Ihre manuell gespeicherte Version bleibt erhalten.)"
    )

    def __init__(self, storage: Any, host: Any) -> None:
        """Store the storage backend and the host (MainWindow)."""
        self._storage = storage
        self._host = host

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def check(self) -> bool:
        """Run the recovery flow.

        Returns ``True`` if the autosave was restored, ``False`` when
        no autosave exists, when it is not newer than the manual save,
        or when the user declined the prompt.
        """
        latest = self._storage.get_latest_autosave_path()
        if not latest:
            return False

        autosave_mtime = self._storage.get_latest_autosave_mtime()
        if autosave_mtime <= self._host.last_manual_save_mtime:
            return False

        if not self._ask_user_should_restore():
            return False

        data = self._storage.load_formation(latest)
        if not data:
            return False

        # M-6 Fix: AutoSave-Timer waehrend des Recovery-Load pausieren.
        # Sonst kann ein QTimer-Feuer zwischen load_formation() und
        # _load_formation_data() einen halb-leeren Auto-Save schreiben,
        # der den noch nicht fertig restaurierten Stand ueberschreibt.
        autosave = getattr(self._host, "autosave", None)
        if autosave is not None and hasattr(autosave, "stop"):
            autosave.stop()

        try:
            # Delegate the actual restore to the host (uses its grid / pool
            # wiring).  We mirror the legacy behaviour: file path is set to
            # the autosave path, and the formation is marked modified so
            # the user can decide whether to save it.
            self._host._load_formation_data(data)
            # m-1 Fix: host.file = None setzen, damit der naechste save_f()
            # ein Save-As triggert (sonst wuerde der Auto-Save-Pfad
            # direkt ueberschrieben).
            self._host.file = None
            self._host._is_modified = True
        finally:
            if autosave is not None and hasattr(autosave, "start"):
                autosave.start()
        return True

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _ask_user_should_restore(self) -> bool:
        """Show the 'Wiederherstellen?' question; return ``True`` on Yes."""
        QMessageBox = _resolve_qmessagebox()
        r = QMessageBox.question(
            self._host,
            self.DIALOG_TITLE,
            self.DIALOG_TEXT,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return r == QMessageBox.StandardButton.Yes
