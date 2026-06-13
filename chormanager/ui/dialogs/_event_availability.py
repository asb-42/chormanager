""":class:`EventAvailabilityDialog` — large dialog for managing per-singer
availability for a specific event.

Extracted from ``chormanager/ui/dialogs/__init__.py`` in M-3 Schritt 4.
This is the largest dialog in the package (~590 LOC) and has 7 methods:
``__init__``, ``_setup_ui``, ``_load_availability``,
``_save_availability_on_change``, ``accept``, ``_export_pdf`` (168 LOC),
and ``_export_availability`` (103 LOC).
"""
from __future__ import annotations

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtCore import Qt  # type: ignore
    from PyQt5.QtWidgets import (  # type: ignore
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

# Module-level imports used by __init__ and lazy methods. The lazy ones
# (ProjectRepository, ReportLab, ExportService) stay lazy in the methods.
from ...config import load_voice_groups
from ...domain.repository import (
    SingerRepository,
    AvailabilityRepository,
)
from ._availability import AVAILABILITY_STATUS


class EventAvailabilityDialog(QDialog):
    """Dialog for managing availability for a specific event."""

    def __init__(
        self,
        db,
        event,
        parent=None,
        besetzung_ids=None,
        besetzung_name=None,
        besetzung_count=0,
    ):
        """Initialize dialog.

        Args:
            db: Database instance.
            event: Event to manage availability for.
            parent: Parent widget.
            besetzung_ids: Optional list of singer IDs to filter by (active besetzung).
                           None means no filter, empty list means no singers to show.
            besetzung_name: Name of the active Besetzung (for display).
            besetzung_count: Number of singers in active Besetzung (for display).
        """
        super().__init__(parent)
        self.db = db
        self.event = event
        self.besetzung_ids = besetzung_ids
        self.besetzung_name = besetzung_name
        self.besetzung_count = besetzung_count
        self.singer_repo = SingerRepository(db)
        self.avail_repo = AvailabilityRepository(db)
        self._setup_ui()
        self._load_availability()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle(f"Verfügbarkeit: {self.event.name}")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)

        # Show Besetzung info if available
        if self.besetzung_name:
            besetzung_info = QLabel(
                f"Die aktuelle Besetzung '{self.besetzung_name}' umfasst {self.besetzung_count} Sänger."
            )
            besetzung_info.setStyleSheet(
                "padding: 8px; background-color: palette(base); color: palette(text); border-radius: 4px; margin: 4px 0;"
            )
            layout.addWidget(besetzung_info)

        # Show event info
        event_date = ""
        if self.event.date and len(self.event.date) >= 10:
            event_date = self.event.date[:10]
        event_info = QLabel(f"Termin: <b>{self.event.name}</b> ({event_date})")
        event_info.setStyleSheet(
            "padding: 8px; background-color: palette(window); color: palette(text); border-radius: 4px; margin: 4px 0;"
        )
        layout.addWidget(event_info)

        toolbar = QHBoxLayout()

        export_pdf_btn = QPushButton("Als PDF exportieren")
        export_pdf_btn.clicked.connect(self._export_pdf)
        toolbar.addWidget(export_pdf_btn)

        export_lo_btn = QPushButton("Export")
        export_lo_btn.clicked.connect(self._export_availability)
        toolbar.addWidget(export_lo_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        filter_layout = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Schnellsuche (Kurzname)...")
        self.search_box.textChanged.connect(self._load_availability)
        filter_layout.addWidget(self.search_box)

        self.voice_filter = QComboBox()
        self.voice_filter.addItem("Alle Stimmgruppen", None)
        voice_groups = load_voice_groups()
        for vg in voice_groups:
            self.voice_filter.addItem(vg["name"], vg["name"])
        self.voice_filter.currentIndexChanged.connect(self._load_availability)
        filter_layout.addWidget(self.voice_filter)

        sort_label = QLabel("Sortieren:")
        filter_layout.addWidget(sort_label)

        self.sort_by_combo = QComboBox()
        self.sort_by_combo.addItem("Stimmgruppe", "voice_group")
        self.sort_by_combo.addItem("Kurzname", "short_name")
        self.sort_by_combo.currentIndexChanged.connect(self._load_availability)
        filter_layout.addWidget(self.sort_by_combo)

        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItem("Aufsteigend", "asc")
        self.sort_order_combo.addItem("Absteigend", "desc")
        self.sort_order_combo.currentIndexChanged.connect(self._load_availability)
        filter_layout.addWidget(self.sort_order_combo)

        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Kurzname", "Stimmgruppe", "Status"])
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self.table.setSortingEnabled(False)

        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_availability(self):
        """Load singers and their availability status."""
        import logging

        logger = logging.getLogger(__name__)

        trace_file = "/tmp/chormanager_trace.txt"
        with open(trace_file, "a") as f:
            f.write(f"Dialog _load_availability called\n")
            f.write(
                f"besetzung_ids: {len(self.besetzung_ids) if self.besetzung_ids else None}\n"
            )

        singers = self.singer_repo.get_active()
        logger.info(f"_load_availability: loaded {len(singers)} active singers")

        if self.besetzung_ids is not None:
            singers_filtered = [s for s in singers if s.id in self.besetzung_ids]
            with open(trace_file, "a") as f:
                f.write(
                    f"Filtered from {len(singers)} to {len(singers_filtered)} singers\n"
                )
            logger.info(
                f"_load_availability: filtered to {len(singers_filtered)} singers (besetzung_ids has {len(self.besetzung_ids)} IDs)"
            )
            singers = singers_filtered
        else:
            with open(trace_file, "a") as f:
                f.write("No filter applied (besetzung_ids is None)\n")
            logger.info("_load_availability: no filter applied (besetzung_ids is None)")

        search_text = self.search_box.text().strip().lower()
        voice_filter = self.voice_filter.currentData()

        if search_text or voice_filter:
            filtered = []
            for singer in singers:
                if voice_filter and singer.voice_group != voice_filter:
                    continue
                if search_text:
                    search_fields = [singer.short_name or "", singer.full_name or ""]
                    if not any(search_text in str(f).lower() for f in search_fields):
                        continue
                filtered.append(singer)
            singers = filtered

        sort_by = self.sort_by_combo.currentData()
        sort_order = self.sort_order_combo.currentData()

        voice_group_order = {
            "Sopran 1": 0,
            "Sopran 2": 1,
            "Alt 1": 2,
            "Alt 2": 3,
            "Tenor 1": 4,
            "Tenor 2": 5,
            "Bass 1": 6,
            "Bass 2": 7,
        }

        reverse = sort_order == "desc"
        if sort_by == "voice_group":
            singers = sorted(
                singers,
                key=lambda s: (
                    voice_group_order.get(s.voice_group, 99),
                    s.short_name or s.full_name or ""
                ),
                reverse=reverse,
            )
        else:
            singers = sorted(
                singers,
                key=lambda s: s.short_name or s.full_name or "",
                reverse=reverse,
            )

        self.table.setRowCount(len(singers))

        self.status_widgets = {}

        voice_group_yes = {}
        voice_group_conditional = {}

        for row, singer in enumerate(singers):
            name_item = QTableWidgetItem(singer.short_name or singer.full_name or "")
            name_item.setData(Qt.ItemDataRole.UserRole, singer.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(singer.voice_group or ""))

            avail = self.avail_repo.get_by_ids(singer.id, self.event.id)
            current_status = avail.status if avail else None

            status_combo = QComboBox()
            status_combo.setMinimumHeight(28)
            status_combo.setMinimumWidth(180)
            status_combo.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            for status_code, status_label, short_label in AVAILABILITY_STATUS:
                status_combo.addItem(f"{status_label}", status_code)

            idx = status_combo.findData(current_status or "none")
            if idx >= 0:
                status_combo.setCurrentIndex(idx)

            status_combo.currentIndexChanged.connect(
                lambda index, sid=singer.id, widget=status_combo: (
                    self._save_availability_on_change(sid, widget)
                )
            )

            self.table.setCellWidget(row, 2, status_combo)
            self.table.setColumnWidth(2, 200)

            # Increase row height for better readability of dropdowns
            self.table.setRowHeight(row, 60)
            vg = singer.voice_group or "Unbekannt"
            if current_status == "yes":
                voice_group_yes[vg] = voice_group_yes.get(vg, 0) + 1
            elif current_status == "conditional":
                voice_group_conditional[vg] = voice_group_conditional.get(vg, 0) + 1

            self.status_widgets[singer.id] = (status_combo, current_status)

        self.table.resizeColumnsToContents()

        yes_count = sum(
            1
            for s in singers
            if self.avail_repo.get_by_ids(s.id, self.event.id)
            and self.avail_repo.get_by_ids(s.id, self.event.id).status == "yes"
        )
        no_count = sum(
            1
            for s in singers
            if self.avail_repo.get_by_ids(s.id, self.event.id)
            and self.avail_repo.get_by_ids(s.id, self.event.id).status == "no"
        )
        none_count = sum(
            1
            for s in singers
            if not self.avail_repo.get_by_ids(s.id, self.event.id)
            or self.avail_repo.get_by_ids(s.id, self.event.id).status == "none"
        )

        total_yes = yes_count
        total_conditional = sum(
            1
            for s in singers
            if self.avail_repo.get_by_ids(s.id, self.event.id)
            and self.avail_repo.get_by_ids(s.id, self.event.id).status == "conditional"
        )

        summary_html = f"<b>Zusammenfassung:</b> {total_yes} verbindlich, {total_conditional} unter Vorbehalt, {no_count} Absage, {none_count} offen"

        if voice_group_yes or voice_group_conditional:
            summary_html += "<br><br><table border='1' cellpadding='3' cellspacing='0' style='border-collapse: collapse; font-size: 11px;'>"
            summary_html += "<tr><th>Stimmgruppe</th><th>Verbindlich</th><th>Vorbehalt</th><th>Gesamt</th></tr>"

            all_vgs = set(
                list(voice_group_yes.keys()) + list(voice_group_conditional.keys())
            )
            for vg in sorted(all_vgs):
                ja = voice_group_yes.get(vg, 0)
                bed = voice_group_conditional.get(vg, 0)
                summary_html += f"<tr><td>{vg}</td><td align='center'>{ja}</td><td align='center'>{bed}</td><td align='center'><b>{ja + bed}</b></td></tr>"

            summary_html += "</table>"

        self.summary_label.setText(summary_html)

    def _save_availability_on_change(self, singer_id: str, widget):
        """Save availability immediately when dropdown changes."""
        status_code = widget.currentData()
        if status_code is not None:
            avail = self.avail_repo.get_by_ids(singer_id, self.event.id)
            if not avail or avail.status != status_code:
                self.avail_repo.update(singer_id, self.event.id, status_code)

    def accept(self):
        """Save availability using per-row dropdown widgets."""
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue
            singer_id = name_item.data(Qt.ItemDataRole.UserRole)
            status_widget = self.table.cellWidget(row, 2)
            if isinstance(status_widget, QComboBox):
                status_code = status_widget.currentData()
                if status_code is not None:
                    avail = self.avail_repo.get_by_ids(singer_id, self.event.id)
                    if not avail or avail.status != status_code:
                        self.avail_repo.update(singer_id, self.event.id, status_code)
        super().accept()

    def _export_pdf(self):
        """Export availability to PDF."""
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
        from pathlib import Path

        singers = self.singer_repo.get_active()

        event_date = (
            self.event.date[:10]
            if self.event.date and len(self.event.date) >= 10
            else "ohne Datum"
        )
        event_type = self.event.event_type or "ohne Typ"

        project_name = ""
        if self.event.project_id:
            from ...domain.repository import ProjectRepository

            project_repo = ProjectRepository(self.db)
            project = project_repo.get_by_id(self.event.project_id)
            if project:
                project_name = project.name

        filename_str = f"{event_date}-{event_type}"
        if project_name:
            filename_str += f"-{project_name}"
        filename_str += ".pdf"

        export_dir = Path("/media/data/coding/chormanager/workdir")
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = export_dir / filename_str

        doc = SimpleDocTemplate(str(filename), pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=14, spaceAfter=10
        )

        event_date = (
            self.event.date[:10]
            if self.event.date and len(self.event.date) >= 10
            else "ohne Datum"
        )
        event_type = self.event.event_type or "ohne Typ"

        project_name = ""
        if self.event.project_id:
            from ...domain.repository import ProjectRepository

            project_repo = ProjectRepository(self.db)
            project = project_repo.get_by_id(self.event.project_id)
            if project:
                project_name = project.name

        filename_str = f"{event_date}-{event_type}"
        if project_name:
            filename_str += f"-{project_name}"
        filename_str += ".pdf"

        export_dir = Path("/media/data/coding/chormanager/workdir")
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = export_dir / filename_str

        elements.append(Paragraph(f"Verfügbarkeit: {self.event.name}", title_style))
        elements.append(
            Paragraph(
                f"Datum: {event_date} | Typ: {event_type}"
                + (f" | Projekt: {project_name}" if project_name else ""),
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.3 * cm))

        status_labels = {
            "yes": "✓ Verfügbar / Zusage",
            "no": "✗ Nicht verfügbar / Absage",
            "none": "○ Keine Rückmeldung",
            "conditional": "✓? Zusage unter Vorbehalt",
            "unknown": "? Weiß nicht",
            "maybe": "~ Vielleicht",
            "": "-",
        }

        voice_group_order = [
            "Sopran 1",
            "Sopran 2",
            "Alt 1",
            "Alt 2",
            "Tenor 1",
            "Tenor 2",
            "Bass 1",
            "Bass 2",
        ]

        singers_by_group = {}
        for singer in singers:
            vg = singer.voice_group or "Ohne Stimmgruppe"
            if vg not in singers_by_group:
                singers_by_group[vg] = []
            singers_by_group[vg].append(singer)

        for vg in singers_by_group:
            singers_by_group[vg] = sorted(
                singers_by_group[vg], key=lambda s: s.short_name or s.full_name or ""
            )

        def voice_group_sort_key(vg):
            vg = vg or "ZzZ"
            for i, prefix in enumerate(voice_group_order):
                if vg.startswith(prefix):
                    return (i, vg)
            return (len(voice_group_order), vg)

        sorted_groups = sorted(singers_by_group.keys(), key=voice_group_sort_key)

        for vg in sorted_groups:
            group_singers = singers_by_group[vg]
            elements.append(Paragraph(f"<b>{vg}</b>", styles["Heading2"]))

            table_data = [["Name", "Status"]]
            for singer in group_singers:
                avail = self.avail_repo.get_by_ids(singer.id, self.event.id)
                status = status_labels.get(avail.status if avail else "", "-")
                table_data.append(
                    [
                        singer.short_name or singer.full_name or "",
                        status,
                    ]
                )

            table = Table(table_data, colWidths=[6 * cm, 6 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ]
                )
            )

            elements.append(table)
            elements.append(Spacer(1, 0.2 * cm))

        doc.build(elements)

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")

    def _export_availability(self):
        """Export availability to file with field selection."""
        avail_fields = [
            {"name": "short_name", "label": "Kurzname"},
            {"name": "voice_group", "label": "Stimmgruppe"},
            {"name": "status", "label": "Status"},
        ]

        from ...ui.export_dialog import ExportDialog

        dialog = ExportDialog(avail_fields, self)
        if not dialog.exec():
            return

        selected_fields = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected_fields:
            QMessageBox.warning(self, "Warnung", "Keine Felder ausgewählt.")
            return

        from ...core.export_service import ExportService
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        from datetime import datetime

        singers = self.singer_repo.get_active()

        if self.besetzung_ids is not None:
            singers = [s for s in singers if s.id in self.besetzung_ids]

        VG_ORDER = [
            "Sopran 1",
            "Sopran 2",
            "Alt 1",
            "Alt 2",
            "Tenor 1",
            "Tenor 2",
            "Bass 1",
            "Bass 2",
        ]

        def sort_key(singer):
            vg = singer.voice_group or ""
            vg_idx = VG_ORDER.index(vg) if vg in VG_ORDER else 999
            return (vg_idx, singer.short_name or singer.full_name or "")

        singers_sorted = sorted(singers, key=sort_key)

        status_labels = {
            "yes": "Zusage",
            "no": "Absage",
            "none": "Offen",
            "conditional": "Vorbehalt",
            "unknown": "Weiß nicht",
            "maybe": "Vielleicht",
        }

        data = []
        for s in singers_sorted:
            row = {}
            if "short_name" in selected_fields:
                row["short_name"] = s.short_name or s.full_name or ""
            if "voice_group" in selected_fields:
                row["voice_group"] = s.voice_group or ""
            if "status" in selected_fields:
                avail = self.avail_repo.get_by_ids(s.id, self.event.id)
                status_code = avail.status if avail else "none"
                row["status"] = status_labels.get(status_code, status_code)
            data.append(row)

        service = ExportService()
        if fmt == "writer":
            content_out = service.export_to_libreoffice_writer(data, selected_fields)
            ext_filter = "LibreOffice Writer (*.odt)"
        elif fmt == "calc":
            content_out = service.export_to_libreoffice_calc(data, selected_fields)
            ext_filter = "LibreOffice Calc (*.ods)"
        else:
            content_out = service.export_to_csv(data, selected_fields)
            ext_filter = "CSV (*.csv)"

        today = datetime.now().strftime("%Y-%m-%d")
        safe_event = self.event.name.replace(" ", "-").replace("/", "-")
        ext_map = {"writer": "odt", "calc": "ods", "csv": "csv"}
        ext = ext_map.get(fmt, "csv")
        default_name = f"{today}-verfuegbarkeit-{safe_event}.{ext}"
        workdir = Path(__file__).parent.parent.parent / "workdir"
        workdir.mkdir(exist_ok=True)
        default_path = str(workdir / default_name)

        filename, _ = QFileDialog.getSaveFileName(
            self, "Verfügbarkeit exportieren", default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content_out)

        QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")

