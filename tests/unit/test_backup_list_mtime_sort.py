"""TDD RED: m10-FIX-A — ``BackupService.list_backups`` must sort by mtime.

The old implementation sorted by filename string (reverse=True). That
meant a backup from yesterday called ``z_backup_20260613_120000.db``
would sort *after* today's ``a_backup_20260614_090000.db`` even though
it's older. m10-FIX-A sorts by file ``mtime`` (newest first) so the
return order is meaningful.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


def _touch(path: Path, content: str = "x") -> None:
    path.write_text(content, encoding="utf-8")


def test_list_backups_sorts_by_mtime_newest_first(tmp_path: Path):
    from chormanager.backup.service import BackupService

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # Create files in deliberately out-of-order names; we set mtimes
    # manually so the test is deterministic.
    a = backup_dir / "a_backup_20260614_090000.db"
    b = backup_dir / "b_backup_20260613_120000.db"
    c = backup_dir / "c_backup_20260614_080000.db"
    for f, mtime in [(a, 1_750_000_000), (b, 1_749_000_000), (c, 1_750_000_500)]:
        _touch(f)
        os.utime(f, (mtime, mtime))

    svc = BackupService(backup_dir=str(backup_dir))
    result = svc.list_backups()
    # The newest mtime is c (1_750_000_500), then a, then b.
    assert result == [str(c), str(a), str(b)], (
        f"list_backups() must return newest-mtime first; got {result}"
    )


def test_list_backups_skips_files_not_matching_pattern(tmp_path: Path):
    from chormanager.backup.service import BackupService

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    keep = backup_dir / "x_backup_20260614_100000.db"
    noise = backup_dir / "noise.txt"
    _touch(keep)
    _touch(noise)
    os.utime(keep, (1_750_001_000, 1_750_001_000))
    os.utime(noise, (1_750_002_000, 1_750_002_000))  # newer mtime

    svc = BackupService(backup_dir=str(backup_dir))
    result = svc.list_backups()
    assert result == [str(keep)]


def test_list_backups_empty_dir(tmp_path: Path):
    from chormanager.backup.service import BackupService

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    svc = BackupService(backup_dir=str(backup_dir))
    assert svc.list_backups() == []
