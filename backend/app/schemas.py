"""Pydantic response/request schemas (Pydantic v2)."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _to_str_or_none(value: Any) -> Optional[str]:
    """Coerce loose SQLite values (e.g. int postal codes in TEXT
    columns of real desktop DBs) to strings."""
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


class _StrCoercionMixin:
    """Coerce contact/address fields that may hold ints in the wild."""

    @field_validator(
        "phone",
        "street",
        "postal_code",
        "city",
        "guardian1_phone",
        "guardian2_phone",
        mode="before",
    )
    @classmethod
    def _coerce_stringy(cls, value: Any) -> Optional[str]:
        return _to_str_or_none(value)


class SingerOut(BaseModel, _StrCoercionMixin):
    """Public singer shape for ``GET /api/singers*`` (volles Modell)."""

    id: str
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
    guardian1: Optional[str] = None
    guardian1_phone: Optional[str] = None
    guardian2: Optional[str] = None
    guardian2_phone: Optional[str] = None
    social_contacts: Optional[str] = None
    joined_year: Optional[int] = None
    joined_month: Optional[int] = None
    left_year: Optional[int] = None
    left_month: Optional[int] = None
    affinity_uuid: Optional[str] = None


class SingerCreate(BaseModel, _StrCoercionMixin):
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
    guardian1: Optional[str] = None
    guardian1_phone: Optional[str] = None
    guardian2: Optional[str] = None
    guardian2_phone: Optional[str] = None
    social_contacts: Optional[str] = None
    joined_year: Optional[int] = None
    joined_month: Optional[int] = None
    left_year: Optional[int] = None
    left_month: Optional[int] = None
    affinity_uuid: Optional[str] = None


class SingerUpdate(BaseModel, _StrCoercionMixin):
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
    guardian1: Optional[str] = None
    guardian1_phone: Optional[str] = None
    guardian2: Optional[str] = None
    guardian2_phone: Optional[str] = None
    social_contacts: Optional[str] = None
    joined_year: Optional[int] = None
    joined_month: Optional[int] = None
    left_year: Optional[int] = None
    left_month: Optional[int] = None
    affinity_uuid: Optional[str] = None


SingerSortField = Literal["full_name", "voice_group", "height"]
SingerSortDirection = Literal["asc", "desc"]


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


class BackupOut(BaseModel):
    """Backup file entry."""

    id: str
    size: int = 0
    modified_at: str = ""


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
