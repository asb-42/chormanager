"""``/api/formations`` CRUD + placements + optimizer (M1 Kernstück).

Storage shape mirrors ``FormationStorage`` (``singers`` unplaced +
``placed``). The optimizer runs the Qt-free ``choraufstellung/core``
rules server-side via :mod:`app.optimizer` as preview-only
(Analyse §3.3); applying goes through placements PUT.
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection
from starlette.background import BackgroundTask

from ..auth import require_chorleiter
from ..deps import get_db
from ..formation_pdf import render_formation_pdf, write_temp_pdf
from ..optimizer import run_preview, rule_info
from ..voice import load_theme_colors
from ..schemas import (
    FormationCreate,
    FormationDoc,
    FormationListItem,
    FormationRuleOut,
    OptimizeIn,
    OptimizeOut,
    OptimizePreviewPlacement,
    PlacedEntry,
    PlacementsPut,
    StoredSinger,
)
from ..tables import (
    availability_table,
    events_table,
    formations_table,
    projects_table,
    singers_table,
)

router = APIRouter(prefix="/api/formations", tags=["formations"])


def _loads(text: Optional[str], default):
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


def _dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _to_doc(row) -> FormationDoc:
    data = dict(row)
    return FormationDoc(
        id=data["id"],
        name=data.get("name"),
        rows=data["rows"],
        cols=data["cols"],
        staggered=bool(data.get("staggered") or 0),
        voicing_config=_loads(data.get("voicing_config"), []),
        singers=[StoredSinger(**s) for s in _loads(data.get("singers"), [])],
        placed=[PlacedEntry(**p) for p in _loads(data.get("placed"), [])],
        metadata=_loads(data.get("metadata"), {}),
        event_id=data.get("event_id"),
    )


def _read_row(db: Connection, formation_id: str):
    stmt = select(formations_table).where(
        formations_table.c.id == formation_id
    )
    row = db.execute(stmt).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Formation not found")
    return row


@router.get("", response_model=List[FormationListItem])
def list_formations(
    db: Connection = Depends(get_db),
) -> List[FormationListItem]:
    """List formations (compact, newest first)."""
    stmt = select(formations_table).order_by(
        formations_table.c.updated_at.desc()
    )
    items = []
    for row in db.execute(stmt).mappings().all():
        singers_text = row["singers"] or "[]"
        placed_text = row["placed"] or "[]"
        items.append(
            FormationListItem(
                id=row["id"],
                name=row["name"],
                rows=row["rows"],
                cols=row["cols"],
                event_id=row["event_id"],
                updated_at=row["updated_at"],
                metadata=_loads(row["metadata"], {}),
                size=len(singers_text) + len(placed_text),
            )
        )
    return items


@router.post("", response_model=FormationDoc, status_code=201)
def create_formation(
    payload: FormationCreate,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> FormationDoc:
    """Create a formation; with ``event_id`` the available singers
    (yes/conditional) are seeded unplaced (404 when unknown)."""
    metadata: Dict = {}
    singers: List[Dict] = []
    if payload.event_id:
        event = db.execute(
            select(
                events_table.c.id,
                events_table.c.name,
                events_table.c.date,
                events_table.c.event_type,
                events_table.c.project_id,
            ).where(events_table.c.id == payload.event_id)
        ).mappings().first()
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        project_name = ""
        if event["project_id"]:
            project = db.execute(
                select(projects_table.c.name).where(
                    projects_table.c.id == event["project_id"]
                )
            ).first()
            if project is not None:
                project_name = project[0] or ""
        metadata = {
            "project": project_name,
            "event": event["name"],
            "event_date": (event["date"] or "")[:10],
            "event_type": event["event_type"],
        }
        stmt = (
            select(
                singers_table.c.id,
                singers_table.c.full_name,
                singers_table.c.short_name,
                singers_table.c.voice_group,
                singers_table.c.height,
                singers_table.c.affinity_uuid,
            )
            .select_from(
                singers_table.join(
                    availability_table,
                    availability_table.c.singer_id == singers_table.c.id,
                )
            )
            .where(
                (availability_table.c.event_id == payload.event_id)
                & (availability_table.c.status.in_(["yes", "conditional"]))
            )
            .order_by(singers_table.c.full_name)
        )
        for row in db.execute(stmt).mappings().all():
            singers.append(
                {
                    "singer_id": row["id"],
                    "name": row["short_name"] or row["full_name"],
                    "voice_group": row["voice_group"],
                    "height": row["height"] or 0,
                    "affinity": row["affinity_uuid"] or "",
                }
            )
    name = payload.name
    if not name:
        if metadata:
            name = f"{metadata['event']} {metadata['event_date']}".strip()
        else:
            name = "Neue Aufstellung"
    now = datetime.now().isoformat()
    formation_id = str(uuid.uuid4())
    db.execute(
        insert(formations_table).values(
            id=formation_id,
            name=name,
            rows=payload.rows,
            cols=payload.cols,
            staggered=int(payload.staggered),
            voicing_config=_dumps([]),
            singers=_dumps(singers),
            placed=_dumps([]),
            metadata=_dumps(metadata),
            event_id=payload.event_id,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return _to_doc(_read_row(db, formation_id))


@router.get("/rules", response_model=List[FormationRuleOut])
def list_rules() -> List[FormationRuleOut]:
    """Optimizer rule catalog for the dialog (open, no auth)."""
    return [FormationRuleOut(**entry) for entry in rule_info()]


@router.get("/{formation_id}", response_model=FormationDoc)
def get_formation(
    formation_id: str, db: Connection = Depends(get_db)
) -> FormationDoc:
    """Return the full formation document (404 when unknown)."""
    return _to_doc(_read_row(db, formation_id))


@router.put("/{formation_id}/placements", response_model=FormationDoc)
def put_placements(
    formation_id: str,
    payload: PlacementsPut,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> FormationDoc:
    """Replace placements (optionally resize); validates bounds,
    known singers and unique cells (422 otherwise). Omitted singers
    become unplaced. Atomic: one commit at the end."""
    doc = _to_doc(_read_row(db, formation_id))
    rows = payload.rows if payload.rows is not None else doc.rows
    cols = payload.cols if payload.cols is not None else doc.cols
    staggered = (
        payload.staggered if payload.staggered is not None
        else doc.staggered
    )
    known = {s.singer_id: s for s in doc.singers}
    for placed in doc.placed:
        known.setdefault(placed.singer.singer_id, placed.singer)
    seen = set()
    placed_entries = []
    for placement in payload.placements:
        singer = known.get(placement.singer_id)
        if singer is None:
            raise HTTPException(
                status_code=422,
                detail=f"unknown singer: {placement.singer_id}",
            )
        if not (0 <= placement.row < rows and 0 <= placement.col < cols):
            raise HTTPException(
                status_code=422,
                detail=f"out of bounds: {placement.singer_id}",
            )
        if (placement.row, placement.col) in seen:
            raise HTTPException(
                status_code=422,
                detail=f"duplicate cell: {(placement.row, placement.col)}",
            )
        seen.add((placement.row, placement.col))
        placed_entries.append(
            {
                "singer": singer.model_dump(),
                "row": placement.row,
                "col": placement.col,
            }
        )
    placed_ids = {p["singer"]["singer_id"] for p in placed_entries}
    singers = [
        singer.model_dump()
        for sid, singer in known.items()
        if sid not in placed_ids
    ]
    db.execute(
        update(formations_table)
        .where(formations_table.c.id == formation_id)
        .values(
            rows=rows,
            cols=cols,
            staggered=int(staggered),
            singers=_dumps(singers),
            placed=_dumps(placed_entries),
            updated_at=datetime.now().isoformat(),
        )
    )
    db.commit()
    return _to_doc(_read_row(db, formation_id))


@router.post("/{formation_id}/optimize", response_model=OptimizeOut)
def optimize_formation(
    formation_id: str,
    payload: OptimizeIn,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> OptimizeOut:
    """Optimizer preview (Analyse §3.3): runs the rules, returns
    positions + stats WITHOUT persisting (apply via placements PUT).
    Unknown rule ids yield 422."""
    doc = _to_doc(_read_row(db, formation_id))
    stored = [s.model_dump() for s in doc.singers]
    positions = {s["singer_id"]: (-1, -1) for s in stored}
    for placed in doc.placed:
        stored.append(placed.singer.model_dump())
        positions[placed.singer.singer_id] = (placed.row, placed.col)
    try:
        placements, swaps, cost, messages = run_preview(
            stored, positions, doc.rows, doc.cols, doc.staggered,
            payload.rule_ids,
        )
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return OptimizeOut(
        placements=[OptimizePreviewPlacement(**p) for p in placements],
        swap_count=swaps,
        cost=cost,
        applied_rules=list(payload.rule_ids),
        messages=messages,
    )


@router.delete("/{formation_id}", status_code=204)
def delete_formation(
    formation_id: str,
    db: Connection = Depends(get_db),
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete a formation (404 when unknown)."""
    _read_row(db, formation_id)
    db.execute(
        delete(formations_table).where(
            formations_table.c.id == formation_id
        )
    )
    db.commit()
    return Response(status_code=204)


@router.get("/{formation_id}/pdf")
def formation_pdf(
    formation_id: str, db: Connection = Depends(get_db)
) -> FileResponse:
    """Formation grid PDF (§5.3: zentrierte Kurznamen, Farben +
    Gruppen-Text, Kopf, Fit-Skalierung)."""
    doc = _to_doc(_read_row(db, formation_id)).model_dump()
    theme = load_theme_colors()
    colors = {
        group_id: shades.get("light", "#cccccc")
        for group_id, shades in theme.items()
    }
    path = write_temp_pdf(render_formation_pdf(doc, colors), "formation-")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"aufstellung-{formation_id[:8]}.pdf",
        background=BackgroundTask(os.unlink, path),
    )
