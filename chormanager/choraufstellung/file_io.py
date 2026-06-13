"""File-IO bridge for ChorAufstellung formations.

Extracted from :mod:`main` (M-2 Schritt 8). The class encapsulates:

* prompt-before-discard + reset (:meth:`FormationFileIO.new`)
* file-open dialog + JSON load (:meth:`FormationFileIO.open`)
* save / save-as dispatch (:meth:`FormationFileIO.save`, :meth:`FormationFileIO.save_as`)
* atomic write helper (:meth:`FormationFileIO.save_to_path`)
* deterministic auto-filename generator (:meth:`FormationFileIO.generate_filename`)
* dict → host-window applier (:meth:`FormationFileIO.load_formation_data`)

The dialog methods (``new``, ``open``, ``save``, ``save_as``) call into
``QFileDialog`` / ``QMessageBox`` and therefore require a Qt event loop.
The non-dialog helpers (``save_to_path``, ``generate_filename``,
``load_formation_data``) are pure Python and can be unit-tested
without a running QApplication.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

# Qt is imported lazily inside the dialog-touching methods so that the
# headless tests can import this module under QT_QPA_PLATFORM=offscreen
# without paying the Qt-import cost.
if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


class FormationFileIO:
    """Encapsulates all read/write file operations for the formation."""

    def __init__(self, storage: Any) -> None:
        """Store the storage backend (``FormationStorage`` instance).

        The host window is supplied per-call (as the ``host``/``parent``
        argument) so that the bridge itself stays window-agnostic and
        can be reused by tests and by the ChorManager launcher.
        """
        self._storage = storage

    # ------------------------------------------------------------------
    # pure-Python helpers (testable without Qt)
    # ------------------------------------------------------------------

    def generate_filename(self, event_date: str, event_name: Optional[str] = None) -> str:
        """Return ``choraufstellung-DATE-version-TODAY.json``.

        ``event_date`` is truncated to the first 10 characters (YYYY-MM-DD).
        When ``event_date`` is empty, today's date is used instead.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        date_part = event_date[:10] if event_date else today
        return f"choraufstellung-{date_part}-version-{today}.json"

    def save_to_path(self, filepath: str, grid: Any, metadata: Optional[dict] = None) -> bool:
        """Persist the formation to ``filepath`` via the storage layer.

        Returns ``True`` on success, ``False`` if the storage backend
        reports a failure. The atomic write (tmp + os.replace) is
        handled by :class:`FormationStorage` itself.
        """
        placed = grid.get_placed_singers()
        return self._storage.save_formation(
            singers=getattr(grid, "_host_singers", None) or [],
            rows=grid.rows,
            cols=grid.cols,
            filepath=filepath,
            placed=placed,
            staggered=grid.staggered,
            metadata=metadata,
        )

    def load_formation_data(self, host: Any, data: dict) -> None:
        """Apply ``data`` (from :meth:`FormationStorage.load_formation`) to ``host``.

        Mutates ``host.singers``, ``host.grid.{rows,cols,staggered,singers}``,
        ``host.pool``, and resets ``host._is_modified`` to ``False``.
        Falls back to the existing defaults when keys are missing.
        """
        rows = data.get("rows", 3)
        cols = data.get("cols", 4)
        staggered = data.get("staggered", False)

        # Re-hydrate singers via Singer.from_dict when available so that
        # .row / .col / .affinity attributes are restored properly.
        singer_payloads = data.get("singers", [])
        singers = self._rehydrate_singers(singer_payloads)
        host.singers = singers
        # Make sure every singer has the ``affinity`` attribute
        for s in host.singers:
            if not hasattr(s, "affinity"):
                s.affinity = ""

        host.grid.singers = [s for s in host.singers if getattr(s, "row", -1) >= 0]
        host.grid.rows = rows
        host.grid.cols = cols
        host.grid.staggered = staggered
        if hasattr(host.grid, "refresh_grid"):
            host.grid.refresh_grid()

        host.pool.singers = host.singers
        host.pool.placed_singer_ids = host.grid.get_placed_singer_ids()
        host.pool.update_singers(host.singers, host.pool.placed_singer_ids)

        host._is_modified = False
        if hasattr(host, "update_grid_count"):
            host.update_grid_count()

        # Sync the rows/cols combo boxes if the host has them.
        for attr, value in (("rs", rows), ("cs", cols)):
            if getattr(host, attr, None) is not None:
                cb = getattr(host, attr)
                cb.blockSignals(True)
                cb.setCurrentText(str(value))
                cb.blockSignals(False)

    # ------------------------------------------------------------------
    # dialog-touching methods (require Qt event loop)
    # ------------------------------------------------------------------

    def new(self, parent: Any, is_modified: bool) -> bool:
        """Prompt the user to save unsaved changes, then reset state.

        Returns ``True`` when a new (empty) formation is in place,
        ``False`` when the user cancelled.
        """
        if is_modified:
            from PyQt6.QtWidgets import QMessageBox  # type: ignore

            r = QMessageBox.question(
                parent, "Ungespeichert", "Änderungen speichern?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Save:
                if not parent.save_f():
                    return False
            elif r == QMessageBox.StandardButton.Cancel:
                return False
        # Reset to a blank state
        parent.grid.singers = []
        if hasattr(parent.grid, "refresh_grid"):
            parent.grid.refresh_grid()
        parent.singers = []
        parent.file = None
        parent._is_modified = False
        if hasattr(parent, "update_grid_count"):
            parent.update_grid_count()
        return True

    def open(self, parent: Any) -> Optional[str]:
        """Open a JSON file and return the path that was loaded.

        Returns ``None`` when the user cancelled the dialog.
        """
        from PyQt6.QtWidgets import QFileDialog  # type: ignore

        fp, _ = QFileDialog.getOpenFileName(
            parent, "Öffnen", "", "JSON (*.json);;Alle (*)"
        )
        if not fp:
            return None
        data = self._storage.load_formation(fp)
        if not data:
            return None
        self.load_formation_data(parent, data)
        parent.file = fp
        # Keep a copy of the metadata for later save-as
        parent._loaded_metadata = data.get("metadata", {})
        return fp

    def save(self, parent: Any, grid: Any) -> bool:
        """Save to the existing file or fall back to :meth:`save_as`."""
        # If there is no known file, defer to save_as (which shows the dialog).
        if not getattr(parent, "file", None):
            return self.save_as(parent, grid)
        return self.save_to_path(
            parent.file, grid, metadata=getattr(parent, "_loaded_metadata", None)
        )

    def save_as(self, parent: Any, grid: Any) -> bool:
        """Show a file dialog and write to the chosen path."""
        from PyQt6.QtWidgets import QFileDialog  # type: ignore

        from config import get_data_dir  # type: ignore  # local import to avoid hard dep

        data_dir = get_data_dir()
        auto_name = self.generate_filename(
            parent._loaded_metadata.get("event_date", "")
            if getattr(parent, "_loaded_metadata", None)
            else "",
            parent._loaded_metadata.get("event", "")
            if getattr(parent, "_loaded_metadata", None)
            else None,
        )
        fp, _ = QFileDialog.getSaveFileName(
            parent, "Speichern",
            os.path.join(data_dir, auto_name),
            "JSON (*.json)",
        )
        if not fp:
            return False
        if not fp.endswith(".json"):
            fp += ".json"
        ok = self.save_to_path(
            fp, grid, metadata=getattr(parent, "_loaded_metadata", None)
        )
        if ok:
            parent.file = fp
            parent._is_modified = False
        return ok

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _rehydrate_singers(self, payloads: List[dict]) -> List[Any]:
        """Re-hydrate singer dicts into :class:`Singer` instances.

        Falls back to a generic object with the same attributes if the
        :mod:`singer_model` module is unavailable (e.g. when only a
        JSON payload is loaded without Qt).
        """
        try:
            from singer_model import Singer  # type: ignore

            return [Singer.from_dict(p) for p in payloads]
        except Exception:
            # Build a duck-typed singer so the grid can read .row / .col / .affinity
            out: List[Any] = []
            for p in payloads:
                s = type("_AnonSinger", (), {})()
                for k, v in (p or {}).items():
                    setattr(s, k, v)
                out.append(s)
            return out
