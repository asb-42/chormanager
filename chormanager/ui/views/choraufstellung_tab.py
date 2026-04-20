from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal


class ChorAufstellungTab(QWidget):
    """Tab for opening standalone ChorAufstellung app."""
    
    set_project_filter = pyqtSignal(object)
    
    def __init__(self, db, parent=None):
        """Initialize the ChorAufstellung tab."""
        super().__init__(parent)
        self.db = db
        self._current_project = None
        self._current_event = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        self.title_label = QLabel("Choraufstellung")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header.addWidget(self.title_label)
        
        self.load_btn = QPushButton("Aus ChorManager laden")
        self.load_btn.clicked.connect(self._load_from_chormanager)
        header.addWidget(self.load_btn)
        
        layout.addLayout(header)
        
        info_label = QLabel("Klicken Sie auf 'Aus ChorManager laden', um dieChoraufstellung-App mit den Sängern für den gewählten Termin zu öffnen.")
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
    
    def set_project(self, project):
        """Set the current project."""
        self._current_project = project
    
    def set_event(self, event):
        """Set the current event."""
        self._current_event = event
    
    def _load_from_chormanager(self):
        """Open standalone ChorAufstellung app."""
        try:
            if not self._current_project:
                QMessageBox.warning(
                    self,
                    "Kein Projekt",
                    "Bitte wählen Sie zuerst ein Projekt aus."
                )
                return
            
            if not self._current_event or not self._current_event.date:
                QMessageBox.warning(
                    self,
                    "Kein Termin",
                    "Bitte wählen Sie zuerst einen Termin aus."
                )
                return
            
            main_window = self.window()
            if hasattr(main_window, '_open_choraufstellung'):
                main_window._open_choraufstellung()
            else:
                QMessageBox.information(
                    self,
                    "Info",
                    "Bitte nutzen Sie: Menü → Choraufstellung → In Choraufstellung öffnen"
                )
        
        except Exception as e:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Fehler beim Öffnen der Choraufstellung:\n{str(e)}"
            )