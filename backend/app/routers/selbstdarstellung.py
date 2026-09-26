"""``/api/selbstdarstellung`` read endpoint (M1 increment 2c)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.engine import Connection

from ..deps import get_db
from ..schemas import SelbstdarstellungOut
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
