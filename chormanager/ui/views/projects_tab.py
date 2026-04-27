"""Projects tab view for ChorManager."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QLabel,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QLineEdit as QLineEditW,
    QTextEdit,
    QStyledItemDelegate,
    QComboBox,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPainter

from ...data.database import Database
from ...domain.repository import ProjectRepository, EventRepository
from ...config import get_last_active_project_id, set_last_active_project_id

class PaddedDelegate(QStyledItemDelegate):
    """Custom delegate with padding for better text display."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), size.height() + 10)

    def paint(self, painter, option, index):
        option.rect = option.rect.adjusted(0, 5, 0, -5)
        super().paint(painter, option, index)

class ProjectDialog:
    """Dialog for adding/editing projects."""

    def __init__(self, project=None, parent=None):
        """Initialize dialog."""
        self.dialog = QDialog(parent)
        self.project = project

        layout = QFormLayout(self.dialog)

        self.name_input = QLineEditW()
        layout.addRow("Name:", self.name_input)

        self.spielzeit_input = QLineEdit()
        self.spielzeit_input.setMaxLength(25)
        layout.addRow("Spielzeit:", self.spielzeit_input)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        layout.addRow("Beschreibung:", self.description_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.dialog.accept)
        button_box.rejected.connect(self.dialog.reject)
        layout.addRow(button_box)

        if project:
            self.name_input.setText(project.name)
            if project.description:
                self.description_input.setPlainText(project.description)
            if project.spielzeit:
                self.spielzeit_input.setText(project.spielzeit)

            self.dialog.setWindowTitle("Projekt bearbeiten")
        else:
            self.dialog.setWindowTitle("Neues Projekt")

    def exec(self):
        """Show dialog and return result."""
        return self.dialog.exec()

    def get_data(self):
        """Get form data."""
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "spielzeit": self.spielzeit_input.text().strip(),
        }

class ProjectsTab(QWidget):
    """Tab widget for project management."""

    current_project_changed = pyqtSignal()

    def __init__(self, db: Database, parent=None):
        """Initialize projects tab."""
        super().__init__(parent)
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.event_repo = EventRepository(db)

        self.current_project = None
        self._setup_ui()
        self._load_projects()

    def set_current_project(self, project):
        self.current_project = project
        if project:
            set_last_active_project_id(project.id)
        self.current_project_changed.emit()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._load_projects)
        toolbar.addWidget(self.search_box)
        self.sort_field = QComboBox()
        self.sort_field.addItem("Sortieren nach Name", "name")
        self.sort_field.addItem("Sortieren nach Spielzeit", "spielzeit")
        self.sort_field.currentIndexChanged.connect(self._load_projects)
        toolbar.addWidget(self.sort_field)

        self.sort_order = QComboBox()
        self.sort_order.addItem("Aufsteigend", Qt.SortOrder.AscendingOrder)
        self.sort_order.addItem("Absteigend", Qt.SortOrder.DescendingOrder)
        self.sort_order.currentIndexChanged.connect(self._load_projects)
        toolbar.addWidget(self.sort_order)


        self.sort_field = QComboBox()
        self.sort_field.addItem("Sortieren nach Name", "name")
        self.sort_field.addItem("Sortieren nach Spielzeit", "spielzeit")
        self.sort_field.currentIndexChanged.connect(self._load_projects)
        toolbar.addWidget(self.sort_field)

        self.sort_order = QComboBox()
        self.sort_order.addItem("Aufsteigend", Qt.SortOrder.AscendingOrder)
        self.sort_order.addItem("Absteigend", Qt.SortOrder.DescendingOrder)
        self.sort_order.currentIndexChanged.connect(self._load_projects)
        toolbar.addWidget(self.sort_order)


        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_project)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Spielzeit", "Name", "Beschreibung", "Aktiv", "Anz. Termine"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)

        # Apply custom delegate with padding
        self.table.setItemDelegate(PaddedDelegate())
        self.table.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(self.table)

    def _load_active_project(self):
        """Load the last active project."""
        last_active_id = get_last_active_project_id()
        if last_active_id:
            active = self.project_repo.get_by_id(last_active_id)
            if active:
                self.current_project = active
                self.current_project_changed.emit()

    def _load_projects(self):
        """Load projects into table."""
        search_text = self.search_box.text().lower() if self.search_box.text() else ""

        projects = self.project_repo.get_all()

        if search_text:
            projects = [p for p in projects if search_text in (p.name or "").lower()]

        event_counts = {}
        for p in projects:
            events = self.event_repo.get_all()
            event_counts[p.id] = len([e for e in events if e.project_id == p.id])

        sort_field = self.sort_field.currentData()
        sort_order = self.sort_order.currentData()
        reverse_sort = sort_order == Qt.SortOrder.DescendingOrder

        def get_sort_key(p):
            if sort_field == 'spielzeit':
                return (p.spielzeit or '').lower()
            else:
                return (p.name or '').lower()

        projects = sorted(projects, key=get_sort_key, reverse=reverse_sort)


        last_active_id = get_last_active_project_id()

        self.table.setRowCount(len(projects))

        # Select the active project row (search in full unsorted list)
        if self.current_project:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.text() == self.current_project.name:
                    self.table.selectRow(row)
                    break

        for row, project in enumerate(projects):
            self.table.setItem(row, 0, QTableWidgetItem(project.spielzeit or ""))
            name_item = QTableWidgetItem(project.name or "")
            name_item.setData(Qt.ItemDataRole.UserRole, project.id)
            self.table.setItem(row, 1, name_item)

            desc = project.description or ""
            if len(desc) > 50:
                desc = desc[:47] + "..."
            self.table.setItem(row, 2, QTableWidgetItem(desc))

            is_active = 1 if project.id == last_active_id else 0
            active_text = chr(0x2713) if is_active else ""
            self.table.setItem(row, 3, QTableWidgetItem(active_text))

            event_count = event_counts.get(project.id, 0)
            count_item = QTableWidgetItem(str(event_count))
            count_item.setData(Qt.ItemDataRole.UserRole, event_count)
            self.table.setItem(row, 4, count_item)

        self.table.resizeColumnsToContents()

    def _add_project(self):
        """Add new project."""
        dialog = ProjectDialog(parent=self)

        if dialog.exec():
            data = dialog.get_data()

            if not data.get("name"):
                return

            project = self.project_repo.create(**data)
            self._load_projects()

    def _edit_project(self):
        """Edit selected project."""
        from PyQt6.QtWidgets import QMessageBox

        current_row = self.table.currentRow()

        if current_row < 0:
            return

        item = self.table.item(current_row, 1)
        project_id = item.data(Qt.ItemDataRole.UserRole)

        project = self.project_repo.get_by_id(project_id)

        if not project:
            return

        dialog = ProjectDialog(project=project, parent=self)

        if dialog.exec():
            data = dialog.get_data()
            data = {k: v for k, v in data.items() if v is not None}
            self.project_repo.update(project.id, **data)
            self._load_projects()

    def _show_context_menu(self, pos):
        """Show context menu."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        dup_action = menu.addAction("Duplizieren")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == edit_action:
            self._edit_project()
        elif action == dup_action:
            self._duplicate_project()

    def _duplicate_project(self):
        """Duplicate selected project."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        item = self.table.item(current_row, 0)
        project_id = item.data(Qt.ItemDataRole.UserRole)

        project = self.project_repo.get_by_id(project_id)

        projects = self.project_repo.get_all()

        if not project:
            return

        new_project = self.project_repo.create(
            name=f"{project.name} (Kopie)",
            description=project.description,
            is_active=False,
        )

        dialog = ProjectDialog(project=new_project, parent=self)
        dialog.exec()
        self._load_projects()

    def _delete_project(self):
        """Delete selected project."""
        from PyQt6.QtWidgets import QMessageBox

        current_row = self.table.currentRow()

        if current_row < 0:
            return

        item = self.table.item(current_row, 0)
        project_id = item.data(Qt.ItemDataRole.UserRole)

        project = self.project_repo.get_by_id(project_id)

        projects = self.project_repo.get_all()

        if not project:
            return

        reply = QMessageBox.question(
            self,
            "Löschen",
            "Möchten Sie dieses Projekt wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.project_repo.delete(project.id)

            if self.current_project and self.current_project.id == project.id:
                self.current_project = None

            self._load_projects()

    def _set_active(self):
        """Set selected project as active."""
        current_row = self.table.currentRow()

        if current_row < 0:
            return

        item = self.table.item(current_row, 1)
        project_id = item.data(Qt.ItemDataRole.UserRole)

        project = self.project_repo.get_by_id(project_id)

        if not project:
            return

        self.set_current_project(project)
        self._load_projects()
