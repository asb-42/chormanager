"""``/api/projects`` read endpoints + summary (M1 increment 2a)."""
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.engine import Connection

from ..deps import get_db
from ..schemas import EventSummaryItem, ProjectOut, ProjectSummary
from ..tables import availability_table, events_table, projects_table
from ..tables import singers_table

router = APIRouter(prefix="/api/projects", tags=["projects"])

_UNKNOWN_VOICE_GROUP = "Ohne Stimmgruppe"


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Connection = Depends(get_db)) -> List[ProjectOut]:
    """List projects ordered by name."""
    stmt = select(projects_table).order_by(projects_table.c.name)
    rows = db.execute(stmt).mappings().all()
    return [ProjectOut(**dict(row)) for row in rows]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str, db: Connection = Depends(get_db)
) -> ProjectOut:
    """Return one project by id (404 when unknown)."""
    stmt = select(projects_table).where(projects_table.c.id == project_id)
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut(**dict(row))


@router.get("/{project_id}/summary", response_model=ProjectSummary)
def project_summary(
    project_id: str, db: Connection = Depends(get_db)
) -> ProjectSummary:
    """Zusagen-Auswertung je Termin und Stimmgruppe (Desktop-Parität)."""
    exists = db.execute(
        select(projects_table.c.id).where(
            projects_table.c.id == project_id
        )
    ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="Project not found")

    yes = func.sum(
        case((availability_table.c.status == "yes", 1), else_=0)
    )
    cond = func.sum(
        case((availability_table.c.status == "conditional", 1), else_=0)
    )
    stmt = (
        select(
            events_table.c.id,
            events_table.c.name,
            events_table.c.date,
            func.coalesce(yes, 0).label("yes"),
            func.coalesce(cond, 0).label("conditional"),
        )
        .select_from(
            events_table.outerjoin(
                availability_table,
                availability_table.c.event_id == events_table.c.id,
            )
        )
        .where(events_table.c.project_id == project_id)
        .group_by(events_table.c.id)
        .order_by(events_table.c.date)
    )
    events = [
        EventSummaryItem(
            event_id=row["id"],
            name=row["name"],
            date=row["date"],
            yes=row["yes"],
            conditional=row["conditional"],
        )
        for row in db.execute(stmt).mappings().all()
    ]

    grouped = (
        select(
            singers_table.c.voice_group,
            availability_table.c.status,
            func.count().label("n"),
        )
        .select_from(
            availability_table.join(
                singers_table,
                singers_table.c.id == availability_table.c.singer_id,
            ).join(
                events_table,
                events_table.c.id == availability_table.c.event_id,
            )
        )
        .where(events_table.c.project_id == project_id)
        .group_by(singers_table.c.voice_group, availability_table.c.status)
    )
    by_voice_group: Dict[str, Dict[str, int]] = {}
    for row in db.execute(grouped).mappings().all():
        vg = row["voice_group"] or _UNKNOWN_VOICE_GROUP
        bucket = by_voice_group.setdefault(
            vg, {"yes": 0, "conditional": 0}
        )
        if row["status"] in bucket:
            bucket[row["status"]] = row["n"]
        else:
            bucket[row["status"]] = row["n"]
    return ProjectSummary(
        project_id=project_id, events=events, by_voice_group=by_voice_group
    )
