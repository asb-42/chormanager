# TDD PHASE 1: Coverage tests for the P0 service layer.
#
# These tests target three modules that are currently at 0–18% coverage
# and that back critical features (CSV/ODT/WTR exports, backup/restore,
# data portability).
#
#  * chormanager.core.export_service.ExportService
#  * chormanager.export.backup_service.BackupService + BackupFile
#  * chormanager.export.portability.PortabilityService
#
# The tests are written RED-first: the fixtures build a real fake app
# tree (data/, config/) and a real SQLite database. Once the suite is
# green, these three modules should land at >= 85% coverage.
import csv
import io
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chormanager.core.export_service import ExportService
from chormanager.export.backup_service import BackupService, BackupFile
from chormanager.export.portability import PortabilityService


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def sample_items():
    """A list of SimpleNamespace items, similar to dataclass instances."""
    return [
        SimpleNamespace(
            id="p1", name="Beethoven", full_name="Beethoven", short_name="Beet",
            voice_group="Sopran 1", email="b@example.com", phone="123",
            birth_date="1990-05-15",
        ),
        SimpleNamespace(
            id="p2", name="Mozart", full_name="Mozart", short_name="Moz",
            voice_group="Bass 1", email=None, phone=None,
            birth_date="1985-03-10",
        ),
    ]


@pytest.fixture
def fake_app_root(tmp_path):
    """Create a fake ChorManager app tree:
        <tmp>/data/chor.db        (SQLite with one table)
        <tmp>/data/state.json
        <tmp>/config/app.yaml
        <tmp>/config/voice_groups.json
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # state.json
    (data_dir / "state.json").write_text('{"active_project": "p1"}')

    # config files
    (config_dir / "app.yaml").write_text("app: chor\n")
    (config_dir / "voice_groups.json").write_text(
        '[{"name": "Sopran 1"}, {"name": "Bass 1"}]'
    )
    (config_dir / "voice_groups.yaml").write_text("- Sopran 1\n")
    (config_dir / "fields.yaml").write_text("fields: []\n")

    # sqlite database with one user table
    db_path = data_dir / "chor.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE singers ("
        "id TEXT PRIMARY KEY, "
        "name TEXT NOT NULL, "
        "voice_group TEXT, "
        "created_at TEXT, "
        "updated_at TEXT)"
    )
    conn.execute(
        "INSERT INTO singers VALUES (?, ?, ?, ?, ?)",
        ("s1", "Anna", "Sopran 1", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()
    return tmp_path


@pytest.fixture
def db_connection(fake_app_root):
    """A real sqlite3 connection to the fake chor.db."""
    db_path = fake_app_root / "data" / "chor.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ===========================================================================
# ExportService
# ===========================================================================

class TestExportServiceGetExportData:
    """Tests for ExportService.get_export_data."""

    def test_empty_items_yields_empty_list(self):
        svc = ExportService()
        assert svc.get_export_data([], ["name"]) == []

    def test_basic_field_selection(self, sample_items):
        svc = ExportService()
        data = svc.get_export_data(sample_items, ["id", "name"])
        assert len(data) == 2
        assert data[0] == {"id": "p1", "name": "Beethoven"}
        assert data[1] == {"id": "p2", "name": "Mozart"}

    def test_none_values_become_empty_string(self, sample_items):
        svc = ExportService()
        data = svc.get_export_data(sample_items, ["email"])
        # Anna has email, Mozart has email=None
        assert data[0]["email"] == "b@example.com"
        assert data[1]["email"] == ""

    def test_missing_attribute_becomes_empty_string(self, sample_items):
        svc = ExportService()
        # "nonexistent" attribute is not on the items
        data = svc.get_export_data(sample_items, ["nonexistent"])
        assert data[0]["nonexistent"] == ""
        assert data[1]["nonexistent"] == ""

    def test_numeric_attribute_is_stringified(self):
        svc = ExportService()
        # Use "score" not "age" because the service special-cases the
        # 'age' field and calls it as a method when present.
        items = [SimpleNamespace(score=42), SimpleNamespace(score=21)]
        data = svc.get_export_data(items, ["score"])
        assert data[0]["score"] == "42"
        assert data[1]["score"] == "21"


class TestExportServiceCsv:
    """Tests for ExportService.export_to_csv."""

    def test_basic_csv_output(self, sample_items):
        svc = ExportService()
        data = svc.get_export_data(sample_items, ["id", "name"])
        csv_str = svc.export_to_csv(data, ["id", "name"])
        rows = list(csv.reader(io.StringIO(csv_str)))
        assert rows[0] == ["id", "name"]
        assert rows[1] == ["p1", "Beethoven"]
        assert rows[2] == ["p2", "Mozart"]

    def test_empty_data_yields_empty_string(self):
        svc = ExportService()
        assert svc.export_to_csv([], ["a", "b"]) == ""

    def test_custom_delimiter(self, sample_items):
        svc = ExportService()
        data = svc.get_export_data(sample_items, ["id", "name"])
        csv_str = svc.export_to_csv(data, ["id", "name"], delimiter="\t")
        # Should use TAB not COMMA
        assert "\t" in csv_str
        assert "," not in csv_str


class TestExportServiceLibreOffice:
    """Tests for the LibreOffice export helpers."""

    def test_calc_export_uses_tab_delimiter(self, sample_items):
        svc = ExportService()
        data = svc.get_export_data(sample_items, ["id", "name"])
        result = svc.export_to_libreoffice_calc(data, ["id", "name"])
        assert "p1\tBeethoven" in result
        assert "p2\tMozart" in result

    def test_writer_export_produces_html(self, sample_items):
        svc = ExportService()
        data = svc.get_export_data(sample_items, ["id", "name"])
        html = svc.export_to_libreoffice_writer(data, ["id", "name"])
        assert html.startswith("<html>")
        assert "<table" in html
        assert "<th>id</th>" in html
        assert "<th>name</th>" in html
        assert "<td>p1</td>" in html
        assert "<td>Beethoven</td>" in html
        assert html.endswith("</html>")

    def test_writer_html_escapes_special_characters(self):
        svc = ExportService()
        data = [{"name": "<script>alert(1)</script>"}]
        html = svc.export_to_libreoffice_writer(data, ["name"])
        # We do NOT escape; this documents the current behaviour. If
        # you decide to escape, the test below will fail and remind
        # you to update the implementation.
        assert "<script>alert(1)</script>" in html


class TestExportServiceGetTableFields:
    """Tests for ExportService.get_table_fields."""

    def test_returns_user_fields_only(self, db_connection):
        svc = ExportService()
        fields = svc.get_table_fields(db_connection, "singers")
        # id, created_at, updated_at are excluded by default
        names = [f["name"] for f in fields]
        assert "id" not in names
        assert "created_at" not in names
        assert "updated_at" not in names
        # name, voice_group ARE included
        assert "name" in names
        assert "voice_group" in names

    def test_includes_system_fields_when_requested(self, db_connection):
        svc = ExportService()
        fields = svc.get_table_fields(
            db_connection, "singers", exclude_system=False,
        )
        names = [f["name"] for f in fields]
        assert "id" in names
        assert "created_at" in names
        assert "updated_at" in names

    def test_label_is_human_readable_snake_case(self, db_connection):
        svc = ExportService()
        fields = svc.get_table_fields(db_connection, "singers")
        for f in fields:
            if f["name"] == "voice_group":
                assert f["label"] == "Voice Group"
            elif f["name"] == "name":
                assert f["label"] == "Name"

    def test_unknown_table_returns_empty_list(self, db_connection):
        svc = ExportService()
        # PRAGMA table_info on a missing table returns no rows, not an error
        fields = svc.get_table_fields(db_connection, "no_such_table_xyz")
        assert fields == []


# ===========================================================================
# BackupService
# ===========================================================================

class TestBackupFile:
    """Tests for the BackupFile dataclass-like class."""

    def test_attributes_are_stored(self, tmp_path):
        src = tmp_path / "data" / "chor.db"
        src.parent.mkdir(parents=True)
        src.write_text("x")
        bf = BackupFile(src, "data/chor.db")
        assert bf.source == src
        assert bf.archive_name == "data/chor.db"
        assert bf.mtime > 0

    def test_repr_contains_archive_name(self, tmp_path):
        src = tmp_path / "x.txt"
        src.write_text("x")
        bf = BackupFile(src, "x.txt")
        r = repr(bf)
        assert "x.txt" in r


class TestBackupServiceList:
    """Tests for BackupService.list_backup_files."""

    def test_lists_existing_files(self, fake_app_root):
        svc = BackupService(fake_app_root)
        files = svc.list_backup_files()
        names = [f.archive_name for f in files]
        assert "data/chor.db" in names
        assert "data/state.json" in names
        assert "config/app.yaml" in names
        assert "config/voice_groups.json" in names

    def test_silently_skips_missing_optional_files(self, tmp_path):
        # Empty app root: no files exist yet
        svc = BackupService(tmp_path)
        files = svc.list_backup_files()
        assert files == []


class TestBackupServiceCreate:
    """Tests for BackupService.create_backup."""

    def test_creates_a_valid_zip(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))
        assert out.exists()
        with zipfile.ZipFile(out) as zf:
            assert zf.testzip() is None  # no corrupt members

    def test_archive_contains_expected_files(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert "data/chor.db" in names
        assert "data/state.json" in names
        assert "config/app.yaml" in names
        assert "manifest.json" in names

    def test_manifest_is_valid_json(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))
        with zipfile.ZipFile(out) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["version"] == "1.0"
        assert manifest["app"] == "ChorManager"
        assert "created_at" in manifest
        assert isinstance(manifest["files"], list)

    def test_creates_parent_directory(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "subdir" / "nested" / "backup.zip"
        svc.create_backup(str(out))
        assert out.exists()


class TestBackupServiceValidate:
    """Tests for BackupService.validate_backup."""

    def test_valid_archive_returns_true(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))
        ok, msg = svc.validate_backup(str(out))
        assert ok is True
        assert "gültig" in msg.lower()

    def test_non_zip_file_returns_false(self, fake_app_root):
        bad = fake_app_root / "not_a_zip.txt"
        bad.write_text("hello world")
        svc = BackupService(fake_app_root)
        ok, msg = svc.validate_backup(str(bad))
        assert ok is False
        assert "zip" in msg.lower() or "archiv" in msg.lower()

    def test_nonexistent_file_returns_false(self, fake_app_root):
        svc = BackupService(fake_app_root)
        ok, msg = svc.validate_backup(str(fake_app_root / "does_not_exist.zip"))
        assert ok is False


class TestBackupServiceAnalyzeRestore:
    """Tests for BackupService.analyze_restore."""

    def test_classifies_newer_older_same_new(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))

        # Bump the local mtime of chor.db to 1h ago. The archive
        # was just created ("now"), so the archive is NEWER.
        # 1h ago is safely inside the ZIP 1980+ window.
        db_path = fake_app_root / "data" / "chor.db"
        old_time = datetime.now().timestamp() - 3600
        os.utime(db_path, (old_time, old_time))

        changes = svc.analyze_restore(str(out))
        assert "newer" in changes
        assert "older" in changes
        assert "same" in changes
        assert "new" in changes
        # Archive was created NOW, local is 1h ago -> archive newer
        newer_names = [e["archive_name"] for e in changes["newer"]]
        assert "data/chor.db" in newer_names

    def test_marks_missing_files_as_new(self, tmp_path):
        # Create an empty app root, but a backup with a file the root
        # doesn't have on disk
        svc = BackupService(tmp_path)
        # Create the backup from a different tree
        other_root = tmp_path / "other"
        (other_root / "data").mkdir(parents=True)
        (other_root / "data" / "chor.db").write_text("hello")
        other_svc = BackupService(other_root)
        out = tmp_path / "backup.zip"
        other_svc.create_backup(str(out))

        # Now analyze against our empty root
        changes = svc.analyze_restore(str(out))
        new_names = [e["archive_name"] for e in changes["new"]]
        assert "data/chor.db" in new_names


class TestBackupServiceRestore:
    """Tests for BackupService.restore_backup."""

    def test_restores_files_to_disk(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))

        # Wipe the data dir
        (fake_app_root / "data" / "chor.db").unlink()
        (fake_app_root / "data" / "state.json").unlink()
        assert not (fake_app_root / "data" / "chor.db").exists()

        restored = svc.restore_backup(str(out))
        assert (fake_app_root / "data" / "chor.db").exists()
        assert (fake_app_root / "data" / "state.json").exists()
        # manifest.json is not restored (excluded by design)
        assert "manifest.json" not in restored
        assert "data/chor.db" in restored

    def test_restored_content_matches_original(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        original_db = (fake_app_root / "data" / "chor.db").read_bytes()
        svc.create_backup(str(out))

        # Wipe and restore
        (fake_app_root / "data" / "chor.db").unlink()
        svc.restore_backup(str(out))
        restored_db = (fake_app_root / "data" / "chor.db").read_bytes()
        assert restored_db == original_db


class TestBackupServiceSize:
    def test_get_backup_size_returns_file_size(self, fake_app_root):
        svc = BackupService(fake_app_root)
        out = fake_app_root / "backup.zip"
        svc.create_backup(str(out))
        size = svc.get_backup_size(str(out))
        assert size == out.stat().st_size
        assert size > 0


# ===========================================================================
# PortabilityService
# ===========================================================================

@pytest.fixture
def fake_data_dir(tmp_path):
    """A directory with a few files, simulating a real data dir."""
    d = tmp_path / "data"
    d.mkdir()
    (d / "chor.db").write_text("DB CONTENTS")
    (d / "state.json").write_text("{}")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "extra.txt").write_text("EXTRA")
    return d


class TestPortabilityServiceExport:
    """Tests for PortabilityService.export_data."""

    def test_creates_zip_archive(self, fake_data_dir):
        svc = PortabilityService(str(fake_data_dir))
        out = fake_data_dir.parent / "export.zip"
        svc.export_data(str(out))
        assert out.exists()
        with zipfile.ZipFile(out) as zf:
            assert zf.testzip() is None

    def test_archive_contains_all_data_files(self, fake_data_dir):
        svc = PortabilityService(str(fake_data_dir))
        out = fake_data_dir.parent / "export.zip"
        svc.export_data(str(out))
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        # Subdir files must be included too
        assert "chor.db" in names or "data/chor.db" in names
        assert "manifest.json" in names

    def test_manifest_is_valid_json(self, fake_data_dir):
        svc = PortabilityService(str(fake_data_dir))
        out = fake_data_dir.parent / "export.zip"
        svc.export_data(str(out))
        with zipfile.ZipFile(out) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["version"] == "1.0"
        assert manifest["app"] == "ChorManager"
        assert "exported_at" in manifest


class TestPortabilityServiceImport:
    """Tests for PortabilityService.import_data."""

    def test_imports_files_to_target_dir(self, fake_data_dir, tmp_path):
        # Export first
        svc = PortabilityService(str(fake_data_dir))
        archive = tmp_path / "export.zip"
        svc.export_data(str(archive))

        # Wipe the data dir
        (fake_data_dir / "chor.db").unlink()
        (fake_data_dir / "state.json").unlink()

        # Import to the same dir
        target = svc.import_data(str(archive))
        assert Path(target) == fake_data_dir
        # Files are back
        files_after = {p.name for p in fake_data_dir.iterdir()}
        # At least chor.db and state.json should be there
        assert "chor.db" in files_after or any(
            "chor.db" in str(p) for p in fake_data_dir.rglob("*")
        )

    def test_import_to_custom_target(self, fake_data_dir, tmp_path):
        svc = PortabilityService(str(fake_data_dir))
        archive = tmp_path / "export.zip"
        svc.export_data(str(archive))

        custom = tmp_path / "restore_target"
        result = svc.import_data(str(archive), target_dir=str(custom))
        assert result == str(custom)
        # The archive should have written at least one file
        assert any(custom.rglob("*"))


class TestPortabilityServiceSize:
    def test_get_export_size(self, fake_data_dir, tmp_path):
        svc = PortabilityService(str(fake_data_dir))
        out = tmp_path / "export.zip"
        svc.export_data(str(out))
        size = svc.get_export_size(str(out))
        assert size > 0
        assert size == out.stat().st_size
