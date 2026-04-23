"""Events tab view for ChorManager."""

from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QComboBox,
    QLabel,
    QHeaderView,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QAction

from ...data.database import Database
from ...domain.repository import (
    EventRepository,
    SingerRepository,
    AvailabilityRepository,
    ProjectRepository,
)
from ..dialogs import EventDialog


class EventsTab(QWidget):
    """Tab widget for term management."""

    event_selected = pyqtSignal(object)

    def __init__(self, db: Database, parent=None):
        """Initialize events tab."""
        super().__init__(parent)
        self.db = db
        self.event_repo = EventRepository(db)
        self.singer_repo = SingerRepository(db)
        self.avail_repo = AvailabilityRepository(db)
        self.project_repo = ProjectRepository(db)

        self.project_filter = None

        self._setup_ui()
        self._load_events()

    def set_project_filter(self, project):
        """Set project filter - only show events belonging to project."""
        self.project_filter = project
        self._load_events()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)

        # Seitentitel
        title = QLabel("📅 Terminverwaltung")
        title.setObjectName("pageTitle")
        title.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: #2c3e50; margin-bottom: 10px;"
        )
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        toolbar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._load_events)
        toolbar.addWidget(self.search_box)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Alle Typen", None)
        self.type_filter.currentIndexChanged.connect(self._load_events)
        toolbar.addWidget(self.type_filter)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._edit_event)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Datum", "Name", "Typ", "Projekt", "Verbindl. Zusagen", "Vorbehalt"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        # Disable column sorting since we sort by date manually
        self.table.setSortingEnabled(False)

        layout.addWidget(self.table)

        self._load_type_filter()

    def _load_type_filter(self):
        """Load event types into filter."""
        event_types = [
            ("gp", "Generalprobe (GP)"),
            ("op", "Orchesterprobe (OP)"),
            ("sofa", "Auftritt (SOFA)"),
            ("probe", "Probe"),
            ("konzert", "Konzert"),
            ("auftritt", "Auftritt"),
            ("sonstiges", "Sonstiges"),
        ]
        for type_code, type_name in event_types:
            self.type_filter.addItem(type_name, type_code)

    def _on_selection_changed(self, selected, deselected):
        """Handle event selection."""
        rows = self.table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            item = self.table.item(row, 0)
            if item:
                event_id = item.data(Qt.ItemDataRole.UserRole)
                event = self.event_repo.get_by_id(event_id)
                if event:
                    self.event_selected.emit(event)

    def _load_events(self):
        """Load events into table with filters."""
        search_text = self.search_box.text().lower() if self.search_box.text() else ""
        type_filter = self.type_filter.currentData()

        events = self.event_repo.get_all()

        if self.project_filter:
            events = [e for e in events if e.project_id == self.project_filter.id]

        events = sorted(events, key=lambda e: e.date or "")

        if search_text or type_filter:
            filtered = []
            for event in events:
                if type_filter and event.event_type != type_filter:
                    continue

                if search_text:
                    search_fields = [
                        event.name or "",
                        event.description or "",
                        event.event_type or "",
                    ]
                    if not any(search_text in str(f).lower() for f in search_fields):
                        continue

                filtered.append(event)
            events = filtered

        self.table.setRowCount(len(events))

        event_type_labels = {
            "gp": "GP",
            "op": "OP",
            "sofa": "SOFA",
            "probe": "Probe",
            "konzert": "Konzert",
            "auftritt": "Auftritt",
            "sonstiges": "Sonstiges",
        }

        for row, event in enumerate(events):
            date_display = ""
            if event.date and len(event.date) >= 10:
                try:
                    dt = datetime.strptime(event.date[:10], "%Y-%m-%d")
                    date_display = dt.strftime("%d.%m.%Y")
                except:
                    date_display = event.date[:10]

            date_item = QTableWidgetItem(date_display)
            date_item.setData(Qt.ItemDataRole.UserRole, event.id)
            self.table.setItem(row, 0, date_item)

            self.table.setItem(row, 1, QTableWidgetItem(event.name or ""))

            type_label = event_type_labels.get(event.event_type, event.event_type or "")
            self.table.setItem(row, 2, QTableWidgetItem(type_label))

            project_name = ""
            if event.project_id:
                project = self.project_repo.get_by_id(event.project_id)
                project_name = project.name if project else ""
            self.table.setItem(row, 3, QTableWidgetItem(project_name))

            availabilities = self.avail_repo.get_by_event(event.id)
            yes_count = sum(1 for a in availabilities if a.status == "yes")
            conditional_count = sum(
                1 for a in availabilities if a.status == "conditional"
            )
            self.table.setItem(row, 4, QTableWidgetItem(str(yes_count)))
            self.table.setItem(row, 5, QTableWidgetItem(str(conditional_count)))

        self.table.resizeColumnsToContents()

    def _add_event(self):
        """Add new event."""
        prefilled_project_id = self.project_filter.id if self.project_filter else None
        dialog = EventDialog(
            db=self.db, parent=self, prefilled_project_id=prefilled_project_id
        )

        if dialog.exec():
            data = dialog.get_data()

            if not data.get("name"):
                return

            self.event_repo.create(**data)
            self._load_events()

    def _edit_event(self):
        """Edit selected event."""
        current_row = self.table.currentRow()

        if current_row < 0:
            return

        item = self.table.item(current_row, 0)
        event_id = item.data(Qt.ItemDataRole.UserRole)

        event = self.event_repo.get_by_id(event_id)

        if not event:
            return

        dialog = EventDialog(event=event, db=self.db, parent=self)

        if dialog.exec():
            data = dialog.get_data()

            data = {k: v for k, v in data.items() if v is not None}

            self.event_repo.update(event_id, **data)
            self._load_events()

    def _delete_event(self):
        """Delete selected event."""
        from PyQt6.QtWidgets import QMessageBox

        current_row = self.table.currentRow()

        if current_row < 0:
            return

        item = self.table.item(current_row, 0)
        event_id = item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Löschen",
            "Möchten Sie diesen Termin wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.event_repo.delete(event_id)
            self._load_events()

    def _manage_availability(self):
        """Manage availability for selected event."""
        from PyQt6.QtWidgets import QMessageBox
        from ..dialogs import EventAvailabilityDialog

        current_row = self.table.currentRow()

        if current_row < 0:
            QMessageBox.information(
                self, "Information", "Bitte wählen Sie einen Termin aus"
            )
            return

        item = self.table.item(current_row, 0)
        event_id = item.data(Qt.ItemDataRole.UserRole)

        event = self.event_repo.get_by_id(event_id)

        if not event:
            return

        besetzung_ids = None
        main_window = self.window()
        if hasattr(main_window, "besetzung_tab"):
            active_besetzung = main_window.besetzung_tab.get_active_besetzung()
            if active_besetzung:
                besetzung_ids = active_besetzung.get_singer_ids()
                QMessageBox.information(
                    self, "DEBUG",
                    f"Aktive Besetzung: {active_besetzung.name}\n"
                    f"Anzahl Sänger: {len(besetzung_ids)}"
                )
            else:
                QMessageBox.information(self, "DEBUG", "Keine aktive Besetzung")
        else:
            QMessageBox.information(self, "DEBUG", "Keine besetzung_tab")

        dialog = EventAvailabilityDialog(self.db, event, self, besetzung_ids=besetzung_ids)
        dialog.exec()

        self._load_events()

    def _show_context_menu(self, pos):
        """Show context menu."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        dup_action = menu.addAction("Duplizieren")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == edit_action:
            self._edit_event()
        elif action == dup_action:
            self._duplicate_event()

    def _duplicate_event(self):
        """Duplicate selected event."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        item = self.table.item(current_row, 0)
        event_id = item.data(Qt.ItemDataRole.UserRole)

        event = self.event_repo.get_by_id(event_id)
        if not event:
            return

        new_event = self.event_repo.create(
            name=f"{event.name} (Kopie)",
            date=event.date,
            event_type=event.event_type,
            project_id=event.project_id,
            location=event.location,
            description=event.description,
        )

        dialog = EventDialog(event=new_event, db=self.db, parent=self)
        dialog.exec()
        self._load_events()

    def _set_selected_event(self):
        """Set selected event as active."""
        from PyQt6.QtWidgets import QMessageBox
        from ...config import set_last_active_event_id

        current_row = self.table.currentRow()

        if current_row < 0:
            QMessageBox.information(
                self, "Information", "Bitte wählen Sie einen Termin aus"
            )
            return

        item = self.table.item(current_row, 0)
        event_id = item.data(Qt.ItemDataRole.UserRole)

        event = self.event_repo.get_by_id(event_id)

        if not event:
            return

        set_last_active_event_id(event_id)
        self.event_selected.emit(event)
