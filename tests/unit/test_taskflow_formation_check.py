"""Unit tests for the formation-existence predicate (taskflow).

Regression background (user report 2026-09):
After running the "Eine Aufstellung für einen Auftritt planen" wizard
end-to-end, the Aufgaben card still showed the final step
"Aufstellung erstellen" as open (○). Root cause: the step had no
``check`` predicate, so ``is_done()`` could never become true.

Fix contract pinned here:
* ``check_formation(context)`` returns True when a formation file
  whose ``metadata`` matches the resolved event (by event name AND
  event date) exists in the choraufstellung data directory.
* The catalog wires ``aufstellung_oeffnen`` to that predicate.
* Mismatches (different date, different name, no event) stay open.
* The check never raises — broken/missing data dir counts as open.
"""

import json
import os

import pytest

from chormanager.data.database import Database

from chormanager.domain.taskflow import (
    StepStatus,
    TaskContext,
    evaluate_task,
    get_task,
)


def _seed_event(db, name="Konzert", date="2026-09-01",
                event_type="konzert", project_id=None):
    from chormanager.domain.repository import EventRepository

    kwargs = {"name": name, "date": date, "event_type": event_type}
    if project_id is not None:
        kwargs["project_id"] = project_id
    return EventRepository(db).create(**kwargs)


def _write_formation(tmp_path, event_name, event_date, placed=1):
    """Write a formation JSON like the editor would produce."""
    data_dir = tmp_path / "formations"
    data_dir.mkdir(exist_ok=True)
    payload = {
        "version": "1.0",
        "saved_at": "2026-09-08T12:00:00",
        "rows": 2,
        "cols": 5,
        "staggered": False,
        "voicing_config": [],
        "singers": [],
        "placed": [f"s{i}" for i in range(placed)],
        "metadata": {
            "project": "",
            "event": event_name,
            "event_date": event_date,
            "event_type": "auftritt",
        },
    }
    (data_dir / f"choraufstellung-{event_date}-version-2026-09-08.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return data_dir


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "formation_check.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


class TestCheckFormation:
    """check_formation: is there a formation file for the event?"""

    def test_open_without_event(self, db, monkeypatch, tmp_path):
        from chormanager.domain.taskflow import check_formation

        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(tmp_path / "formations"),
        )
        assert check_formation(TaskContext(db=db)) is False

    def test_done_when_matching_formation_exists(
        self, db, monkeypatch, tmp_path
    ):
        from chormanager.domain.taskflow import check_formation

        event = _seed_event(db, name="Erster Auftritt", date="2026-09-12")
        data_dir = _write_formation(
            tmp_path, event_name="Erster Auftritt", event_date="2026-09-12"
        )
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(data_dir),
        )
        assert check_formation(TaskContext(db=db, event=event)) is True

    def test_stays_open_for_different_date(
        self, db, monkeypatch, tmp_path
    ):
        from chormanager.domain.taskflow import check_formation

        event = _seed_event(db, name="Erster Auftritt", date="2026-09-12")
        _write_formation(
            tmp_path, event_name="Erster Auftritt", event_date="2026-09-13"
        )
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(tmp_path / "formations"),
        )
        assert check_formation(TaskContext(db=db, event=event)) is False

    def test_stays_open_for_different_name(
        self, db, monkeypatch, tmp_path
    ):
        from chormanager.domain.taskflow import check_formation

        event = _seed_event(db, name="Erster Auftritt", date="2026-09-12")
        _write_formation(
            tmp_path, event_name="Anderer Auftritt", event_date="2026-09-12"
        )
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(tmp_path / "formations"),
        )
        assert check_formation(TaskContext(db=db, event=event)) is False

    def test_never_raises_on_missing_dir(self, db, monkeypatch, tmp_path):
        from chormanager.domain.taskflow import check_formation

        event = _seed_event(db)
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(tmp_path / "does-not-exist"),
        )
        assert check_formation(TaskContext(db=db, event=event)) is False

    def test_never_raises_on_corrupt_json(self, db, monkeypatch, tmp_path):
        from chormanager.domain.taskflow import check_formation

        event = _seed_event(db, name="Konzert", date="2026-09-01")
        data_dir = tmp_path / "formations"
        data_dir.mkdir()
        (data_dir / "choraufstellung-2026-09-01-version-x.json").write_text(
            "{ not json", encoding="utf-8"
        )
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(data_dir),
        )
        assert check_formation(TaskContext(db=db, event=event)) is False

    def test_ignores_autosave_backups(self, db, monkeypatch, tmp_path):
        """Backups under data/backups must not count as formations."""
        from chormanager.domain.taskflow import check_formation

        event = _seed_event(db, name="Konzert", date="2026-09-01")
        data_dir = tmp_path / "formations"
        backups = data_dir / "backups"
        backups.mkdir(parents=True)
        payload = {
            "metadata": {"event": "Konzert", "event_date": "2026-09-01"},
            "placed": ["s1"],
        }
        (backups / "autosave_20260901_120000.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(data_dir),
        )
        assert check_formation(TaskContext(db=db, event=event)) is False


class TestCatalogWiring:
    """The catalog wires aufstellung_oeffnen to check_formation."""

    def test_final_step_has_a_check(self):
        task = get_task("aufstellung_planen")
        final = task.steps[-1]
        assert final.id == "aufstellung_oeffnen"
        assert final.check is not None, (
            "Regression 2026-09: the final step needs a DB-side check "
            "(check_formation) so the Aufgaben card can show ✓ after "
            "the wizard created a formation."
        )

    def test_final_step_done_when_formation_exists(
        self, db, monkeypatch, tmp_path
    ):
        event = _seed_event(db, name="Erster Auftritt", date="2026-09-12")
        data_dir = _write_formation(
            tmp_path, event_name="Erster Auftritt", event_date="2026-09-12"
        )
        monkeypatch.setattr(
            "chormanager.domain.taskflow.checker.get_data_dir",
            lambda: str(data_dir),
        )
        task = get_task("aufstellung_planen")
        rows = evaluate_task(task, TaskContext(db=db, event=event))
        assert rows[-1][1] is StepStatus.DONE
