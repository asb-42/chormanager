"""Export dialog for ChorManager - allows field selection for exports."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialogButtonBox,
    QCheckBox,
    QGroupBox,
    QScrollArea,
    QWidget,
)
from PyQt6.QtCore import Qt


class ExportDialog(QDialog):
    """Dialog for configuring export fields and format."""

    def __init__(self, fields, parent=None):
        """Initialize export dialog.
        
        Args:
            fields: List of field dictionaries from config.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.fields = fields
        self.selected_fields = []
        self.export_format = "calc"  # default
        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Export konfigurieren")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Export-Format wählen und Felder auswählen")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Format selection
        format_group = QGroupBox("Export-Format")
        format_layout = QHBoxLayout()

        self.calc_radio = QPushButton("LibreOffice Calc")
        self.calc_radio.setCheckable(True)
        self.calc_radio.setChecked(True)
        self.calc_radio.clicked.connect(lambda: self._set_format("calc"))
        format_layout.addWidget(self.calc_radio)

        self.writer_radio = QPushButton("LibreOffice Writer")
        self.writer_radio.setCheckable(True)
        self.writer_radio.clicked.connect(lambda: self._set_format("writer"))
        format_layout.addWidget(self.writer_radio)

        self.csv_radio = QPushButton("CSV")
        self.csv_radio.setCheckable(True)
        self.csv_radio.clicked.connect(lambda: self._set_format("csv"))
        format_layout.addWidget(self.csv_radio)

        format_layout.addStretch()
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Field selection
        field_group = QGroupBox("Felder auswählen")
        field_layout = QVBoxLayout()

        # Scroll area for fields
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.field_layout = QVBoxLayout(scroll_widget)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        field_layout.addWidget(scroll_area)

        field_group.setLayout(field_layout)
        layout.addWidget(field_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_fields(self):
        """Populate field checkboxes."""
        self.field_checkboxes = {}

        for field in self.fields:
            field_name = field.get("name", "")
            field_label = field.get("label", field_name)

            checkbox = QCheckBox(field_label)
            checkbox.setChecked(True)  # default: export all
            checkbox.setObjectName(field_name)
            self.field_checkboxes[field_name] = checkbox
            self.field_layout.addWidget(checkbox)

    def _set_format(self, fmt):
        """Set export format."""
        self.export_format = fmt
        self.calc_radio.setChecked(fmt == "calc")
        self.writer_radio.setChecked(fmt == "writer")
        self.csv_radio.setChecked(fmt == "csv")

    def get_selected_fields(self):
        """Get list of selected field names.
        
        Returns:
            List of field names that are checked.
        """
        selected = []
        for field_name, checkbox in self.field_checkboxes.items():
            if checkbox.isChecked():
                selected.append(field_name)
        return selected

    def get_export_format(self):
        """Get selected export format.
        
        Returns:
            str: "calc", "writer", or "csv".
        """
        return self.export_format
