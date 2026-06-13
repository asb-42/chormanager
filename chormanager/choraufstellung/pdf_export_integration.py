"""PDF-Export-Bridge for ChorAufstellung (M-2 Schritt 9).

Extracted from :meth:`MainWindow.export_pdf` (Z. 707–773 in the legacy
``main.py``). The class encapsulates the dialog + filename + write
+ result-feedback cycle so that the menu action and any programmatic
caller go through a single, testable entry point.

Design notes
------------
* **Lazy Qt:** Qt widgets are imported only when :meth:`run` is
  actually called, so the rest of the module loads in plain Python
  and can be unit-tested under ``QT_QPA_PLATFORM=offscreen`` without
  touching the event loop.
* **Deterministic defaults:** the file name and subtitle helpers
  depend only on host attributes (``event_date``, ``event_name``,
  ``project_name``) and the current date. They never touch Qt and
  can be unit-tested without a host window.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    pass


# Module-level handle so tests can monkey-patch the dialog class
# without having to re-import ``pdf_export_dialog``.
_PDFExportDialog: Any = None

# Real Qt names (lazily resolved, but module-level so tests can patch).
QMessageBox: Any = None
QDesktopServices: Any = None


def _resolve_dialog() -> Any:
    """Lazy lookup of :class:`PDFExportDialog` (cached in module globals)."""
    global _PDFExportDialog
    if _PDFExportDialog is None:
        from pdf_export_dialog import PDFExportDialog  # type: ignore
        _PDFExportDialog = PDFExportDialog
    return _PDFExportDialog


def _resolve_qt() -> None:
    """Lazy lookup of ``QMessageBox`` + ``QDesktopServices`` (cached)."""
    global QMessageBox, QDesktopServices
    if QMessageBox is None:
        from PyQt6.QtWidgets import QMessageBox as _QMB  # type: ignore
        QMessageBox = _QMB
    if QDesktopServices is None:
        from PyQt6.QtGui import QDesktopServices as _QDS  # type: ignore
        QDesktopServices = _QDS


class PDFExportBridge:
    """Encapsulates the "Choraufstellung → PDF" workflow."""

    def __init__(self, host: Any) -> None:
        """Store the host window (``MainWindow`` or compatible).

        The host must expose:
        * ``pdf``     – an object with ``export_formation(singers, rows, cols, fp, **kw)``
        * ``grid``    – with ``rows``, ``cols``, ``staggered`` attributes
        * ``singers`` – the singer list
        * ``event_date`` / ``event_name`` / ``project_name`` – optional strings
        """
        self._host = host

    # ------------------------------------------------------------------
    # pure-Python helpers (testable without Qt)
    # ------------------------------------------------------------------

    def default_filename(self) -> str:
        """Return ``choraufstellung-DATE-version-TODAY.pdf``.

        The DATE is taken from the host's ``event_date`` attribute
        (truncated to the first 10 characters) and falls back to
        today's date when no event date is set.
        """
        event_date = self._event_date() or ""
        if event_date:
            event_date = event_date[:10]
        today = datetime.now().strftime("%Y-%m-%d")
        date_part = event_date if event_date else today
        return f"choraufstellung-{date_part}-version-{today}.pdf"

    def default_subtitle(self) -> str:
        """Return the human-readable subtitle for the PDF.

        Layout: ``"{project}: {event} - {date}"`` with whichever
        fragments are present. Empty string when nothing is set.
        """
        project_name = (self._host.project_name or "") if hasattr(self._host, "project_name") else ""
        event_name = (self._host.event_name or "") if hasattr(self._host, "event_name") else ""
        event_date = self._event_date()

        subtitle = ""
        if event_name:
            subtitle = event_name
        if event_date:
            subtitle += f" - {event_date}"
        if project_name:
            subtitle = f"{project_name}: {subtitle}" if subtitle else project_name
        return subtitle

    def workdir(self) -> str:
        """Return (and create) the PDF workdir: ``<data-dir>/../workdir``.

        Mirrors the original MainWindow behaviour: the workdir lives
        one level above the data dir so it is easy to find for the
        user.
        """
        # Lazy import to avoid a hard dep on config at module load time
        from config import get_data_dir  # type: ignore

        data_dir = get_data_dir()
        wd = os.path.join(os.path.dirname(data_dir), "workdir")
        os.makedirs(wd, exist_ok=True)
        return wd

    # ------------------------------------------------------------------
    # dialog-touching entry point (requires Qt event loop)
    # ------------------------------------------------------------------

    def run(self) -> Optional[str]:
        """Show the PDF export dialog and write the file.

        Returns the absolute path of the written PDF, or ``None`` when
        the user cancelled or the export failed.
        """
        # Lazy Qt imports — the names live in this module's globals so
        # tests can monkey-patch them via ``monkeypatch.setattr`` on the
        # bridge module itself.
        from PyQt6.QtWidgets import QDialog  # type: ignore
        from PyQt6.QtCore import QUrl  # type: ignore

        _resolve_qt()
        import pdf_export_integration as _self  # noqa: WPS433
        QMessageBox = _self.QMessageBox  # noqa: N806
        QDesktopServices = _self.QDesktopServices  # noqa: N806

        # Look up the dialog class via the module-level handle so
        # tests can monkey-patch ``pdf_export_integration._PDFExportDialog``
        # and have the change take effect on the next call.
        PDFExportDialog = _resolve_dialog()  # noqa: N806

        dlg = PDFExportDialog(
            self._host,
            default_filename=self.default_filename(),
            event_info=self.default_subtitle(),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None

        settings = dlg.get_settings()
        wd = self.workdir()
        fp = os.path.join(wd, settings["filename"])
        if not fp.endswith(".pdf"):
            fp += ".pdf"

        title = "Choraufstellung"
        subtitle = self.default_subtitle()

        success = self._host.pdf.export_formation(
            self._host.singers,
            self._host.grid.rows,
            self._host.grid.cols,
            fp,
            title=title,
            subtitle=subtitle,
            staggered=self._host.grid.staggered,
            orientation=settings["orientation"],
            color_mode=settings["color_mode"],
            text_rotation=settings["text_rotation"],
        )

        if success:
            QMessageBox.information(
                self._host, "PDF Export", f"PDF exportiert nach:\n{fp}"
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(fp)))
            return fp
        QMessageBox.warning(self._host, "Fehler", "PDF-Export fehlgeschlagen.")
        return None

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _event_date(self) -> str:
        """Read the event date from the host (env var overrides attribute)."""
        env = os.environ.get("CHOR_EVENT_DATE", "")
        if env:
            return env
        return getattr(self._host, "event_date", "") or ""
