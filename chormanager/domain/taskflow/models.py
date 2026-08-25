"""Task value objects for the ChorManager task flow.

The classes in this module describe *tasks* a choir director performs
("plan a formation", "record availability") as ordered chains of
*steps*. A step either has a database-side completion ``check``
(prerequisite) or is a pure action performed inside the wizard
(``check=None``).

This module must stay free of Qt imports so it can be unit-tested
headless and reused by other front-ends later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional


class StepStatus(str, Enum):
    """Completion state of a single :class:`TaskStep`."""

    DONE = "done"
    OPEN = "open"


@dataclass
class TaskContext:
    """Mutable context threaded through checks and wizard steps.

    Attributes:
        db: Database handle (``chormanager.data.database.Database``).
        project: Project selected/created during the current run.
        event: Event selected/created during the current run.
        besetzung: Besetzung selected/created during the current run.

    The pinned entities take precedence over automatic detection so a
    half-finished run keeps referring to the objects the user chose.
    """

    db: Any = None
    project: Any = None
    event: Any = None
    besetzung: Any = None


@dataclass
class TaskStep:
    """A single step inside a task chain.

    Attributes:
        id: Stable identifier unique within its task.
        title: Human-readable German title shown in the UI.
        description: One-sentence explanation for non-technical users.
        check: Optional predicate ``check(context) -> bool`` evaluated
            against the current database state. ``None`` marks a pure
            action step that can only be completed by executing it.
    """

    id: str
    title: str
    description: str = ""
    check: Optional[Callable[[Any], bool]] = None

    def is_done(self, context: Any) -> bool:
        """Return whether this step is satisfied for ``context``.

        A missing or failing check counts as *not done* so one broken
        predicate can never abort the whole evaluation.
        """
        if self.check is None:
            return False
        try:
            return bool(self.check(context))
        except Exception:
            return False


@dataclass
class TaskDefinition:
    """An end-user task modelled as an ordered list of steps.

    Attributes:
        id: Stable identifier (see ``catalog.TASK_IDS``).
        title: Card headline shown on the tasks view.
        subtitle: Friendly one-liner explaining when to use the task.
        icon_name: FDO-style icon name hint for the UI layer.
        steps: Ordered chain; prerequisites come before actions.
    """

    id: str
    title: str
    subtitle: str
    icon_name: str
    steps: List[TaskStep] = field(default_factory=list)

    def step_ids(self) -> List[str]:
        """Return the ids of all steps in order."""
        return [step.id for step in self.steps]
