"""Unit tests for the taskflow domain logic (models + checker).

The taskflow package is pure Python (no Qt imports) and evaluates
task dependency chains (e.g. "plan a formation") against the
repositories. These tests exercise the models and the checker
against a real, temporary SQLite database.
"""

import pytest

from chormanager.data.database import Database

from chormanager.domain.taskflow import (
    StepStatus,
    TaskContext,
    TaskDefinition,
    TaskStep,
    evaluate_task,
    get_task,
    next_open_step,
    progress,
)


PERFORMANCE_TYPES = ("konzert", "auftritt", "sofa")


@pytest.fixture
def db(tmp_path):
    """Create a fresh test database."""
    database = Database(str(tmp_path / "taskflow.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


@pytest.fixture
def make_active_project(monkeypatch):
    """Factory: create a project AND make it the UI's active project.

    The UI's "Aktives Projekt" lives in the config key
    ``last_active_project_id`` (that is what the info bar shows), so
    tests must patch that key — the legacy DB flag alone must NOT
    make a project count as active.
    """
    import chormanager.config as config_module
    from chormanager.domain.repository import ProjectRepository

    def _make(db, name="Hoffmann 2026"):
        repo = ProjectRepository(db)
        project = repo.create(name=name)
        repo.set_active(project.id)  # DB-Flag synchron halten
        monkeypatch.setattr(
            config_module,
            "get_last_active_project_id",
            lambda: project.id,
        )
        return project

    return _make


def _seed_project(db, name="Hoffmann 2026", active=True):
    """Create a project row; only sets the legacy DB flag.

    NOTE: this does NOT make the project 'active' for the checker —
    use ``make_active_project`` for that.
    """
    from chormanager.domain.repository import ProjectRepository

    repo = ProjectRepository(db)
    project = repo.create(name=name)
    if active:
        repo.set_active(project.id)
    return project


def _seed_event(db, project_id=None, name="Konzert", date="2026-09-01",
                event_type="konzert"):
    from chormanager.domain.repository import EventRepository

    repo = EventRepository(db)
    kwargs = {"name": name, "date": date, "event_type": event_type}
    if project_id is not None:
        kwargs["project_id"] = project_id
    return repo.create(**kwargs)


def _seed_besetzung(db, project_id, singer_ids):
    from chormanager.domain.repository import BesetzungRepository

    repo = BesetzungRepository(db)
    return repo.create(name="Konzertbesetzung", project_id=project_id,
                       singer_ids=singer_ids)


def _seed_singer(db, full_name="Anna Alt", voice_group="Alt 1"):
    from chormanager.domain.repository import SingerRepository

    repo = SingerRepository(db)
    return repo.create(full_name=full_name, voice_group=voice_group)


def _seed_availability(db, singer_id, event_id, status="yes"):
    from chormanager.domain.repository import AvailabilityRepository

    repo = AvailabilityRepository(db)
    return repo.update(singer_id, event_id, status)


class TestTaskStep:
    """Tests for the TaskStep value object."""

    def test_action_step_without_check_is_never_done(self):
        step = TaskStep(id="x", title="Etwas tun")
        assert step.is_done(TaskContext()) is False

    def test_check_returning_true_means_done(self):
        step = TaskStep(id="x", title="X", check=lambda ctx: True)
        assert step.is_done(TaskContext()) is True

    def test_failing_check_is_treated_as_open(self):
        def broken(ctx):
            raise RuntimeError("boom")

        step = TaskStep(id="x", title="X", check=broken)
        # A crashing check must not break the whole evaluation.
        assert step.is_done(TaskContext()) is False


class TestCheckerHelpers:
    """Tests for evaluate_task / next_open_step / progress."""

    def _two_step_task(self):
        steps = [
            TaskStep(id="a", title="A", check=lambda ctx: bool(ctx.project)),
            TaskStep(id="b", title="B"),
        ]
        return TaskDefinition(
            id="t", title="T", subtitle="", icon_name="", steps=steps
        )

    def test_evaluate_returns_ordered_statuses(self):
        task = self._two_step_task()
        context = TaskContext(project=object())
        rows = evaluate_task(task, context)

        assert [status for _, status in rows] == [
            StepStatus.DONE,
            StepStatus.OPEN,
        ]

    def test_next_open_step_returns_first_open(self):
        task = self._two_step_task()
        context = TaskContext()
        assert next_open_step(task, context).id == "a"

        context.project = object()
        assert next_open_step(task, context).id == "b"

    def test_progress_counts_done_steps(self):
        task = self._two_step_task()

        assert progress(task, TaskContext()) == (0, 2)
        assert progress(task, TaskContext(project=object())) == (1, 2)


class TestAufstellungPlanenChain:
    """Dependency-chain tests for the 'Neue Aufstellung planen' task."""

    @pytest.fixture
    def task(self):
        return get_task("aufstellung_planen")

    def test_empty_db_all_prerequisites_open(self, db, task):
        rows = evaluate_task(task, TaskContext(db=db))
        statuses = [status for _, status in rows]

        assert statuses == [StepStatus.OPEN] * 5
        assert progress(task, TaskContext(db=db)) == (0, 5)

    def test_active_project_satisfies_first_step(self, db, task,
                                                  make_active_project):
        project = make_active_project(db)
        context = TaskContext(db=db)
        rows = evaluate_task(task, context)

        assert rows[0] == (task.steps[0], StepStatus.DONE)
        assert next_open_step(task, context).id == task.steps[1].id

    def test_event_must_belong_to_project(self, db, task,
                                           make_active_project):
        project = make_active_project(db)
        other = _seed_project(db, name="Anderes Projekt", active=False)
        _seed_event(db, project_id=other.id)

        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[1][1] is StepStatus.OPEN

        _seed_event(db, project_id=project.id)
        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[1][1] is StepStatus.DONE

    def test_besetzung_must_belong_to_project(self, db, task,
                                               make_active_project):
        project = make_active_project(db)
        _seed_event(db, project_id=project.id)
        other = _seed_project(db, name="Fremd", active=False)
        _seed_besetzung(db, other.id, [])

        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[2][1] is StepStatus.OPEN

        _seed_besetzung(db, project.id, [])
        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[2][1] is StepStatus.DONE

    def test_availability_counts_yes_and_conditional(self, db, task,
                                                      make_active_project):
        project = make_active_project(db)
        event = _seed_event(db, project_id=project.id)
        _seed_besetzung(db, project.id, [])
        singer = _seed_singer(db)

        _seed_availability(db, singer.id, event.id, status="no")
        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[3][1] is StepStatus.OPEN

        _seed_availability(db, singer.id, event.id, status="conditional")
        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[3][1] is StepStatus.DONE

    def test_contextual_event_beats_auto_detection(self, db, task,
                                                    make_active_project):
        project = make_active_project(db)
        old_event = _seed_event(db, project_id=project.id,
                                date="2026-01-01")
        new_event = _seed_event(db, project_id=project.id,
                                date="2026-12-31")

        # Only the newest event has a yes-answer; the wizard context
        # pins an older one, so the check must look at that one.
        singer = _seed_singer(db)
        _seed_availability(db, singer.id, new_event.id, status="yes")

        pinned = TaskContext(db=db, event=old_event)
        rows = evaluate_task(task, pinned)
        assert rows[3][1] is StepStatus.OPEN

        unpinned = TaskContext(db=db)
        rows = evaluate_task(task, unpinned)
        assert rows[3][1] is StepStatus.DONE

    def test_legacy_db_flag_alone_is_not_active(self, db, task):
        """Regression: the wizard said 'Projekt bereits vorhanden'
        while the info bar showed 'Keines'. The legacy
        ``projects.is_active`` DB flag must NOT count as active —
        only the UI's config key does."""
        _seed_project(db)  # sets only the DB flag

        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[0][1] is StepStatus.OPEN

    def test_final_step_stays_open_until_executed(self, db, task):
        """The last step is an action performed by the wizard; it has
        no DB-side completion condition."""
        final_row = evaluate_task(task, TaskContext(db=db))[-1]
        assert final_row[0].id == "aufstellung_oeffnen"
        assert final_row[1] is StepStatus.OPEN


class TestOtherTasks:
    """Chain tests for the three smaller tasks."""

    def test_termin_anlegen_requires_project(self, db, make_active_project):
        task = get_task("termin_anlegen")
        rows = evaluate_task(task, TaskContext(db=db))
        assert [s for _, s in rows] == [StepStatus.OPEN, StepStatus.OPEN]

        make_active_project(db)
        rows = evaluate_task(task, TaskContext(db=db))
        assert [s for _, s in rows][:2] == [StepStatus.DONE, StepStatus.OPEN]

    def test_verfuegbarkeit_termin_step_needs_explicit_pick(self, db):
        """Regression: 'Termin auswählen' is THE decision of this task
        and must never be auto-detected as done."""
        task = get_task("verfuegbarkeit_erfassen")
        _seed_event(db, project_id=_seed_project(db).id)

        rows = evaluate_task(task, TaskContext(db=db))
        assert rows[0][1] is StepStatus.OPEN

        from chormanager.domain.repository import EventRepository
        pinned = EventRepository(db).get_all()[0]
        rows = evaluate_task(task, TaskContext(db=db, event=pinned))
        assert rows[0][1] is StepStatus.DONE

    def test_verfuegbarkeit_besetzung_step_matches_event_project(
        self, db
    ):
        """The besetzung must belong to the termin's project."""
        task = get_task("verfuegbarkeit_erfassen")
        project = _seed_project(db)
        other = _seed_project(db, name="Fremd", active=False)
        event = _seed_event(db, project_id=project.id)
        _seed_besetzung(db, other.id, [])

        context = TaskContext(db=db, event=event)
        rows = evaluate_task(task, context)
        assert rows[1][1] is StepStatus.OPEN

        _seed_besetzung(db, project.id, [])
        rows = evaluate_task(task, context)
        assert rows[1][1] is StepStatus.DONE

    def test_verfuegbarkeit_besetzung_step_skipped_without_project(
        self, db
    ):
        """A termin without project has no besetzung linkage; the step
        counts as satisfied (all active singers will be shown)."""
        task = get_task("verfuegbarkeit_erfassen")
        event = _seed_event(db, project_id=None)

        rows = evaluate_task(task, TaskContext(db=db, event=event))
        assert rows[1][1] is StepStatus.DONE

    def test_mitglied_aufnehmen_has_no_prerequisites(self, db):
        task = get_task("mitglied_aufnehmen")
        assert len(task.steps) >= 1
        rows = evaluate_task(task, TaskContext(db=db))
        assert all(status is StepStatus.OPEN for _, status in rows)


class TestBesetzungResolverForEvent:
    """resolve_besetzung_for_event mirrors the event's project."""

    def test_prefers_pinned_besetzung_of_same_project(self, db):
        from chormanager.domain.taskflow import resolve_besetzung_for_event

        project = _seed_project(db)
        event = _seed_event(db, project_id=project.id)
        besetzung = _seed_besetzung(db, project.id, [])

        context = TaskContext(db=db, event=event, besetzung=besetzung)
        assert resolve_besetzung_for_event(context) is besetzung

    def test_detects_first_besetzung_of_event_project(self, db):
        from chormanager.domain.taskflow import resolve_besetzung_for_event

        project = _seed_project(db)
        event = _seed_event(db, project_id=project.id)
        besetzung = _seed_besetzung(db, project.id, [])

        context = TaskContext(db=db, event=event)
        assert resolve_besetzung_for_event(context).id == besetzung.id

    def test_none_without_event(self, db):
        from chormanager.domain.taskflow import resolve_besetzung_for_event

        assert resolve_besetzung_for_event(TaskContext(db=db)) is None
