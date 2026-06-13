""":class:`EventDialog` + :class:`EventListDialog`.

Extracted from ``chormanager/ui/dialogs/__init__.py`` in M-3 Schritt 3.
Both classes deal with creating, editing, and listing calendar events.
``EventListDialog`` additionally shows a per-event availability table.
"""
from __future__ import annotations

try:
    from PyQt6.QtCore import Qt, QDateTime
    from PyQt6.QtWidgets import (
        QComboBox,
        QDateTimeEdit,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLineEdit,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtCore import Qt, QDateTime  # type: ignore
    from PyQt5.QtWidgets import (  # type: ignore
        QComboBox,
        QDateTimeEdit,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLineEdit,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
    )


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
        from ...domain.repository import ProjectRepository

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
        self.location_input = QLineEdit()
        layout.addRow("Ort:", self.location_input)

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

        if self.event.location:
            self.location_input.setText(self.event.location)

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
            "location": self.location_input.text().strip(),
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
        from ...domain.repository import EventRepository

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

        from ...domain.repository import AvailabilityRepository

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

