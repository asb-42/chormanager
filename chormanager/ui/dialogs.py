"""Dialogs for event management."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDateTimeEdit,
    QTextEdit,
    QPushButton,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QRadioButton,
    QButtonGroup,
    QLabel,
    QScrollArea,
    QWidget,
    QGroupBox,
    QStyledItemDelegate,
    QSizePolicy,
)
from PyQt6.QtCore import QDateTime, Qt

from ..domain.repository import SingerRepository, AvailabilityRepository


AVAILABILITY_STATUS = [
    ("yes", "✓ Verfügbar / Zusage", "yes"),
    ("no", "✗ Nicht verfügbar / Absage", "no"),
    ("none", "○ Keine Rückmeldung", "none"),
    ("conditional", "✓? Zusage unter Vorbehalt", "conditional"),
    ("unknown", "? Weiß nicht", "unknown"),
    ("maybe", "~ Vielleicht", "maybe"),
]


class AvailabilityDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        from PyQt6.QtWidgets import QComboBox

        combo = QComboBox(parent)
        for status_code, status_label, short_label in AVAILABILITY_STATUS:
            combo.addItem(status_label, status_code)
        return combo

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if value is None:
            value = "none"
        i = editor.findData(value)
        if i >= 0:
            editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class AvailabilityDialog(QDialog):
    """Dialog for managing singer availability."""

    def __init__(self, singer_id: str, event_id: str, parent=None):
        """Initialize dialog.

        Args:
            singer_id: Singer ID.
            event_id: Event ID.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.singer_id = singer_id
        self.event_id = event_id
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Verfügbarkeit")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        self.status_combo = QComboBox()
        self.status_combo.addItem("✓ Verfügbar / Zusage", "yes")
        self.status_combo.addItem("✗ Nicht verfügbar / Absage", "no")
        self.status_combo.addItem("○ Keine Rückmeldung", "none")
        self.status_combo.addItem("✓? Zusage unter Vorbehalt", "conditional")
        self.status_combo.addItem("? Weiß nicht", "unknown")
        self.status_combo.addItem("Vielleicht", "maybe")

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_status(self):
        """Get selected status."""
        return self.status_combo.currentData()

    def accept(self):
        from ..domain.repository import AvailabilityRepository
        from ..data.database import Database

        db = Database()
        db.connect()
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(self.singer_id, self.event_id, self.get_status())
        db.close()
        super().accept()


class EventDialog(QDialog):
    """Dialog for creating/editing events."""

    def __init__(self, event=None, db=None, parent=None, prefilled_project_id=None):
        """Initialize dialog.

        Args:
            event: Event to edit, or None for new event.
            db: Database instance for loading projects.
            parent: Parent widget.
            prefilled_project_id: Pre-filled project ID for new events.
        """
        super().__init__(parent)
        self.event = event
        self.db = db
        self.prefilled_project_id = prefilled_project_id
        self._setup_ui(db)

        if event:
            self._populate_from_event()
        elif prefilled_project_id:
            self._select_project(prefilled_project_id)

    def _setup_ui(self, db=None):
        """Set up the UI."""
        from ..domain.repository import ProjectRepository

        self.setWindowTitle(
            "Termin hinzufügen" if not self.event else "Termin bearbeiten"
        )
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        layout.addRow("Name:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Generalprobe (GP)", "gp")
        self.type_combo.addItem("Orchesterprobe (OP)", "op")
        self.type_combo.addItem("Auftritt (SOFA)", "sofa")
        self.type_combo.addItem("Probe", "probe")
        self.type_combo.addItem("Konzert", "konzert")
        self.type_combo.addItem("Auftritt", "auftritt")
        self.type_combo.addItem("Sonstiges", "sonstiges")
        layout.addRow("Typ:", self.type_combo)

        self.date_input = QDateTimeEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDateTime(QDateTime.currentDateTime())
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        layout.addRow("Datum/Zeit:", self.date_input)

        self.project_combo = QComboBox()
        self.project_combo.addItem("(keins)", None)
        if db:
            project_repo = ProjectRepository(db)
            projects = project_repo.get_all()
            for p in projects:
                self.project_combo.addItem(p.name, p.id)
        layout.addRow("Projekt:", self.project_combo)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        layout.addRow("Beschreibung:", self.description_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def _populate_from_event(self):
        """Populate fields from event data."""
        self.name_input.setText(self.event.name)

        index = self.type_combo.findData(self.event.event_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        if self.event.date:
            dt = QDateTime.fromString(self.event.date, Qt.DateFormat.ISODate)
            if dt.isValid():
                self.date_input.setDateTime(dt)

        if self.event.description:
            self.description_input.setPlainText(self.event.description)

        if self.event.project_id:
            index = self.project_combo.findData(self.event.project_id)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)

    def _select_project(self, project_id):
        """Pre-select project in combo box."""
        index = self.project_combo.findData(project_id)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)

    def get_data(self):
        """Get form data as dictionary."""
        data = {
            "name": self.name_input.text().strip(),
            "event_type": self.type_combo.currentData(),
            "date": self.date_input.dateTime().toString(Qt.DateFormat.ISODate),
            "description": self.description_input.toPlainText().strip(),
            "project_id": self.project_combo.currentData(),
        }
        return data


class EventListDialog(QDialog):
    """Dialog showing events and their availability."""

    def __init__(self, db, parent=None, active_event_id=None):
        super().__init__(parent)
        self.db = db
        self.active_event_id = active_event_id
        self._setup_ui()
        self._load_events()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Verfügbarkeit verwalten")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

        self.event_combo = QComboBox()
        self.event_combo.currentIndexChanged.connect(self._on_event_changed)
        layout.addWidget(self.event_combo)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Sänger", "Stimmgruppe", "Status"])
        layout.addWidget(self.table)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_events(self):
        """Load events into combo box."""
        from ..domain.repository import EventRepository

        repo = EventRepository(self.db)

        if self.active_event_id:
            event = repo.get_by_id(self.active_event_id)
            if event:
                self.event_combo.addItem(f"{event.name} ({event.date})", event.id)
                self.event_combo.setCurrentIndex(0)
        else:
            events = repo.get_all()
            for event in events:
                self.event_combo.addItem(f"{event.name} ({event.date})", event.id)

    def _on_event_changed(self, index):
        """Handle event selection change."""
        event_id = self.event_combo.currentData()
        if not event_id:
            return

        self._load_availability(event_id)

    def _load_availability(self, event_id: str):
        """Load availability for selected event."""
        from ..domain.repository import SingerRepository, AvailabilityRepository

        singer_repo = SingerRepository(self.db)
        avail_repo = AvailabilityRepository(self.db)

        singers = singer_repo.get_all()

        self.table.setRowCount(len(singers))

        self.status_widgets = {}

        for row, singer in enumerate(singers):
            name_item = QTableWidgetItem(singer.full_name or "")
            name_item.setData(Qt.ItemDataRole.UserRole, singer.id)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(singer.voice_group or ""))

            avail = avail_repo.get_by_ids(singer.id, event_id)
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

            self.table.setCellWidget(row, 2, status_combo)
            self.table.setColumnWidth(2, 200)
            self.table.setRowHeight(row, 60)

            self.status_widgets[singer.id] = (status_combo, current_status)

        self.table.resizeColumnsToContents()
        # Ensure vertical header height accommodates dropdowns
        try:
            self.table.verticalHeader().setDefaultSectionSize(60)
        except Exception:
            pass

    def accept(self):
        event_id = self.event_combo.currentData()
        if not event_id:
            super().accept()
            return

        from ..domain.repository import AvailabilityRepository

        avail_repo = AvailabilityRepository(self.db)

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue
            singer_id = name_item.data(Qt.ItemDataRole.UserRole)
            status_widget = self.table.cellWidget(row, 2)
            if isinstance(status_widget, QComboBox):
                status_code = status_widget.currentData()
                if status_code is not None:
                    avail = avail_repo.get_by_ids(singer_id, event_id)
                    if not avail or avail.status != status_code:
                        avail_repo.update(singer_id, event_id, status_code)
        super().accept()


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

        toolbar = QHBoxLayout()

        export_pdf_btn = QPushButton("Als PDF exportieren")
        export_pdf_btn.clicked.connect(self._export_pdf)
        toolbar.addWidget(export_pdf_btn)

        export_lo_btn = QPushButton("Als LibreOffice exportieren")
        export_lo_btn.clicked.connect(self._export_libreoffice)
        toolbar.addWidget(export_lo_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Kurzname", "Stimmgruppe", "Status"])
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)

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

        singers = self.singer_repo.get_active()

        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=14, spaceAfter=10
        )

        elements.append(Paragraph(f"Verfügbarkeit: {self.event.name}", title_style))
        elements.append(
            Paragraph(
                f"Datum: {self.event.date[:10]} | Typ: {self.event.event_type}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.3 * cm))

        status_symbols = {
            "yes": "✓",
            "no": "✗",
            "none": "○",
            "conditional": "✓?",
            "unknown": "?",
            "maybe": "~",
        }

        table_data = [["Name", "Stimmgruppe", "Status"]]
        for singer in singers:
            avail = self.avail_repo.get_by_ids(singer.id, self.event.id)
            status = status_symbols.get(avail.status if avail else "", "-")
            table_data.append(
                [
                    singer.short_name or singer.full_name or "",
                    singer.voice_group or "",
                    status,
                ]
            )

        table = Table(table_data, colWidths=[5 * cm, 3 * cm, 2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                ]
            )
        )

        elements.append(table)

        doc.build(elements)

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")

    def _export_libreoffice(self):
        """Export availability to LibreOffice."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import subprocess
        import tempfile
        import os

        singers = self.singer_repo.get_active()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            import csv

            writer = csv.writer(f)
            writer.writerow(["Name", "Stimmgruppe", "Status"])

            status_symbols = {
                "yes": "✓",
                "no": "✗",
                "none": "○",
                "conditional": "✓?",
                "unknown": "?",
                "maybe": "~",
            }

            for singer in singers:
                avail = self.avail_repo.get_by_ids(singer.id, self.event.id)
                status = status_symbols.get(avail.status if avail else "", "-")
                writer.writerow(
                    [
                        singer.short_name or singer.full_name or "",
                        singer.voice_group or "",
                        status,
                    ]
                )

            temp_csv = f.name

        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Exportieren", "", "LibreOffice Dateien (*.xls)"
            )

            if not filename:
                return

            out_dir = os.path.dirname(filename) or "."
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "xls",
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
                expected_output = os.path.join(out_dir, base_name + ".xls")
                if expected_output != filename and os.path.exists(expected_output):
                    os.rename(expected_output, filename)
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            else:
                QMessageBox.warning(
                    self, "Fehler", f"LibreOffice Fehler:\n{result.stderr}"
                )

        finally:
            if os.path.exists(temp_csv):
                os.unlink(temp_csv)


class ConfigDialog(QDialog):
    """Dialog for configuration settings."""

    def __init__(self, db=None, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Konfiguration")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        from PyQt6.QtWidgets import QScrollArea, QWidget, QGroupBox

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        data_dir_group = QGroupBox("Datenspeicher")
        data_dir_layout = QFormLayout()

        self.data_dir_input = QLineEdit()
        self.data_dir_input.setText("./data")
        data_dir_layout.addRow("Datenverzeichnis:", self.data_dir_input)

        self.db_filename_input = QLineEdit()
        self.db_filename_input.setText("chor.db")
        data_dir_layout.addRow("Datenbankdatei:", self.db_filename_input)

        reset_btn = QPushButton("Zurücksetzen")
        reset_btn.clicked.connect(lambda: self.data_dir_input.setText("./data"))
        data_dir_layout.addRow("", reset_btn)

        data_dir_group.setLayout(data_dir_layout)
        scroll_layout.addWidget(data_dir_group)

        backup_group = QGroupBox("Backup-Einstellungen")
        backup_layout = QFormLayout()

        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setText("./data/backups")
        backup_layout.addRow("Backup-Verzeichnis:", self.backup_dir_input)

        self.backup_count_input = QLineEdit()
        self.backup_count_input.setText("10")
        backup_layout.addRow("Anzahl Backups:", self.backup_count_input)

        reset_backup_btn = QPushButton("Zurücksetzen")
        reset_backup_btn.clicked.connect(
            lambda: self.backup_dir_input.setText("./data/backups")
        )
        backup_layout.addRow("", reset_backup_btn)

        backup_group.setLayout(backup_layout)
        scroll_layout.addWidget(backup_group)

        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout()

        self.log_level_input = QComboBox()
        self.log_level_input.addItem("INFO", "INFO")
        self.log_level_input.addItem("DEBUG", "DEBUG")
        self.log_level_input.addItem("WARNING", "WARNING")
        self.log_level_input.addItem("ERROR", "ERROR")
        logging_layout.addRow("Log-Level:", self.log_level_input)

        self.log_file_input = QLineEdit()
        self.log_file_input.setText("./data/logs/chormanager.log")
        logging_layout.addRow("Log-Datei:", self.log_file_input)

        reset_log_btn = QPushButton("Zurücksetzen")
        reset_log_btn.clicked.connect(
            lambda: self.log_file_input.setText("./data/logs/chormanager.log")
        )
        logging_layout.addRow("", reset_log_btn)

        logging_group.setLayout(logging_layout)
        scroll_layout.addWidget(logging_group)

        choraufstellung_group = QGroupBox("Choraufstellung-Integration")
        choraufstellung_layout = QFormLayout()

        self.choraufstellung_path_input = QLineEdit()
        self.choraufstellung_path_input.setText("/media/data/coding/choraufstellung")
        choraufstellung_layout.addRow("App-Pfad:", self.choraufstellung_path_input)

        reset_chor_btn = QPushButton("Zurücksetzen")
        reset_chor_btn.clicked.connect(
            lambda: self.choraufstellung_path_input.setText(
                "/media/data/coding/choraufstellung"
            )
        )
        choraufstellung_layout.addRow("", reset_chor_btn)

        choraufstellung_group.setLayout(choraufstellung_layout)
        scroll_layout.addWidget(choraufstellung_group)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_config(self):
        """Load current configuration."""
        pass

    def get_config(self):
        """Get configuration values."""
        return {
            "data_dir": self.data_dir_input.text(),
            "db_filename": self.db_filename_input.text(),
            "backup_dir": self.backup_dir_input.text(),
            "backup_count": self.backup_count_input.text(),
            "log_level": self.log_level_input.currentData(),
            "log_file": self.log_file_input.text(),
            "choraufstellung_path": self.choraufstellung_path_input.text(),
        }


class SelbstdarstellungDialog(QDialog):
    """Dialog for selbstdarstellung (self-presentation) text."""

    def __init__(self, db=None, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        self._load_content()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Selbstdarstellung")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        from PyQt6.QtWidgets import QTextEdit

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Text für Selbstdarstellung eingeben...")
        layout.addWidget(self.text_input)

        self.last_modified_label = QLabel("Zuletzt bearbeitet: -")
        layout.addWidget(self.last_modified_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_content(self):
        """Load content from database."""
        if not self.db:
            return

        result = self.db.execute("SELECT * FROM selbstdarstellung WHERE id = 'main'")
        row = result.fetchone()

        if row:
            row_dict = dict(row)
            self.text_input.setPlainText(row_dict.get("content", ""))
            updated_at = row_dict.get("updated_at", "")
            if updated_at:
                from datetime import datetime

                dt = datetime.fromisoformat(updated_at)
                self.last_modified_label.setText(
                    f"Zuletzt bearbeitet: {dt.strftime('%d.%m.%Y %H:%M')}"
                )

    def _save(self):
        """Save content to database."""
        if not self.db:
            self.accept()
            return

        from datetime import datetime

        content = self.text_input.toPlainText()
        now = datetime.now().isoformat()

        result = self.db.execute("SELECT id FROM selbstdarstellung WHERE id = 'main'")
        if result.fetchone():
            self.db.execute(
                "UPDATE selbstdarstellung SET content = ?, updated_at = ? WHERE id = 'main'",
                (content, now),
            )
        else:
            self.db.execute(
                "INSERT INTO selbstdarstellung (id, content, updated_at) VALUES (?, ?, ?)",
                ("main", content, now),
            )
        self.db.commit()
        self.accept()


class SingerSelectionDialog(QDialog):
    """Dialog for selecting singers for a Besetzung."""

    def __init__(self, db, pre_selected_ids=None, parent=None):
        """Initialize dialog.

        Args:
            db: Database instance.
            pre_selected_ids: List of pre-selected singer IDs.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.db = db
        self.pre_selected_ids = pre_selected_ids or []
        self.selected_ids = set(self.pre_selected_ids)
        self._setup_ui()
        self._load_singers()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Sänger auswählen")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Markieren Sie die Sänger, die zur Besetzung gehören sollen."
        )
        layout.addWidget(info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["✓", "Name", "Kurzname", "Stimmgruppe", "Alter"]
        )
        self.table.setColumnWidth(0, 40)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Alle auswählen")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Alle abwählen")
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(deselect_all_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_singers(self):
        """Load singers into table."""
        singer_repo = SingerRepository(self.db)
        singers = singer_repo.get_all()

        self.table.setRowCount(len(singers))

        from PyQt6.QtWidgets import QCheckBox, QTableWidgetItem
        from PyQt6.QtCore import Qt

        for row, singer in enumerate(singers):
            checkbox = QCheckBox()
            checkbox.setCheckState(
                Qt.CheckState.Checked
                if singer.id in self.selected_ids
                else Qt.CheckState.Unchecked
            )
            checkbox.stateChanged.connect(
                lambda state, sid=singer.id: self._on_checkbox_changed(sid, state)
            )
            self.table.setCellWidget(row, 0, checkbox)

            self.table.setItem(row, 1, QTableWidgetItem(singer.full_name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(singer.short_name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(singer.voice_group or ""))

            age = singer.age()
            self.table.setItem(
                row, 4, QTableWidgetItem(str(age) if age is not None else "-")
            )

    def _on_checkbox_changed(self, singer_id, state):
        """Handle checkbox state change."""
        from PyQt6.QtCore import Qt

        if state == Qt.CheckState.Checked:
            self.selected_ids.add(singer_id)
        else:
            self.selected_ids.discard(singer_id)

    def _select_all(self):
        """Select all singers."""
        singer_repo = SingerRepository(self.db)
        singers = singer_repo.get_all()

        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState.Checked)

        self.selected_ids = {s.id for s in singers}

    def _deselect_all(self):
        """Deselect all singers."""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

        self.selected_ids.clear()

    def get_selected_ids(self) -> list:
        """Get list of selected singer IDs."""
        return list(self.selected_ids)
