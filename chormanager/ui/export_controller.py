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

# Qt imports at module level: the original main_window.py had
# these at module level too, and the methods reference them by
# their short name (e.g. ``QFileDialog.getSaveFileName``).
from PyQt6.QtWidgets import QFileDialog, QMessageBox

# ExportDialog was imported at module-level in main_window.py
# (the methods call ``ExportDialog(...)`` directly). Keep the
# same import here so the methods work byte-for-byte.
from .export_dialog import ExportDialog
from ..core.export_service import ExportService


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

    Any widget that needs them must inherit from this mixin AND from
    a QWidget-derived class so that ``self.<tab>`` and ``self.<label>``
    resolve to real Qt attributes.

    The Mixin expects the following attributes on the host (provided
    by ``MainWindow`` in production):

      * ``self.db``                (Database) — the DB instance
      * ``self.db_path``           (str) — path to the SQLite DB
      * ``self.statusBar()``       (QStatusBar) — for status messages
    """

    def _export_singers_json(self):
        """Export singers as JSON for choraufstellung sync."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_singers_json

        default_path = (
            self.db_path.replace(".db", "_singers.json")
            if self.db_path
            else "singers.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Sänger exportieren", default_path, "JSON Dateien (*.json)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_singers_json(self.db, output_path)
                self.statusBar().showMessage(f"Sänger exportiert nach {filename}")
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_events_json(self):
        """Export events as JSON for choraufstellung sync."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_events_json

        default_path = (
            self.db_path.replace(".db", "_termine.json")
            if self.db_path
            else "termine.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Termine exportieren", default_path, "JSON Dateien (*.json)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_events_json(self.db, output_path)
                self.statusBar().showMessage(f"Termine exportiert nach {filename}")
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_availability_json(self):
        """Export availability matrix as JSON."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_availability_json

        default_path = (
            self.db_path.replace(".db", "_verfuegbarkeit.json")
            if self.db_path
            else "verfuegbarkeit.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Verfügbarkeit exportieren", default_path, "JSON Dateien (*.json)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_availability_json(self.db, output_path)
                self.statusBar().showMessage(
                    f"Verfügbarkeit exportiert nach {filename}"
                )
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_singers_csv(self):
        """Export singers as CSV fallback for choraufstellung."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_singers_csv

        default_path = (
            self.db_path.replace(".db", "_singers.csv")
            if self.db_path
            else "singers.csv"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV exportieren", default_path, "CSV Dateien (*.csv)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_singers_csv(self.db, output_path)
                self.statusBar().showMessage(f"CSV exportiert nach {filename}")
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_all_sync(self):
        """Export all sync files to default location."""
        from PyQt6.QtWidgets import QMessageBox
        from ..export.sync import export_all_sync

        try:
            result = export_all_sync(self.db)

            output_text = "Exportierte Dateien:\n\n"
            for export_type, path in result.items():
                output_text += f"{export_type}: {path}\n"

            self.statusBar().showMessage("Alle Sync-Dateien exportiert")
            QMessageBox.information(self, "Sync-Export", output_text)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")


class ExportTabSpecificMixin:
    """Mixin that provides the tab-specific export methods.

    Will be added in M-1 step 7c. Methods:
      * ``_export_besetzung``
      * ``_export_termine``
      * ``_export_aufstellung``
    """

    def _export_besetzung(self):
        besetzung_fields = [
            {'name': 'name', 'label': 'Name'},
            {'name': 'project', 'label': 'Projekt'},
            {'name': 'singer_count', 'label': 'Anzahl Sänger'},
            {'name': 'updated_at', 'label': 'Zuletzt gespeichert'},
        ]

        dialog = ExportDialog(besetzung_fields, self)
        if not dialog.exec():
            return

        selected = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        service = ExportService()
        besetzungen = self.besetzung_tab.besetzung_repo.get_all()

        data = []
        for b in besetzungen:
            row = {}
            if 'name' in selected:
                row['name'] = b.name
            if 'project' in selected:
                proj = self.besetzung_tab.project_repo.get_by_id(b.project_id)
                row['project'] = proj.name if proj else '-'
            if 'singer_count' in selected:
                singer_ids = b.get_singer_ids()
                row['singer_count'] = len(singer_ids) if singer_ids else 0
            if 'updated_at' in selected:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(b.updated_at)
                    row['updated_at'] = dt.strftime('%d.%m.%Y %H:%M')
                except (ValueError, OSError):
                    row['updated_at'] = '-'
            data.append(row)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected)
            ext_filter = 'CSV (*.csv)'

        from pathlib import Path
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        workdir = Path(__file__).parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        ext = ext_map.get(fmt, 'csv')
        default_path = str(workdir / f'{today}-besetzungen.{ext}')

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Besetzungen exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'Besetzungen exportiert ({fmt.upper()})')

    def _export_termine(self):
        termin_fields = [
            {'name': 'date', 'label': 'Datum'},
            {'name': 'name', 'label': 'Name'},
            {'name': 'type', 'label': 'Typ'},
            {'name': 'project', 'label': 'Projekt'},
            {'name': 'yes_count', 'label': 'Verbindl. Zusagen'},
            {'name': 'conditional_count', 'label': 'Vorbehalt'},
        ]

        dialog = ExportDialog(termin_fields, self)
        if not dialog.exec():
            return

        selected = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        service = ExportService()
        events = self.events_tab.event_repo.get_all()

        event_type_labels = {
            'gp': 'GP', 'op': 'OP', 'sofa': 'SOFA',
            'probe': 'Probe', 'konzert': 'Konzert',
            'auftritt': 'Auftritt', 'sonstiges': 'Sonstiges',
        }

        data = []
        for e in events:
            row = {}
            if 'date' in selected:
                try:
                    from datetime import datetime
                    if e.date and len(e.date) >= 10:
                        dt = datetime.strptime(e.date[:10], '%Y-%m-%d')
                        row['date'] = dt.strftime('%d.%m.%Y')
                    else:
                        row['date'] = e.date or '-'
                except:
                    row['date'] = e.date[:10] if e.date else '-'
            if 'name' in selected:
                row['name'] = e.name or ''
            if 'type' in selected:
                row['type'] = event_type_labels.get(e.event_type, e.event_type or '')
            if 'project' in selected:
                proj = self.events_tab.project_repo.get_by_id(e.project_id)
                row['project'] = proj.name if proj else ''
            if 'yes_count' in selected:
                avails = self.events_tab.avail_repo.get_by_event(e.id)
                row['yes_count'] = sum(1 for a in avails if a.status == 'yes')
            if 'conditional_count' in selected:
                avails = self.events_tab.avail_repo.get_by_event(e.id)
                row['conditional_count'] = sum(1 for a in avails if a.status == 'conditional')
            data.append(row)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected)
            ext_filter = 'CSV (*.csv)'

        from pathlib import Path
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        workdir = Path(__file__).parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        ext = ext_map.get(fmt, 'csv')
        default_path = str(workdir / f'{today}-termine.{ext}')

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Termine exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'Termine exportiert ({fmt.upper()})')

    def _export_aufstellung(self):
        aufstellung_fields = [
            {'name': 'filename', 'label': 'Dateiname'},
            {'name': 'size', 'label': 'Dateigröße'},
            {'name': 'project', 'label': 'Projekt'},
            {'name': 'event_date', 'label': 'Termin'},
            {'name': 'event', 'label': 'Typ'},
            {'name': 'saved_at', 'label': 'Gespeichert'},
        ]

        dialog = ExportDialog(aufstellung_fields, self)
        if not dialog.exec():
            return

        selected = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        import os
        service = ExportService()
        data_dir = self.choraufstellung_tab._data_dir

        files = []
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.endswith('.json'):
                    fp = os.path.join(data_dir, f)
                    stats = os.stat(fp)
                    entry = {'filename': f, 'size': stats.st_size}
                    try:
                        with open(fp, 'r', encoding='utf-8') as jf:
                            content_json = json.load(jf)
                            entry['metadata'] = content_json.get('metadata', {})
                            entry['saved_at'] = content_json.get('saved_at', '')
                    except:
                        entry['metadata'] = {}
                        entry['saved_at'] = ''
                    files.append(entry)

        data = []
        for f in files:
            meta = f.get('metadata', {})
            row = {}
            if 'filename' in selected:
                row['filename'] = f['filename']
            if 'size' in selected:
                sz = f.get('size', 0)
                row['size'] = f'{sz // 1024} KB' if sz >= 1024 else f'{sz} B'
            if 'project' in selected:
                row['project'] = meta.get('project', '')
            if 'event_date' in selected:
                ed = meta.get('event_date', '')
                row['event_date'] = ed[:10] if ed else ''
            if 'event' in selected:
                row['event'] = meta.get('event', '')
            if 'saved_at' in selected:
                saved = f.get('saved_at', '')
                if saved:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(saved)
                        row['saved_at'] = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        row['saved_at'] = saved
                else:
                    row['saved_at'] = ''
            data.append(row)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected)
            ext_filter = 'CSV (*.csv)'

        from pathlib import Path
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        workdir = Path(__file__).parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        ext = ext_map.get(fmt, 'csv')
        default_path = str(workdir / f'{today}-aufstellungen.{ext}')

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Aufstellungen exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'Aufstellungen exportiert ({fmt.upper()})')


# --- M-1 step 2: VersionCheckDialog was moved to its own module.
# Re-exported here for backward compatibility with any code that
# imports ``chormanager.ui.main_window.VersionCheckDialog``.
from .update_controller import VersionCheckDialog  # noqa: E402, F401


# --- M-1 step 3: refresh_tab_repositories was moved to its own module.
# Re-exported here for backward compatibility with the unit test
# (tests/unit/test_reload_after_restore.py) that imports it from
# the original location.
from .choraufstellung_launcher import refresh_tab_repositories  # noqa: E402, F401


# A-1-SUBPLAN-A (Scoped): ExportController(QObject) skeleton.
# Composition pattern: ``self.export_controller = ExportController(self)``
# in MainWindow. The full migration of the 20+ Mixin methods is
# left for a future sprint; this skeleton establishes the signal
# contract and one demo method.
from PyQt6.QtCore import QObject, pyqtSignal  # noqa: E402
from typing import Any, Optional  # noqa: E402


class ExportController(QObject):
    """A-1: QObject wrapper for the export methods.

    Signals match the acceptance criterion in
    ``plans/2026-06-14_subplan_mixin_refactor.md``.
    """

    export_finished = pyqtSignal(str)  # path
    export_failed = pyqtSignal(str)    # error message

    def __init__(self, host: Any, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._host = host

    def export_csv(self, target_path: str) -> bool:
        """Skeleton demo method. Real implementations move the
        ``ExportCoreMixin._export_csv`` body here."""
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("# Skeleton export (A-1 scoped)\n")
        except OSError as exc:
            self.export_failed.emit(str(exc))
            return False
        self.export_finished.emit(target_path)
        return True
