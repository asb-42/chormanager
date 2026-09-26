"""``/api/events`` read + write endpoints (M1)."""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import case, delete, func, insert, or_, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import EventCreate, EventOut, EventUpdate
from ..tables import availability_table, events_table

router = APIRouter(prefix="/api/events", tags=["events"])

_READ_COLUMNS = [
    events_table.c.id,
    events_table.c.name,
    events_table.c.date,
    events_table.c.event_type,
    events_table.c.location,
    events_table.c.description,
    events_table.c.project_id,
]

_YES = func.sum(case((availability_table.c.status == "yes", 1), else_=0))
_COND = func.sum(
    case((availability_table.c.status == "conditional", 1), else_=0)
)


def _with_counts(stmt):
    """Join availability counts (Desktop: Zusagen/Vorbehalt-Spalten)."""
    return (
        stmt.add_columns(
            func.coalesce(_YES, 0).label("yes_count"),
            func.coalesce(_COND, 0).label("conditional_count"),
        )
        .select_from(
            events_table.outerjoin(
                availability_table,
                availability_table.c.event_id == events_table.c.id,
            )
        )
        .group_by(*_READ_COLUMNS)
    )


@router.get("", response_model=List[EventOut])
def list_events(
    project_id: Optional[str] = None,
    search: Optional[str] = None,
    event_type: Optional[str] = None,
    db: Connection = Depends(get_db),
) -> List[EventOut]:
    """List events (date desc), optionally filtered."""
    stmt = select(*_READ_COLUMNS).order_by(events_table.c.date.desc())
    if project_id:
        stmt = stmt.where(events_table.c.project_id == project_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                events_table.c.name.ilike(like),
                events_table.c.description.ilike(like),
                events_table.c.event_type.ilike(like),
            )
        )
    if event_type:
        stmt = stmt.where(events_table.c.event_type == event_type)
    rows = db.execute(_with_counts(stmt)).mappings().all()
    return [EventOut(**dict(row)) for row in rows]


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: str, db: Connection = Depends(get_db)
) -> EventOut:
    """Return one event by id (404 when unknown)."""
    stmt = select(*_READ_COLUMNS).where(events_table.c.id == event_id)
    row = db.execute(_with_counts(stmt)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventOut(**dict(row))


def _read_one(db: Connection, event_id: str) -> EventOut:
    stmt = select(*_READ_COLUMNS).where(events_table.c.id == event_id)
    row = db.execute(_with_counts(stmt)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventOut(**dict(row))


@router.post("", response_model=EventOut, status_code=201)
def create_event(
    payload: EventCreate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> EventOut:
    """Create an event (id/timestamps generated server-side)."""
    now = datetime.now().isoformat()
    event_id = str(uuid.uuid4())
    db.execute(
        insert(events_table).values(
            id=event_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(exclude_unset=True),
        )
    )
    db.commit()
    return _read_one(db, event_id)


@router.put("/{event_id}", response_model=EventOut)
def update_event(
    event_id: str,
    payload: EventUpdate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> EventOut:
    """Partially update an event (404 when unknown)."""
    _read_one(db, event_id)
    values = payload.model_dump(exclude_unset=True)
    if values:
        db.execute(
            update(events_table)
            .where(events_table.c.id == event_id)
            .values(updated_at=datetime.now().isoformat(), **values)
        )
        db.commit()
    return _read_one(db, event_id)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: str,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete an event incl. availability rows (deterministic cascade)."""
    _read_one(db, event_id)
    db.execute(
        delete(availability_table).where(
            availability_table.c.event_id == event_id
        )
    )
    db.execute(delete(events_table).where(events_table.c.id == event_id))
    db.commit()
    return Response(status_code=204)
