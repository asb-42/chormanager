"""Dependency evaluation for task chains.

The checker inspects the repositories through a :class:`TaskContext`
and reports, for every step of a :class:`TaskDefinition`, whether the
prerequisite is already satisfied. It never mutates data.

All check helpers are pure predicates ``check(context) -> bool`` and
are shared with the catalog so the UI layer can reuse them.
"""
from __future__ import annotations

import json
import os
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


def get_data_dir() -> str:
    """Return the choraufstellung data directory (formation JSONs).

    Mirrors :func:`chormanager.chor aufstellung.config.get_data_dir`
    without importing the Qt-bound choraufstellung package: the
    formation editor stores its JSON files next to its own module
    (``chormanager/choraufstellung/data``). Imported lazily and
    wrapped in try/except so a broken path never crashes evaluation.
    """
    try:
        from ...choraufstellung.config import get_data_dir as _ca_get_data_dir

        return _ca_get_data_dir()
    except Exception:
        # Fallback: derive the sibling package location directly.
        try:
            return os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "choraufstellung", "data",
            )
        except Exception:
            return ""


# ----------------------------------------------------------------------
# shared predicates (used by catalog.py)
# ----------------------------------------------------------------------

def resolve_project(context: TaskContext) -> Optional[Any]:
    """Return the pinned project or the UI's active project.

    The single source of truth for "Aktives Projekt" is the config
    key ``last_active_project_id`` — exactly what the info bar shows.
    The legacy ``projects.is_active`` DB flag is deliberately ignored:
    it is written by different code paths and can diverge from the UI
    (which produced "bereits vorhanden" while the info bar said
    "Keines").
    """
    if context.project is not None:
        return context.project
    if context.db is None:
        return None
    from ... import config as app_config

    project_id = app_config.get_last_active_project_id()
    if not project_id:
        return None
    return ProjectRepository(context.db).get_by_id(project_id)


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


def check_formation(context: TaskContext) -> bool:
    """True when a saved formation matches the resolved event.

    A formation "belongs" to an event when its ``metadata`` block
    carries the same ``event`` (name) AND ``event_date``. That is
    exactly what the choraufstellung editor writes when it is
    launched via the task wizard (``CHOR_EVENT_*`` env vars become
    ``_loaded_metadata`` and are persisted on save).

    Robustness contract (pinned by unit tests):
    * missing data directory  -> False (never raises)
    * corrupt JSON file       -> False (file is skipped)
    * ``backups/`` sub-folder -> ignored (autosaves don't count)
    * no event resolvable     -> False
    """
    event = resolve_event(context)
    if event is None:
        return False

    event_name = (getattr(event, "name", None) or "").strip()
    event_date = (getattr(event, "date", None) or "")[:10]
    if not event_name or not event_date:
        return False

    data_dir = get_data_dir()
    if not data_dir or not os.path.isdir(data_dir):
        return False

    try:
        entries = os.listdir(data_dir)
    except OSError:
        return False

    for filename in entries:
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            continue
        if (
            (metadata.get("event") or "").strip() == event_name
            and (metadata.get("event_date") or "")[:10] == event_date
        ):
            return True
    return False


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


def evaluate_task_for_card(
    task: TaskDefinition, context: TaskContext
) -> List[Tuple[TaskStep, StepStatus]]:
    """Evaluate every step for the Aufgaben-CARD display.

    Differs from :func:`evaluate_task` only in using
    ``TaskStep.is_done_for_card`` (the ``card_check`` predicate): the
    card shows the GLOBAL database state, while the wizard keeps its
    explicit-pick semantics (e.g. ``check_event_pinned``).

    Args:
        task: The task definition to evaluate.
        context: Current database context (usually nothing pinned).

    Returns:
        Ordered ``(step, status)`` tuples mirroring ``task.steps``.
    """
    return [
        (
            step,
            StepStatus.DONE
            if step.is_done_for_card(context)
            else StepStatus.OPEN,
        )
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
