import os
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
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt


class ChorAufstellungTab(QWidget):
    """Tab for opening standalone ChorAufstellung app."""

    set_project_filter = pyqtSignal(object)

    def __init__(self, db, parent=None):
        """Initialize the ChorAufstellung tab."""
        super().__init__(parent)
        self.db = db
        self._current_project = None
        self._current_event = None
        self._data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "choraufstellung",
            "data",
        )
        self._data_dir = os.path.normpath(self._data_dir)
        self._setup_ui()
        self._load_formations()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.load_btn = QPushButton("Aus ChorManager laden")
        self.load_btn.clicked.connect(self._load_from_chormanager)
        header.addWidget(self.load_btn)

        layout.addLayout(header)

        # Search box for formations
        search_layout = QHBoxLayout()
        search_layout.addStretch()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._load_formations)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        info_label = QLabel(
            "Klicken Sie auf 'Neue Aufstellung', um eine Aufstellung für einen Termin zu erstellen."
        )
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)
        self.table = QTableWidget()
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Dateiname", "Dateigröße", "Projekt", "Termin", "Typ", "Gespeichert"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def set_project(self, project):
        """Set the current project."""
        self._current_project = project

    def set_event(self, event):
        """Set the current event."""
        self._current_event = event

    def _new_formation(self):
        from ..dialogs import NewFormationDialog

        main_window = self.window()
        projects_tab = getattr(main_window, "projects_tab", None)
        current_project = projects_tab.current_project if projects_tab else None

        dialog = NewFormationDialog(self.db, current_project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        event = dialog.get_event()
        if not event:
            return

        if hasattr(main_window, "_open_choraufstellung_for_event"):
            main_window._open_choraufstellung_for_event(event)
        else:
            QMessageBox.warning(
                self, "Fehler", "Funktion zum Öffnen der Choraufstellung nicht verfügbar."
            )

    def _load_from_chormanager(self, event=None):
        try:
            main_window = self.window()
            
            #Check for pending event from NewFormationDialog
            event = event or getattr(self, "_pending_event", None)
            if event:
                self._pending_event = None
                main_window._open_choraufstellung_for_event(event)
                return
            
            if not hasattr(main_window, "_open_choraufstellung"):
                QMessageBox.information(
                    self,
                    "Info",
                    "Bitte nutzen Sie: Menü → Choraufstellung → In Choraufstellung öffnen",
                )
                return

            main_window._open_choraufstellung()

        except Exception as e:
            QMessageBox.warning(
                self, "Fehler", f"Fehler beim Öffnen der Choraufstellung:\n{str(e)}"
            )

    def _load_formations(self):
        """Load formations from data directory with search filter."""
        if not os.path.exists(self._data_dir):
            self.table.setRowCount(0)
            return

        search_text = (
            self.search_box.text().lower()
            if hasattr(self, "search_box") and self.search_box.text()
            else ""
        )

        files = []
        for f in os.listdir(self._data_dir):
            if f.endswith(".json"):
                fp = os.path.join(self._data_dir, f)
                stats = os.stat(fp)
                data = {
                    "filename": f,
                    "size": stats.st_size,
                    "modified": stats.st_mtime,
                }

                try:
                    with open(fp, "r", encoding="utf-8") as jf:
                        content = json.load(jf)
                        data["metadata"] = content.get("metadata", {})
                        data["saved_at"] = content.get("saved_at", "")
                        data["version"] = content.get("version", "")
                except:
                    data["metadata"] = {}
                    data["saved_at"] = ""

                files.append(data)

        files.sort(key=lambda x: x["modified"], reverse=True)

        # Apply search filter
        if search_text:
            filtered_files = []
            for f in files:
                meta = f.get("metadata", {})
                search_fields = [
                    f["filename"],
                    meta.get("project", ""),
                    meta.get("event", ""),
                    meta.get("event_date", ""),
                ]
                if any(search_text in str(field).lower() for field in search_fields):
                    filtered_files.append(f)
            files = filtered_files

        self.table.setRowCount(len(files))
        for row, f in enumerate(files):
            meta = f.get("metadata", {})

            self.table.setItem(row, 0, QTableWidgetItem(f["filename"]))
            # Dateigröße
            size = f.get("size", 0)
            size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
            self.table.setItem(row, 1, QTableWidgetItem(size_str))
            self.table.setItem(row, 2, QTableWidgetItem(meta.get("project", "")))
            # Termin (event_date)
            event_date = meta.get("event_date", "")
            if event_date:
                event_date = event_date[:10]
            self.table.setItem(row, 3, QTableWidgetItem(event_date))
            # Typ (event - der Event-Name)
            self.table.setItem(row, 4, QTableWidgetItem(meta.get("event", "")))

            saved = f.get("saved_at", "")
            if saved:
                try:
                    dt = datetime.fromisoformat(saved)
                    saved = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            self.table.setItem(row, 5, QTableWidgetItem(saved))

        self.table.resizeColumnsToContents()

    def _show_context_menu(self, pos):
        """Show context menu."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        dup_action = menu.addAction("Duplizieren")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == edit_action:
            self._edit_formation()
        elif action == dup_action:
            self._duplicate_formation()

    def _edit_formation(self):
        """Open formation in external editor."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        filename = self.table.item(current_row, 0).text()
        filepath = os.path.join(self._data_dir, filename)

        main_window = self.window()
        if hasattr(main_window, "_open_choraufstellung_file"):
            main_window._open_choraufstellung_file(filepath)
        else:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Info",
                f"Datei kann nicht direkt geöffnet werden.\nDateipfad: {filepath}",
            )

    def _duplicate_formation(self):
        """Duplicate selected formation."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        source_file = self.table.item(current_row, 0).text()
        source_path = os.path.join(self._data_dir, source_file)

        project_name, ok1 = QInputDialog.getText(self, "Duplizieren", "Projektname:")
        if not ok1 or not project_name:
            return

        event_name, ok2 = QInputDialog.getText(self, "Duplizieren", "Termin (Datum):")
        if not ok2 or not event_name:
            return

        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        new_filename = f"choraufstellung-{event_name[:10]}-version-{today}.json"
        new_path = os.path.join(self._data_dir, new_filename)

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["metadata"] = {"project": project_name, "event": event_name}
            data["saved_at"] = datetime.now().isoformat()
            data["version"] = "1.0"

            with open(new_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._load_formations()

        except Exception as e:
            QMessageBox.warning(
                self, "Fehler", f"Duplizieren fehlgeschlagen:\n{str(e)}"
            )

    def _delete_formation(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        filename = self.table.item(current_row, 0).text()
        filepath = os.path.join(self._data_dir, filename)

        reply = QMessageBox.question(
            self,
            "Löschen bestätigen",
            f"Möchten Sie '{filename}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            os.remove(filepath)
            self._load_formations()
        except Exception as e:
            QMessageBox.warning(
                self, "Fehler", f"Löschen fehlgeschlagen:\n{str(e)}"
            )

    def has_formation_for_event(self, event):
        """Check if a formation file exists for the given event."""
        if not event or not event.name:
            return False
        for row in range(self.table.rowCount()):
            filename = self.table.item(row, 0)
            if filename and event.name[:10] in filename.text():
                return True
        return False

    def load_for_event(self, event):
        """Load formation data for a specific event."""
        self._load_from_chormanager()
