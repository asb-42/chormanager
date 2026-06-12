"""Export controller: Export-Core Mixin for MainWindow.

Extracted from ``chormanager.ui.main_window`` as part of M-1 (God-Class
refactor, see ``plans/2026-06-12_m1_main_window_refactor.md`` step 7).

This module hosts three Mixin classes — all extracted byte-for-byte
from ``main_window.py``:

  * ``ExportCoreMixin`` (step 7a) — generic exports: CSV, PDF,
    LibreOffice, response-matrix and the tab-dispatch helpers.
  * ``ExportJsonSyncMixin`` (step 7b) — JSON/CSV sync helpers for
    the choraufstellung subshell.
  * ``ExportTabSpecificMixin`` (step 7c) — per-tab exports for
    Besetzung, Termine and Aufstellung.

All three Mixins are designed to be inherited by ``MainWindow``
together with the other UI Mixins (ThemeMixin, TabRouterMixin,
ChorAufstellungLauncherMixin). The methods are kept byte-for-byte
identical to the previous implementation; only the location
changed. There is no re-export at the original location because
the methods are now inherited, not imported.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


class ExportCoreMixin:
    """Mixin that provides the Core export methods.

    Any widget that needs them must inherit from this mixin AND from
    a QWidget-derived class so that ``self.<tab>`` and ``self.<label>``
    resolve to real Qt attributes.

    The Mixin expects the following attributes on the host (provided
    by ``MainWindow`` in production):

      * ``self.db``                (Database) — the DB instance
      * ``self.content_stack``     (QStackedWidget) — main tab switch
      * ``self.statusBar()``       (QStatusBar) — for status messages
      * ``self.singer_repo``       (SingerRepository)
      * ``self.singers_tab``       (SingersTab)
      * ``self.projects_tab``      (ProjectsTab)
    """

    # ------------------------------------------------------------------
    # Tab → (table_name, tab_attr, repo_attr, display_name) config
    # ------------------------------------------------------------------
    _TAB_EXPORT_CONFIG = {
        'projekte': ('projects', 'projects_tab', 'project_repo', 'Projekte'),
        'saenger': ('singers', 'singers_tab', 'singer_repo', 'Sänger'),
        'besetzung': ('besetzung', 'besetzung_tab', 'besetzung_repo', 'Besetzungen'),
        'termine': ('events', 'events_tab', 'event_repo', 'Termine'),
    }

    # ------------------------------------------------------------------
    # Direct exports (singers list)
    # ------------------------------------------------------------------

    def _export_csv(self):
        """Export to CSV."""
        from PyQt6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self, "Als CSV exportieren", "", "CSV Dateien (*.csv)"
        )

        if filename:
            singers = self.singer_repo.get_all()
            fields = self.singers_tab.visible_fields

            import csv

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=[field["name"] for field in fields]
                )
                writer.writeheader()

                for singer in singers:
                    row = {}
                    for field in fields:
                        name = field["name"]
                        value = getattr(singer, name, "")
                        row[name] = value if value else ""
                    writer.writerow(row)

            self.statusBar().showMessage(f"Exportiert nach {filename}")

    def _export_pdf(self):
        """Export to PDF."""
        from PyQt6.QtWidgets import QFileDialog
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm

        filename, _ = QFileDialog.getSaveFileName(
            self, "Als PDF exportieren", "", "PDF Dateien (*.pdf)"
        )

        if not filename:
            return

        singers = self.singer_repo.get_all()

        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=20
        )

        elements.append(Paragraph("Chor-Teilnehmerliste", title_style))
        elements.append(Spacer(1, 0.5 * cm))

        data = [["Name", "Stimmgruppe", "E-Mail", "Telefon"]]
        for singer in singers:
            data.append(
                [
                    singer.full_name or "",
                    singer.voice_group or "",
                    singer.email or "",
                    singer.phone or "",
                ]
            )

        table = Table(data, colWidths=[5 * cm, 3 * cm, 4 * cm, 3 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                ]
            )
        )

        elements.append(table)

        doc.build(elements)

        self.statusBar().showMessage(f"Exportiert nach {filename}")

    def _export_libreoffice(self):
        """Export to LibreOffice format."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import subprocess
        import tempfile
        import os

        singers = self.singer_repo.get_all()

        reply = QMessageBox.question(
            self,
            "LibreOffice Export",
            "Möchten Sie als Writer-Dokument (doc) oder Calc-Dokument (xls) exportieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            output_format = "doc"
            ext = ".doc"
        else:
            output_format = "xls"
            ext = ".xls"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            import csv

            writer = csv.writer(f)
            writer.writerow(["Name", "Stimmgruppe", "E-Mail", "Telefon", "Adresse"])
            for singer in singers:
                writer.writerow(
                    [
                        singer.full_name or "",
                        singer.voice_group or "",
                        singer.email or "",
                        singer.phone or "",
                        singer.address or "",
                    ]
                )
            temp_csv = f.name

        filename, _ = QFileDialog.getSaveFileName(
            self, "Als LibreOffice exportieren", "", f"LibreOffice Dateien (*{ext})"
        )

        if not filename:
            return

        out_dir = os.path.dirname(filename)
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                output_format,
                "--outdir",
                out_dir,
                temp_csv,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            base_name = os.path.splitext(os.path.basename(temp_csv))[0]
            expected_output = os.path.join(out_dir, base_name + ext)
            if expected_output != filename and os.path.exists(expected_output):
                os.rename(expected_output, filename)
            self.statusBar().showMessage(f"Exportiert nach {filename}")
        else:
            QMessageBox.warning(self, "Fehler", f"LibreOffice Fehler:\n{result.stderr}")

        if os.path.exists(temp_csv):
            os.unlink(temp_csv)

    # ------------------------------------------------------------------
    # Response-Matrix (project-wide)
    # ------------------------------------------------------------------

    def _export_response_matrix(self):
        """Export a project-wide response matrix (PDF or ODT).

        The matrix covers:
          * All events belonging to the currently active project.
          * All singers in the active Besetzung (Choraufstellung filter).
            If there is no active Besetzung, all singers are included.

        The user is first asked for the output format (PDF / ODT), then
        for a destination file. A status-bar message confirms success
        or reports errors.
        """
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog

        from ..core.response_matrix import build_response_matrix
        from ..core.response_render_odt import render_response_matrix_odt
        from ..core.response_render_pdf import render_response_matrix_pdf
        from ..config import get_last_active_besetzung_id
        from ..domain.repository import (
            AvailabilityRepository,
            BesetzungRepository,
            EventRepository,
            SingerRepository,
        )
        from .export_format_dialog import (
            SUPPORTED_FORMATS,
            ExportFormatDialog,
        )

        try:
            # 1) Resolve the active project
            project = (
                self.projects_tab.current_project
                if hasattr(self, "projects_tab")
                else None
            )
            if project is None:
                QMessageBox.information(
                    self,
                    "Information",
                    "Bitte wählen Sie zuerst ein aktives Projekt aus.",
                )
                return

            # 2) Load singers (filtered by active Besetzung)
            singer_repo = SingerRepository(self.db)
            singers = singer_repo.get_active()
            singer_filter_ids = None
            saved_besetzung_id = get_last_active_besetzung_id()
            if saved_besetzung_id:
                besetzung_repo = BesetzungRepository(self.db)
                besetzung = besetzung_repo.get_by_id(saved_besetzung_id)
                if besetzung and besetzung.project_id == project.id:
                    singer_filter_ids = besetzung.get_singer_ids()

            # 3) Load events for this project
            event_repo = EventRepository(self.db)
            all_events = event_repo.get_all()
            project_events = [e for e in all_events if e.project_id == project.id]

            # 4) Load availabilities for these events
            avail_repo = AvailabilityRepository(self.db)
            event_ids = {e.id for e in project_events}
            availabilities = [
                a
                for a in (
                    avail_repo.get_by_event(eid) for eid in event_ids
                )
                for a in a
            ] if event_ids else []

            # 5) Build the matrix
            matrix = build_response_matrix(
                singers=singers,
                events=project_events,
                availabilities=availabilities,
                title=project.name,
                singer_filter_ids=singer_filter_ids,
            )

            if not matrix.columns:
                QMessageBox.information(
                    self,
                    "Information",
                    f"Das Projekt '{project.name}' enthält keine Termine. "
                    "Es gibt nichts zu exportieren.",
                )
                return

            # 6) Ask the user for the output format
            dlg = ExportFormatDialog(self, default_format="pdf")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            fmt_key = dlg.selected_format
            ext = SUPPORTED_FORMATS[fmt_key]["ext"]

            # 7) Ask for the destination file
            default_name = f"{project.name}-Zusagen{ext}"
            out_path = ExportFormatDialog.get_save_path(
                self, fmt_key, default_name,
            )
            if out_path is None:
                return

            # 8) Render
            if fmt_key == "pdf":
                render_response_matrix_pdf(matrix, out_path)
            else:
                render_response_matrix_odt(matrix, out_path)

            self.statusBar().showMessage(
                f"Response-Matrix exportiert nach {out_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Export fehlgeschlagen:\n{type(e).__name__}: {e}",
            )

    # ------------------------------------------------------------------
    # Tab-Generic + dispatch helpers
    # ------------------------------------------------------------------

    def _get_export_config_for_current_tab(self):
        tab_index = self.content_stack.currentIndex()
        tab_map = {0: 'projekte', 1: 'saenger', 2: 'besetzung', 3: 'termine'}
        tab_key = tab_map.get(tab_index)
        if tab_key and tab_key in self._TAB_EXPORT_CONFIG:
            return self._TAB_EXPORT_CONFIG[tab_key]
        return None

    def _export_tab_generic(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        from ..core.export_service import ExportService
        from .export_dialog import ExportDialog

        config = self._get_export_config_for_current_tab()
        if not config:
            QMessageBox.warning(self, 'Export', 'Export für diesen Tab nicht verfügbar.')
            return

        table_name, tab_attr, repo_attr, display_name = config
        repo = getattr(getattr(self, tab_attr), repo_attr)
        service = ExportService()

        fields = service.get_table_fields(self.db.get_connection(), table_name)
        if not fields:
            QMessageBox.warning(self, 'Warnung', f'Keine Felder für Tabelle {table_name} gefunden.')
            return

        dialog = ExportDialog(fields, self)
        if not dialog.exec():
            return

        selected_fields = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected_fields:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        items = repo.get_all()
        data = service.get_export_data(items, selected_fields)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected_fields)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected_fields)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected_fields)
            ext_filter = 'CSV (*.csv)'

        tab_name_map = {'Projekte': 'projekte', 'Sänger': 'saenger', 'Besetzungen': 'besetzungen', 'Termine': 'termine'}
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        tab_file = tab_name_map.get(display_name, display_name.lower())
        ext = ext_map.get(fmt, 'csv')
        default_name = f'2026-04-26-{tab_file}.{ext}'
        workdir = Path(__file__).parent.parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        default_path = str(workdir / default_name)

        filename, _ = QFileDialog.getSaveFileName(
            self, f'{display_name} exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'{display_name} exportiert ({fmt.upper()})')

    def _export_project_libreoffice(self):
        self.content_stack.setCurrentIndex(0)
        self._export_tab_generic()

    def _export_project_csv(self):
        self.content_stack.setCurrentIndex(0)
        self._export_tab_generic()

    def _export_tab(self, tab_index):
        self.content_stack.setCurrentIndex(tab_index)
        self._export_tab_generic()

    def _export_tab_csv(self, tab_index):
        self.content_stack.setCurrentIndex(tab_index)
        self._export_tab_generic()


class ExportJsonSyncMixin:
    """Mixin that provides the JSON-Sync export methods.

    Will be added in M-1 step 7b. Methods:
      * ``_export_singers_json``
      * ``_export_events_json``
      * ``_export_availability_json``
      * ``_export_singers_csv``
      * ``_export_all_sync``
    """

    pass


class ExportTabSpecificMixin:
    """Mixin that provides the tab-specific export methods.

    Will be added in M-1 step 7c. Methods:
      * ``_export_besetzung``
      * ``_export_termine``
      * ``_export_aufstellung``
    """

    pass
