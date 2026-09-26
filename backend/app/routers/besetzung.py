"""``/api/besetzungen`` read + write endpoints (M1)."""
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import BesetzungCreate, BesetzungOut, BesetzungUpdate
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
        updated_at=row.get("updated_at") or "",
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


def _read_one(db: Connection, besetzung_id: str) -> BesetzungOut:
    stmt = select(besetzung_table).where(
        besetzung_table.c.id == besetzung_id
    )
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Besetzung not found")
    return _to_out(dict(row))


@router.post("", response_model=BesetzungOut, status_code=201)
def create_besetzung(
    payload: BesetzungCreate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> BesetzungOut:
    """Create a lineup (``singer_ids`` stored as JSON text)."""
    now = datetime.now().isoformat()
    besetzung_id = str(uuid.uuid4())
    data = payload.model_dump(exclude_unset=True)
    data["singer_ids"] = json.dumps(data.get("singer_ids", []),
                                    ensure_ascii=False)
    db.execute(
        insert(besetzung_table).values(
            id=besetzung_id, created_at=now, updated_at=now, **data
        )
    )
    db.commit()
    return _read_one(db, besetzung_id)


@router.put("/{besetzung_id}", response_model=BesetzungOut)
def update_besetzung(
    besetzung_id: str,
    payload: BesetzungUpdate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> BesetzungOut:
    """Partially update a lineup (404 when unknown)."""
    _read_one(db, besetzung_id)
    values = payload.model_dump(exclude_unset=True)
    if "singer_ids" in values and values["singer_ids"] is not None:
        values["singer_ids"] = json.dumps(values["singer_ids"],
                                          ensure_ascii=False)
    if values:
        db.execute(
            update(besetzung_table)
            .where(besetzung_table.c.id == besetzung_id)
            .values(updated_at=datetime.now().isoformat(), **values)
        )
        db.commit()
    return _read_one(db, besetzung_id)


@router.delete("/{besetzung_id}", status_code=204)
def delete_besetzung(
    besetzung_id: str,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete a lineup (404 when unknown)."""
    _read_one(db, besetzung_id)
    db.execute(
        delete(besetzung_table).where(
            besetzung_table.c.id == besetzung_id
        )
    )
    db.commit()
    return Response(status_code=204)
