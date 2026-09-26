"""``/api/events/{id}/availability`` matrix + bulk (M1 increment 2b).

First write endpoint: bulk upsert is UPDATE-first + INSERT on
miss (m7-Pattern der Repositories), dialektneutral für SQLite +
MariaDB, ein Commit am Ende (atomar).
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import (
    AvailabilityBulk,
    AvailabilityMatrix,
    AvailabilityMatrixEntry,
)
from ..tables import availability_table, events_table, singers_table

router = APIRouter(tags=["availability"])


def _require_event(db: Connection, event_id: str) -> None:
    exists = db.execute(
        select(events_table.c.id).where(events_table.c.id == event_id)
    ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="Event not found")


@router.get(
    "/api/events/{event_id}/availability",
    response_model=AvailabilityMatrix,
)
def get_matrix(
    event_id: str, db: Connection = Depends(get_db)
) -> AvailabilityMatrix:
    """Full matrix: every singer, missing row reads as ``none``."""
    _require_event(db, event_id)
    stmt = (
        select(
            singers_table.c.id,
            singers_table.c.full_name,
            singers_table.c.short_name,
            singers_table.c.voice_group,
            availability_table.c.status,
        )
        .select_from(
            singers_table.outerjoin(
                availability_table,
                (availability_table.c.singer_id == singers_table.c.id)
                & (availability_table.c.event_id == event_id),
            )
        )
        .order_by(singers_table.c.full_name)
    )
    entries = [
        AvailabilityMatrixEntry(
            singer_id=row["id"],
            full_name=row["full_name"],
            short_name=row["short_name"],
            voice_group=row["voice_group"],
            status=row["status"] or "none",
        )
        for row in db.execute(stmt).mappings().all()
    ]
    return AvailabilityMatrix(event_id=event_id, entries=entries)


@router.put("/api/events/{event_id}/availability")
def put_bulk(
    event_id: str,
    payload: AvailabilityBulk,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> dict:
    """Bulk upsert of statuses (atomic: one commit at the end)."""
    _require_event(db, event_id)
    now = datetime.now().isoformat()
    updated = 0
    for entry in payload.entries:
        touched = db.execute(
            update(availability_table)
            .where(
                (availability_table.c.singer_id == entry.singer_id)
                & (availability_table.c.event_id == event_id)
            )
            .values(status=entry.status, updated_at=now)
        ).rowcount
        if not touched:
            db.execute(
                insert(availability_table).values(
                    id=str(uuid.uuid4()),
                    singer_id=entry.singer_id,
                    event_id=event_id,
                    status=entry.status,
                    created_at=now,
                    updated_at=now,
                )
            )
        updated += 1
    db.commit()
    return {"event_id": event_id, "updated": updated}
