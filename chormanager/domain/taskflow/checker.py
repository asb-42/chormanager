"""Dependency evaluation for task chains.

The checker inspects the repositories through a :class:`TaskContext`
and reports, for every step of a :class:`TaskDefinition`, whether the
prerequisite is already satisfied. It never mutates data.

All check helpers are pure predicates ``check(context) -> bool`` and
are shared with the catalog so the UI layer can reuse them.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ..repository import (
    AvailabilityRepository,
    BesetzungRepository,
    EventRepository,
    ProjectRepository,
)
from .models import StepStatus, TaskContext, TaskDefinition, TaskStep

#: Statuses that count as "will attend" for planning purposes.
_POSITIVE_STATUSES = ("yes", "conditional")


# ----------------------------------------------------------------------
# shared predicates (used by catalog.py)
# ----------------------------------------------------------------------

def resolve_project(context: TaskContext) -> Optional[Any]:
    """Return the pinned project or the currently active one."""
    if context.project is not None:
        return context.project
    if context.db is None:
        return None
    return ProjectRepository(context.db).get_active()


def check_project(context: TaskContext) -> bool:
    """True when an active (or pinned) project exists."""
    return resolve_project(context) is not None


def check_termin(context: TaskContext) -> bool:
    """True when an event is pinned or the project has any event."""
    if context.event is not None:
        return True
    project = resolve_project(context)
    if project is None or context.db is None:
        return False
    events = EventRepository(context.db).get_all()
    return any(event.project_id == project.id for event in events)


def check_besetzung(context: TaskContext) -> bool:
    """True when a besetzung is pinned or the project has one."""
    if context.besetzung is not None:
        return True
    project = resolve_project(context)
    if project is None or context.db is None:
        return False
    besetzungen = BesetzungRepository(context.db).get_by_project(project.id)
    return len(besetzungen) > 0


def _latest_project_event(context: TaskContext) -> Optional[Any]:
    """Return the newest event of the resolved project, if any."""
    project = resolve_project(context)
    if project is None or context.db is None:
        return None
    events = [
        event
        for event in EventRepository(context.db).get_all()
        if event.project_id == project.id
    ]
    if not events:
        return None
    # ISO dates sort lexicographically; empty dates sink to the end.
    return max(events, key=lambda event: event.date or "")


def resolve_event(context: TaskContext) -> Optional[Any]:
    """Return the pinned event or the project's latest one."""
    if context.event is not None:
        return context.event
    return _latest_project_event(context)


def check_event_pinned(context: TaskContext) -> bool:
    """True only when the wizard context pins a concrete event.

    Used for steps where picking the termin IS the user's decision
    (e.g. recording availability) — such steps are never auto-done.
    """
    return context.event is not None


def resolve_besetzung_for_event(context: TaskContext) -> Optional[Any]:
    """Return the besetzung matching the pinned event's project.

    Prefers the pinned besetzung; falls back to the first besetzung of
    the event's project. Returns ``None`` when no event is pinned or
    the project has none.
    """
    if context.besetzung is not None:
        return context.besetzung
    event = context.event
    if event is None or context.db is None or not event.project_id:
        return None
    besetzungen = BesetzungRepository(context.db).get_by_project(
        event.project_id
    )
    return besetzungen[0] if besetzungen else None


def check_besetzung_for_event(context: TaskContext) -> bool:
    """True when the termin's project has a (pinned) besetzung.

    A termin without project has no besetzung linkage at all — the
    step counts as satisfied (the availability dialog will then show
    all active singers).
    """
    if resolve_besetzung_for_event(context) is not None:
        return True
    event = context.event
    return event is not None and not event.project_id


def resolve_besetzung(context: TaskContext) -> Optional[Any]:
    """Return the pinned besetzung or the project's first one."""
    if context.besetzung is not None:
        return context.besetzung
    project = resolve_project(context)
    if project is None or context.db is None:
        return None
    besetzungen = BesetzungRepository(context.db).get_by_project(project.id)
    return besetzungen[0] if besetzungen else None


def check_availability(context: TaskContext) -> bool:
    """True when the relevant event has at least one positive reply."""
    event = resolve_event(context)
    if event is None or context.db is None:
        return False
    availabilities = AvailabilityRepository(context.db).get_by_event(event.id)
    return any(a.status in _POSITIVE_STATUSES for a in availabilities)


# ----------------------------------------------------------------------
# evaluation API
# ----------------------------------------------------------------------

def evaluate_task(
    task: TaskDefinition, context: TaskContext
) -> List[Tuple[TaskStep, StepStatus]]:
    """Evaluate every step of ``task`` against ``context``.

    Args:
        task: The task definition to evaluate.
        context: Current wizard/database context.

    Returns:
        Ordered ``(step, status)`` tuples mirroring ``task.steps``.
    """
    return [
        (step, StepStatus.DONE if step.is_done(context) else StepStatus.OPEN)
        for step in task.steps
    ]


def next_open_step(
    task: TaskDefinition, context: TaskContext
) -> Optional[TaskStep]:
    """Return the first step whose prerequisite is still open."""
    for step, status in evaluate_task(task, context):
        if status is StepStatus.OPEN:
            return step
    return None


def progress(
    task: TaskDefinition, context: TaskContext
) -> Tuple[int, int]:
    """Return ``(done_count, total_count)`` for ``task``."""
    rows = evaluate_task(task, context)
    done = sum(1 for _, status in rows if status is StepStatus.DONE)
    return done, len(rows)
