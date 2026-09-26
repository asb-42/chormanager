"""``/api/repertoire`` read endpoints (M1 increment 2c)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.engine import Connection

from ..deps import get_db
from ..schemas import RepertoireOut
from ..tables import repertoire_table

router = APIRouter(prefix="/api/repertoire", tags=["repertoire"])


@router.get("", response_model=List[RepertoireOut])
def list_repertoire(
    project_id: Optional[str] = None,
    db: Connection = Depends(get_db),
) -> List[RepertoireOut]:
    """List repertoire entries, optionally filtered by project."""
    stmt = select(repertoire_table).order_by(repertoire_table.c.title)
    if project_id:
        stmt = stmt.where(repertoire_table.c.project_id == project_id)
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
