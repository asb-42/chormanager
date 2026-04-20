"""Tests for backup service."""

import pytest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestBackupService:
    """Tests for BackupService."""

    def test_create_backup(self):
        """Test creating a backup."""
        from chormanager.backup.service import BackupService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.db")
            backup_dir = os.path.join(tmpdir, "backups")
            
            with open(source, "w") as f:
                f.write("test data")
            
            service = BackupService(backup_dir)
            backup_path = service.create_backup(source)
            
            assert os.path.exists(backup_path)
            assert "backup" in backup_path

    def test_create_backup_with_timestamp(self):
        """Test backup has timestamp in filename."""
        from chormanager.backup.service import BackupService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.db")
            backup_dir = os.path.join(tmpdir, "backups")
            
            with open(source, "w") as f:
                f.write("test data")
            
            service = BackupService(backup_dir)
            backup_path = service.create_backup(source)
            
            timestamp = datetime.now().strftime("%Y%m%d")
            assert timestamp in Path(backup_path).name

    def test_list_backups(self):
        """Test listing backups."""
        from chormanager.backup.service import BackupService
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.db")
            backup_dir = os.path.join(tmpdir, "backups")
            
            with open(source, "w") as f:
                f.write("test data")
            
            service = BackupService(backup_dir)
            service.create_backup(source)
            time.sleep(1.1)  # Wait to get different timestamp
            service.create_backup(source)
            
            backups = service.list_backups()
            
            assert len(backups) == 2

    def test_max_backups(self):
        """Test max backups limit."""
        from chormanager.backup.service import BackupService
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.db")
            backup_dir = os.path.join(tmpdir, "backups")
            
            with open(source, "w") as f:
                f.write("test data")
            
            service = BackupService(backup_dir, max_backups=3)
            
            for i in range(5):
                service.create_backup(source)
                time.sleep(1.1)
            
            backups = service.list_backups()
            
            # After creating 5 with max 3, we should have 3
            assert len(backups) == 3

    def test_restore_backup(self):
        """Test restoring from backup."""
        from chormanager.backup.service import BackupService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.db")
            backup_dir = os.path.join(tmpdir, "backups")
            restore = os.path.join(tmpdir, "restored.db")
            
            with open(source, "w") as f:
                f.write("original data")
            
            service = BackupService(backup_dir)
            backup_path = service.create_backup(source)
            
            service.restore_backup(backup_path, restore)
            
            with open(restore, "r") as f:
                assert f.read() == "original data"

    def test_cleanup_old_backups(self):
        """Test cleaning up old backups."""
        from chormanager.backup.service import BackupService
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.db")
            backup_dir = os.path.join(tmpdir, "backups")
            
            with open(source, "w") as f:
                f.write("test data")
            
            service = BackupService(backup_dir, max_backups=2)
            
            for i in range(3):
                service.create_backup(source)
                time.sleep(1.1)
            
            backups = service.list_backups()
            
            assert len(backups) == 2
