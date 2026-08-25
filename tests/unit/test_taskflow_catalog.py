"""Unit tests for the taskflow catalog (the 4 core tasks)."""

import pytest

from chormanager.domain.taskflow import (
    TASK_IDS,
    TaskDefinition,
    get_all_tasks,
    get_task,
)


EXPECTED_TASK_IDS = (
    "aufstellung_planen",
    "termin_anlegen",
    "verfuegbarkeit_erfassen",
    "mitglied_aufnehmen",
)


class TestCatalog:
    def test_catalog_contains_exactly_the_core_tasks(self):
        assert tuple(TASK_IDS) == EXPECTED_TASK_IDS

    def test_get_task_returns_definitions(self):
        for task_id in EXPECTED_TASK_IDS:
            task = get_task(task_id)
            assert isinstance(task, TaskDefinition)
            assert task.id == task_id

    def test_unknown_task_raises_key_error(self):
        with pytest.raises(KeyError):
            get_task("gibts_nicht")

    def test_every_step_has_unique_id_and_german_title(self):
        for task in get_all_tasks():
            step_ids = [step.id for step in task.steps]
            assert len(step_ids) == len(set(step_ids)), task.id
            for step in task.steps:
                assert step.title.strip(), (task.id, step.id)
                assert step.description.strip(), (task.id, step.id)

    def test_titles_are_non_empty(self):
        for task in get_all_tasks():
            assert task.title.strip()
            assert task.subtitle.strip()

    def test_aufstellung_chain_order(self):
        """The formation chain must follow the choir-director workflow:
        project -> termin -> besetzung -> availability -> formation."""
        steps = get_task("aufstellung_planen").steps
        assert [s.id for s in steps] == [
            "projekt_waehlen",
            "termin_waehlen",
            "besetzung_waehlen",
            "verfuegbarkeit_erfassen",
            "aufstellung_oeffnen",
        ]

    def test_verfuegbarkeit_chain_order(self):
        """Pick termin -> check besetzung -> record replies."""
        steps = get_task("verfuegbarkeit_erfassen").steps
        assert [s.id for s in steps] == [
            "termin_waehlen",
            "besetzung_pruefen",
            "verfuegbarkeit_erfassen",
        ]
