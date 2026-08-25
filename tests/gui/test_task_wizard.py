"""GUI tests for the TaskWizard (dialogs/_task_wizard.py).

The wizard is tested with *injected* step executors (plain callables)
so no modal dialog ever blocks the headless test run.
"""

import pytest

from chormanager.data.database import Database
from chormanager.domain.taskflow import get_task


@pytest.fixture
def db(tmp_path):
    """Create a fresh test database."""
    database = Database(str(tmp_path / "task_wizard.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


class TestTaskWizardStructure:
    def test_intro_page_plus_one_page_per_open_step(self, qtbot, db):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        task = get_task("aufstellung_planen")
        wizard = TaskWizard(db, task)
        qtbot.addWidget(wizard)

        # Empty DB: all 5 steps are open -> intro + 5 step pages.
        assert wizard.page_count() == 1 + len(task.steps)

    def test_satisfied_prerequisites_are_skipped(self, qtbot, db):
        from chormanager.domain.repository import ProjectRepository
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        repo = ProjectRepository(db)
        project = repo.create(name="P")
        repo.set_active(project.id)

        task = get_task("termin_anlegen")
        wizard = TaskWizard(db, task)
        qtbot.addWidget(wizard)

        # projekt done at build time -> only the action page remains.
        assert wizard.page_count() == 1 + 1

    def test_intro_page_lists_all_steps(self, qtbot, db):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        task = get_task("mitglied_aufnehmen")
        wizard = TaskWizard(db, task)
        qtbot.addWidget(wizard)

        intro_text = wizard.intro_label.text()
        for step in task.steps:
            assert step.title in intro_text


class TestTaskWizardExecution:
    def _wizard(self, qtbot, db, executors):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        task = get_task("aufstellung_planen")
        wizard = TaskWizard(db, task, executors=executors)
        qtbot.addWidget(wizard)
        return wizard

    def test_executor_is_called_and_pins_context(self, qtbot, db):
        calls = []

        def fake_project(ctx):
            calls.append(ctx)
            return object()

        executors = {
            "projekt_waehlen": fake_project,
            "termin_waehlen": lambda ctx: None,
            "besetzung_waehlen": lambda ctx: None,
            "verfuegbarkeit_erfassen": lambda ctx: None,
            "aufstellung_oeffnen": lambda ctx: True,
        }

        wizard = self._wizard(qtbot, db, executors)
        project_page = wizard.step_pages["projekt_waehlen"]

        project_page.run_executor()

        assert len(calls) == 1
        assert project_page.isComplete()

    def test_falsy_executor_result_keeps_page_incomplete(self, qtbot, db):
        executors = {
            "projekt_waehlen": lambda ctx: None,
            "termin_waehlen": lambda ctx: None,
            "besetzung_waehlen": lambda ctx: None,
            "verfuegbarkeit_erfassen": lambda ctx: None,
            "aufstellung_oeffnen": lambda ctx: True,
        }

        wizard = self._wizard(qtbot, db, executors)
        page = wizard.step_pages["projekt_waehlen"]
        page.run_executor()

        assert not page.isComplete()

    def test_success_color_follows_dark_theme(self, qtbot, db, monkeypatch):
        import chormanager.ui.theme_manager as tm
        from chormanager.ui.theme_manager import accent_color

        monkeypatch.setattr(tm, "get_theme", lambda: "dark")
        executors = {
            "projekt_waehlen": lambda ctx: object(),
            "termin_waehlen": lambda ctx: None,
            "besetzung_waehlen": lambda ctx: None,
            "verfuegbarkeit_erfassen": lambda ctx: None,
            "aufstellung_oeffnen": lambda ctx: True,
        }

        wizard = self._wizard(qtbot, db, executors)
        page = wizard.step_pages["projekt_waehlen"]
        page.run_executor()

        assert page.status_label.text().startswith("\u2713")
        sheet = page.status_label.styleSheet()
        assert accent_color("success", "dark") in sheet
        assert "#2e7d32" not in sheet

    def test_accept_emits_task_completed_with_context(self, qtbot, db):
        sentinel_project = object()
        executors = {
            "projekt_waehlen": lambda ctx: sentinel_project,
            "termin_waehlen": lambda ctx: None,
            "besetzung_waehlen": lambda ctx: None,
            "verfuegbarkeit_erfassen": lambda ctx: None,
            "aufstellung_oeffnen": lambda ctx: True,
        }

        wizard = self._wizard(qtbot, db, executors)
        wizard.show()
        wizard.step_pages["projekt_waehlen"].run_executor()

        results = []
        wizard.task_completed.connect(
            lambda task_id, context: results.append((task_id, context))
        )

        with qtbot.waitSignal(wizard.task_completed, timeout=2000):
            wizard.accept()

        task_id, context = results[0]
        assert task_id == "aufstellung_planen"
        assert context.project is sentinel_project


class TestPickDialogs:
    def test_event_pick_dialog_returns_selection(self, qtbot, db):
        from PyQt6.QtWidgets import QDialog

        from chormanager.domain.repository import EventRepository
        from chormanager.ui.dialogs._task_wizard import EventPickDialog

        event_repo = EventRepository(db)
        event_a = event_repo.create(name="A", date="2026-01-01",
                                    event_type="konzert")
        event_b = event_repo.create(name="B", date="2026-02-01",
                                    event_type="probe")

        dialog = EventPickDialog(db, project=None)
        qtbot.addWidget(dialog)

        # Newest first; selecting index 0 must yield event_b.
        assert dialog.combo.count() == 2
        dialog.combo.setCurrentIndex(0)
        dialog.accept()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.get_event().id == event_b.id

    def test_event_pick_dialog_empty_list_not_accepted(self, qtbot, db):
        from chormanager.ui.dialogs._task_wizard import EventPickDialog

        dialog = EventPickDialog(db, project=None)
        qtbot.addWidget(dialog)

        assert dialog.combo.count() == 0
        # Accept with nothing selected must be refused.
        dialog._on_accept()
        assert dialog.result() != dialog.DialogCode.Accepted
