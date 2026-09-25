import os
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QDialog,
    QComboBox,
    QStackedWidget,
)
from PyQt6.QtCore import pyqtSignal, Qt


class ChorAufstellungTab(QWidget):
    """Tab for opening standalone ChorAufstellung app."""

    set_project_filter = pyqtSignal(object)

    def __init__(self, db, parent=None):
        """Initialize the ChorAufstellung tab."""
        super().__init__(parent)
        self.db = db
        self._current_project = None
        self._current_event = None
        self._data_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "choraufstellung",
            "data",
        )
        self._data_dir = os.path.normpath(self._data_dir)
        # Phase 2 (M0, increment 2/3): embedded-editor state. Until
        # increment 3/3 the legacy subprocess path stays the default;
        # the embedded editor is opt-in per file (see open_embedded).
        self._embedded_file = None
        self._embedded_meta = {}
        self._embedded_voicing = []
        self._setup_ui()
        self._load_formations()

    def _setup_ui(self):
        """Set up the user interface."""
        # List page keeps the pre-existing file manager UI verbatim;
        # the embedded editor lives on a second stacked page.
        self._list_page = QWidget()
        layout = QVBoxLayout(self._list_page)

        # The old "Aus ChorManager laden" button was removed in
        # 2026-06-12 (bug-fix). It was wired to a handler that
        # always spawned a fresh editor (no CHOR_FILE) and therefore
        # showed an empty grid even when a saved formation was
        # selected. The supported ways to open a saved formation are
        # now: the context toolbar's "Bearbeiten" action, the table
        # row's right-click "Bearbeiten" action, and the main menu
        # "Aufstellung → In Aufstellung öffnen…" entry, all of which
        # delegate to ``_edit_formation``.

        layout.addStretch()
        layout.takeAt(0)  # belt-and-suspenders: keep a clean top

        search_layout = QHBoxLayout()
        search_layout.addStretch()
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Termin ↓ (neueste zuerst)", "event_date_desc")
        self.sort_combo.addItem("Termin ↑ (älteste zuerst)", "event_date_asc")
        self.sort_combo.addItem("Dateiname ↑", "filename_asc")
        self.sort_combo.addItem("Dateiname ↓", "filename_desc")
        self.sort_combo.addItem("Gespeichert ↓ (neueste zuerst)", "modified_desc")
        self.sort_combo.addItem("Gespeichert ↑ (älteste zuerst)", "modified_asc")
        self.sort_combo.currentIndexChanged.connect(self._load_formations)
        search_layout.addWidget(self.sort_combo)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Suchen...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._load_formations)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        info_label = QLabel(
            "Klicken Sie auf 'Neue Aufstellung', um eine Aufstellung für einen Termin zu erstellen."
        )
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)
        self.table = QTableWidget()
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Dateiname", "Dateigröße", "Projekt", "Termin", "Typ", "Gespeichert"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self._editor_page = self._build_editor_page()
        self._stack = QStackedWidget()
        self._stack.addWidget(self._list_page)
        self._stack.addWidget(self._editor_page)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stack)

    def _build_editor_page(self):
        """Build the embedded-editor page (toolbar + editor widget)."""
        from chormanager.choraufstellung.editor_widget import (
            FormationEditorWidget,
        )

        page = QWidget()
        page_layout = QVBoxLayout(page)
        toolbar = QHBoxLayout()
        back_button = QPushButton("← Zurück zur Liste")
        back_button.clicked.connect(self.close_embedded)
        toolbar.addWidget(back_button)
        save_button = QPushButton("Speichern")
        save_button.clicked.connect(self._on_save_button)
        toolbar.addWidget(save_button)
        self._editor_label = QLabel("")
        toolbar.addWidget(self._editor_label)
        toolbar.addStretch()
        page_layout.addLayout(toolbar)
        self.editor = FormationEditorWidget()
        page_layout.addWidget(self.editor, 1)
        return page

    def _on_save_button(self):
        """Save-button handler: failures are modal (the editor page
        has no status label of its own)."""
        if not self.save_embedded():
            QMessageBox.warning(self, "Fehler", "Speichern fehlgeschlagen.")

    def set_project(self, project):
        """Set the current project."""
        self._current_project = project

    def set_event(self, event):
        """Set the current event."""
        self._current_event = event

    def _new_formation(self):
        from ..dialogs import NewFormationDialog

        if self.db is None:
            # No database: no projects/events to choose from. Production
            # always passes a db; this guards headless/test usage.
            self.status_label.setText("Keine Datenbank verbunden.")
            return

        main_window = self.window()
        projects_tab = getattr(main_window, "projects_tab", None)
        current_project = projects_tab.current_project if projects_tab else None

        dialog = NewFormationDialog(self.db, current_project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        event = dialog.get_event()
        if not event:
            return

        # Since 3/3 the embedded editor is the only target: seed it
        # directly instead of spawning a subprocess via MainWindow.
        if not self.open_new_for_event(event):
            QMessageBox.warning(
                self, "Fehler", "Aufstellung kann nicht erstellt werden."
            )

    def _load_from_chormanager(self, event=None):
        """Open a saved formation in the embedded Choraufstellung editor.

        Since 3/3 every path here is embedded (no subprocess):

          * with an event -> seed the editor via open_new_for_event
          * with a selected table row -> open THAT file embedded
          * otherwise -> new-formation dialog (pick an event first)
        """
        try:
            if event:
                if not self.open_new_for_event(event):
                    QMessageBox.warning(
                        self, "Fehler", "Aufstellung kann nicht erstellt werden."
                    )
                return

            if self.table.currentRow() >= 0:
                self._edit_formation()
                return

            self._new_formation()

        except Exception as e:
            QMessageBox.warning(
                self, "Fehler", f"Fehler beim Öffnen der Choraufstellung:\n{str(e)}"
            )

    def _load_formations(self):
        """Load formations from data directory with search filter."""
        if not os.path.exists(self._data_dir):
            self.table.setRowCount(0)
            return

        search_text = (
            self.search_box.text().lower()
            if hasattr(self, "search_box") and self.search_box.text()
            else ""
        )

        sort_key = self.sort_combo.currentData() if hasattr(self, "sort_combo") else "event_date_desc"

        files = []
        for f in os.listdir(self._data_dir):
            if f.endswith(".json"):
                fp = os.path.join(self._data_dir, f)
                stats = os.stat(fp)
                data = {
                    "filename": f,
                    "size": stats.st_size,
                    "modified": stats.st_mtime,
                }

                try:
                    with open(fp, "r", encoding="utf-8") as jf:
                        content = json.load(jf)
                        data["metadata"] = content.get("metadata", {})
                        data["saved_at"] = content.get("saved_at", "")
                        data["version"] = content.get("version", "")
                except:
                    data["metadata"] = {}
                    data["saved_at"] = ""

                files.append(data)

        if sort_key == "event_date_desc":
            files.sort(key=lambda x: x.get("metadata", {}).get("event_date", ""), reverse=True)
        elif sort_key == "event_date_asc":
            files.sort(key=lambda x: x.get("metadata", {}).get("event_date", ""), reverse=False)
        elif sort_key == "filename_asc":
            files.sort(key=lambda x: x["filename"], reverse=False)
        elif sort_key == "filename_desc":
            files.sort(key=lambda x: x["filename"], reverse=True)
        elif sort_key == "modified_desc":
            files.sort(key=lambda x: x["modified"], reverse=True)
        elif sort_key == "modified_asc":
            files.sort(key=lambda x: x["modified"], reverse=False)
        else:
            files.sort(key=lambda x: x.get("metadata", {}).get("event_date", ""), reverse=True)

        if search_text:
            filtered_files = []
            for f in files:
                meta = f.get("metadata", {})
                search_fields = [
                    f["filename"],
                    meta.get("project", ""),
                    meta.get("event", ""),
                    meta.get("event_date", ""),
                ]
                if any(search_text in str(field).lower() for field in search_fields):
                    filtered_files.append(f)
            files = filtered_files

        self.table.setRowCount(len(files))
        for row, f in enumerate(files):
            meta = f.get("metadata", {})

            self.table.setItem(row, 0, QTableWidgetItem(f["filename"]))
            size = f.get("size", 0)
            size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
            self.table.setItem(row, 1, QTableWidgetItem(size_str))
            self.table.setItem(row, 2, QTableWidgetItem(meta.get("project", "")))
            event_date = meta.get("event_date", "")
            if event_date:
                try:
                    from datetime import datetime
                    event_date = datetime.fromisoformat(event_date).strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    event_date = event_date[:10] if len(event_date) >= 10 else ""
            self.table.setItem(row, 3, QTableWidgetItem(event_date))
            event_type = meta.get("event_type", "")
            if not event_type:
                event_type = meta.get("event", "")
            self.table.setItem(row, 4, QTableWidgetItem(event_type))

            saved = f.get("saved_at", "")
            if saved:
                try:
                    dt = datetime.fromisoformat(saved)
                    saved = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            self.table.setItem(row, 5, QTableWidgetItem(saved))

        self.table.resizeColumnsToContents()

    def _show_context_menu(self, pos):
        """Show context menu."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        embed_action = menu.addAction("Im Tab bearbeiten")
        dup_action = menu.addAction("Duplizieren")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == edit_action:
            self._edit_formation()
        elif action == embed_action:
            self._open_embedded_selected()
        elif action == dup_action:
            self._duplicate_formation()

    def _open_embedded_selected(self):
        """Open the selected formation in the embedded editor."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return False
        filename = self.table.item(current_row, 0).text()
        return self.open_embedded(os.path.join(self._data_dir, filename))

    def open_embedded(self, filepath):
        """Open a formation file in the embedded editor (no subprocess).

        Args:
            filepath: Path to a formation JSON file.

        Returns:
            True if the file was loaded and the editor page is shown,
            False otherwise (stays on the list page).
        """
        from chormanager.choraufstellung.storage import FormationStorage

        try:
            data = FormationStorage(filepath).load_formation()
        except Exception:
            data = None
        if not data:
            self.status_label.setText(
                f"Datei kann nicht geöffnet werden: {filepath}"
            )
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = {}
        self._embedded_file = filepath
        self._embedded_meta = raw.get("metadata", {}) or {}
        self._embedded_voicing = raw.get("voicing_config", []) or []
        self.editor.load_formation_data(data)
        self._editor_label.setText(os.path.basename(filepath))
        self._stack.setCurrentWidget(self._editor_page)
        return True

    def save_embedded(self):
        """Save the embedded editor state back to its file.

        Metadata and voicing config from the loaded file are
        preserved; placements are rebuilt from the grid.

        Returns:
            True on success, False otherwise.
        """
        if not self._embedded_file:
            return False
        try:
            from chormanager.choraufstellung.storage import FormationStorage

            grid = self.editor.grid
            placed = grid.get_placed_singers()
            placed_ids = {s.singer_id for s, _row, _col in placed}
            unplaced = [
                s for s in self.editor.singers
                if s.singer_id not in placed_ids
            ]
            ok = FormationStorage().save_formation(
                unplaced,
                grid.rows,
                grid.cols,
                self._embedded_file,
                placed_singers=placed,
                staggered=grid.staggered,
                voicing_config=self._embedded_voicing,
                metadata=self._embedded_meta,
            )
        except Exception as e:
            self.status_label.setText(f"Speichern fehlgeschlagen:\n{str(e)}")
            return False
        if not ok:
            self.status_label.setText("Speichern fehlgeschlagen.")
            return False
        self._load_formations()
        self.status_label.setText(
            f"Gespeichert: {os.path.basename(self._embedded_file)}"
        )
        return True

    def close_embedded(self):
        """Return from the embedded editor to the file list."""
        self._embedded_file = None
        self._stack.setCurrentWidget(self._list_page)
        self._load_formations()

    def _gather_available_singers(self, event):
        """Collect formation payloads for an event.

        Singers with availability ``yes`` or ``conditional`` become
        one payload each (same shape the legacy temp-JSON flow used).

        Args:
            event: Domain event with ``id``.

        Returns:
            List of formation singer dicts (possibly empty).
        """
        from ...domain.repository import (
            AvailabilityRepository,
            SingerRepository,
        )

        singer_repo = SingerRepository(self.db)
        avail_repo = AvailabilityRepository(self.db)
        payloads = []
        for singer in singer_repo.get_all():
            try:
                avail = avail_repo.get_by_ids(singer.id, event.id)
            except Exception:
                continue
            if avail is not None and avail.status in ("yes", "conditional"):
                payloads.append(
                    {
                        "singer_id": singer.id,
                        "name": singer.short_name or singer.full_name,
                        "voice_group": singer.voice_group,
                        "height": singer.height or 0,
                        "affinity": singer.affinity_uuid or "",
                    }
                )
        return payloads

    def open_new_for_event(self, event):
        """Seed the embedded editor with an event's available singers.

        Replaces the legacy temp-JSON + subprocess flow
        (``_open_choraufstellung_for_event``): the target filename is
        generated up front so :meth:`save_embedded` can persist it.

        Args:
            event: Domain event with ``id``, ``name``, ``date``,
                ``event_type`` attributes.

        Returns:
            True if the editor page is shown, False otherwise.
        """
        from chormanager.choraufstellung.file_io import FormationFileIO
        from chormanager.choraufstellung.singer_model import (
            Singer,
            resolve_voice_group,
        )

        if event is None or self.db is None:
            return False
        try:
            singers = []
            for payload in self._gather_available_singers(event):
                try:
                    singers.append(
                        Singer(
                            name=payload["name"],
                            voice_group=resolve_voice_group(
                                payload.get("voice_group")
                            ),
                            height=int(payload.get("height", 0) or 0),
                            singer_id=payload.get("singer_id") or "",
                            affinity=payload.get("affinity") or "",
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    continue
            date_part = (event.date or "")[:10]
            # generate_filename is a pure helper; storage is unused.
            filename = FormationFileIO(None).generate_filename(
                date_part, event.name
            )
            window = self.window()
            projects_tab = getattr(window, "projects_tab", None)
            project = getattr(projects_tab, "current_project", None)
            self._embedded_file = os.path.join(self._data_dir, filename)
            self._embedded_meta = {
                "project": project.name if project else "",
                "event": event.name,
                "event_date": date_part,
                "event_type": event.event_type or "",
            }
            self._embedded_voicing = []
            self.editor.set_singers(singers)
            self._editor_label.setText(filename)
            self._stack.setCurrentWidget(self._editor_page)
            return True
        except Exception as e:
            self.status_label.setText(
                "Aufstellung kann nicht erstellt werden: " + str(e)
            )
            return False

    def _edit_formation(self):
        """Open the selected formation in the embedded editor.

        Default since 3/3 (no subprocess). With no row selected this
        is a no-op, as before.
        """
        if self.table.currentRow() < 0:
            return
        if not self._open_embedded_selected():
            QMessageBox.warning(
                self, "Fehler", "Die ausgewählte Aufstellung kann nicht geöffnet werden."
            )

    def _duplicate_formation(self):
        """Duplicate selected formation."""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        source_file = self.table.item(current_row, 0).text()
        source_path = os.path.join(self._data_dir, source_file)

        project_name, ok1 = QInputDialog.getText(self, "Duplizieren", "Projektname:")
        if not ok1 or not project_name:
            return

        event_name, ok2 = QInputDialog.getText(self, "Duplizieren", "Termin (Datum):")
        if not ok2 or not event_name:
            return

        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        new_filename = f"choraufstellung-{event_name[:10]}-version-{today}.json"
        new_path = os.path.join(self._data_dir, new_filename)

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["metadata"] = {"project": project_name, "event": event_name}
            data["saved_at"] = datetime.now().isoformat()
            data["version"] = "1.0"

            with open(new_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._load_formations()

        except Exception as e:
            QMessageBox.warning(
                self, "Fehler", f"Duplizieren fehlgeschlagen:\n{str(e)}"
            )

    def _delete_formation(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        filename = self.table.item(current_row, 0).text()
        filepath = os.path.join(self._data_dir, filename)

        reply = QMessageBox.question(
            self,
            "Löschen bestätigen",
            f"Möchten Sie '{filename}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            os.remove(filepath)
            self._load_formations()
        except Exception as e:
            QMessageBox.warning(
                self, "Fehler", f"Löschen fehlgeschlagen:\n{str(e)}"
            )

    def has_formation_for_event(self, event):
        """Check if a formation file exists for the given event."""
        if not event or not event.name:
            return False
        for row in range(self.table.rowCount()):
            filename = self.table.item(row, 0)
            if filename and event.name[:10] in filename.text():
                return True
        return False

    def load_for_event(self, event):
        """Load formation data for a specific event."""
        self._load_from_chormanager()
