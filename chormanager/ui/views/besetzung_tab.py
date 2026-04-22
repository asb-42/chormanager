import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QInputDialog,
    QComboBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ...domain.repository import BesetzungRepository, ProjectRepository
from ...data.database import Database


class BesetzungTab(QWidget):
    """Tab for managing Besetzung (singer lineups)."""

    set_besetzung_filter = pyqtSignal(object)

    def __init__(self, db, parent=None):
        """Initialize the Besetzung tab."""
        super().__init__(parent)
        self.db = db
        self.besetzung_repo = BesetzungRepository(db)
        self.project_repo = ProjectRepository(db)
        self.current_project = None
        self._setup_ui()
        self._load_besetzungen()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        page_title = QLabel("👥 Besetzungen")
        page_title.setObjectName("pageTitle")
        page_title.setStyleSheet(
            "font-size: 18pt; font-weight: bold; color: #2c3e50; margin-bottom: 10px;"
        )
        layout.addWidget(page_title)

        toolbar = QHBoxLayout()

        self.new_btn = QPushButton("Neue Besetzung")
        self.new_btn.clicked.connect(self._new_besetzung)
        toolbar.addWidget(self.new_btn)

        self.addWidget = QPushButton("Bearbeiten")
        self.addWidget.clicked.connect(self._edit_besetzung)
        toolbar.addWidget(self.addWidget)

        self.delete_btn = QPushButton("Löschen")
        self.delete_btn.clicked.connect(self._delete_besetzung)
        toolbar.addWidget(self.delete_btn)

        toolbar.addStretch()

        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("Projekt:"))
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        project_layout.addWidget(self.project_combo)
        toolbar.addLayout(project_layout)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Projekt", "Anzahl Sänger", "Zuletzt gespeichert"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_besetzung)
        layout.addWidget(self.table)

    def _load_besetzungen(self):
        """Load all besetzungen."""
        besetzungen = self.besetzung_repo.get_all()

        self.table.setRowCount(len(besetzungen))

        for row, besetzung in enumerate(besetzungen):
            self.table.setItem(row, 0, QTableWidgetItem(besetzung.name))

            project = self.project_repo.get_by_id(besetzung.project_id)
            project_name = project.name if project else "-"
            self.table.setItem(row, 1, QTableWidgetItem(project_name))

            singer_ids = besetzung.get_singer_ids()
            self.table.setItem(row, 2, QTableWidgetItem(str(len(singer_ids))))

            try:
                dt = datetime.fromisoformat(besetzung.updated_at)
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, OSError):
                date_str = "-"
            self.table.setItem(row, 3, QTableWidgetItem(date_str))

    def _on_project_changed(self, index):
        """Handle project filter change."""
        project_id = self.project_combo.currentData()
        if project_id:
            self.current_project = self.project_repo.get_by_id(project_id)
            self._load_project_besetzungen(project_id)
        else:
            self.current_project = None
            self._load_besetzungen()

    def _load_project_besetzungen(self, project_id):
        """Load besetzungen for a specific project."""
        besetzungen = self.besetzung_repo.get_by_project(project_id)

        self.table.setRowCount(len(besetzungen))

        for row, besetzung in enumerate(besetzungen):
            self.table.setItem(row, 0, QTableWidgetItem(besetzung.name))

            singer_ids = besetzung.get_singer_ids()
            self.table.setItem(row, 1, QTableWidgetItem(str(len(singer_ids))))

            try:
                dt = datetime.fromisoformat(besetzung.updated_at)
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, OSError):
                date_str = "-"
            self.table.setItem(row, 2, QTableWidgetItem(date_str))

    def _load_projects(self):
        """Load projects into combo box."""
        self.project_combo.clear()
        self.project_combo.addItem("Alle Projekte", None)

        projects = self.project_repo.get_all()
        for project in projects:
            self.project_combo.addItem(project.name, project.id)

    def _new_besetzung(self):
        """Create a new besetzung."""
        if not self.current_project:
            QMessageBox.warning(
                self,
                "Kein Projekt",
                "Bitte wählen Sie zuerst ein Projekt aus."
            )
            return

        name, ok = QInputDialog.getText(
            self, "Neue Besetzung", "Name der Besetzung:"
        )
        if not ok or not name:
            return

        dialog = SingerSelectionDialog(self.db)
        if dialog.exec() != QDialog.Accepted:
            return

        singer_ids = dialog.get_selected_ids()
        if not singer_ids:
            QMessageBox.warning(
                self,
                "Keine Sänger",
                "Bitte wählen Sie mindestens einen Sänger aus."
            )
            return

        self.besetzung_repo.create(name, self.current_project.id, singer_ids)
        self._load_besetzungen()

    def _edit_besetzung(self):
        """Edit selected besetzung."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                "Keine Auswahl",
                "Bitte wählen Sie eine Besetzung aus."
            )
            return

        besetzungen = self.besetzung_repo.get_all()
        if row >= len(besetzungen):
            return

        besetzung = besetzungen[row]
        current_ids = besetzung.get_singer_ids()

        dialog = SingerSelectionDialog(self.db, pre_selected_ids=current_ids)
        if dialog.exec() != QDialog.Accepted:
            return

        singer_ids = dialog.get_selected_ids()
        self.besetzung_repo.update(besetzung.id, singer_ids=singer_ids)
        self._load_besetzungen()

    def _delete_besetzung(self):
        """Delete selected besetzung."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                "Keine Auswahl",
                "Bitte wählen Sie eine Besetzung aus."
            )
            return

        besetzungen = self.besetzung_repo.get_all()
        if row >= len(besetzungen):
            return

        besetzung = besetzungen[row]
        reply = QMessageBox.question(
            self,
            "Besetzung löschen",
            f"Möchten Sie die Besetzung '{besetzung.name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.besetzung_repo.delete(besetzung.id)
            self._load_besetzungen()

    def get_besetzung_for_project(self, project_id) -> list:
        """Get all besetzungen for a project."""
        return self.besetzung_repo.get_by_project(project_id)