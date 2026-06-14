"""Backup service for ChorManager."""

import logging
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fnmatch import fnmatch

from ..config import load_app_config, get_data_dir

_logger = logging.getLogger(__name__)

# m9-FIX-A: file extensions we treat as SQLite databases and back up via
# the consistent ``Connection.backup`` API rather than a plain file copy.
_SQLITE_SUFFIXES = (".db", ".sqlite", ".sqlite3")


class BackupService:
    """Service for managing backups."""
    
    def __init__(self, backup_dir: Optional[str] = None, max_backups: int = 10):
        """Initialize backup service.
        
        Args:
            backup_dir: Directory for backups. If None, uses config default.
            max_backups: Maximum number of backups to keep.
        """
        if backup_dir is None:
            config = load_app_config()
            data_dir = get_data_dir()
            backup_dir = str(data_dir / "backups")
        
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._max_backups = max_backups
    
    def create_backup(self, source_path: str) -> str:
        """Create a backup of ``source_path``.

        For SQLite files (``.db`` / ``.sqlite`` / ``.sqlite3``) the backup
        is produced via :meth:`sqlite3.Connection.backup`, which yields a
        transactionally consistent snapshot even while the source DB is
        still being written (m9-FIX-A). For all other files we fall back
        to a plain :func:`shutil.copy2`.

        Args:
            source_path: Path to file to backup.

        Returns:
            str: Path to backup file.
        """
        source = Path(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_name = f"{source.stem}_backup_{timestamp}{source.suffix}"
        backup_path = self.backup_dir / backup_name

        if source.suffix.lower() in _SQLITE_SUFFIXES:
            try:
                self._sqlite_backup(source, backup_path)
            except (OSError, sqlite3.Error) as exc:
                _logger.warning(
                    "sqlite3.backup failed for %s (%s); falling back to shutil.copy2",
                    source, exc,
                )
                shutil.copy2(source, backup_path)
        else:
            shutil.copy2(source, backup_path)

        self._cleanup_old_backups()

        return str(backup_path)

    @staticmethod
    def _sqlite_backup(source: Path, dest: Path) -> None:
        """Stream a consistent snapshot of ``source`` SQLite db to ``dest``.

        Uses :meth:`sqlite3.Connection.backup` so the snapshot is
        consistent even while other connections are writing to ``source``.
        """
        src_conn = sqlite3.connect(str(source))
        try:
            dest_conn = sqlite3.connect(str(dest))
            try:
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            src_conn.close()
    
    def list_backups(self, pattern: str = "*_backup_*") -> List[str]:
        """List available backups, newest first.

        Args:
            pattern: Glob pattern for backup files.

        Returns:
            List of backup file paths, ordered by ``mtime`` (newest first).
        """
        backups: list = []
        for file in self.backup_dir.iterdir():
            if fnmatch(file.name, pattern):
                backups.append((str(file), file.stat().st_mtime))

        # m10-FIX-A: sort by mtime, not by filename string.
        return [p for p, _ in sorted(backups, key=lambda t: t[1], reverse=True)]
    
    def restore_backup(self, backup_path: str, destination: str) -> None:
        """Restore a backup.
        
        Args:
            backup_path: Path to backup file.
            destination: Destination path for restored file.
        """
        shutil.copy2(backup_path, destination)
    
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup file.
        
        Args:
            backup_path: Path to backup file.
            
        Returns:
            True if deleted, False if not found.
        """
        path = Path(backup_path)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backups exceeding max limit."""
        backups = self.list_backups()
        
        while len(backups) > self._max_backups:
            oldest = backups.pop()
            self.delete_backup(oldest)
    
    def get_backup_info(self, backup_path: str) -> dict:
        """Get information about a backup.
        
        Args:
            backup_path: Path to backup file.
            
        Returns:
            dict: Backup information (path, size, created_at).
        """
        path = Path(backup_path)
        
        if not path.exists():
            return {}
        
        stat = path.stat()
        
        return {
            "path": str(path),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }


class AutoBackupService:
    """Service for automatic backups."""
    
    def __init__(self, backup_service: Optional[BackupService] = None):
        """Initialize auto backup service.
        
        Args:
            backup_service: BackupService instance.
        """
        if backup_service is None:
            backup_service = BackupService()
        
        self._backup_service = backup_service
        self._config = load_app_config()
    
    def backup_on_start(self, db_path: str) -> Optional[str]:
        """Create backup on application start.
        
        Args:
            db_path: Path to database file.
            
        Returns:
            Path to backup or None if disabled.
        """
        if not self._config["backup"].get("on_start", False):
            return None
        
        if not Path(db_path).exists():
            return None
        
        return self._backup_service.create_backup(db_path)
    
    def backup_before_save(self, db_path: str) -> Optional[str]:
        """Create backup before saving.
        
        Args:
            db_path: Path to database file.
            
        Returns:
            Path to backup or None if disabled.
        """
        if not self._config["backup"].get("before_save", False):
            return None
        
        if not Path(db_path).exists():
            return None
        
        return self._backup_service.create_backup(db_path)
