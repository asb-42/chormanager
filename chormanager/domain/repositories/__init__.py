"""Repository layer for ChorManager — individual repository modules."""

from .singer import SingerRepository
from .event import EventRepository
from .availability import AvailabilityRepository
from .project import ProjectRepository
from .besetzung import BesetzungRepository
from .repertoire import RepertoireRepository

__all__ = [
    "SingerRepository",
    "EventRepository",
    "AvailabilityRepository",
    "ProjectRepository",
    "BesetzungRepository",
    "RepertoireRepository",
]
