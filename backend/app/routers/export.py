"""Export endpoints: CSV, Sync-JSON, Zusagen-PDF (M1).

Shapes kompatibel zu ``export/sync.py`` (Choraufstellung-Import);
Zusagen-PDF via ``core/response_matrix`` + ``core/response_render_pdf``
(reportlab, server-seitig §3.1). Reads sind offen.
"""
import csv
import io
import os
import tempfile
from types import SimpleNamespace
from typing import Dict, List

from chormanager.core.response_matrix import build_response_matrix
from chormanager.core.response_render_pdf import render_response_matrix_pdf
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.engine import Connection
from starlette.background import BackgroundTask

from ..deps import get_db
from ..tables import availability_table, events_table, projects_table
from ..tables import singers_table

router = APIRouter(prefix="/api/export", tags=["export"])

_CSV_HEADER = ["singer_id", "name", "voice_group", "affinity"]


@router.get("/singers.csv")
def singers_csv(db: Connection = Depends(get_db)) -> Response:
    """Singer CSV (Shape wie ``export_singers_csv``)."""
    stmt = (
        select(
            singers_table.c.id,
            singers_table.c.full_name,
            singers_table.c.short_name,
            singers_table.c.voice_group,
            singers_table.c.affinity_uuid,
        )
        .order_by(singers_table.c.full_name)
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CSV_HEADER)
    for row in db.execute(stmt).mappings().all():
        writer.writerow(
            [
                row["id"],
                row["short_name"] or row["full_name"] or "",
                row["voice_group"] or "",
                row["affinity_uuid"] or "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=singers.csv"},
    )


@router.get("/sync.json")
def sync_json(db: Connection = Depends(get_db)) -> Dict:
    """Sync-Dokument (Shapes wie singers/termine/verfuegbarkeit.json)."""
    singers = [
        {
            "singer_id": row["id"],
            "name": row["short_name"] or row["full_name"] or "",
            "voice_group": row["voice_group"] or "",
            "affinity": row["affinity_uuid"] or "",
        }
        for row in db.execute(
            select(
                singers_table.c.id,
                singers_table.c.full_name,
                singers_table.c.short_name,
                singers_table.c.voice_group,
                singers_table.c.affinity_uuid,
            ).order_by(singers_table.c.full_name)
        ).mappings()
    ]
    events = [
        {
            "event_id": row["id"],
            "name": row["name"],
            "date": row["date"],
            "event_type": row["event_type"],
            "description": row["description"] or "",
        }
        for row in db.execute(
            select(
                events_table.c.id,
                events_table.c.name,
                events_table.c.date,
                events_table.c.event_type,
                events_table.c.description,
            ).order_by(events_table.c.date)
        ).mappings()
    ]
    status_by_pair = {
        (row["singer_id"], row["event_id"]): row["status"]
        for row in db.execute(select(availability_table)).mappings()
    }
    matrix = []
    for event in events:
        matrix.append(
            {
                "event_id": event["event_id"],
                "event_name": event["name"],
                "date": event["date"],
                "event_type": event["event_type"],
                "availability": [
                    {
                        "singer_id": singer["singer_id"],
                        "name": singer["name"],
                        "voice_group": singer["voice_group"],
                        "status": status_by_pair.get(
                            (singer["singer_id"], event["event_id"]),
                            "unknown",
                        ),
                    }
                    for singer in singers
                ],
            }
        )
    return {"singers": singers, "events": events, "availability": matrix}


@router.get("/zusagen.pdf")
def zusagen_pdf(
    project_id: str, db: Connection = Depends(get_db)
) -> FileResponse:
    """Zusagen/Absagen-Liste eines Projekts als PDF (reportlab)."""
    project = db.execute(
        select(projects_table.c.id, projects_table.c.name).where(
            projects_table.c.id == project_id
        )
    ).mappings().first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    event_rows = db.execute(
        select(
            events_table.c.id,
            events_table.c.date,
            events_table.c.event_type,
        )
        .where(events_table.c.project_id == project_id)
        .order_by(events_table.c.date)
    ).mappings().all()
    singer_rows = db.execute(
        select(
            singers_table.c.id,
            singers_table.c.full_name,
            singers_table.c.short_name,
            singers_table.c.voice_group,
        ).order_by(singers_table.c.full_name)
    ).mappings().all()
    avail_rows = db.execute(select(availability_table)).mappings().all()
    matrix = build_response_matrix(
        singers=[
            SimpleNamespace(
                id=row["id"],
                short_name=row["short_name"],
                full_name=row["full_name"],
                voice_group=row["voice_group"],
            )
            for row in singer_rows
        ],
        events=[
            SimpleNamespace(
                id=row["id"], date=row["date"], event_type=row["event_type"]
            )
            for row in event_rows
        ],
        availabilities=[
            SimpleNamespace(
                singer_id=row["singer_id"],
                event_id=row["event_id"],
                status=row["status"],
            )
            for row in avail_rows
        ],
        title=project["name"],
    )
    tmp = tempfile.NamedTemporaryFile(
        suffix=".pdf", prefix="zusagen-", delete=False
    )
    tmp.close()
    render_response_matrix_pdf(matrix, tmp.name)
    return FileResponse(
        tmp.name,
        media_type="application/pdf",
        filename=f"zusagen-{project['name'][:30]}.pdf",
        background=BackgroundTask(os.unlink, tmp.name),
    )
