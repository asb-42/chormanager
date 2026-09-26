"""``/api/repertoire`` read + write endpoints (M1)."""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import (
    RepertoireCreate,
    RepertoireOut,
    RepertoireSortDirection,
    RepertoireSortField,
    RepertoireUpdate,
)
from ..tables import repertoire_table

router = APIRouter(prefix="/api/repertoire", tags=["repertoire"])

_SORT_COLUMNS = {
    "title": repertoire_table.c.title,
    "composer": repertoire_table.c.composer,
    "country": repertoire_table.c.country,
    "location": repertoire_table.c.location,
}


@router.get("", response_model=List[RepertoireOut])
def list_repertoire(
    project_id: Optional[str] = None,
    search: Optional[str] = None,
    sort: RepertoireSortField = "title",
    direction: RepertoireSortDirection = "asc",
    db: Connection = Depends(get_db),
) -> List[RepertoireOut]:
    """List repertoire entries (Desktop-Suche + -Sortierung)."""
    order_column = _SORT_COLUMNS[sort]
    order = order_column.desc() if direction == "desc" else order_column.asc()
    stmt = select(repertoire_table).order_by(order)
    if project_id:
        stmt = stmt.where(repertoire_table.c.project_id == project_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                repertoire_table.c.composer.ilike(like),
                repertoire_table.c.title.ilike(like),
                repertoire_table.c.dates.ilike(like),
                repertoire_table.c.country.ilike(like),
                repertoire_table.c.publisher.ilike(like),
                repertoire_table.c.arrangement.ilike(like),
            )
        )
    rows = db.execute(stmt).mappings().all()
    return [RepertoireOut(**dict(row)) for row in rows]


@router.get("/{repertoire_id}", response_model=RepertoireOut)
def get_repertoire(
    repertoire_id: str, db: Connection = Depends(get_db)
) -> RepertoireOut:
    """Return one repertoire entry by id (404 when unknown)."""
    stmt = select(repertoire_table).where(
        repertoire_table.c.id == repertoire_id
    )
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Repertoire not found")
    return RepertoireOut(**dict(row))


def _read_one(db: Connection, repertoire_id: str) -> RepertoireOut:
    stmt = select(repertoire_table).where(
        repertoire_table.c.id == repertoire_id
    )
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Repertoire not found")
    return RepertoireOut(**dict(row))


@router.post("", response_model=RepertoireOut, status_code=201)
def create_repertoire(
    payload: RepertoireCreate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> RepertoireOut:
    """Create a repertoire entry (id/timestamps server-side)."""
    now = datetime.now().isoformat()
    repertoire_id = str(uuid.uuid4())
    db.execute(
        insert(repertoire_table).values(
            id=repertoire_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(exclude_unset=True),
        )
    )
    db.commit()
    return _read_one(db, repertoire_id)


@router.put("/{repertoire_id}", response_model=RepertoireOut)
def update_repertoire(
    repertoire_id: str,
    payload: RepertoireUpdate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> RepertoireOut:
    """Partially update a repertoire entry (404 when unknown)."""
    _read_one(db, repertoire_id)
    values = payload.model_dump(exclude_unset=True)
    if values:
        db.execute(
            update(repertoire_table)
            .where(repertoire_table.c.id == repertoire_id)
            .values(updated_at=datetime.now().isoformat(), **values)
        )
        db.commit()
    return _read_one(db, repertoire_id)


@router.delete("/{repertoire_id}", status_code=204)
def delete_repertoire(
    repertoire_id: str,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete a repertoire entry (404 when unknown)."""
    _read_one(db, repertoire_id)
    db.execute(
        delete(repertoire_table).where(
            repertoire_table.c.id == repertoire_id
        )
    )
    db.commit()
    return Response(status_code=204)
