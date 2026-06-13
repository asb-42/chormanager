""":class:`ConfigDialog` — application configuration settings dialog.

Extracted from ``chormanager/ui/dialogs/__init__.py`` in M-3 Schritt 5.
Allows editing of theme, voice-group selection, and field choices.
"""
from __future__ import annotations

try:
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtWidgets import (  # type: ignore
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
    )


class ConfigDialog(QDialog):
    """Dialog for configuration settings."""

    def __init__(self, db=None, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Konfiguration")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        from PyQt6.QtWidgets import QScrollArea, QWidget, QGroupBox

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        data_dir_group = QGroupBox("Datenspeicher")
        data_dir_layout = QFormLayout()

        self.data_dir_input = QLineEdit()
        self.data_dir_input.setText("./data")
        data_dir_layout.addRow("Datenverzeichnis:", self.data_dir_input)

        self.db_filename_input = QLineEdit()
        self.db_filename_input.setText("chor.db")
        data_dir_layout.addRow("Datenbankdatei:", self.db_filename_input)

        reset_btn = QPushButton("Zurücksetzen")
        reset_btn.clicked.connect(lambda: self.data_dir_input.setText("./data"))
        data_dir_layout.addRow("", reset_btn)

        data_dir_group.setLayout(data_dir_layout)
        scroll_layout.addWidget(data_dir_group)

        backup_group = QGroupBox("Backup-Einstellungen")
        backup_layout = QFormLayout()

        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setText("./data/backups")
        backup_layout.addRow("Backup-Verzeichnis:", self.backup_dir_input)

        self.backup_count_input = QLineEdit()
        self.backup_count_input.setText("10")
        backup_layout.addRow("Anzahl Backups:", self.backup_count_input)

        reset_backup_btn = QPushButton("Zurücksetzen")
        reset_backup_btn.clicked.connect(
            lambda: self.backup_dir_input.setText("./data/backups")
        )
        backup_layout.addRow("", reset_backup_btn)

        backup_group.setLayout(backup_layout)
        scroll_layout.addWidget(backup_group)

        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout()

        self.log_level_input = QComboBox()
        self.log_level_input.addItem("INFO", "INFO")
        self.log_level_input.addItem("DEBUG", "DEBUG")
        self.log_level_input.addItem("WARNING", "WARNING")
        self.log_level_input.addItem("ERROR", "ERROR")
        logging_layout.addRow("Log-Level:", self.log_level_input)

        self.log_file_input = QLineEdit()
        self.log_file_input.setText("./data/logs/chormanager.log")
        logging_layout.addRow("Log-Datei:", self.log_file_input)

        reset_log_btn = QPushButton("Zurücksetzen")
        reset_log_btn.clicked.connect(
            lambda: self.log_file_input.setText("./data/logs/chormanager.log")
        )
        logging_layout.addRow("", reset_log_btn)

        logging_group.setLayout(logging_layout)
        scroll_layout.addWidget(logging_group)

        choraufstellung_group = QGroupBox("Choraufstellung-Integration")
        choraufstellung_layout = QFormLayout()

        self.choraufstellung_path_input = QLineEdit()
        self.choraufstellung_path_input.setText("/media/data/coding/choraufstellung")
        choraufstellung_layout.addRow("App-Pfad:", self.choraufstellung_path_input)

        reset_chor_btn = QPushButton("Zurücksetzen")
        reset_chor_btn.clicked.connect(
            lambda: self.choraufstellung_path_input.setText(
                "/media/data/coding/choraufstellung"
            )
        )
        choraufstellung_layout.addRow("", reset_chor_btn)

        choraufstellung_group.setLayout(choraufstellung_layout)
        scroll_layout.addWidget(choraufstellung_group)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_config(self):
        """Load current configuration."""
        pass

    def get_config(self):
        """Get configuration values."""
        return {
            "data_dir": self.data_dir_input.text(),
            "db_filename": self.db_filename_input.text(),
            "backup_dir": self.backup_dir_input.text(),
            "backup_count": self.backup_count_input.text(),
            "log_level": self.log_level_input.currentData(),
            "log_file": self.log_file_input.text(),
            "choraufstellung_path": self.choraufstellung_path_input.text(),
        }

