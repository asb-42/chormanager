"""TaskFlowController — wires the Aufgaben view to the wizard and the
Choraufstellung launcher.

Composition controller per the A-1 migration rule: new behaviour is
added as a QObject owned by MainWindow, not as a new mixin method.

Responsibilities
----------------
* Open a :class:`~chormanager.ui.dialogs.TaskWizard` when the user
  starts a task on the Aufgaben view.
* After the ``aufstellung_planen`` wizard finishes, launch the existing
  Choraufstellung editor for the termin chosen in the wizard.
* Refresh the affected tabs after any completed task.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMessageBox

from .dialogs import TaskWizard

if TYPE_CHECKING:  # pragma: no cover
    from .main_window import MainWindow


class TaskFlowController(QObject):
    """Owns the task-start → wizard → post-launch flow."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window
        window.tasks_view.task_started.connect(self.start_task)

    # ------------------------------------------------------------------
    # slots
    # ------------------------------------------------------------------

    def start_task(self, task_id: str) -> None:
        """Open the wizard for ``task_id``.

        The wizard context is pre-pinned from the CURRENT UI state
        (active project / active termin / active besetzung) so the
        confirm pages show exactly what the info bar shows — no
        divergence between "the app's state" and the wizard.

        Args:
            task_id: One of :data:`chormanager.domain.taskflow.TASK_IDS`.
        """
        window = self._window
        from ..domain.taskflow import TaskContext, get_task

        context = TaskContext(db=window.db)
        context.project = getattr(window.projects_tab, "current_project",
                                  None)
        context.event = getattr(window, "current_event", None)

        from ..config import get_last_active_besetzung_id
        from ..domain.repository import BesetzungRepository

        saved_besetzung_id = get_last_active_besetzung_id()
        if saved_besetzung_id:
            context.besetzung = BesetzungRepository(
                window.db
            ).get_by_id(saved_besetzung_id)

        wizard = TaskWizard(window.db, get_task(task_id), parent=window,
                            context=context)
        wizard.task_completed.connect(self._on_task_completed)
        wizard.show()
        wizard.raise_()

    def _on_task_completed(self, task_id: str, context) -> None:
        """Handle a successfully finished wizard run."""
        window = self._window
        try:
            if task_id == "aufstellung_planen":
                self._launch_choraufstellung(context)
            else:
                self._refresh_tabs()
                window.statusBar().showMessage("Aufgabe abgeschlossen", 4000)
        except Exception as exc:
            QMessageBox.warning(
                window,
                "Fehler",
                f"Die Aufgabe konnte nicht abgeschlossen werden:\n{exc}",
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _launch_choraufstellung(self, context) -> None:
        """Hand the wizard's termin over to the formation editor."""
        window = self._window
        event = getattr(context, "event", None)
        if event is None:
            QMessageBox.information(
                window,
                "Kein Termin",
                "Es wurde kein Termin ausgewählt. Die Aufstellung kann "
                "später über den Termine-Tab geöffnet werden.",
            )
            return

        window.current_event = event
        if hasattr(window, "events_tab"):
            window.events_tab.event_selected.emit(event)

        launcher = getattr(window, "_open_choraufstellung_for_event", None)
        if launcher is None:
            QMessageBox.warning(
                window,
                "Fehler",
                "Die Choraufstellung ist nicht verfügbar.",
            )
            return
        launcher(event)

    def _refresh_tabs(self) -> None:
        """Reload every tab that could have been touched by the task."""
        window = self._window
        window.projects_tab._load_projects()
        window.singers_tab._load_singers()
        window.events_tab._load_events()
        window.besetzung_tab._load_besetzungen()
