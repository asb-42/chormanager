"""Tests for ApplicationBackupService (ZIP-based backup)."""

import pytest
import zipfile
from pathlib import Path
from chormanager.export.backup_service import ApplicationBackupService


class TestApplicationBackupService:
    """Tests for ZIP-based application backup."""

    @pytest.fixture
    def app_root(self, tmp_path):
        """Create a minimal app structure."""
        (tmp_path / "data").mkdir()
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "app.yaml").write_text("app: {name: test}")
        (tmp_path / "data" / "chor.db").write_text("fake db")
        return tmp_path

    @pytest.fixture
    def service(self, app_root):
        return ApplicationBackupService(app_root)

    def test_list_backup_files(self, service):
        """List files that should be in backup."""
        files = service.list_backup_files()
        assert isinstance(files, list)

    def test_create_backup(self, service, tmp_path):
        """Create a ZIP backup."""
        output = tmp_path / "backup.zip"
        result = service.create_backup(str(output))
        assert Path(result).exists()
        assert zipfile.is_zipfile(result)

    def test_create_backup_contains_manifest(self, service, tmp_path):
        """Backup ZIP contains manifest.json."""
        output = tmp_path / "backup.zip"
        service.create_backup(str(output))
        with zipfile.ZipFile(output) as zf:
            assert "manifest.json" in zf.namelist()

    def test_create_backup_manifest_has_version(self, service, tmp_path):
        """Manifest contains version field."""
        import json
        output = tmp_path / "backup.zip"
        service.create_backup(str(output))
        with zipfile.ZipFile(output) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert "version" in manifest
            assert "files" in manifest

    def test_validate_backup_valid(self, service, tmp_path):
        """Validate a valid backup file."""
        output = tmp_path / "backup.zip"
        service.create_backup(str(output))
        valid, msg = service.validate_backup(str(output))
        assert valid is True

    def test_validate_backup_invalid_zip(self, service, tmp_path):
        """Validate an invalid file."""
        bad_file = tmp_path / "bad.zip"
        bad_file.write_text("not a zip")
        valid, msg = service.validate_backup(str(bad_file))
        assert valid is False

    def test_validate_backup_nonexistent(self, service, tmp_path):
        """Validate a nonexistent file."""
        valid, msg = service.validate_backup(str(tmp_path / "missing.zip"))
        assert valid is False

    def test_analyze_restore_new_files(self, service, tmp_path):
        """Analyze restore identifies new files."""
        output = tmp_path / "backup.zip"
        service.create_backup(str(output))
        changes = service.analyze_restore(str(output))
        assert "newer" in changes
        assert "older" in changes
        assert "new" in changes

    def test_get_backup_size(self, service, tmp_path):
        """Get backup file size."""
        output = tmp_path / "backup.zip"
        service.create_backup(str(output))
        size = service.get_backup_size(str(output))
        assert size > 0
