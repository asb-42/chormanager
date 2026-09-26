"""Pydantic response/request schemas (Pydantic v2)."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SingerOut(BaseModel):
    """Public singer shape for ``GET /api/singers*``."""

    id: str
    full_name: str
    short_name: Optional[str] = None
    voice_group: Optional[str] = None
    height: Optional[int] = None
    email: Optional[str] = None
    affinity_uuid: Optional[str] = None


class SingerCreate(BaseModel):
    """Payload for ``POST /api/singers`` (id/timestamps server-side)."""

    full_name: str
    short_name: Optional[str] = None
    birth_date: Optional[str] = None
    voice_group: Optional[str] = None
    height: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    affinity_uuid: Optional[str] = None


class SingerUpdate(BaseModel):
    """Payload for ``PUT /api/singers/{id}`` (partial)."""

    full_name: Optional[str] = None
    short_name: Optional[str] = None
    birth_date: Optional[str] = None
    voice_group: Optional[str] = None
    height: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
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


class EventCreate(BaseModel):
    """Payload for ``POST /api/events``."""

    name: str
    date: str
    event_type: str
    location: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None


class EventUpdate(BaseModel):
    """Payload for ``PUT /api/events/{id}`` (partial)."""

    name: Optional[str] = None
    date: Optional[str] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None


class ProjectCreate(BaseModel):
    """Payload for ``POST /api/projects``."""

    name: str
    description: Optional[str] = None
    spielzeit: Optional[str] = None
    is_active: Optional[int] = 0


class ProjectUpdate(BaseModel):
    """Payload for ``PUT /api/projects/{id}`` (partial)."""

    name: Optional[str] = None
    description: Optional[str] = None
    spielzeit: Optional[str] = None
    is_active: Optional[int] = None


class BesetzungCreate(BaseModel):
    """Payload for ``POST /api/besetzungen``."""

    name: str
    project_id: Optional[str] = None
    singer_ids: List[str] = []


class BesetzungUpdate(BaseModel):
    """Payload for ``PUT /api/besetzungen/{id}`` (partial)."""

    name: Optional[str] = None
    project_id: Optional[str] = None
    singer_ids: Optional[List[str]] = None


class RepertoireCreate(BaseModel):
    """Payload for ``POST /api/repertoire``."""

    title: str
    composer: Optional[str] = None
    dates: Optional[str] = None
    country: Optional[str] = None
    publisher: Optional[str] = None
    arrangement: Optional[str] = None
    location: Optional[str] = None
    project_id: Optional[str] = None


class RepertoireUpdate(BaseModel):
    """Payload for ``PUT /api/repertoire/{id}`` (partial)."""

    title: Optional[str] = None
    composer: Optional[str] = None
    dates: Optional[str] = None
    country: Optional[str] = None
    publisher: Optional[str] = None
    arrangement: Optional[str] = None
    location: Optional[str] = None
    project_id: Optional[str] = None


class SelbstdarstellungPut(BaseModel):
    """Payload for ``PUT /api/selbstdarstellung`` (upsert)."""

    content: str


class FormationCreate(BaseModel):
    """Payload for ``POST /api/formations``."""

    name: Optional[str] = None
    rows: int = Field(ge=1, le=50)
    cols: int = Field(ge=1, le=50)
    staggered: bool = False
    event_id: Optional[str] = None


class FormationListItem(BaseModel):
    """Compact shape for ``GET /api/formations``."""

    id: str
    name: Optional[str] = None
    rows: int
    cols: int
    event_id: Optional[str] = None
    updated_at: str


class FormationRuleOut(BaseModel):
    """Optimizer rule catalog entry."""

    id: str
    name: str
    primary: bool


class StoredSinger(BaseModel):
    """Singer dict as stored inside a formation."""

    singer_id: str
    name: str = ""
    voice_group: Optional[str] = None
    height: Optional[int] = 0
    affinity: str = ""


class PlacedEntry(BaseModel):
    """One placed singer (singer snapshot + position)."""

    singer: StoredSinger
    row: int
    col: int


class FormationDoc(BaseModel):
    """Full formation document."""

    id: str
    name: Optional[str] = None
    rows: int
    cols: int
    staggered: bool = False
    voicing_config: List[str] = []
    singers: List[StoredSinger] = []
    placed: List[PlacedEntry] = []
    metadata: Dict = {}
    event_id: Optional[str] = None


class PlacementIn(BaseModel):
    """One placement within ``PlacementsPut``."""

    singer_id: str
    row: int
    col: int


class PlacementsPut(BaseModel):
    """Payload for ``PUT /api/formations/{id}/placements``."""

    rows: Optional[int] = Field(default=None, ge=1, le=50)
    cols: Optional[int] = Field(default=None, ge=1, le=50)
    staggered: Optional[bool] = None
    placements: List[PlacementIn] = []


class OptimizeIn(BaseModel):
    """Payload for ``POST /api/formations/{id}/optimize``."""

    rule_ids: List[str] = []


class OptimizePreviewPlacement(BaseModel):
    """One previewed position (not persisted)."""

    singer_id: str
    row: int
    col: int


class OptimizeOut(BaseModel):
    """Optimizer preview (apply via placements PUT)."""

    placements: List[OptimizePreviewPlacement] = []
    swap_count: int = 0
    cost: float = 0.0
    applied_rules: List[str] = []
    messages: List[str] = []
