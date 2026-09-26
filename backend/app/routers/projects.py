"""``/api/projects`` read + write endpoints with summary (M1)."""
import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import case, delete, func, insert, select, update
from sqlalchemy.engine import Connection

from ..auth import require_chorleiter
from ..deps import get_db
from ..schemas import (
    EventSummaryItem,
    ProjectCreate,
    ProjectOut,
    ProjectSummary,
    ProjectUpdate,
)
from ..tables import availability_table, events_table, projects_table
from ..tables import besetzung_table, repertoire_table, singers_table

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


def _read_one(db: Connection, project_id: str) -> ProjectOut:
    stmt = select(projects_table).where(projects_table.c.id == project_id)
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut(**dict(row))


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> ProjectOut:
    """Create a project (id/timestamps generated server-side)."""
    now = datetime.now().isoformat()
    project_id = str(uuid.uuid4())
    db.execute(
        insert(projects_table).values(
            id=project_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(exclude_unset=True),
        )
    )
    db.commit()
    return _read_one(db, project_id)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> ProjectOut:
    """Partially update a project (404 when unknown)."""
    _read_one(db, project_id)
    values = payload.model_dump(exclude_unset=True)
    if values:
        db.execute(
            update(projects_table)
            .where(projects_table.c.id == project_id)
            .values(updated_at=datetime.now().isoformat(), **values)
        )
        db.commit()
    return _read_one(db, project_id)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete a project; children keep existing with ``project_id``
    set to NULL (explicit SET NULL, dialektneutral)."""
    _read_one(db, project_id)
    for table in (events_table, besetzung_table, repertoire_table):
        db.execute(
            update(table)
            .where(table.c.project_id == project_id)
            .values(project_id=None)
        )
    db.execute(
        delete(projects_table).where(projects_table.c.id == project_id)
    )
    db.commit()
    return Response(status_code=204)


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
