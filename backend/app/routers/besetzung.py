"""``/api/besetzungen`` read endpoints (M1 increment 2c)."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.engine import Connection

from ..deps import get_db
from ..schemas import BesetzungOut
from ..tables import besetzung_table

router = APIRouter(prefix="/api/besetzungen", tags=["besetzung"])


def _to_out(row) -> BesetzungOut:
    """Parse ``singer_ids`` JSON, fall back to ``[]`` when corrupt."""
    try:
        parsed = json.loads(row["singer_ids"] or "[]")
        singer_ids = parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        singer_ids = []
    return BesetzungOut(
        id=row["id"],
        name=row["name"],
        project_id=row["project_id"],
        singer_ids=[str(s) for s in singer_ids],
    )


@router.get("", response_model=List[BesetzungOut])
def list_besetzungen(
    project_id: Optional[str] = None,
    db: Connection = Depends(get_db),
) -> List[BesetzungOut]:
    """List lineups, optionally filtered by project."""
    stmt = select(besetzung_table).order_by(besetzung_table.c.name)
    if project_id:
        stmt = stmt.where(besetzung_table.c.project_id == project_id)
    return [_to_out(dict(row)) for row in db.execute(stmt).mappings()]


@router.get("/{besetzung_id}", response_model=BesetzungOut)
def get_besetzung(
    besetzung_id: str, db: Connection = Depends(get_db)
) -> BesetzungOut:
    """Return one lineup by id (404 when unknown)."""
    stmt = select(besetzung_table).where(
        besetzung_table.c.id == besetzung_id
    )
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Besetzung not found")
    return _to_out(dict(row))
