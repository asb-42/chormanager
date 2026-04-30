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
    QLineEdit,
    QMenu,
    QComboBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ...domain.repository import RepertoireRepository, ProjectRepository
from ...config import get_last_active_project_id, set_last_active_project_id


class RepertoireTab(QWidget):
    set_repertoire_filter = pyqtSignal(object)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.repertoire_repo = RepertoireRepository(db)
        self.current_project = None
        self._setup_ui()
        self._load_repertoire()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        self.sort_field = QComboBox()
        self.sort_field.addItem("Sortieren nach Komponist", "composer")
        self.sort_field.addItem("Sortieren nach Land", "country")
        self.sort_field.addItem("Sortieren nach Standort", "location")
        self.sort_field.setCurrentIndex(0)
        self.sort_field.currentIndexChanged.connect(self._load_repertoire)
        toolbar.addWidget(self.sort_field)

        self.sort_order = QComboBox()
        self.sort_order.addItem("Aufsteigend", Qt.SortOrder.AscendingOrder)
        self.sort_order.addItem("Absteigend", Qt.SortOrder.DescendingOrder)
        self.sort_order.setCurrentIndex(0)
        self.sort_order.currentIndexChanged.connect(self._load_repertoire)
        toolbar.addWidget(self.sort_order)

        toolbar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._load_repertoire)
        toolbar.addWidget(self.search_box)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Komponist",
                "Titel",
                "Lebensdaten",
                "Land",
                "Verlag",
                "Besetzung",
                "Standort",
                "Programm",
            ]
        )
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._edit_repertoire)
        layout.addWidget(self.table)

    def _load_repertoire(self):
        all_items = self.repertoire_repo.get_all()
        project_repo = ProjectRepository(self.db)
        projects = {p.id: p.name for p in project_repo.get_all()}

        search_text = self.search_box.text().lower() if self.search_box.text() else ""

        if search_text:
            all_items = [
                r
                for r in all_items
                if (
                    search_text in (r.composer or "").lower()
                    or search_text in (r.title or "").lower()
                    or search_text in (r.dates or "").lower()
                    or search_text in (r.country or "").lower()
                    or search_text in (r.publisher or "").lower()
                    or search_text in (r.arrangement or "").lower()
                    or search_text in (r.location or "").lower()
                    or search_text in (projects.get(r.project_id, "") or "").lower()
                )
            ]

        sort_field = self.sort_field.currentData()
        sort_order = self.sort_order.currentData()
        reverse_sort = sort_order == Qt.SortOrder.DescendingOrder

        def get_sort_key(item):
            if sort_field == "composer":
                return (item.composer or "").lower()
            elif sort_field == "country":
                return (item.country or "").lower()
            elif sort_field == "location":
                return (item.location or "").lower()
            return (item.composer or "").lower()

        all_items = sorted(all_items, key=get_sort_key, reverse=reverse_sort)

        self.table.setRowCount(len(all_items))

        for row, rep in enumerate(all_items):
            self.table.setItem(row, 0, QTableWidgetItem(rep.composer or ""))
            self.table.setItem(row, 1, QTableWidgetItem(rep.title or ""))
            self.table.setItem(row, 2, QTableWidgetItem(rep.dates or ""))
            self.table.setItem(row, 3, QTableWidgetItem(rep.country or ""))
            self.table.setItem(row, 4, QTableWidgetItem(rep.publisher or ""))
            self.table.setItem(row, 5, QTableWidgetItem(rep.arrangement or ""))
            self.table.setItem(row, 6, QTableWidgetItem(rep.location or ""))
            project_name = projects.get(rep.project_id, "") if rep.project_id else ""
            self.table.setItem(row, 7, QTableWidgetItem(project_name))

        for i in range(8):
            self.table.resizeColumnToContents(i)

    def set_project(self, project):
        self.current_project = project
        self._load_repertoire()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        add_action = menu.addAction("Hinzufügen")
        edit_action = menu.addAction("Bearbeiten")
        delete_action = menu.addAction("Löschen")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == add_action:
            self._add_repertoire()
        elif action == edit_action:
            self._edit_repertoire()
        elif action == delete_action:
            self._delete_repertoire()

    def _add_repertoire(self):
        from ...ui.dialogs import RepertoireDialog

        dialog = RepertoireDialog(self.db, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._load_repertoire()

    def _edit_repertoire(self):
        row = self.table.currentRow()
        if row < 0:
            return

        composer = self.table.item(row, 0).text()
        title = self.table.item(row, 1).text()

        items = self.repertoire_repo.get_all()
        repertoire = None
        for r in items:
            if r.composer == composer and r.title == title:
                repertoire = r
                break

        if not repertoire:
            return

        from ...ui.dialogs import RepertoireDialog

        dialog = RepertoireDialog(self.db, self, repertoire)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._load_repertoire()

    def _delete_repertoire(self):
        row = self.table.currentRow()
        if row < 0:
            return

        composer = self.table.item(row, 0).text()
        title = self.table.item(row, 1).text()

        items = self.repertoire_repo.get_all()
        repertoire = None
        for r in items:
            if r.composer == composer and r.title == title:
                repertoire = r
                break

        if not repertoire:
            return

        reply = QMessageBox.question(
            self,
            "Löschen bestätigen",
            f"Möchten Sie '{repertoire.title}' von {repertoire.composer} wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.repertoire_repo.delete(repertoire.id)
            self._load_repertoire()
