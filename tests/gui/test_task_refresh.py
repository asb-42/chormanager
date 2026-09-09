"""GUI regression tests: the Aufgaben view refreshes after a wizard run.

User report 2026-09: after completing the "Eine Aufstellung für einen
Auftritt planen" wizard, the Aufgaben page still showed every step as
open — the cards were never re-evaluated because
``TaskFlowController._refresh_tabs()`` reloaded the four data tabs but
not ``tasks_view``.

Contracts pinned here:
* ``TaskFlowController._refresh_tabs`` refreshes ``window.tasks_view``.
* ``MainWindow._refresh_tabs`` (context menu / restore path) does too.
* After the aufstellung editor subprocess returns, the view refreshes.
"""

import pytest


@pytest.fixture
def main_window(qtbot, tmp_path, monkeypatch):
    """Create the real MainWindow against a temporary database."""
    from chormanager.ui.main_window import MainWindow

    window = MainWindow(db_path=str(tmp_path / "refresh.db"))
    qtbot.addWidget(window)
    yield window
    window.close()


class TestRefreshAfterWizard:
    def test_controller_refresh_includes_tasks_view(
        self, main_window, monkeypatch
    ):
        """_refresh_tabs must call tasks_view.refresh()."""
        controller = main_window.task_flow_controller

        called = []
        monkeypatch.setattr(
            main_window.tasks_view, "refresh",
            lambda: called.append(True),
        )
        controller._refresh_tabs()
        assert called, (
            "TaskFlowController._refresh_tabs() must refresh the "
            "Aufgaben view — otherwise completed steps stay visually "
            "open after a wizard run."
        )

    def test_main_window_refresh_includes_tasks_view(
        self, main_window, monkeypatch
    ):
        """MainWindow._refresh_tabs must call tasks_view.refresh()."""
        called = []
        monkeypatch.setattr(
            main_window.tasks_view, "refresh",
            lambda: called.append(True),
        )
        main_window._refresh_tabs()
        assert called

    def test_on_task_completed_refreshes_tasks_view(
        self, main_window, monkeypatch
    ):
        """A finished wizard run re-evaluates the Aufgaben cards."""
        from chormanager.domain.taskflow import TaskContext

        called = []
        monkeypatch.setattr(
            main_window.tasks_view, "refresh",
            lambda: called.append(True),
        )
        # Use a task that does NOT launch the editor subprocess.
        main_window.task_flow_controller._on_task_completed(
            "termin_anlegen", TaskContext(db=main_window.db)
        )
        assert called

    def test_choraufstellung_launch_refreshes_after_editor_returns(
        self, main_window, monkeypatch
    ):
        """After the blocking editor subprocess returns, refresh runs."""
        from chormanager.domain.taskflow import TaskContext
        from chormanager.domain.repository import ProjectRepository, EventRepository

        # Seed a project + event so _launch_choraufstellung can proceed.
        repo = ProjectRepository(main_window.db)
        project = repo.create(name="Hoffmann")
        event = EventRepository(main_window.db).create(
            name="Konzert", date="2026-09-01",
            event_type="konzert", project_id=project.id,
        )

        # Do NOT actually spawn the editor: stub the launcher mixin.
        launched = []
        monkeypatch.setattr(
            main_window,
            "_open_choraufstellung_for_event",
            lambda ev: launched.append(ev),
        )
        refreshed = []
        monkeypatch.setattr(
            main_window.tasks_view, "refresh",
            lambda: refreshed.append(True),
        )

        main_window.task_flow_controller._on_task_completed(
            "aufstellung_planen",
            TaskContext(db=main_window.db, event=event),
        )
        assert launched, "editor launcher should have been called"
        assert refreshed, (
            "After the aufstellung editor closes, the Aufgaben view "
            "must refresh so 'Aufstellung erstellen' can flip to ✓."
        )


class TestNonAufstellungTasksSyncTermin:
    """2026-09 audit: after termin_aufstellen/verfuegbarkeit wizards the
    active termin (if the run pinned one) must be reflected in the UI.

    The wizard now syncs the termin when it is picked/created
    (_sync_active_event), but the completion handler previously never
    propagated context.event for the NON-editor tasks either — the
    info bar could still show an older termin until a manual refresh.
    """

    def test_task_completed_syncs_context_event(self, main_window):
        from chormanager.domain.repository import (
            EventRepository,
            ProjectRepository,
        )
        from chormanager.domain.taskflow import TaskContext

        window = main_window
        project = ProjectRepository(window.db).create(name="P")
        event = EventRepository(window.db).create(
            name="Wizard-Termin", date="2026-09-05",
            event_type="konzert", project_id=project.id,
        )

        # Vorher: kein aktiver Termin
        assert window.current_event is None or (
            window.current_event.id != event.id
        )

        window.task_flow_controller._on_task_completed(
            "termin_anlegen",
            TaskContext(db=window.db, event=event),
        )

        assert window.current_event is not None
        assert window.current_event.id == event.id, (
            "A wizard run that pinned a termin must make it the UI's "
            "active termin (info bar) — not only the editor task."
        )
        assert "Wizard-Termin" in window.event_info_label.text()
