"""``/api/selbstdarstellung`` read + upsert endpoint (M1)."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import SelbstdarstellungOut, SelbstdarstellungPut
from ..tables import selbstdarstellung_table

router = APIRouter(tags=["selbstdarstellung"])


@router.get(
    "/api/selbstdarstellung", response_model=SelbstdarstellungOut
)
def get_selbstdarstellung(
    db: Connection = Depends(get_db),
) -> SelbstdarstellungOut:
    """Return the marketing text (blank when the table is empty)."""
    stmt = select(selbstdarstellung_table).limit(1)
    row = db.execute(stmt).mappings().first()
    if row is None:
        return SelbstdarstellungOut(id=None, content="")
    return SelbstdarstellungOut(
        id=row["id"], content=row["content"] or ""
    )


@router.put(
    "/api/selbstdarstellung", response_model=SelbstdarstellungOut
)
def put_selbstdarstellung(
    payload: SelbstdarstellungPut,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> SelbstdarstellungOut:
    """Upsert the (single) marketing text (idempotent)."""
    now = datetime.now().isoformat()
    row = db.execute(
        select(selbstdarstellung_table.c.id).limit(1)
    ).mappings().first()
    if row is None:
        new_id = str(uuid.uuid4())
        db.execute(
            insert(selbstdarstellung_table).values(
                id=new_id, content=payload.content, updated_at=now
            )
        )
        db.commit()
        return SelbstdarstellungOut(id=new_id, content=payload.content)
    db.execute(
        update(selbstdarstellung_table)
        .where(selbstdarstellung_table.c.id == row["id"])
        .values(content=payload.content, updated_at=now)
    )
    db.commit()
    return SelbstdarstellungOut(id=row["id"], content=payload.content)
