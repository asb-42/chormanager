"""Unit tests: action steps become DB-checkable (2026-09 audit, part 1).

The audit found the same regression class as 'Aufstellung erstellen'
in the three OTHER wizards: their action steps had no ``check``, so
the Aufgaben card kept showing them open after the task was actually
executed and the data existed in the DB.

Pinned contracts:
* 'termin_anlegen' (task termin_anlegen) — done when the resolved
  project has any event. This mirrors what check_termin already
  proves; the step now simply shares it.
* 'verfuegbarkeit_erfassen' (task verfuegbarkeit_erfassen, last
  step) — done when the relevant event has at least one positive
  reply (same predicate as the earlier prerequisite step, so the
  card reflects 'Zusagen wurden erfasst').
* 'mitglied_aufnehmen' deliberately stays a pure action (which
  singer?) — the card already shows 'Sofort startbar'.
"""

import pytest

from chormanager.data.database import Database

from chormanager.domain.taskflow import (
    StepStatus,
    TaskContext,
    evaluate_task,
    get_task,
)


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "action_checks.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


def _seed_full(db):
    from chormanager.domain.repository import (
        AvailabilityRepository,
        BesetzungRepository,
        EventRepository,
        ProjectRepository,
        SingerRepository,
    )

    project = ProjectRepository(db).create(name="Hoffmann")
    event = EventRepository(db).create(
        name="Konzert", date="2026-09-01",
        event_type="konzert", project_id=project.id,
    )
    BesetzungRepository(db).create(
        name="B", project_id=project.id, singer_ids=[]
    )
    singer = SingerRepository(db).create(
        full_name="Anna Alt", voice_group="Alt 1"
    )
    AvailabilityRepository(db).update(singer.id, event.id, "yes")
    return project, event


class TestTerminAnlegenActionCheck:
    def test_step_has_a_check(self):
        task = get_task("termin_anlegen")
        final = task.steps[-1]
        assert final.id == "termin_anlegen"
        assert final.check is not None, (
            "Regression 2026-09: after creating the termin via the "
            "wizard the card must show ✓ (event exists for project)."
        )

    def test_stays_open_without_event(self, db, monkeypatch):
        from chormanager.domain.repository import ProjectRepository

        project = ProjectRepository(db).create(name="P")
        monkeypatch.setattr(
            "chormanager.config.get_last_active_project_id",
            lambda: project.id,
        )
        task = get_task("termin_anlegen")
        rows = evaluate_task(task, TaskContext(db=db, project=project))
        assert rows[-1][1] is StepStatus.OPEN

    def test_done_when_event_exists(self, db, monkeypatch):
        project, event = _seed_full(db)
        monkeypatch.setattr(
            "chormanager.config.get_last_active_project_id",
            lambda: project.id,
        )
        task = get_task("termin_anlegen")
        rows = evaluate_task(task, TaskContext(db=db, project=project))
        assert rows[-1][1] is StepStatus.DONE


class TestVerfuegbarkeitActionCheck:
    def test_last_step_has_a_check(self):
        task = get_task("verfuegbarkeit_erfassen")
        final = task.steps[-1]
        assert final.id == "verfuegbarkeit_erfassen"
        assert final.check is not None, (
            "Regression 2026-09: after recording replies the card "
            "must show the step as done."
        )

    def test_done_when_positive_reply_exists(self, db):
        project, event = _seed_full(db)
        task = get_task("verfuegbarkeit_erfassen")
        rows = evaluate_task(
            task, TaskContext(db=db, event=event)
        )
        # termin step: pinned event counts
        assert rows[0][1] is StepStatus.DONE
        # last step: a positive reply exists
        assert rows[-1][1] is StepStatus.DONE

    def test_stays_open_without_replies(self, db):
        from chormanager.domain.repository import (
            EventRepository,
            ProjectRepository,
        )

        project = ProjectRepository(db).create(name="P")
        event = EventRepository(db).create(
            name="Konzert", date="2026-09-01",
            event_type="konzert", project_id=project.id,
        )
        task = get_task("verfuegbarkeit_erfassen")
        rows = evaluate_task(task, TaskContext(db=db, event=event))
        assert rows[-1][1] is StepStatus.OPEN


class TestMitgliedStaysAction:
    def test_mitglied_remains_pure_action(self):
        task = get_task("mitglied_aufnehmen")
        assert all(step.check is None for step in task.steps), (
            "mitglied_aufnehmen deliberately stays a pure action — "
            "no DB-side check can identify 'the' newly added member."
        )
