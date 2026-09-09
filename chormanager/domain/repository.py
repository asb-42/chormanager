"""Repository layer for ChorManager — backward-compatible re-exports.

Individual repositories are now in domain/repositories/.

The module-level :func:`_whitelist_kwargs` helper (S-1 fix: SQL column
injection guard) is re-exported here so existing callers that import it
from ``chormanager.domain.repository`` keep working.
"""

from typing import Any, Dict, Iterable

from .repositories.singer import SingerRepository
from .repositories.event import EventRepository
from .repositories.availability import AvailabilityRepository
from .repositories.project import ProjectRepository
from .repositories.besetzung import BesetzungRepository
from .repositories.repertoire import RepertoireRepository


def _whitelist_kwargs(kwargs: Dict[str, Any], allowed: Iterable[str]) -> Dict[str, Any]:
    """Filter kwargs against a column whitelist.

    Args:
        kwargs: Input keyword-arguments (e.g. from create(**kwargs)).
        allowed: Allowed column names (e.g. class._COLS).

    Returns:
        Dict[str, Any]: New dict containing only allowed columns
        (order preserved from kwargs).

    Raises:
        ValueError: If kwargs contain a column that is not allowed.
    """
    allowed_set = set(allowed)
    unknown = [k for k in kwargs.keys() if k not in allowed_set]
    if unknown:
        raise ValueError(
            f"Unknown column(s) for INSERT/UPDATE: {unknown!r}. "
            f"Allowed: {sorted(allowed_set)}"
        )
    return {k: v for k, v in kwargs.items() if k in allowed_set}


__all__ = [
    "SingerRepository",
    "EventRepository",
    "AvailabilityRepository",
    "ProjectRepository",
    "BesetzungRepository",
    "RepertoireRepository",
    "_whitelist_kwargs",
]
