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
    QDialog,
    QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ...domain.repository import BesetzungRepository, ProjectRepository
from ...data.database import Database
from ...ui.dialogs import SingerSelectionDialog
from ...config import get_last_active_besetzung_id, set_last_active_besetzung_id


class BesetzungTab(QWidget):
    """Tab for managing Besetzung (singer lineups)."""

    set_besetzung_filter = pyqtSignal(object)
    active_besetzung_changed = pyqtSignal(object)

    def __init__(self, db, parent=None):
        """Initialize the Besetzung tab."""
        super().__init__(parent)
        self.db = db
        self.besetzung_repo = BesetzungRepository(db)
        self.project_repo = ProjectRepository(db)
        self.current_project = None
        self._active_besetzung = None
        self._setup_ui()
        self._load_besetzungen()
        self._restore_active_besetzung()

    def _restore_active_besetzung(self):
        """Restore previously active besetzung from config."""
        saved_id = get_last_active_besetzung_id()
        if saved_id:
            besetzung = self.besetzung_repo.get_by_id(saved_id)
            if besetzung:
                self._active_besetzung = saved_id
                self.active_besetzung_changed.emit(besetzung)

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

        self.set_active_btn = QPushButton("Als aktiv setzen")
        self.set_active_btn.clicked.connect(self._set_active_besetzung)
        toolbar.addWidget(self.set_active_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Projekt", "Anzahl Sänger", "Zuletzt gespeichert"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_besetzung)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table)

    def _load_besetzungen(self):
        """Load besetzungen for current project."""
        if self.current_project:
            besetzungen = self.besetzung_repo.get_by_project(self.current_project.id)
        else:
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

        dialog = SingerSelectionDialog(self.db, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
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

        if self.current_project:
            besetzungen = self.besetzung_repo.get_by_project(self.current_project.id)
        else:
            besetzungen = self.besetzung_repo.get_all()

        if row >= len(besetzungen):
            return

        besetzung = besetzungen[row]
        current_ids = besetzung.get_singer_ids()

        dialog = SingerSelectionDialog(self.db, pre_selected_ids=current_ids, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
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

    def _set_active_besetzung(self):
        """Set selected besetzung as active for the project."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                "Keine Auswahl",
                "Bitte wählen Sie eine Besetzung aus."
            )
            return

        if self.current_project:
            besetzungen = self.besetzung_repo.get_by_project(self.current_project.id)
        else:
            besetzungen = self.besetzung_repo.get_all()

        if row >= len(besetzungen):
            return

        besetzung = besetzungen[row]
        self._active_besetzung = besetzung.id
        set_last_active_besetzung_id(besetzung.id)
        self.active_besetzung_changed.emit(besetzung)
        QMessageBox.information(
            self,
            "Aktiv gesetzt",
            f"Besetzung '{besetzung.name}' ist jetzt die aktive Besetzung für das Projekt."
        )

    def _show_context_menu(self, position):
        """Show context menu for besetzung table."""
        row = self.table.currentRow()
        if row < 0:
            return

        menu = QMenu()
        menu.addAction("Bearbeiten", self._edit_besetzung)
        menu.addAction("Umbenennen", self._rename_besetzung)
        menu.addAction("Als aktiv setzen", self._set_active_besetzung)
        menu.addSeparator()
        menu.addAction("Löschen", self._delete_besetzung)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _rename_besetzung(self):
        """Rename selected besetzung."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self,
                "Keine Auswahl",
                "Bitte wählen Sie eine Besetzung aus."
            )
            return

        if self.current_project:
            besetzungen = self.besetzung_repo.get_by_project(self.current_project.id)
        else:
            besetzungen = self.besetzung_repo.get_all()

        if row >= len(besetzungen):
            return

        besetzung = besetzungen[row]
        new_name, ok = QInputDialog.getText(
            self, "Besetzung umbenennen",
            "Neuer Name:", text=besetzung.name
        )
        if ok and new_name and new_name != besetzung.name:
            self.besetzung_repo.update(besetzung.id, name=new_name)
            self._load_besetzungen()

    def get_besetzung_for_project(self, project_id) -> list:
        """Get all besetzungen for a project."""
        return self.besetzung_repo.get_by_project(project_id)
    
    def get_active_besetzung(self):
        """Get the currently active besetzung."""
        if self._active_besetzung:
            return self.besetzung_repo.get_by_id(self._active_besetzung)
        return None
    
    def set_active_besetzung(self, besetzung_id):
        """Set the active besetzung for the project."""
        self._active_besetzung = besetzung_id

    def set_project(self, project):
        """Set the current project for this tab."""
        self.current_project = project
        self._load_besetzungen()