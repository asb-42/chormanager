"""ChorManager task flow: guided, dependency-checked user tasks.

This package is the domain core of the Aufgaben view: it models
end-user tasks ("plan a formation") as ordered step chains and
evaluates their prerequisites against the repositories.

* :mod:`.models`   — value objects (TaskStep, TaskDefinition, context)
* :mod:`.checker`  — dependency evaluation + shared predicates
* :mod:`.catalog`  — the concrete catalog of tasks

The package must stay free of Qt imports.
"""
from .checker import (
    check_availability,
    check_besetzung,
    check_project,
    check_termin,
    evaluate_task,
    next_open_step,
    progress,
    resolve_besetzung,
    resolve_event,
    resolve_project,
)
from .catalog import TASK_IDS, get_all_tasks, get_task
from .models import StepStatus, TaskContext, TaskDefinition, TaskStep

__all__ = [
    # models
    "StepStatus",
    "TaskContext",
    "TaskDefinition",
    "TaskStep",
    # checker
    "check_availability",
    "check_besetzung",
    "check_project",
    "check_termin",
    "evaluate_task",
    "next_open_step",
    "progress",
    "resolve_besetzung",
    "resolve_event",
    "resolve_project",
    # catalog
    "TASK_IDS",
    "get_all_tasks",
    "get_task",
]
