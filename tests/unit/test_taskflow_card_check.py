"""Unit tests: card_check — separate card-display predicate (audit 2026-09).

Problem pinned here: the verfuegbarkeit_erfassen card showed
'Termin auswählen' as permanently open even with dozens of termine,
because its wizard step uses ``check_event_pinned`` — a predicate that
can only be satisfied INSIDE a wizard run (a pinned context event).

Design: :class:`TaskStep` gains an optional ``card_check`` used ONLY
by the Aufgaben-card display (global view over the DB). It falls
back to ``check`` when absent. The wizard keeps using ``check``
(explicit pick semantics), so no wizard behaviour changes.

Wired in the catalog:
* verfuegbarkeit.termin_waehlen: card shows check_termin semantics
  (any event for the active project) via card_check=check_termin
* verfuegbarkeit.besetzung_pruefen: card shows the project-level
  check via card_check=check_besetzung
"""

import pytest

from chormanager.data.database import Database

from chormanager.domain.taskflow import (
    StepStatus,
    TaskContext,
    TaskStep,
    evaluate_task_for_card,
    get_task,
)


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "card_check.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


class TestModelCardCheck:
    def test_card_check_defaults_to_check(self):
        step = TaskStep(id="s", title="S", check=lambda ctx: True)
        assert step.card_check is step.check

    def test_is_done_for_card_uses_card_check(self):
        step = TaskStep(
            id="s",
            title="S",
            check=lambda ctx: False,
            card_check=lambda ctx: True,
        )
        # wizard view (is_done) → check → False
        assert step.is_done(TaskContext()) is False
        # card view → card_check → True
        assert step.is_done_for_card(TaskContext()) is True

    def test_evaluate_task_for_card(self):
        step = TaskStep(
            id="s", title="S", check=lambda ctx: False,
            card_check=lambda ctx: True,
        )
        from chormanager.domain.taskflow.models import TaskDefinition

        task = TaskDefinition(
            id="t", title="T", subtitle="", icon_name="i", steps=[step]
        )
        rows = evaluate_task_for_card(task, TaskContext())
        assert rows[0][1] is StepStatus.DONE


class TestVerfuegbarkeitCard:
    def _seed(self, db):
        from chormanager.domain.repository import (
            BesetzungRepository,
            EventRepository,
            ProjectRepository,
        )

        project = ProjectRepository(db).create(name="Hoffmann")
        EventRepository(db).create(
            name="Konzert", date="2026-09-01",
            event_type="konzert", project_id=project.id,
        )
        BesetzungRepository(db).create(
            name="B", project_id=project.id, singer_ids=[]
        )
        return project

    def test_card_shows_termin_done_with_existing_event(
        self, db, monkeypatch
    ):
        project = self._seed(db)
        monkeypatch.setattr(
            "chormanager.config.get_last_active_project_id",
            lambda: project.id,
        )
        task = get_task("verfuegbarkeit_erfassen")
        ctx = TaskContext(db=db)  # card context: nothing pinned

        # Wizard semantics: pinned event required → still open
        rows_wizard = [
            (s, StepStatus.DONE if s.is_done(ctx) else StepStatus.OPEN)
            for s in task.steps
        ]
        assert rows_wizard[0][1] is StepStatus.OPEN

        # Card semantics: any event for the project → done
        rows_card = evaluate_task_for_card(task, ctx)
        assert rows_card[0][1] is StepStatus.DONE, (
            "Card must show 'Termin auswählen' as ✓ when termine "
            "exist — check_event_pinned can never be true outside "
            "a wizard run (regression 2026-09)."
        )

    def test_card_shows_besetzung_done_with_existing_besetzung(
        self, db, monkeypatch
    ):
        project = self._seed(db)
        monkeypatch.setattr(
            "chormanager.config.get_last_active_project_id",
            lambda: project.id,
        )
        task = get_task("verfuegbarkeit_erfassen")
        rows_card = evaluate_task_for_card(task, TaskContext(db=db))
        assert rows_card[1][1] is StepStatus.DONE, (
            "Card must show 'Besetzung prüfen' as ✓ when the project "
            "has a besetzung (card_check=check_besetzung)."
        )

    def test_wizard_semantics_unchanged(self, db, monkeypatch):
        """The wizard (evaluate_task) still requires the pinned event."""
        project = self._seed(db)
        monkeypatch.setattr(
            "chormanager.config.get_last_active_project_id",
            lambda: project.id,
        )
        task = get_task("verfuegbarkeit_erfassen")
        rows = evaluate_task_for_card  # noqa: F841  (see import)
        # evaluate_task with unpinned context stays OPEN for step 0:
        from chormanager.domain.taskflow import evaluate_task as et

        assert et(task, TaskContext(db=db))[0][1] is StepStatus.OPEN


class TestTasksViewUsesCardCheck:
    """The TasksView card display uses evaluate_task_for_card."""

    def test_card_shows_checkmarks_with_data(self, qtbot, tmp_path, monkeypatch):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from chormanager.data.database import Database
        from chormanager.ui.views.tasks_view import TaskCard

        db = Database(str(tmp_path / "card_gui.db"))
        db.connect()
        db.create_tables()

        from chormanager.domain.repository import (
            BesetzungRepository,
            EventRepository,
            ProjectRepository,
        )

        project = ProjectRepository(db).create(name="Hoffmann")
        EventRepository(db).create(
            name="Konzert", date="2026-09-01",
            event_type="konzert", project_id=project.id,
        )
        BesetzungRepository(db).create(
            name="B", project_id=project.id, singer_ids=[]
        )
        monkeypatch.setattr(
            "chormanager.config.get_last_active_project_id",
            lambda: project.id,
        )

        task = get_task("verfuegbarkeit_erfassen")
        card = TaskCard(task)
        qtbot.addWidget(card)
        card.update_status(TaskContext(db=db))

        text = card.checklist_label.text()
        assert "\u2713 Termin auswählen" in text, (
            "Card must show the termin step as ✓ when termine exist "
            "(card_check) even though check_event_pinned is False."
        )
        assert "\u2713 Besetzung prüfen" in text
        db.close()
