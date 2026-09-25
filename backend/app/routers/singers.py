"""``/api/singers`` read endpoints (M1 increment 1)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.engine import Connection

from ..deps import get_db
from ..schemas import SingerOut
from ..tables import singers_table

router = APIRouter(prefix="/api/singers", tags=["singers"])

_READ_COLUMNS = [
    singers_table.c.id,
    singers_table.c.full_name,
    singers_table.c.short_name,
    singers_table.c.voice_group,
    singers_table.c.height,
    singers_table.c.email,
    singers_table.c.affinity_uuid,
]


@router.get("", response_model=List[SingerOut])
def list_singers(
    search: Optional[str] = None,
    voice_group: Optional[str] = None,
    db: Connection = Depends(get_db),
) -> List[SingerOut]:
    """List singers, optionally filtered by search/voice group."""
    stmt = select(*_READ_COLUMNS).order_by(singers_table.c.full_name)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                singers_table.c.full_name.ilike(like),
                singers_table.c.short_name.ilike(like),
                singers_table.c.email.ilike(like),
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
