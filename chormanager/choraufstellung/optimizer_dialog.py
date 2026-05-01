try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QFrame, QCheckBox, QGroupBox
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QFrame, QCheckBox, QGroupBox
    )
    from PyQt5.QtCore import Qt


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
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        p1_label = QLabel("Priority 1 (Makro):")
        p1_label.setStyleSheet("font-weight: bold;")
        self.priority1_combo = QComboBox()
        self.priority1_combo.addItem("- Keine -", "")
        self.priority1_combo.addItem("SATB (Stimmgruppe)", "satb")
        self.priority1_combo.addItem("SBTA (Stimmgruppe)", "sbta")
        self.priority1_combo.addItem("S1 S2 A1 A2 T1 T2 B1 B2", "s1s2a1a2t1t2b1b2")
        self.priority1_combo.addItem("S1 S2 B1 B2 T1 T2 A1 A2", "s1s2b1b2t1t2a1a2")
        self.priority1_combo.addItem("Nach Größe", "height")
        layout.addWidget(p1_label)
        layout.addWidget(self.priority1_combo)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)

        refinement_group = QGroupBox("Feinjustierung (lokale Swaps)")
        refinement_layout = QVBoxLayout(refinement_group)

        self.affinity_check = QCheckBox("Nähe (Singpartner)")
        self.voice_group_cohesion_check = QCheckBox("Stimmgruppe zusammenhalten")
        self.voice_group_cohesion_check.setChecked(True)

        refinement_layout.addWidget(self.affinity_check)
        refinement_layout.addWidget(self.voice_group_cohesion_check)
        layout.addWidget(refinement_group)

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
        if p1:
            rules.append(p1)

        if self.affinity_check.isChecked():
            rules.append("affinity")

        return rules
