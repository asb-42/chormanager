"""Singers tab view for ChorManager."""

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
    QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter

from ...data.database import Database
from ...domain.repository import SingerRepository
from ...config import load_voice_groups, load_fields


class PaddedDelegate(QStyledItemDelegate):
    """Custom delegate with padding for better text display."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), size.height() + 6)

    def paint(self, painter, option, index):
        option.rect = option.rect.adjusted(0, 3, 0, -3)
        super().paint(painter, option, index)


class SingersTab(QWidget):
    """Tab widget for singer management."""

    def __init__(self, db: Database, parent=None):
        """Initialize singers tab.

        Args:
            db: Database instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.db = db
        self.singer_repo = SingerRepository(db)

        self._setup_ui()
        self._load_singers()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)

        # Seitentitel
        title = QLabel("👤 Sängerverwaltung")
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
        self.search_box.textChanged.connect(self._load_singers)
        toolbar.addWidget(self.search_box)

        self.voice_filter = QComboBox()
        self.voice_filter.addItem("Alle Stimmgruppen", None)

        voice_groups = load_voice_groups()
        for vg in voice_groups:
            self.voice_filter.addItem(vg["name"], vg["name"])

        self.voice_filter.currentIndexChanged.connect(self._load_singers)
        toolbar.addWidget(self.voice_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Alle Mitglieder", "all")
        self.status_filter.addItem("Alle aktiven Mitglieder", "active")
        self.status_filter.addItem("Alle minderjährigen", "minor")
        self.status_filter.addItem("Alle U16", "u16")
        self.status_filter.currentIndexChanged.connect(self._load_singers)
        toolbar.addWidget(self.status_filter)

        self.besetzung_filter = None

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_singer)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        visible_fields = [
            "full_name",
            "short_name",
            "voice_group",
            "gender",
            "birth_date",
            "is_adult",
            "email",
            "phone",
            "postal_code",
            "city",
        ]
        fields = load_fields()
        self.visible_fields = [f for f in fields if f["name"] in visible_fields] + [
            {"name": "id", "label": "UUID"}
        ]

        self.project_filter = None

        self.table.setColumnCount(len(self.visible_fields))

        headers = [f["label"] for f in self.visible_fields]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)

        # Apply custom delegate with padding
        self.table.setItemDelegate(PaddedDelegate())

        layout.addWidget(self.table)

    def set_project_filter(self, project):
        """Set project filter - only show singers with availability in project events."""
        self.project_filter = project
        self._load_singers()

    def set_besetzung_filter(self, besetzung):
        """Set Besetzung filter - only show singers in the besetzung."""
        self.besetzung_filter = besetzung
        self._load_singers()

    def _load_singers(self):
        """Load singers into table with filters."""
        from datetime import datetime
        from ...domain.repository import EventRepository, AvailabilityRepository

        search_text = self.search_box.text().lower() if self.search_box.text() else ""
        voice_filter = self.voice_filter.currentData()
        status_filter = self.status_filter.currentData()

        singers = self.singer_repo.get_all()

        if self.project_filter:
            from ...domain.repository import EventRepository

            event_repo = EventRepository(self.db)
            all_events = event_repo.get_all()
            project_event_ids = [
                e.id for e in all_events if e.project_id == self.project_filter.id
            ]
            if project_event_ids:
                singers = self.singer_repo.get_all()

        if self.besetzung_filter:
            singer_ids = self.besetzung_filter.get_singer_ids()
            singers = [s for s in singers if s.id in singer_ids]

        # Apply status filter (all/active/minor/u16)
        if status_filter and status_filter != "all":
            filtered = []
            for singer in singers:
                if status_filter == "active":
                    # Active = no exit date
                    if not singer.left_year and not singer.left_month:
                        filtered.append(singer)
                elif status_filter == "minor":
                    # Minor = under 18 years old
                    age = singer.age()
                    if age is not None and age < 18:
                        filtered.append(singer)
                elif status_filter == "u16":
                    # U16 = under 16 years old
                    age = singer.age()
                    if age is not None and age < 16:
                        filtered.append(singer)
            singers = filtered

        if search_text or voice_filter:
            filtered = []
            for singer in singers:
                if voice_filter and singer.voice_group != voice_filter:
                    continue

                if search_text:
                    search_fields = [
                        singer.full_name or "",
                        singer.short_name or "",
                        singer.email or "",
                        singer.phone or "",
                        singer.address or "",
                    ]
                    if not any(search_text in str(f).lower() for f in search_fields):
                        continue

                filtered.append(singer)
            singers = filtered

        self.table.setRowCount(len(singers))

        for row, singer in enumerate(singers):
            for col, field in enumerate(self.visible_fields):
                name = field["name"]
                field_type = field.get("type", "string")

                if name == "is_adult":
                    age = singer.age()
                    value = str(age) if age is not None else ""
                elif (
                    field_type == "computed"
                    and field.get("computed_from") == "birth_date"
                ):
                    age = singer.age()
                    value = str(age) if age is not None else ""
                else:
                    value = getattr(singer, name, "")

                if value is None:
                    value = ""

                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, singer.id)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def _add_singer(self):
        """Add new singer."""
        from ..main_window import SingerDialog

        dialog = SingerDialog(parent=self)

        if dialog.exec():
            data = dialog.get_data()
            data = {k: v for k, v in data.items() if v is not None}
            self.singer_repo.create(**data)
            self._load_singers()

    def _edit_singer(self):
        """Edit selected singer."""
        from PyQt6.QtWidgets import QMessageBox
        from ..main_window import SingerDialog

        current_row = self.table.currentRow()

        if current_row < 0:
            QMessageBox.information(
                self, "Information", "Bitte wählen Sie einen Sänger aus"
            )
            return

        item = self.table.item(current_row, 0)
        singer_id = item.data(Qt.ItemDataRole.UserRole)

        singer = self.singer_repo.get_by_id(singer_id)

        if not singer:
            return

        dialog = SingerDialog(singer=singer, parent=self)

        if dialog.exec():
            data = dialog.get_data()

            data = {k: v for k, v in data.items() if v is not None}

            self.singer_repo.update(singer_id, **data)
            self._load_singers()

    def _delete_singer(self):
        """Delete selected singer."""
        from PyQt6.QtWidgets import QMessageBox

        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, "Information", "Bitte wählen Sie einen Sänger aus"
            )
            return

        item = self.table.item(current_row, 0)
        singer_id = item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Löschen",
            "Möchten Sie diesen Sänger wirklich löschen?\n\n"
            "Alle Verknüpfungen (Verfügbarkeiten) werden ebenfalls gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.singer_repo.delete(singer_id)
            self._load_singers()

    def _duplicate_singer(self):
        """Duplicate selected singer."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        item = self.table.item(current_row, 0)
        singer_id = item.data(Qt.ItemDataRole.UserRole)

        singer = self.singer_repo.get_by_id(singer_id)
        if not singer:
            return

        # Create duplicate with "(Kopie)" suffix
        singer_dict = singer.to_dict()
        singer_dict.pop("id", None)
        singer_dict.pop("created_at", None)
        singer_dict.pop("updated_at", None)
        singer_dict["full_name"] = f"{singer.full_name} (Kopie)"

        self.singer_repo.create(**singer_dict)
        self._load_singers()

    def _show_context_menu(self, pos):
        """Show context menu."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        dup_action = menu.addAction("Duplizieren")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == edit_action:
            self._edit_singer()
        elif action == dup_action:
            self._duplicate_singer()
