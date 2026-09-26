"""``/api/singers`` read + write endpoints (M1)."""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import (
    SingerCreate,
    SingerOut,
    SingerSortDirection,
    SingerSortField,
    SingerUpdate,
)
from ..tables import availability_table, singers_table

router = APIRouter(prefix="/api/singers", tags=["singers"])

_READ_COLUMNS = [
    singers_table.c.id,
    singers_table.c.full_name,
    singers_table.c.short_name,
    singers_table.c.birth_date,
    singers_table.c.voice_group,
    singers_table.c.height,
    singers_table.c.email,
    singers_table.c.phone,
    singers_table.c.street,
    singers_table.c.postal_code,
    singers_table.c.city,
    singers_table.c.gender,
    singers_table.c.guardian1,
    singers_table.c.guardian1_phone,
    singers_table.c.guardian2,
    singers_table.c.guardian2_phone,
    singers_table.c.social_contacts,
    singers_table.c.joined_year,
    singers_table.c.joined_month,
    singers_table.c.left_year,
    singers_table.c.left_month,
    singers_table.c.affinity_uuid,
]

_SORT_COLUMNS = {
    "full_name": singers_table.c.full_name,
    "voice_group": singers_table.c.voice_group,
    "height": singers_table.c.height,
}


@router.get("", response_model=List[SingerOut])
def list_singers(
    search: Optional[str] = None,
    voice_group: Optional[str] = None,
    sort: SingerSortField = "full_name",
    direction: SingerSortDirection = "asc",
    db: Connection = Depends(get_db),
) -> List[SingerOut]:
    """List singers, optionally filtered and sorted (Desktop-Parität)."""
    order_column = _SORT_COLUMNS[sort]
    order = order_column.desc() if direction == "desc" else order_column.asc()
    stmt = select(*_READ_COLUMNS).order_by(order)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                singers_table.c.full_name.ilike(like),
                singers_table.c.short_name.ilike(like),
                singers_table.c.email.ilike(like),
                singers_table.c.phone.ilike(like),
                singers_table.c.street.ilike(like),
                singers_table.c.city.ilike(like),
            )
        )
    if voice_group:
        stmt = stmt.where(singers_table.c.voice_group == voice_group)
    rows = db.execute(stmt).mappings().all()
    return [SingerOut(**dict(row)) for row in rows]


@router.get("/{singer_id}", response_model=SingerOut)
def get_singer(
    singer_id: str, db: Connection = Depends(get_db)
) -> SingerOut:
    """Return one singer by id (404 when unknown)."""
    stmt = select(*_READ_COLUMNS).where(singers_table.c.id == singer_id)
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Singer not found")
    return SingerOut(**dict(row))


def _read_one(db: Connection, singer_id: str) -> SingerOut:
    stmt = select(*_READ_COLUMNS).where(singers_table.c.id == singer_id)
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Singer not found")
    return SingerOut(**dict(row))


@router.post("", response_model=SingerOut, status_code=201)
def create_singer(
    payload: SingerCreate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> SingerOut:
    """Create a singer (id/timestamps generated server-side)."""
    now = datetime.now().isoformat()
    singer_id = str(uuid.uuid4())
    db.execute(
        insert(singers_table).values(
            id=singer_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(exclude_unset=True),
        )
    )
    db.commit()
    return _read_one(db, singer_id)


@router.put("/{singer_id}", response_model=SingerOut)
def update_singer(
    singer_id: str,
    payload: SingerUpdate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> SingerOut:
    """Partially update a singer (404 when unknown)."""
    _read_one(db, singer_id)
    values = payload.model_dump(exclude_unset=True)
    if values:
        db.execute(
            update(singers_table)
            .where(singers_table.c.id == singer_id)
            .values(updated_at=datetime.now().isoformat(), **values)
        )
        db.commit()
    return _read_one(db, singer_id)


@router.delete("/{singer_id}", status_code=204)
def delete_singer(
    singer_id: str,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete a singer incl. availability rows (deterministic
    cascade on both dialects)."""
    _read_one(db, singer_id)
    db.execute(
        delete(availability_table).where(
            availability_table.c.singer_id == singer_id
        )
    )
    db.execute(
        delete(singers_table).where(singers_table.c.id == singer_id)
    )
    db.commit()
    return Response(status_code=204)
