"""Tab router: selection, context-toolbar and info-label updates.

Extracted from chormanager.ui.main_window as part of M-1 (God-Class
refactor, see plans/2026-06-12_m1_main_window_refactor.md step 5).

The class is a Mixin that contributes the tab-routing methods to the
host widget: ``_emit_selection`` (the entry point hit on every tab
change), ``_on_selection_changed`` and ``_update_context_toolbar``
(which together adapt the context toolbar to the current selection),
``_update_info_labels`` (info bar), ``_on_project_changed``,
``_on_event_selected``, ``_on_besetzung_changed`` and
``_on_tab_changed``.

This is the area where the phase-6 bug lived: ``_emit_selection`` had
to read the table row from ``self.projects_tab.table.currentRow()``
to discover the actually-selected project, not just rely on
``self.projects_tab.current_project``. The regression test
``tests/unit/test_phase6_project_toolbar_fix.py`` exercises this
path and must continue to pass.

Methods are kept byte-for-byte identical to the previous
implementation; only the location changed. There is no re-export
at the original location because the methods are now inherited, not
imported.

KNOWN DEAD CODE
---------------
The duplicate ``_on_selection_changed`` that existed in the
original main_window.py (Python kept the second; the first was
unreachable) was removed in a dedicated cleanup commit. Only the
one remaining definition lives here now.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QStyle

from ..config import set_last_active_project_id
from .icons import get_icon


class TabRouterMixin:
    """Mixin that provides the tab-routing methods.

    Any widget that needs them must inherit from this mixin AND from
    a QWidget-derived class so that ``self.<tab>`` and ``self.<label>``
    resolve to real Qt attributes.
    """


    def _emit_selection(self, tab_index):
        """Emit selection signal with current selected item for given tab.

        Args:
            tab_index: Index of tab (0-3)
        """
        selection = None
        if tab_index == 0:
            # Read the table selection first (user-driven), then fall
            # back to the programmatically-set current_project.
            # Bug fix: previously we only read current_project, so a
            # table row click never reached the context toolbar.
            row = self.projects_tab.table.currentRow()
            if row >= 0:
                item = self.projects_tab.table.item(row, 1)
                if item is not None:
                    project_id = item.data(Qt.ItemDataRole.UserRole)
                    if project_id:
                        selection = (
                            self.projects_tab.project_repo.get_by_id(project_id)
                        )
            if selection is None and self.projects_tab.current_project:
                selection = self.projects_tab.current_project
        elif tab_index == 1:
            row = self.singers_tab.table.currentRow()
            if row >= 0:
                item = self.singers_tab.table.item(row, 0)
                singer_id = item.data(Qt.ItemDataRole.UserRole)
                selection = (
                    self.singers_tab.singer_repo.get_by_id(singer_id)
                    if singer_id
                    else None
                )
        elif tab_index == 2:  # Besetzung
            row = self.besetzung_tab.table.currentRow()
            if row >= 0:
                besetzungen = self.besetzung_tab.besetzung_repo.get_all()
                selection = besetzungen[row] if row < len(besetzungen) else None
        elif tab_index == 3:  # Events
            row = self.events_tab.table.currentRow()
            if row >= 0:
                item = self.events_tab.table.item(row, 0)
                event_id = item.data(Qt.ItemDataRole.UserRole)
                selection = (
                    self.events_tab.event_repo.get_by_id(event_id) if event_id else None
                )
        elif tab_index == 4:  # Aufstellung
            row = self.choraufstellung_tab.table.currentRow()
            if row >= 0:
                filename = self.choraufstellung_tab.table.item(row, 0).text()
                selection = filename
        elif tab_index == 5:  # Repertoire
            row = self.repertoire_tab.table.currentRow()
            if row >= 0:
                title = self.repertoire_tab.table.item(row, 1).text()
                selection = title

        self._on_selection_changed(tab_index, selection)

    def _update_context_toolbar(self, tab_index, selection):
        """Update toolbar actions based on active tab and selection.

        Args:
            tab_index: Index of active tab (0=Projects, 1=Singers, 2=Events, 3=Aufstellung)
            selection: Selected item object (Project/Event/Singer/formation file) or None
        """
        if not hasattr(self, "context_toolbar"):
            return
        self.context_toolbar.clear()

        if tab_index == 0:  # Projects
            add_action = QAction("Hinzufügen", self)
            add_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            add_action.triggered.connect(self._new_projekt)
            add_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("Aktualisieren", self)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            refresh_action.triggered.connect(self._refresh_tabs)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            self.context_toolbar.addAction(refresh_action)

            if selection:
                set_active_action = QAction("Als aktives Projekt setzen", self)
                set_active_action.setIcon(
                    get_icon("folder-remote", QStyle.StandardPixmap.SP_DirLinkIcon)
                )
                set_active_action.triggered.connect(self.projects_tab._set_active)
                self.context_toolbar.addAction(set_active_action)

                edit_action = QAction("Bearbeiten", self)
                edit_action.setIcon(
                    get_icon(
                        "document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView
                    )
                )
                edit_action.triggered.connect(self._edit_project)
                self.context_toolbar.addAction(edit_action)

                dup_action = QAction("Duplizieren", self)
                dup_action.setIcon(
                    get_icon("edit-copy", QStyle.StandardPixmap.SP_FileIcon)
                )
                dup_action.triggered.connect(self._duplicate_project)
                self.context_toolbar.addAction(dup_action)

                delete_action = QAction("Löschen", self)
                delete_action.setIcon(
                    get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon)
                )
                delete_action.triggered.connect(self._delete_project)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 1:  # Singers
            add_action = QAction("Hinzufügen", self)
            add_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            add_action.triggered.connect(self._add_singer)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("Aktualisieren", self)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            refresh_action.triggered.connect(self._refresh_tabs)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            self.context_toolbar.addAction(refresh_action)

            if selection:
                edit_action = QAction("Bearbeiten", self)
                edit_action.setIcon(
                    get_icon(
                        "document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView
                    )
                )
                edit_action.triggered.connect(self._edit_singer)
                self.context_toolbar.addAction(edit_action)

                delete_action = QAction("Löschen", self)
                delete_action.setIcon(
                    get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon)
                )
                delete_action.triggered.connect(self._delete_singer)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 2:  # Besetzung
            add_action = QAction("Neue Besetzung", self)
            add_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            add_action.triggered.connect(self.besetzung_tab._new_besetzung)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("Aktualisieren", self)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            refresh_action.triggered.connect(self._refresh_tabs)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            self.context_toolbar.addAction(refresh_action)

            if selection:
                edit_action = QAction("Bearbeiten", self)
                edit_action.setIcon(
                    get_icon(
                        "document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView
                    )
                )
                edit_action.triggered.connect(self.besetzung_tab._edit_besetzung)
                self.context_toolbar.addAction(edit_action)

                active_action = QAction("Als aktiv setzen", self)
                active_action.setIcon(
                    get_icon("folder-remote", QStyle.StandardPixmap.SP_DirLinkIcon)
                )
                active_action.triggered.connect(
                    self.besetzung_tab._set_active_besetzung
                )
                self.context_toolbar.addAction(active_action)

                delete_action = QAction("Löschen", self)
                delete_action.setIcon(
                    get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon)
                )
                delete_action.triggered.connect(self.besetzung_tab._delete_besetzung)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 3:  # Events
            add_action = QAction("Neuer Termin", self)
            add_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            add_action.triggered.connect(self._new_event)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("Aktualisieren", self)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            refresh_action.triggered.connect(self._refresh_tabs)
            refresh_action.setIcon(
                get_icon("view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
            )
            self.context_toolbar.addAction(refresh_action)

            if selection:
                # Primary actions
                avail_action = QAction("Verfügbarkeit erfassen", self)
                avail_action.setIcon(
                    get_icon("view-calendar", QStyle.StandardPixmap.SP_FileIcon)
                )
                avail_action.triggered.connect(self._manage_availability)
                self.context_toolbar.addAction(avail_action)

                # Aufstellung: prüfen, ob bereits Datei existiert
                formation_exists = False
                if hasattr(self, "choraufstellung_tab"):
                    formation_exists = self.choraufstellung_tab.has_formation_for_event(
                        selection
                    )

                if formation_exists:
                    open_action = QAction("Aufstellung bearbeiten", self)
                    open_action.setIcon(
                        get_icon(
                            "document-edit",
                            QStyle.StandardPixmap.SP_FileDialogDetailedView,
                        )
                    )
                else:
                    open_action = QAction("Aufstellung öffnen", self)
                    open_action.setIcon(
                        get_icon(
                            "document-open", QStyle.StandardPixmap.SP_DialogOpenButton
                        )
                    )
                open_action.triggered.connect(
                    lambda checked=False, ev=selection: (
                        self._open_choraufstellung_for_event(ev)
                    )
                )
                self.context_toolbar.addAction(open_action)

                set_active_action = QAction("Als aktiven Termin setzen", self)
                set_active_action.setIcon(
                    get_icon("x-office-calendar", QStyle.StandardPixmap.SP_FileIcon)
                )
                set_active_action.triggered.connect(self.events_tab._set_selected_event)
                self.context_toolbar.addAction(set_active_action)

                self.context_toolbar.addSeparator()

                # Project-wide response-matrix export (PDF / ODT)
                self.export_matrix_action = QAction(
                    "Zusagen/Absagen-Liste exportieren", self
                )
                self.export_matrix_action.setIcon(
                    get_icon(
                        "document-save",
                        QStyle.StandardPixmap.SP_DialogSaveButton,
                    )
                )
                self.export_matrix_action.setToolTip(
                    "Erstellt eine projekt-weite Übersicht der Zusagen und "
                    "Absagen für alle Termine als PDF oder LibreOffice-Datei."
                )
                self.export_matrix_action.triggered.connect(
                    self._export_response_matrix
                )
                self.context_toolbar.addAction(self.export_matrix_action)

                self.context_toolbar.addSeparator()

                edit_action = QAction("Bearbeiten", self)
                edit_action.setIcon(
                    get_icon(
                        "document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView
                    )
                )
                edit_action.triggered.connect(self._edit_event)
                self.context_toolbar.addAction(edit_action)

                dup_action = QAction("Duplizieren", self)
                dup_action.setIcon(
                    get_icon("edit-copy", QStyle.StandardPixmap.SP_FileIcon)
                )
                dup_action.triggered.connect(self._duplicate_event)
                self.context_toolbar.addAction(dup_action)

                delete_action = QAction("Löschen", self)
                delete_action.setIcon(
                    get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon)
                )
                delete_action.triggered.connect(self._delete_event)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 4:  # Aufstellung
            new_action = QAction("Neue Aufstellung", self)
            new_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            new_action.triggered.connect(self._new_formation)
            self.context_toolbar.addAction(new_action)

            if selection:
                edit_action = QAction("Bearbeiten", self)
                edit_action.setIcon(
                    get_icon(
                        "document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView
                    )
                )
                edit_action.triggered.connect(self._edit_formation)
                self.context_toolbar.addAction(edit_action)

                dup_action = QAction("Duplizieren", self)
                dup_action.setIcon(
                    get_icon("edit-copy", QStyle.StandardPixmap.SP_FileIcon)
                )
                dup_action.triggered.connect(self._duplicate_formation)
                self.context_toolbar.addAction(dup_action)

                delete_action = QAction("Löschen", self)
                delete_action.setIcon(
                    get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon)
                )
                delete_action.triggered.connect(self._delete_formation)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 5:  # Repertoire
            if not hasattr(self, "repertoire_tab"):
                return
            add_action = QAction("Hinzufügen", self)
            add_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
            add_action.triggered.connect(self.repertoire_tab._add_repertoire)
            self.context_toolbar.addAction(add_action)

            selection = self.repertoire_tab.table.currentRow() >= 0
            if selection:
                edit_action = QAction("Bearbeiten", self)
                edit_action.setIcon(
                    get_icon(
                        "document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView
                    )
                )
                edit_action.triggered.connect(self.repertoire_tab._edit_repertoire)
                self.context_toolbar.addAction(edit_action)

                delete_action = QAction("Löschen", self)
                delete_action.setIcon(
                    get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon)
                )
                delete_action.triggered.connect(self.repertoire_tab._delete_repertoire)
                self.context_toolbar.addAction(delete_action)

    def _on_selection_changed(self, tab_index, selection):
        """Handle selection change from any tab to update context toolbar.

        Args:
            tab_index: Index of the tab (int)
            selection: Selected object (Project/Event/Singer) or None
        """
        self._update_context_toolbar(tab_index, selection)

    def _update_info_labels(self):
        """Update the info labels in the info bar."""
        # Update project info label
        if self.projects_tab.current_project:
            project = self.projects_tab.current_project
            self.project_info_label.setText(f"{project.name}")
        else:
            self.project_info_label.setText("Keines")

        # Update event info label
        if self.current_event:
            event = self.current_event
            self.event_info_label.setText(f"{event.name} ({event.date[:10]})")
        else:
            self.event_info_label.setText("Keiner")

    def _on_project_changed(self):
        """Handle project selection change."""
        project = self.projects_tab.current_project
        self._update_info_labels()
        self.current_project = project

        if project:
            set_last_active_project_id(project.id)

        if hasattr(self, "events_tab"):
            self.events_tab.set_project_filter(project)
        if hasattr(self, "besetzung_tab"):
            self.besetzung_tab.set_project(project)
        if hasattr(self, "choraufstellung_tab"):
            self.choraufstellung_tab.set_project(project)

        self._refresh_tabs()

    def _on_event_selected(self, event):
        """Handle event selection."""
        self.current_event = event
        self._update_info_labels()
        if hasattr(self, "choraufstellung_tab"):
            self.choraufstellung_tab.set_event(event)

        if event:
            self.event_info_label.setText(
                f"<b>Ausgewählter Termin:</b> {event.name} am {event.date[:10]}"
            )
            self.event_info_label.setVisible(True)
        else:
            self.event_info_label.setVisible(False)

    def _on_besetzung_changed(self, besetzung):
        """Handle active besetzung change."""
        if besetzung:
            self.besetzung_info_label.setText(f"<b>{besetzung.name}</b>")
            self.besetzung_info_label.setVisible(True)
        else:
            self.besetzung_info_label.setText("Keine")
            self.besetzung_info_label.setVisible(False)

    def _on_tab_changed(self, index):
        if index == 2:
            self.events_tab._load_events()
        elif index == 3:
            QTimer.singleShot(0, self.choraufstellung_tab._load_formations)
        self._emit_selection(index)
