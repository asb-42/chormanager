""":class:`SelbstdarstellungDialog` — edit the "Selbstdarstellung" text.

Extracted from ``chormanager/ui/dialogs/__init__.py`` in M-3 Schritt 6.
Simple text-edit dialog with Load/Save using the state-store.
"""
from __future__ import annotations

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QLabel,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtWidgets import (  # type: ignore
        QDialog,
        QDialogButtonBox,
        QLabel,
        QVBoxLayout,
    )


class SelbstdarstellungDialog(QDialog):
    """Dialog for selbstdarstellung (self-presentation) text."""

    def __init__(self, db=None, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        self._load_content()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Selbstdarstellung")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        from PyQt6.QtWidgets import QTextEdit

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Text für Selbstdarstellung eingeben...")
        layout.addWidget(self.text_input)

        self.last_modified_label = QLabel("Zuletzt bearbeitet: -")
        layout.addWidget(self.last_modified_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_content(self):
        """Load content from database."""
        if not self.db:
            return

        result = self.db.execute("SELECT * FROM selbstdarstellung WHERE id = 'main'")
        row = result.fetchone()

        if row:
            row_dict = dict(row)
            self.text_input.setPlainText(row_dict.get("content", ""))
            updated_at = row_dict.get("updated_at", "")
            if updated_at:
                from datetime import datetime

                dt = datetime.fromisoformat(updated_at)
                self.last_modified_label.setText(
                    f"Zuletzt bearbeitet: {dt.strftime('%d.%m.%Y %H:%M')}"
                )

    def _save(self):
        """Save content to database."""
        if not self.db:
            self.accept()
            return

        from datetime import datetime

        content = self.text_input.toPlainText()
        now = datetime.now().isoformat()

        result = self.db.execute("SELECT id FROM selbstdarstellung WHERE id = 'main'")
        if result.fetchone():
            self.db.execute(
                "UPDATE selbstdarstellung SET content = ?, updated_at = ? WHERE id = 'main'",
                (content, now),
            )
        else:
            self.db.execute(
                "INSERT INTO selbstdarstellung (id, content, updated_at) VALUES (?, ?, ?)",
                ("main", content, now),
            )
        self.db.commit()
        self.accept()

