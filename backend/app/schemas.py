"""Pydantic response/request schemas (Pydantic v2)."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class SingerOut(BaseModel):
    """Public singer shape for ``GET /api/singers*``."""

    id: str
    full_name: str
    short_name: Optional[str] = None
    voice_group: Optional[str] = None
    height: Optional[int] = None
    email: Optional[str] = None
    affinity_uuid: Optional[str] = None


class EventOut(BaseModel):
    """Public event shape incl. Zusagen counts (Desktop-Parität)."""

    id: str
    name: str
    date: str
    event_type: str
    location: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None
    yes_count: int = 0
    conditional_count: int = 0


class ProjectOut(BaseModel):
    """Public project shape for ``GET /api/projects*``."""

    id: str
    name: str
    description: Optional[str] = None
    is_active: Optional[int] = 0
    spielzeit: Optional[str] = None


class EventSummaryItem(BaseModel):
    """Per-event Zusagen counts within a project summary."""

    event_id: str
    name: str
    date: str
    yes: int = 0
    conditional: int = 0


class ProjectSummary(BaseModel):
    """Zusagen-Auswertung je Termin und Stimmgruppe."""

    project_id: str
    events: List[EventSummaryItem] = []
    by_voice_group: Dict[str, Dict[str, int]] = {}


AvailabilityStatus = Literal[
    "yes", "no", "none", "conditional", "unknown", "maybe"
]


class AvailabilityEntry(BaseModel):
    """One singer status within a bulk update."""

    singer_id: str
    status: AvailabilityStatus


class AvailabilityBulk(BaseModel):
    """Bulk payload for ``PUT /api/events/{id}/availability``."""

    entries: List[AvailabilityEntry] = []


class AvailabilityMatrixEntry(BaseModel):
    """One matrix row (missing availability reads as ``none``)."""

    singer_id: str
    full_name: str
    short_name: Optional[str] = None
    voice_group: Optional[str] = None
    status: str


class AvailabilityMatrix(BaseModel):
    """Full availability matrix of one event."""

    event_id: str
    entries: List[AvailabilityMatrixEntry] = []


class BesetzungOut(BaseModel):
    """Public lineup shape (``singer_ids`` parsed to a list)."""

    id: str
    name: str
    project_id: Optional[str] = None
    singer_ids: List[str] = []


class RepertoireOut(BaseModel):
    """Public repertoire shape."""

    id: str
    composer: Optional[str] = None
    title: str
    dates: Optional[str] = None
    country: Optional[str] = None
    publisher: Optional[str] = None
    arrangement: Optional[str] = None
    location: Optional[str] = None
    project_id: Optional[str] = None


class SelbstdarstellungOut(BaseModel):
    """Marketing text (empty table reads as blank content)."""

    id: Optional[str] = None
    content: str = ""
