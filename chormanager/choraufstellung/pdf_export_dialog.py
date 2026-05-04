try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QCheckBox, QGroupBox, QLineEdit
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QCheckBox, QGroupBox, QLineEdit
    )
    from PyQt5.QtCore import Qt


class PDFExportDialog(QDialog):
    def __init__(self, parent=None, default_filename="", event_info=""):
        super().__init__(parent)
        self.setWindowTitle("PDF Export")
        self.setMinimumWidth(400)
        self.default_filename = default_filename
        self.event_info = event_info
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        if self.event_info:
            info_label = QLabel(f"<b>{self.event_info}</b>")
            info_label.setStyleSheet("color: #333; font-size: 10pt;")
            layout.addWidget(info_label)
            layout.addSpacing(10)
        
        orientation_group = QGroupBox("Ausrichtung")
        orientation_layout = QVBoxLayout(orientation_group)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Querformat (empfohlen)", "landscape")
        self.orientation_combo.addItem("Hochformat", "portrait")
        orientation_layout.addWidget(self.orientation_combo)
        layout.addWidget(orientation_group)
        
        color_group = QGroupBox("Farbe")
        color_layout = QVBoxLayout(color_group)
        self.color_combo = QComboBox()
        self.color_combo.addItem("Farbig", "color")
        self.color_combo.addItem("Schwarzweiß", "bw")
        color_layout.addWidget(self.color_combo)
        layout.addWidget(color_group)
        
        text_group = QGroupBox("Textausrichtung")
        text_layout = QVBoxLayout(text_group)
        self.text_rotation_combo = QComboBox()
        self.text_rotation_combo.addItem("Standard (waagerecht)", "horizontal")
        self.text_rotation_combo.addItem("90° rotiert (senkrecht)", "vertical")
        text_layout.addWidget(self.text_rotation_combo)
        layout.addWidget(text_group)
        
        filename_group = QGroupBox("Dateiname")
        filename_layout = QVBoxLayout(filename_group)
        self.filename_input = QLineEdit(self.default_filename)
        filename_layout.addWidget(self.filename_input)
        layout.addWidget(filename_group)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        export_btn = QPushButton("PDF exportieren")
        export_btn.setDefault(True)
        export_btn.clicked.connect(self.accept)
        button_layout.addWidget(export_btn)
        layout.addLayout(button_layout)
    
    def get_settings(self):
        return {
            "orientation": self.orientation_combo.currentData(),
            "color_mode": self.color_combo.currentData(),
            "text_rotation": self.text_rotation_combo.currentData(),
            "filename": self.filename_input.text().strip()
        }
