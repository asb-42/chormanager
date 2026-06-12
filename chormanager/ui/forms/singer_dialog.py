"""Dialog for adding/editing a singer.

Extracted from chormanager.ui.main_window as part of M-1 (God-Class
refactor, see plans/2026-06-12_m1_main_window_refactor.md step 1).

The class is kept byte-for-byte identical to the previous
implementation; only the location changed. A re-export at the
original location (``chormanager.ui.main_window.SingerDialog``) is
preserved for backward compatibility with any external import.
"""
from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
)

from ...config import load_fields, load_voice_groups
from ...domain.repository import SingerRepository


class SingerDialog(QDialog):
    """Dialog for adding/editing a singer."""

    def __init__(self, singer=None, db=None, parent=None):
        """Initialize dialog.

        Args:
            singer: Singer to edit, or None for new singer.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.singer = singer
        self.db = db
        self._setup_ui()

        if singer:
            self._populate_from_singer()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle(
            "Sänger hinzufügen" if not self.singer else "Sänger bearbeiten"
        )
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        voice_choices = load_voice_groups()
        voice_names = [g["name"] for g in voice_choices]

        fields = load_fields()

        self.inputs = {}

        for field in fields:
            name = field["name"]
            label = field["label"]
            field_type = field["type"]

            if field_type == "computed":
                continue

            elif field_type == "integer":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

            if field_type == "string":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "text":
                widget = QTextEdit()
                widget.setMaximumHeight(80)
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(QDate.currentDate())
                self.inputs[name] = widget
                layout.addRow(label, widget)

                if name == "birth_date":
                    age_layout = QHBoxLayout()
                    age_layout.addWidget(QLabel("Alter:"))
                    self._age_label = QLabel("-")
                    age_layout.addWidget(self._age_label)
                    age_layout.addWidget(QLabel("Jahre"))
                    age_layout.addStretch()
                    layout.addRow("", age_layout)

            elif field_type == "yearmonth":
                layout.addRow(label, None)
                year_layout = QHBoxLayout()
                year_layout.addWidget(QLabel("Monat:"))
                month_combo = QComboBox()
                month_combo.addItem("", None)
                for i in range(1, 13):
                    month_combo.addItem(f"{i:02d}", i)
                year_layout.addWidget(month_combo)
                self.inputs[f"{name}_month"] = month_combo

                year_layout.addWidget(QLabel("Jahr:"))
                year_combo = QComboBox()
                year_combo.addItem("", None)
                for year in range(2015, 2031):
                    year_combo.addItem(str(year), year)
                year_layout.addWidget(year_combo)
                self.inputs[f"{name}_year"] = year_combo

                layout.addRow(year_layout)

            elif field_type == "voice_group":
                widget = QComboBox()
                widget.addItem("", None)
                for vg in voice_names:
                    widget.addItem(vg, vg)
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "email":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "singer_reference":
                widget = QComboBox()
                widget.addItem("", None)
                singer_repo = SingerRepository(self.db)
                singers = singer_repo.get_all()
                for singer in singers:
                    display = singer.full_name or singer.short_name or f"Sänger {singer.id[:8]}"
                    widget.addItem(display, singer.id)
                self.inputs[name] = widget
                layout.addRow(label, widget)
                if self.singer and hasattr(self.singer, name):
                    current_value = getattr(self.singer, name)
                    if current_value:
                        index = widget.findData(current_value)
                        if index >= 0:
                            widget.setCurrentIndex(index)

            elif field_type == "uuid":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)
                if self.singer and hasattr(self.singer, name):
                    current_value = getattr(self.singer, name)
                    if current_value:
                        widget.setText(str(current_value))

        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)

        layout.addRow(button_box)

    def _populate_from_singer(self):
        """Populate fields from singer data."""
        singer_dict = self.singer.to_dict()

        for name, widget in self.inputs.items():
            value = singer_dict.get(name)

            if value is None:
                continue

            if isinstance(widget, QLineEdit):
                widget.setText(str(value))

            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))

            elif isinstance(widget, QDateEdit):
                if value:
                    date = QDate.fromString(value, Qt.DateFormat.ISODate)
                    if date.isValid():
                        widget.setDate(date)

            if name == "birth_date" and hasattr(self, "_age_label"):
                age = self.singer.age()
                self._age_label.setText(str(age) if age is not None else "-")

            elif isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)

    def get_data(self):
        """Get form data as dictionary."""
        data = {}
        fields = load_fields()
        field_types = {f["name"]: f.get("type", "string") for f in fields}

        for name, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if not value:
                    data[name] = None
                elif field_types.get(name) == "integer":
                    try:
                        data[name] = int(value)
                    except ValueError:
                        data[name] = None
                else:
                    data[name] = value

            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText().strip()
                data[name] = value if value else None

            elif isinstance(widget, QDateEdit):
                date = widget.date()
                if date.isValid():
                    data[name] = date.toString(Qt.DateFormat.ISODate)

            elif isinstance(widget, QComboBox):
                value = widget.currentData()
                data[name] = value

        # yearmonth fields are now split into name_year and name_month
        # so just pass through if present
        for name in ("joined_year", "joined_month"):
            if name in data and data[name] is None:
                del data[name]

        return data
