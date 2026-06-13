""":class:`SingerSelectionDialog` — choose singers for a Besetzung.

Extracted from ``chormanager/ui/dialogs/__init__.py`` in M-3 Schritt 7.
This is a 250-LOC class with 9 methods including ``_export_singers``
which calls into ExportService for CSV/LibreOffice export.
"""
from __future__ import annotations

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )
except ImportError:  # pragma: no cover - PyQt5 fallback
    from PyQt5.QtCore import Qt, pyqtSignal  # type: ignore
    from PyQt5.QtWidgets import (  # type: ignore
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

from ...config import load_voice_groups
from ...domain.repository import SingerRepository


class SingerSelectionDialog(QDialog):
    """Dialog for selecting singers for a Besetzung."""

    def __init__(self, db, pre_selected_ids=None, besetzung_name=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.pre_selected_ids = pre_selected_ids or []
        self.selected_ids = set(self.pre_selected_ids)
        self.besetzung_name = besetzung_name or "besetzung"
        self._setup_ui()
        self._load_singers()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("Sänger auswählen")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Markieren Sie die Sänger, die zur Besetzung gehören sollen."
        )
        layout.addWidget(info_label)

        filter_layout = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen (Name, Kurzname)...")
        self.search_box.textChanged.connect(self._load_singers)
        filter_layout.addWidget(self.search_box)

        self.voice_filter = QComboBox()
        self.voice_filter.addItem("Alle Stimmgruppen", None)
        voice_groups = load_voice_groups()
        for vg in voice_groups:
            self.voice_filter.addItem(vg["name"], vg["name"])
        self.voice_filter.currentIndexChanged.connect(self._load_singers)
        filter_layout.addWidget(self.voice_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Alle Mitglieder", "all")
        self.status_filter.addItem("Aktive Mitglieder", "active")
        self.status_filter.addItem("Minderjährige", "minor")
        self.status_filter.addItem("U16", "u16")
        self.status_filter.currentIndexChanged.connect(self._load_singers)
        filter_layout.addWidget(self.status_filter)

        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["✓", "Name", "Kurzname", "Stimmgruppe", "Alter"]
        )
        self.table.setColumnWidth(0, 40)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Alle auswählen")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Alle abwählen")
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(deselect_all_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_singers)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_singers(self):
        """Load singers into table."""
        singer_repo = SingerRepository(self.db)
        singers = singer_repo.get_all()

        search_text = self.search_box.text().strip().lower()
        voice_filter = self.voice_filter.currentData()
        status_filter = self.status_filter.currentData()

        filtered = []
        for singer in singers:
            if voice_filter and singer.voice_group != voice_filter:
                continue
            if status_filter and status_filter != "all":
                if status_filter == "active":
                    if singer.left_year or singer.left_month:
                        continue
                elif status_filter == "minor":
                    age = singer.age()
                    if age is None or age >= 18:
                        continue
                elif status_filter == "u16":
                    age = singer.age()
                    if age is None or age >= 16:
                        continue
            if search_text:
                search_fields = [singer.full_name or "", singer.short_name or ""]
                if not any(search_text in str(f).lower() for f in search_fields):
                    continue
            filtered.append(singer)

        singers = filtered

        self.table.setRowCount(len(singers))

        from PyQt6.QtWidgets import QCheckBox, QTableWidgetItem
        from PyQt6.QtCore import Qt

        for row, singer in enumerate(singers):
            checkbox = QCheckBox()
            checkbox.setCheckState(
                Qt.CheckState.Checked
                if singer.id in self.selected_ids
                else Qt.CheckState.Unchecked
            )
            checkbox.stateChanged.connect(
                lambda state, sid=singer.id: self._on_checkbox_changed(sid, state)
            )
            self.table.setCellWidget(row, 0, checkbox)

            self.table.setItem(row, 1, QTableWidgetItem(singer.full_name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(singer.short_name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(singer.voice_group or ""))

            age = singer.age()
            self.table.setItem(
                row, 4, QTableWidgetItem(str(age) if age is not None else "-")
            )

    def _on_checkbox_changed(self, singer_id, state):
        """Handle checkbox state change."""
        if state == Qt.CheckState.Checked or state == 2:
            self.selected_ids.add(singer_id)
        else:
            self.selected_ids.discard(singer_id)

    def _select_all(self):
        """Select all singers."""
        singer_repo = SingerRepository(self.db)
        singers = singer_repo.get_all()

        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState.Checked)

        self.selected_ids = {s.id for s in singers}

    def _deselect_all(self):
        """Deselect all singers."""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

        self.selected_ids.clear()

    def get_selected_ids(self) -> list:
        """Get list of selected singer IDs."""
        return list(self.selected_ids)

    def _export_singers(self):
        """Export selected singers to file."""
        if not self.selected_ids:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Warnung", "Keine Sänger ausgewählt.")
            return

        from ...ui.export_dialog import ExportDialog

        singer_fields = [
            {"name": "full_name", "label": "Name"},
            {"name": "short_name", "label": "Kurzname"},
            {"name": "voice_group", "label": "Stimmgruppe"},
            {"name": "age", "label": "Alter"},
        ]

        dialog = ExportDialog(singer_fields, self)
        if not dialog.exec():
            return

        selected_fields = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected_fields:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Warnung", "Keine Felder ausgewählt.")
            return

        from ...domain.repository import SingerRepository
        from ...core.export_service import ExportService
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        from datetime import datetime

        singer_repo = SingerRepository(self.db)
        all_singers = singer_repo.get_all()
        selected_singers = [s for s in all_singers if s.id in self.selected_ids]

        service = ExportService()
        data = service.get_export_data(selected_singers, selected_fields)

        ext_map = {"writer": "odt", "calc": "ods", "csv": "csv"}
        ext = ext_map.get(fmt, "csv")
        today = datetime.now().strftime("%Y-%m-%d")
        safe_name = self.besetzung_name.replace(" ", "-").replace("/", "-")
        default_name = f"{today}-{safe_name}.{ext}"
        workdir = Path(__file__).parent.parent.parent / "workdir"
        workdir.mkdir(exist_ok=True)
        default_path = str(workdir / default_name)

        if fmt == "writer":
            content_out = service.export_to_libreoffice_writer(data, selected_fields)
            ext_filter = "LibreOffice Writer (*.odt)"
        elif fmt == "calc":
            content_out = service.export_to_libreoffice_calc(data, selected_fields)
            ext_filter = "LibreOffice Calc (*.ods)"
        else:
            content_out = service.export_to_csv(data, selected_fields)
            ext_filter = "CSV (*.csv)"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Sänger exportieren", default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content_out)

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")


