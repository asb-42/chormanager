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
        """Handle a successfully finished wizard run.

        2026-09 audit: the wizard context may carry entities the run
        pinned or created (project/event/besetzung). Propagate them to
        the UI so info bar, tabs and the persisted active ids all
        reflect what the wizard did — for EVERY task, not just the
        editor launch.
        """
        window = self._window
        try:
            self._sync_context_to_ui(context)
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

    def _sync_context_to_ui(self, context) -> None:
        """Mirror wizard-pinned entities into the UI state.

        ``context.event`` becomes the active termin (info bar + events
        tab + persisted id) — the wizard's own executors already do
        this for picks made DURING the run, but defensive re-syncing
        keeps the state consistent even for runs whose steps only
        pinned the context without going through the executors.
        """
        window = self._window
        event = getattr(context, "event", None)
        if event is not None and getattr(window, "current_event", None) is not event:
            from .dialogs._task_wizard import _sync_active_event

            _sync_active_event(window.db, event, parent=window)

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

        # 2026-09 audit: persist the wizard's termin as the active
        # termin so it survives a restart (previously the id was only
        # set when the user clicked a table row in the events tab).
        from ..config import set_last_active_event_id

        set_last_active_event_id(event.id)

        launcher = getattr(window, "_open_choraufstellung_for_event", None)
        if launcher is None:
            QMessageBox.warning(
                window,
                "Fehler",
                "Die Choraufstellung ist nicht verfügbar.",
            )
            return
        try:
            launcher(event)
        finally:
            # The launcher runs the editor as a blocking subprocess; by
            # the time it returns the user may have saved a formation.
            # Reload the formation table and re-evaluate the Aufgaben
            # cards so "Aufstellung erstellen" flips to ✓ right away
            # (regression 2026-09: stayed visually open).
            choraufstellung_tab = getattr(window, "choraufstellung_tab", None)
            if choraufstellung_tab is not None:
                choraufstellung_tab._load_formations()
            self._refresh_tabs()

    def _refresh_tabs(self) -> None:
        """Reload every tab that could have been touched by the task.

        Includes the Aufgaben view: the cards re-evaluate their
        prerequisites so completed steps flip to ✓ right away
        (regression 2026-09: they stayed visually open).
        """
        window = self._window
        window.projects_tab._load_projects()
        window.singers_tab._load_singers()
        window.events_tab._load_events()
        window.besetzung_tab._load_besetzungen()
        tasks_view = getattr(window, "tasks_view", None)
        if tasks_view is not None:
            tasks_view.refresh()
