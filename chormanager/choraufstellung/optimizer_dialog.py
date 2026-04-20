try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QFrame
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QFrame
    )
    from PyQt5.QtCore import Qt


# OPTIMIZER: Dialog for selecting optimization rules
class OptimizerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aufstellung optimieren")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background: #f9f6f0; }
            QComboBox { padding: 4px; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Optimierungsregeln auswählen</b>"))
        layout.addWidget(QLabel("Regeln werden von oben nach unten angewendet. "
                                "Nur die erste Primär-Regel (Makro) wird berücksichtigt."))

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        p1_label = QLabel("Priority 1 (Makro):")
        p1_label.setStyleSheet("font-weight: bold;")
        self.priority1_combo = QComboBox()
        self.priority1_combo.addItem("- Keine -", "")
        self.priority1_combo.addItem("SATB (Stimmgruppe)", "satb")
        self.priority1_combo.addItem("Nach Größe", "height")
        layout.addWidget(p1_label)
        layout.addWidget(self.priority1_combo)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep2)

        layout.addWidget(QLabel("Feinjustierung (lokale Swaps):"))

        p2_label = QLabel("Priority 2:")
        self.priority2_combo = QComboBox()
        self.priority2_combo.addItem("- Keine -", "")
        self.priority2_combo.addItem("Nähe (Singpartner)", "affinity")
        layout.addWidget(p2_label)
        layout.addWidget(self.priority2_combo)

        p3_label = QLabel("Priority 3:")
        self.priority3_combo = QComboBox()
        self.priority3_combo.addItem("- Keine -", "")
        self.priority3_combo.addItem("Nähe (Singpartner)", "affinity")
        layout.addWidget(p3_label)
        layout.addWidget(self.priority3_combo)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        optimize_btn = QPushButton("Optimieren")
        optimize_btn.setDefault(True)
        optimize_btn.clicked.connect(self._on_optimize)
        button_layout.addWidget(optimize_btn)
        layout.addLayout(button_layout)

    def _on_optimize(self):
        self.accept()

    def get_selected_rules(self):
        rules = []
        p1 = self.priority1_combo.currentData()
        p2 = self.priority2_combo.currentData()
        p3 = self.priority3_combo.currentData()

        if p1:
            rules.append(p1)
        if p2:
            rules.append(p2)
        if p3:
            rules.append(p3)

        return rules
