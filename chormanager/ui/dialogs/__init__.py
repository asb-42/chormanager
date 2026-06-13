# M-3 Schritt 1: Re-export wrapper for backward compatibility.
# The 12 dialog classes will be incrementally moved into sub-modules
# (_event.py, _config.py, ...) in M-3 Schritte 2-12. The package-level
# re-exports below keep  working.
"""Dialogs for event management."""


from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDateTimeEdit,
    QTextEdit,
    QPushButton,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QRadioButton,
    QButtonGroup,
    QLabel,
    QScrollArea,
    QWidget,
    QGroupBox,
    QStyledItemDelegate,
    QSizePolicy,
    QMessageBox,
    QFileDialog,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtCore import QDateTime, Qt

from ...domain.repository import (
    SingerRepository,
    AvailabilityRepository,
    EventRepository,
    ProjectRepository,
    RepertoireRepository,
)
from ...config import load_voice_groups

# M-3 Schritt 2: Re-exports for back-compat
from ._availability import (
    AvailabilityDelegate,
    AvailabilityDialog,
    AVAILABILITY_STATUS,
)

# M-3 Schritt 3: Re-exports for back-compat
from ._event import (
    EventDialog,
    EventListDialog,
)

# M-3 Schritt 4: Re-exports for back-compat
from ._event_availability import (
    EventAvailabilityDialog,
)

# M-3 Schritt 5: Re-exports for back-compat
from ._config import (
    ConfigDialog,
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


class DropZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(300, 80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.label = QLabel("Backup-Datei hierher ziehen\noder klicken zum Auswählen")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(self.label)
        self.file_path = None

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        if e.mimeData().hasUrls():
            url = e.mimeData().urls()[0]
            self.file_path = url.toLocalFile()
            self.label.setText(f"Ausgewählt:\n{self.file_path}")
            self.label.setStyleSheet("color: #333; font-size: 13px;")
            self.file_selected.emit(self.file_path)

    def mousePressEvent(self, event):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Backup-Datei auswählen", "", "ZIP Dateien (*.zip)"
        )
        if filename:
            self.file_path = filename
            self.label.setText(f"Ausgewählt:\n{filename}")
            self.label.setStyleSheet("color: #333; font-size: 13px;")
            self.file_selected.emit(filename)


from PyQt6.QtCore import pyqtSignal

DropZone.file_selected = pyqtSignal(str)


class BackupRestoreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backup & Restore")
        self.setMinimumSize(550, 450)
        self.service = None
        self.pending_restore_path = None
        self.restored = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        backup_box = QGroupBox("Daten sichern")
        backup_layout = QVBoxLayout(backup_box)

        self.backup_info = QLabel(
            "Erstellt eine ZIP-Datei mit allen App-Daten:\n"
            "• Datenbank (chor.db)\n"
            "• Einstellungen (config/)\n"
            "• Choraufstellung-JSONs"
        )
        self.backup_info.setWordWrap(True)

        self.backup_btn = QPushButton("Backup erstellen...")
        self.backup_btn.clicked.connect(self._on_backup)

        backup_layout.addWidget(self.backup_info)
        backup_layout.addWidget(self.backup_btn)

        restore_box = QGroupBox("Daten wiederherstellen")
        restore_layout = QVBoxLayout(restore_box)

        restore_info = QLabel(
            "Stellt Daten aus einer Backup-Datei wieder her.\n"
            "Nur neuere Dateien werden überschrieben."
        )
        restore_info.setWordWrap(True)

        self.drop_zone = DropZone()
        self.drop_zone.file_selected.connect(self._on_file_dropped)

        self.restore_btn = QPushButton("Backup-Datei laden...")
        self.restore_btn.clicked.connect(lambda: self.drop_zone.mousePressEvent(None))

        restore_layout.addWidget(restore_info)
        restore_layout.addWidget(self.drop_zone)
        restore_layout.addWidget(self.restore_btn)

        layout.addWidget(backup_box)
        layout.addWidget(restore_box)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_backup(self):
        if self.service is None:
            return
        default_name = (
            f"chormanager-data-backup-{datetime.now().strftime('%Y-%m-%d')}.zip"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Backup speichern unter", default_name, "ZIP Dateien (*.zip)"
        )
        if not filename:
            return
        try:
            path = self.service.create_backup(filename)
            mb = QMessageBox(self)
            mb.setWindowTitle("Backup erstellt")
            mb.setText(f"Backup erfolgreich gespeichert:\n{path}")
            mb.setIcon(QMessageBox.Icon.Information)
            mb.exec()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Backup fehlgeschlagen:\n{e}")

    def _on_file_dropped(self, path):
        if self.service is None:
            return
        valid, msg = self.service.validate_backup(path)
        if not valid:
            QMessageBox.warning(self, "Ungültige Datei", msg)
            return
        changes = self.service.analyze_restore(path)
        total = len(changes["newer"]) + len(changes["new"]) + len(changes["older"])
        if total == 0:
            QMessageBox.information(
                self, "Restore", "Keine Dateien zum Wiederherstellen."
            )
            return
        self.pending_restore_path = path
        self._show_restore_warning(changes)

    def _show_restore_warning(self, changes):
        msg = QMessageBox(self)
        msg.setWindowTitle("Wiederherstellung bestätigen")
        msg.setIcon(QMessageBox.Icon.Warning)

        lines = []
        lines.append("Die folgenden Dateien werden überschrieben:\n")

        if changes["newer"]:
            lines.append("=== NEUERE Version aus Backup (wird überschrieben) ===")
            for c in changes["newer"]:
                lines.append(f"  {c['archive_name']}")
                lines.append(f"    Lokal:      {c['local_mtime_str']}")
                lines.append(f"    Backup:     {c['archive_mtime_str']}")
            lines.append("")

        if changes["new"]:
            lines.append("=== NEUE Dateien aus Backup (werden hinzugefügt) ===")
            for c in changes["new"]:
                lines.append(f"  {c['archive_name']}  (lokal: nicht vorhanden)")
            lines.append("")

        if changes["older"]:
            lines.append("=== LOKAL NEUER (keine Änderung) ===")
            for c in changes["older"]:
                lines.append(f"  {c['archive_name']}")
                lines.append(f"    Lokal:      {c['local_mtime_str']}")
                lines.append(f"    Backup:     {c['archive_mtime_str']}")

        msg.setText("\n".join(lines))
        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)

        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Ok:
            self._do_restore()

    def _do_restore(self):
        if not self.pending_restore_path:
            return
        try:
            restored = self.service.restore_backup(self.pending_restore_path)
            self.restored = True
            QMessageBox.information(
                self, "Erfolgreich", f"{len(restored)} Dateien wiederhergestellt."
            )
            self.accept()
            self.drop_zone.label.setText(
                "Backup-Datei hierher ziehen\noder klicken zum Auswählen"
            )
            self.drop_zone.label.setStyleSheet("color: #888; font-size: 13px;")
            self.drop_zone.file_path = None
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Restore fehlgeschlagen:\n{e}")


from pathlib import Path
from datetime import datetime


class NewFormationDialog(QDialog):
    def __init__(self, db, current_project=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.event_repo = EventRepository(db)
        self.project_repo = ProjectRepository(db)
        self.current_project = current_project
        self.selected_event = None
        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        self.setWindowTitle("Neue Choraufstellung")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        form.addRow("Projekt:", self.project_combo)

        self.event_combo = QComboBox()
        form.addRow("Termin:", self.event_combo)

        layout.addLayout(form)

        self.info_label = QLabel(
            "Wählen Sie einen Termin aus. Die Sänger mit Zusagen für diesen Termin "
            "werden an die Choraufstellung übergeben."
        )
        self.info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(self.info_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_projects(self):
        self.project_combo.clear()
        projects = self.project_repo.get_all()

        if self.current_project:
            self.project_combo.addItem(self.current_project.name, self.current_project)
            self.project_combo.setEnabled(False)
            self._on_project_changed(0)
        else:
            self.project_combo.addItem("-- Alle Projekte --", None)
            for p in projects:
                self.project_combo.addItem(p.name, p)
            if projects:
                self.project_combo.setCurrentIndex(1)

    def _on_project_changed(self, index):
        self.event_combo.clear()
        project = self.project_combo.currentData()

        if project:
            all_events = self.event_repo.get_all()
            events = [e for e in all_events if e.project_id == project.id]
        else:
            events = self.event_repo.get_all()

        for e in events:
            label = f"{e.date[:10]} - {e.name} ({e.event_type})"
            self.event_combo.addItem(label, e)

    def _on_accept(self):
        self.selected_event = self.event_combo.currentData()
        if not self.selected_event:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie einen Termin aus.")
            return
        self.accept()

    def get_event(self):
        return self.selected_event


class RepertoireDialog(QDialog):
    def __init__(self, db, parent=None, repertoire=None):
        super().__init__(parent)
        self.db = db
        self.repertoire_repo = RepertoireRepository(db)
        self.repertoire = repertoire
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(
            "Repertoire bearbeiten" if self.repertoire else "Neues Repertoire"
        )
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        self.composer_input = QLineEdit()
        self.composer_input.setPlaceholderText("Name des Komponisten")
        layout.addRow("Komponist:", self.composer_input)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Titel des Stücks")
        layout.addRow("Titel:", self.title_input)

        self.dates_input = QLineEdit()
        self.dates_input.setPlaceholderText("z.B. 1803-1870")
        layout.addRow("Lebensdaten:", self.dates_input)

        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("Nationalität")
        layout.addRow("Land:", self.country_input)

        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("Verlag")
        layout.addRow("Verlag:", self.publisher_input)

        self.arrangement_input = QLineEdit()
        self.arrangement_input.setPlaceholderText("z.B. Gemischter Chor")
        layout.addRow("Besetzung:", self.arrangement_input)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Wo sind die Noten?")
        layout.addRow("Standort:", self.location_input)

        self.program_combo = QComboBox()
        self.program_combo.setPlaceholderText("Programm auswählen")
        self.program_combo.addItem("", "")
        project_repo = ProjectRepository(self.db)
        projects = project_repo.get_all()
        for project in projects:
            self.program_combo.addItem(project.name, project.id)
        layout.addRow("Programm:", self.program_combo)

        if self.repertoire:
            self.composer_input.setText(self.repertoire.composer)
            self.title_input.setText(self.repertoire.title)
            self.dates_input.setText(self.repertoire.dates)
            self.country_input.setText(self.repertoire.country)
            self.publisher_input.setText(self.repertoire.publisher)
            self.arrangement_input.setText(self.repertoire.arrangement)
            self.location_input.setText(self.repertoire.location)
            if self.repertoire.project_id:
                index = self.program_combo.findData(self.repertoire.project_id)
                if index >= 0:
                    self.program_combo.setCurrentIndex(index)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self):
        composer = self.composer_input.text().strip()
        title = self.title_input.text().strip()

        if not title:
            QMessageBox.warning(self, "Warnung", "Titel ist erforderlich.")
            return

        dates = self.dates_input.text().strip()
        country = self.country_input.text().strip()
        publisher = self.publisher_input.text().strip()
        arrangement = self.arrangement_input.text().strip()
        location = self.location_input.text().strip()
        project_id = self.program_combo.currentData() or ""

        if self.repertoire:
            self.repertoire_repo.update(
                self.repertoire.id,
                composer=composer,
                title=title,
                dates=dates,
                country=country,
                publisher=publisher,
                arrangement=arrangement,
                location=location,
                project_id=project_id,
            )
        else:
            self.repertoire_repo.create(
                composer=composer,
                title=title,
                dates=dates,
                country=country,
                publisher=publisher,
                arrangement=arrangement,
                location=location,
                project_id=project_id,
            )

        self.accept()
