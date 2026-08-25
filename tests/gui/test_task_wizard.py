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
    def test_intro_page_plus_one_page_per_step(self, qtbot, db):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        task = get_task("aufstellung_planen")
        wizard = TaskWizard(db, task)
        qtbot.addWidget(wizard)

        # Every step gets a page (satisfied ones become confirm
        # pages) -- nothing may be silently skipped.
        assert wizard.page_count() == 1 + len(task.steps)
        assert set(wizard.step_pages) == set(task.step_ids())

    def test_satisfied_step_is_not_silently_skipped(self, qtbot, db,
                                                     monkeypatch):
        from chormanager.domain.repository import ProjectRepository
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        import chormanager.config as config_module

        repo = ProjectRepository(db)
        project = repo.create(name="Hoffmann OKO")
        repo.set_active(project.id)
        monkeypatch.setattr(
            config_module,
            "get_last_active_project_id",
            lambda: project.id,
        )

        task = get_task("termin_anlegen")
        wizard = TaskWizard(db, task)
        qtbot.addWidget(wizard)

        page = wizard.step_pages["projekt_waehlen"]
        # Regression: the page must exist AND require an explicit
        # confirmation even though a project is already active.
        assert not page.isComplete()
        assert "Hoffmann OKO" in page.detected_label.text()

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


class TestSatisfiedStepConfirmation:
    """Satisfied prerequisites need an explicit user confirmation."""

    def _seed_active_project(self, db, monkeypatch, name="Hoffmann OKO"):
        import chormanager.config as config_module
        from chormanager.domain.repository import ProjectRepository

        repo = ProjectRepository(db)
        project = repo.create(name=name)
        repo.set_active(project.id)
        # The UI's active project lives in the config key (info bar).
        monkeypatch.setattr(
            config_module,
            "get_last_active_project_id",
            lambda: project.id,
        )
        return project

    def _executors(self, overrides=None):
        base = {
            "projekt_waehlen": lambda ctx: None,
            "termin_waehlen": lambda ctx: None,
            "besetzung_waehlen": lambda ctx: None,
            "verfuegbarkeit_erfassen": lambda ctx: None,
            "aufstellung_oeffnen": lambda ctx: True,
            "termin_anlegen": lambda ctx: True,
        }
        base.update(overrides or {})
        return base

    def test_confirm_detected_pins_entity(self, qtbot, db, monkeypatch):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        project = self._seed_active_project(db, monkeypatch)
        task = get_task("termin_anlegen")
        wizard = TaskWizard(db, task,
                            executors=self._executors())
        qtbot.addWidget(wizard)

        page = wizard.step_pages["projekt_waehlen"]
        assert not page.isComplete()

        page.confirm_detected()

        assert page.isComplete()
        # get_active() re-reads the row -> compare by id, not identity.
        assert wizard.context.project.id == project.id

    def test_alternative_executor_replaces_detection(self, qtbot, db,
                                                      monkeypatch):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        self._seed_active_project(db, monkeypatch, name="Alt")
        replacement = object()

        wizard = TaskWizard(
            db, get_task("termin_anlegen"),
            executors=self._executors(
                {"projekt_waehlen": lambda ctx: replacement}
            ),
        )
        qtbot.addWidget(wizard)

        page = wizard.step_pages["projekt_waehlen"]
        page.run_executor()

        assert page.isComplete()
        assert wizard.context.project is replacement

    def test_satisfied_availability_step_confirms_without_pin(
        self, qtbot, db
    ):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        wizard = TaskWizard(
            db, get_task("aufstellung_planen"),
            executors=self._executors(),
        )
        qtbot.addWidget(wizard)

        page = wizard.step_pages["verfuegbarkeit_erfassen"]
        page.confirm_detected()

        assert page.isComplete()

    def test_use_button_confirms_detected_entity(self, qtbot, db,
                                                  monkeypatch):
        from chormanager.ui.dialogs._task_wizard import TaskWizard

        project = self._seed_active_project(db, monkeypatch)
        wizard = TaskWizard(
            db, get_task("termin_anlegen"),
            executors=self._executors(),
        )
        qtbot.addWidget(wizard)
        qtbot.addWidget  # noqa: B018 (keep qtbot tracking explicit)

        page = wizard.step_pages["projekt_waehlen"]
        page.use_button.click()

        assert page.isComplete()
        assert wizard.context.project.id == project.id


class TestDefaultExecutors:
    def test_termin_anlegen_is_not_the_noop_executor(self):
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        executors = build_default_executors(db=None, parent=None)
        assert executors["termin_anlegen"] is not (
            executors["aufstellung_oeffnen"]
        )

    def test_termin_anlegen_creates_event_via_dialog(
        self, qtbot, db, monkeypatch
    ):
        from PyQt6.QtWidgets import QDialog

        import chormanager.ui.dialogs._task_wizard as tw
        from chormanager.domain.repository import EventRepository
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        captured = {}

        class FakeEventDialog:
            def __init__(self, db=None, parent=None,
                         prefilled_project_id=None):
                captured["prefilled"] = prefilled_project_id

            def exec(self):
                return QDialog.DialogCode.Accepted

            @staticmethod
            def get_data():
                return {
                    "name": "Herbstkonzert",
                    "date": "2026-11-15",
                    "event_type": "konzert",
                    "project_id": None,
                }

        monkeypatch.setattr(tw, "EventDialog", FakeEventDialog)

        context = TaskContextStub = None  # noqa: F841 (readability)
        from chormanager.domain.taskflow import TaskContext

        context = TaskContext(db=db)
        event = build_default_executors(db, parent=None)[
            "termin_anlegen"
        ](context)

        assert event is not None
        assert event.name == "Herbstkonzert"
        assert EventRepository(db).get_by_id(event.id) is not None
        assert captured["prefilled"] is None

    def test_termin_anlegen_cancel_returns_none(self, qtbot, db,
                                                monkeypatch):
        from PyQt6.QtWidgets import QDialog

        import chormanager.ui.dialogs._task_wizard as tw
        from chormanager.domain.taskflow import TaskContext
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        class CancelledDialog:
            def __init__(self, **kwargs):
                pass

            def exec(self):
                return QDialog.DialogCode.Rejected

        monkeypatch.setattr(tw, "EventDialog", CancelledDialog)

        result = build_default_executors(db, parent=None)[
            "termin_anlegen"
        ](TaskContext(db=db))

        assert result is None

    def test_besetzung_pruefen_pins_besetzung_of_event_project(
        self, qtbot, db, monkeypatch
    ):
        from PyQt6.QtWidgets import QDialog

        import chormanager.ui.dialogs._task_wizard as tw
        from chormanager.domain.repository import (
            BesetzungRepository,
            EventRepository,
            ProjectRepository,
        )
        from chormanager.domain.taskflow import TaskContext
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        project = ProjectRepository(db).create(name="P")
        event = EventRepository(db).create(
            name="E", date="2026-10-01", event_type="konzert",
            project_id=project.id,
        )
        besetzung = BesetzungRepository(db).create(
            name="B", project_id=project.id, singer_ids=["s1"]
        )

        captured = {}

        class FakePick:
            def __init__(self, db=None, project=None, parent=None):
                captured["project_id"] = project.id if project else None

            def exec(self):
                return QDialog.DialogCode.Accepted

            def get_besetzung(self):
                return besetzung

        monkeypatch.setattr(tw, "BesetzungPickDialog", FakePick)

        import chormanager.config as config_module

        monkeypatch.setattr(
            config_module,
            "set_last_active_besetzung_id",
            lambda bid: captured.setdefault("active", bid),
        )

        context = TaskContext(db=db, event=event)
        result = build_default_executors(db, parent=None)[
            "besetzung_pruefen"
        ](context)

        assert result is besetzung
        assert captured["project_id"] == project.id

    def test_verfuegbarkeit_passes_besetzung_filter(
        self, qtbot, db, monkeypatch
    ):
        from PyQt6.QtWidgets import QDialog

        import chormanager.ui.dialogs._task_wizard as tw
        from chormanager.domain.repository import (
            BesetzungRepository,
            EventRepository,
            ProjectRepository,
        )
        from chormanager.domain.taskflow import TaskContext
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        project = ProjectRepository(db).create(name="P")
        event = EventRepository(db).create(
            name="E", date="2026-10-01", event_type="konzert",
            project_id=project.id,
        )
        besetzung = BesetzungRepository(db).create(
            name="B", project_id=project.id, singer_ids=["s1", "s2"]
        )

        captured = {}

        class FakeAvailDialog:
            def __init__(self, db=None, event=None, parent=None,
                         besetzung_ids=None, besetzung_name=None,
                         besetzung_count=0):
                captured.update(
                    besetzung_ids=besetzung_ids,
                    besetzung_name=besetzung_name,
                    besetzung_count=besetzung_count,
                )

            def exec(self):
                return QDialog.DialogCode.Accepted

        monkeypatch.setattr(tw, "EventAvailabilityDialog", FakeAvailDialog)

        context = TaskContext(db=db, event=event, besetzung=besetzung)
        result = build_default_executors(db, parent=None)[
            "verfuegbarkeit_erfassen"
        ](context)

        assert result is True
        assert captured["besetzung_ids"] == ["s1", "s2"]
        assert captured["besetzung_name"] == "B"
        assert captured["besetzung_count"] == 2

    def test_verfuegbarkeit_without_besetzung_shows_all(
        self, qtbot, db, monkeypatch
    ):
        from PyQt6.QtWidgets import QDialog

        import chormanager.ui.dialogs._task_wizard as tw
        from chormanager.domain.repository import EventRepository
        from chormanager.domain.taskflow import TaskContext
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        event = EventRepository(db).create(
            name="E", date="2026-10-01", event_type="konzert",
        )

        captured = {}

        class FakeAvailDialog:
            def __init__(self, db=None, event=None, parent=None,
                         besetzung_ids=None, besetzung_name=None,
                         besetzung_count=0):
                captured.update(
                    besetzung_ids=besetzung_ids,
                    besetzung_count=besetzung_count,
                )

            def exec(self):
                return QDialog.DialogCode.Accepted

        monkeypatch.setattr(tw, "EventAvailabilityDialog", FakeAvailDialog)

        context = TaskContext(db=db, event=event)
        build_default_executors(db, parent=None)[
            "verfuegbarkeit_erfassen"
        ](context)

        assert captured["besetzung_ids"] is None
        assert captured["besetzung_count"] == 0


class TestPickDialogs:
    def test_project_pick_dialog_lists_and_returns_selection(
        self, qtbot, db
    ):
        from PyQt6.QtWidgets import QDialog

        from chormanager.domain.repository import ProjectRepository
        from chormanager.ui.dialogs._task_wizard import ProjectPickDialog

        repo = ProjectRepository(db)
        p_a = repo.create(name="Altprojekt")
        p_b = repo.create(name="Hoffmann OKO 2026")

        dialog = ProjectPickDialog(db)
        qtbot.addWidget(dialog)

        assert dialog.combo.count() == 2
        dialog.combo.setCurrentIndex(1)  # alphabetical: Hoffmann second
        dialog.accept()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.get_project().id == p_b.id
        assert p_a is not None

    def test_project_pick_dialog_empty_refuses_accept(self, qtbot, db):
        from chormanager.ui.dialogs._task_wizard import ProjectPickDialog

        dialog = ProjectPickDialog(db)
        qtbot.addWidget(dialog)

        dialog._on_accept()
        assert dialog.result() != dialog.DialogCode.Accepted
        assert "Projekt" in dialog.error_label.text()

    def test_do_project_syncs_active_project_sources(
        self, qtbot, db, monkeypatch
    ):
        """Regression: the wizard previously wrote only the legacy DB
        flag, so the info bar stayed at 'Keines' while the checker
        claimed 'bereits vorhanden'."""
        import chormanager.config as config_module

        from chormanager.domain.repository import ProjectRepository
        from chormanager.domain.taskflow import TaskContext
        from chormanager.ui.dialogs._task_wizard import (
            build_default_executors,
        )

        existing = ProjectRepository(db).create(name="Hoffmann OKO")

        captured = {}

        class FakePick:
            def __init__(self, db=None, parent=None):
                pass

            def exec(self):
                from PyQt6.QtWidgets import QDialog

                return QDialog.DialogCode.Accepted

            def get_project(self):
                return existing

        monkeypatch.setattr(
            __import__(
                "chormanager.ui.dialogs._task_wizard",
                fromlist=["ProjectPickDialog"],
            ),
            "ProjectPickDialog",
            FakePick,
        )
        monkeypatch.setattr(
            config_module,
            "set_last_active_project_id",
            lambda pid: captured.setdefault("config", pid),
        )

        context = TaskContext(db=db)
        result = build_default_executors(db, parent=None)[
            "projekt_waehlen"
        ](context)

        assert result is existing
        assert captured["config"] == existing.id
        # Legacy DB flag kept in sync.
        assert ProjectRepository(db).get_active().id == existing.id

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
