"""Main-window action wrappers.

Extracted from ``chormanager.ui.main_window`` as part of M-1
(God-Class refactor, see
``plans/2026-06-12_m1_main_window_refactor.md`` step 8).

This Mixin hosts the per-tab action handlers that bridge menu /
toolbar actions to the underlying tab widgets:

  * Singer:   _add_singer, _edit_singer, _delete_singer
  * Event:    _edit_event, _delete_event, _duplicate_event,
              _manage_availability, _list_events, _new_event
  * Project:  _new_projekt, _edit_project, _delete_project,
              _duplicate_project, _save_projekt, _open_projekt

The methods are kept byte-for-byte identical to the previous
implementation; only the location changed. The first definition
of ``_manage_availability`` (a thin wrapper that calls
``self.events_tab._manage_availability()``) was removed here;
in production MainWindow inherits the second, identical body
from this Mixin.
"""
from __future__ import annotations

# Module-level imports of QDialog / QMessageBox are required because
# several methods (``_new_event`` etc.) reference these names as free
# variables. Without these imports the methods would fail with
# ``NameError`` when called.
from PyQt6.QtWidgets import QDialog, QMessageBox


class MainWindowActionsMixin:
    """Mixin that provides the per-tab action handlers.

    Any widget that needs them must inherit from this mixin AND
    from a QWidget-derived class so that ``self.<tab>`` and
    ``self.<label>`` resolve to real Qt attributes.

    The Mixin expects the following attributes on the host
    (provided by ``MainWindow`` in production):

      * ``self.singers_tab``   (SingersTab)
      * ``self.events_tab``    (EventsTab)
      * ``self.projects_tab``  (ProjectsTab)
      * ``self.db``            (Database)
      * ``self.current_project`` (Project | None)
    """

    # ------------------------------------------------------------------
    # Singer actions
    # ------------------------------------------------------------------

    def _add_singer(self):
        """Add new singer."""
        self.singers_tab._add_singer()

    def _edit_singer(self):
        """Edit selected singer."""
        self.singers_tab._edit_singer()

    def _delete_singer(self):
        self.singers_tab._delete_singer()

    # ------------------------------------------------------------------
    # Event actions
    # ------------------------------------------------------------------

    def _edit_event(self):
        self.events_tab._edit_event()

    def _delete_event(self):
        self.events_tab._delete_event()

    def _duplicate_event(self):
        self.events_tab._duplicate_event()

    def _manage_availability(self):
        """Manage availability for events."""
        self.events_tab._manage_availability()

    def _new_event(self):
        """Create a new event."""
        from .dialogs import EventDialog
        from ..domain.repository import EventRepository

        prefilled_project_id = self.current_project.id if self.current_project else None
        dialog = EventDialog(db=self.db, parent=self, prefilled_project_id=prefilled_project_id)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            if not data.get("name"):
                QMessageBox.warning(self, "Fehler", "Name ist erforderlich")
                return

            repo = EventRepository(self.db)
            repo.create(**data)
            if hasattr(self, 'projects_tab'):
                self.projects_tab._load_projects()
            if hasattr(self, 'events_tab'):
                self.events_tab._load_events()

            self.statusBar().showMessage("Termin erstellt")

    def _list_events(self):
        """List all events."""
        from .dialogs import EventDialog
        from ..domain.repository import EventRepository
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox

        repo = EventRepository(self.db)
        events = repo.get_all()

        if not events:
            QMessageBox.information(self, "Termine", "Keine Termine vorhanden")
            return

        # Show events in a simple dialog
        event_text = "Vorhandene Termine:\n\n"
        for event in events:
            event_text += f"- {event.name} ({event.date}) [{event.event_type}]\n"

        QMessageBox.information(self, "Termine", event_text)

    # ------------------------------------------------------------------
    # Project actions
    # ------------------------------------------------------------------

    def _new_projekt(self):
        """Create new project."""
        self.projects_tab._add_project()

    def _edit_project(self):
        """Edit selected project."""
        self.projects_tab._edit_project()

    def _delete_project(self):
        """Delete selected project."""
        self.projects_tab._delete_project()

    def _duplicate_project(self):
        """Duplicate selected project."""
        self.projects_tab._duplicate_project()

    def _save_projekt(self):
        """Save current project."""
        from PyQt6.QtWidgets import QMessageBox

        project = self.projects_tab.current_project
        if project:
            QMessageBox.information(
                self, "Speichern",
                "Projekt '%s' ist bereits gespeichert." % project.name,
            )
        else:
            QMessageBox.warning(self, "Speichern", "Kein Projekt ausgewählt.")

    def _open_projekt(self):
        """Open existing project."""
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self, "Öffnen", "Bitte wählen Sie ein Projekt aus der Liste aus."
        )
