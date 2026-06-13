""":class:`NewFormationDialog` — pick a project + event for a fresh Choraufstellung.

Extracted from ``chormanager/ui/dialogs/__init__.py`` as part of M-3 Schritt 9.
"""

# Cross-Qt compatibility: PyQt6 first, fall back to PyQt5.
try:
    from PyQt6.QtWidgets import (  # type: ignore
        QDialog,
        QDialogButtonBox,
        QComboBox,
        QFormLayout,
        QLabel,
        QMessageBox,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtWidgets import (  # type: ignore
        QDialog,
        QDialogButtonBox,
        QComboBox,
        QFormLayout,
        QLabel,
        QMessageBox,
        QVBoxLayout,
    )

from ...domain.repository import EventRepository, ProjectRepository


class NewFormationDialog(QDialog):
    def __init__(self, db, current_project=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.event_repo = EventRepository(db)
        self.project_repo = ProjectRepository(db)
        self.current_project = current_project
        self.selected_event = None
        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        self.setWindowTitle("Neue Choraufstellung")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        form.addRow("Projekt:", self.project_combo)

        self.event_combo = QComboBox()
        form.addRow("Termin:", self.event_combo)

        layout.addLayout(form)

        self.info_label = QLabel(
            "Wählen Sie einen Termin aus. Die Sänger mit Zusagen für diesen Termin "
            "werden an die Choraufstellung übergeben."
        )
        self.info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(self.info_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_projects(self):
        self.project_combo.clear()
        projects = self.project_repo.get_all()

        if self.current_project:
            self.project_combo.addItem(self.current_project.name, self.current_project)
            self.project_combo.setEnabled(False)
            self._on_project_changed(0)
        else:
            self.project_combo.addItem("-- Alle Projekte --", None)
            for p in projects:
                self.project_combo.addItem(p.name, p)
            if projects:
                self.project_combo.setCurrentIndex(1)

    def _on_project_changed(self, index):
        self.event_combo.clear()
        project = self.project_combo.currentData()

        if project:
            all_events = self.event_repo.get_all()
            events = [e for e in all_events if e.project_id == project.id]
        else:
            events = self.event_repo.get_all()

        for e in events:
            label = f"{e.date[:10]} - {e.name} ({e.event_type})"
            self.event_combo.addItem(label, e)

    def _on_accept(self):
        self.selected_event = self.event_combo.currentData()
        if not self.selected_event:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie einen Termin aus.")
            return
        self.accept()

    def get_event(self):
        return self.selected_event
