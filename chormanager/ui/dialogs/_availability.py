""":class:`AvailabilityDelegate` + :class:`AvailabilityDialog`.

Extracted from ``chormanager/ui/dialogs.py`` in M-3 Schritt 2.
Both classes are tightly coupled to singer availability status
combo-boxes and form the smallest cohesive unit in the package.
"""
from __future__ import annotations

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QHBoxLayout,
        QStyledItemDelegate,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtCore import Qt  # type: ignore
    from PyQt5.QtWidgets import (  # type: ignore
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QHBoxLayout,
        QStyledItemDelegate,
        QVBoxLayout,
    )

AVAILABILITY_STATUS = [
    ("yes", "✓ Verfügbar / Zusage", "yes"),
    ("no", "✗ Nicht verfügbar / Absage", "no"),
    ("none", "○ Keine Rückmeldung", "none"),
    ("conditional", "✓? Zusage unter Vorbehalt", "conditional"),
    ("unknown", "? Weiß nicht", "unknown"),
    ("maybe", "~ Vielleicht", "maybe"),
]


class AvailabilityDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        from PyQt6.QtWidgets import QComboBox

        combo = QComboBox(parent)
        for status_code, status_label, short_label in AVAILABILITY_STATUS:
            combo.addItem(status_label, status_code)
        return combo

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if value is None:
            value = "none"
        i = editor.findData(value)
        if i >= 0:
            editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class AvailabilityDialog(QDialog):
    """Dialog for managing singer availability."""

    def __init__(self, singer_id: str, event_id: str, parent=None):
        """Initialize dialog.

        Args:
            singer_id: Singer ID.
            event_id: Event ID.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.singer_id = singer_id
        self.event_id = event_id
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Verfügbarkeit")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        self.status_combo = QComboBox()
        self.status_combo.addItem("✓ Verfügbar / Zusage", "yes")
        self.status_combo.addItem("✗ Nicht verfügbar / Absage", "no")
        self.status_combo.addItem("○ Keine Rückmeldung", "none")
        self.status_combo.addItem("✓? Zusage unter Vorbehalt", "conditional")
        self.status_combo.addItem("? Weiß nicht", "unknown")
        self.status_combo.addItem("Vielleicht", "maybe")

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_status(self):
        """Get selected status."""
        return self.status_combo.currentData()

    def accept(self):
        from ...domain.repository import AvailabilityRepository
        from ...data.database import Database

        db = Database()
        db.connect()
        avail_repo = AvailabilityRepository(db)
        avail_repo.update(self.singer_id, self.event_id, self.get_status())
        db.close()
        super().accept()

