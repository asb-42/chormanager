# INTEGRATION: Optimizer Dialog - binds UI to core/rules.py
try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QFrame, QMessageBox
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QFrame, QMessageBox
    )
    from PyQt5.QtCore import Qt


class OptimizerDialog(QDialog):
    def __init__(self, parent=None, engine=None):
        super().__init__(parent)
        self.setWindowTitle("Aufstellung optimieren")
        self.setMinimumWidth(400)
        self.engine = engine
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background: #f9f6f0; }
            QComboBox { padding: 4px; }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("<b>Optimierungsregeln auswählen</b>")
        title.setStyleSheet("font-size: 11pt;")
        layout.addWidget(title)

        desc = QLabel("Regeln werden von oben nach unten angewendet.\n"
                     "Nur die erste Primär-Regel (Makro) wird berücksichtigt.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        p1_label = QLabel("Priority 1 (Makro):")
        p1_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(p1_label)
        self.priority1_combo = QComboBox()
        self._populate_primary_combo()
        layout.addWidget(self.priority1_combo)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep2)

        layout.addWidget(QLabel("Feinjustierung (lokale Swaps):"))

        p2_label = QLabel("Priority 2:")
        layout.addWidget(p2_label)
        self.priority2_combo = QComboBox()
        self._populate_refinement_combo(self.priority2_combo)
        layout.addWidget(self.priority2_combo)

        p3_label = QLabel("Priority 3:")
        layout.addWidget(p3_label)
        self.priority3_combo = QComboBox()
        self._populate_refinement_combo(self.priority3_combo)
        layout.addWidget(self.priority3_combo)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.optimize_btn = QPushButton("Optimieren")
        self.optimize_btn.setDefault(True)
        self.optimize_btn.clicked.connect(self._on_optimize_clicked)
        button_layout.addWidget(self.optimize_btn)

        layout.addLayout(button_layout)

    def _populate_primary_combo(self):
        self.priority1_combo.clear()
        self.priority1_combo.addItem("- Keine -", "")
        try:
            from core.rules import get_primary_rules
            for rule in get_primary_rules():
                rule_id = self._get_rule_id(rule.name)
                self.priority1_combo.addItem(rule.name, rule_id)
        except ImportError:
            self.priority1_combo.addItem("SATB (Stimmgruppe)", "satb")
            self.priority1_combo.addItem("Nach Größe", "height")

    def _populate_refinement_combo(self, combo):
        combo.clear()
        combo.addItem("- Keine -", "")
        try:
            from core.rules import get_refinement_rules
            for rule in get_refinement_rules():
                rule_id = self._get_rule_id(rule.name)
                combo.addItem(rule.name, rule_id)
        except ImportError:
            combo.addItem("Nähe (Singpartner)", "affinity")

    def _get_rule_id(self, name):
        mapping = {
            "SATB (Stimmgruppe)": "satb",
            "Nach Größe": "height",
            "SBTA (Stimmgruppe)": "sbta",
            "Nähe (Singpartner)": "affinity",
            "Stimmgruppe zusammenhalten": "voice_group_cohesion",
        }
        return mapping.get(name, "")

    def _validate(self):
        p1 = self.priority1_combo.currentData()
        p2 = self.priority2_combo.currentData()
        p3 = self.priority3_combo.currentData()

        selected = [r for r in [p1, p2, p3] if r]
        if not selected:
            QMessageBox.warning(self, "Keine Regel", "Bitte mindestens eine Regel auswählen.")
            return False
        return True

    def _on_optimize_clicked(self):
        if self._validate():
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

    def get_primary_rule(self):
        return self.priority1_combo.currentData()

    def get_refinement_rules(self):
        rules = []
        p2 = self.priority2_combo.currentData()
        p3 = self.priority3_combo.currentData()
        if p2:
            rules.append(p2)
        if p3:
            rules.append(p3)
        return rules
