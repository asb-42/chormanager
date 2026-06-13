# M-3 Schritt 1: Re-export wrapper for backward compatibility.
# The 12 dialog classes will be incrementally moved into sub-modules
# (_event.py, _config.py, ...) in M-3 Schritte 2-12. The package-level
# re-exports below keep  working.
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
    QMessageBox,
    QFileDialog,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import QDateTime, Qt

from ...domain.repository import (
    SingerRepository,
    AvailabilityRepository,
    EventRepository,
    ProjectRepository,
    RepertoireRepository,
)
from ...config import load_voice_groups

# M-3 Schritt 2: Re-exports for back-compat
from ._availability import (
    AvailabilityDelegate,
    AvailabilityDialog,
    AVAILABILITY_STATUS,
)

# M-3 Schritt 3: Re-exports for back-compat
from ._event import (
    EventDialog,
    EventListDialog,
)

# M-3 Schritt 4: Re-exports for back-compat
from ._event_availability import (
    EventAvailabilityDialog,
)

# M-3 Schritt 5: Re-exports for back-compat
from ._config import (
    ConfigDialog,
)

# M-3 Schritt 6: Re-exports for back-compat
from ._selbstdarstellung import (
    SelbstdarstellungDialog,
)

# M-3 Schritte 7+8: Re-exports for back-compat
from ._singer_selection import (
    SingerSelectionDialog,
)
from ._backup_restore import (
    DropZone,
    BackupRestoreDialog,
)


# M-3 Schritt 9: Re-exports for back-compat
from ._new_formation import (
    NewFormationDialog,
)









class RepertoireDialog(QDialog):
    def __init__(self, db, parent=None, repertoire=None):
        super().__init__(parent)
        self.db = db
        self.repertoire_repo = RepertoireRepository(db)
        self.repertoire = repertoire
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(
            "Repertoire bearbeiten" if self.repertoire else "Neues Repertoire"
        )
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        self.composer_input = QLineEdit()
        self.composer_input.setPlaceholderText("Name des Komponisten")
        layout.addRow("Komponist:", self.composer_input)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Titel des Stücks")
        layout.addRow("Titel:", self.title_input)

        self.dates_input = QLineEdit()
        self.dates_input.setPlaceholderText("z.B. 1803-1870")
        layout.addRow("Lebensdaten:", self.dates_input)

        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("Nationalität")
        layout.addRow("Land:", self.country_input)

        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("Verlag")
        layout.addRow("Verlag:", self.publisher_input)

        self.arrangement_input = QLineEdit()
        self.arrangement_input.setPlaceholderText("z.B. Gemischter Chor")
        layout.addRow("Besetzung:", self.arrangement_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Wo sind die Noten?")
        layout.addRow("Standort:", self.location_input)

        self.program_combo = QComboBox()
        self.program_combo.setPlaceholderText("Programm auswählen")
        self.program_combo.addItem("", "")
        project_repo = ProjectRepository(self.db)
        projects = project_repo.get_all()
        for project in projects:
            self.program_combo.addItem(project.name, project.id)
        layout.addRow("Programm:", self.program_combo)

        if self.repertoire:
            self.composer_input.setText(self.repertoire.composer)
            self.title_input.setText(self.repertoire.title)
            self.dates_input.setText(self.repertoire.dates)
            self.country_input.setText(self.repertoire.country)
            self.publisher_input.setText(self.repertoire.publisher)
            self.arrangement_input.setText(self.repertoire.arrangement)
            self.location_input.setText(self.repertoire.location)
            if self.repertoire.project_id:
                index = self.program_combo.findData(self.repertoire.project_id)
                if index >= 0:
                    self.program_combo.setCurrentIndex(index)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        composer = self.composer_input.text().strip()
        title = self.title_input.text().strip()

        if not title:
            QMessageBox.warning(self, "Warnung", "Titel ist erforderlich.")
            return

        dates = self.dates_input.text().strip()
        country = self.country_input.text().strip()
        publisher = self.publisher_input.text().strip()
        arrangement = self.arrangement_input.text().strip()
        location = self.location_input.text().strip()
        project_id = self.program_combo.currentData() or ""

        if self.repertoire:
            self.repertoire_repo.update(
                self.repertoire.id,
                composer=composer,
                title=title,
                dates=dates,
                country=country,
                publisher=publisher,
                arrangement=arrangement,
                location=location,
                project_id=project_id,
            )
        else:
            self.repertoire_repo.create(
                composer=composer,
                title=title,
                dates=dates,
                country=country,
                publisher=publisher,
                arrangement=arrangement,
                location=location,
                project_id=project_id,
            )

        self.accept()
