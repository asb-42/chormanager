"""Backup endpoints (M4, SQLite-only).

Reuses ``chormanager.backup.service.FileBackupService`` (Desktop).
Restore disposes pooled engines first so no handle stays open on
the DB file. Non-SQLite URLs (MariaDB: DB-native tools, M5)
are rejected with 400 WITHOUT attempting a connection.
"""
import os
from pathlib import Path
from typing import List

from chormanager.backup.service import FileBackupService
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.engine import make_url

from ..auth import require_chorleiter
from ..deps import dispose_engines, resolve_db_url
from ..schemas import BackupOut

router = APIRouter(prefix="/api/backup", tags=["backup"])


def _service() -> FileBackupService:
    override = os.environ.get("CHORMANAGER_BACKUP_DIR")
    return FileBackupService(
        backup_dir=override if override else None
    )


def _sqlite_file() -> str:
    url = make_url(resolve_db_url())
    if url.drivername.split("+")[0] != "sqlite" or not url.database:
        raise HTTPException(
            status_code=400,
            detail="Backups nur für SQLite-Dateien "
            "(MariaDB: DB-native Tools, siehe M5)",
        )
    return url.database


def _resolve_id(service: FileBackupService, backup_id: str) -> str:
    if not backup_id or "/" in backup_id or "\\" in backup_id:
        raise HTTPException(status_code=404, detail="Backup not found")
    if backup_id.startswith("."):
        raise HTTPException(status_code=404, detail="Backup not found")
    candidate = Path(service.backup_dir) / backup_id
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Backup not found")
    return str(candidate)


@router.get("", response_model=List[BackupOut])
def list_backups() -> List[BackupOut]:
    """List backups, newest first (open read)."""
    _sqlite_file()
    service = _service()
    entries = []
    for path in service.list_backups():
        info = service.get_backup_info(path)
        if info:
            entries.append(
                BackupOut(
                    id=Path(path).name,
                    size=info.get("size", 0),
                    modified_at=info.get("modified_at", ""),
                )
            )
    return entries


@router.post("", response_model=BackupOut, status_code=201)
def create_backup(
    _role: str = Depends(require_chorleiter),
) -> BackupOut:
    """Create a backup of the running database file."""
    service = _service()
    path = service.create_backup(_sqlite_file())
    info = service.get_backup_info(path)
    return BackupOut(
        id=Path(path).name,
        size=info.get("size", 0),
        modified_at=info.get("modified_at", ""),
    )


@router.post("/{backup_id}/restore")
def restore_backup(
    backup_id: str,
    _role: str = Depends(require_chorleiter),
) -> dict:
    """Restore a backup over the running database file."""
    service = _service()
    source = _resolve_id(service, backup_id)
    dispose_engines()
    service.restore_backup(source, _sqlite_file())
    return {"restored": backup_id}


@router.delete("/{backup_id}", status_code=204)
def delete_backup(
    backup_id: str,
    _role: str = Depends(require_chorleiter),
) -> Response:
    """Delete a backup file (404 when unknown)."""
    service = _service()
    source = _resolve_id(service, backup_id)
    if not service.delete_backup(source):
        raise HTTPException(status_code=404, detail="Backup not found")
    return Response(status_code=204)
