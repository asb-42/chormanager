# Test Coverage Plan

**Generated from:** `docs/reports/2026-06-11_code-review.md`
**Date:** 2026-06-11
**Approach:** TDD — write tests first, then verify implementation

---

## Current Test Coverage Summary

| Category | Test Files | Coverage |
|----------|:----------:|:--------:|
| Domain Models | 4 (singer, event, project, affinity) | Good |
| Repository Layer | 1 (database) | Partial |
| Core Services | 2 (export, history) | Partial |
| UI Dialogs | 0 | **None** |
| UI Views | 0 | **None** |
| Main Window | 2 (64+63 lines) | Minimal |
| Choraufstellung | 4 (grid, rules, undo, metadata) | Good |
| Integration | 2 (storage) | Good |

---

## Priority 1: Core Business Logic Tests

### 1.1 ExportService (CSV, LibreOffice, Writer)

**File:** `tests/unit/test_export_service.py` (exists, needs expansion)

**Current coverage:**
- `test_export_to_csv` ✅
- `test_export_to_csv_empty` ✅
- `test_export_to_libreoffice_calc` ✅
- `test_export_to_libreoffice_writer` ✅
- `test_get_export_data` ✅

**Missing tests:**
```python
# Edge cases
def test_export_to_csv_special_characters():
    """CSV with commas, quotes, newlines in data."""

def test_export_to_csv_unicode():
    """CSV with German umlauts (ä, ö, ü, ß)."""

def test_export_to_libreoffice_writer_html_escape():
    """HTML output escapes < and > in data."""

def test_get_export_data_computed_fields():
    """get_export_data handles 'age' as callable."""

def test_get_export_data_none_values():
    """get_export_data converts None to empty string."""

def test_get_export_data_missing_attributes():
    """get_export_data handles items without expected attributes."""
```

### 1.2 FileBackupService

**File:** `tests/unit/test_backup.py` (exists, needs expansion)

**Current coverage:**
- `test_create_backup` ✅
- `test_list_backups` ✅
- `test_max_backups` ✅
- `test_restore_backup` ✅
- `test_cleanup_old_backups` ✅

**Missing tests:**
```python
def test_create_backup_nonexistent_source():
    """Create backup when source file doesn't exist."""

def test_create_backup_preserves_content():
    """Backup file has same content as source."""

def test_list_backups_empty_dir():
    """List backups in empty directory."""

def test_list_backups_sorted_newest_first():
    """Backups sorted by modification time."""

def test_delete_backup_existing():
    """Delete existing backup returns True."""

def test_delete_backup_nonexistent():
    """Delete nonexistent backup returns False."""

def test_get_backup_info():
    """Get backup metadata (size, dates)."""

def test_get_backup_info_nonexistent():
    """Get info for nonexistent backup returns empty dict."""
```

### 1.3 ApplicationBackupService (ZIP backup)

**File:** `tests/unit/test_backup_service.py` (NEW)

```python
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

    def test_analyze_restore(self, service, tmp_path):
        """Analyze what restore would do."""
        output = tmp_path / "backup.zip"
        service.create_backup(str(output))
        changes = service.analyze_restore(str(output))
        assert "newer" in changes
        assert "older" in changes
        assert "new" in changes
```

### 1.4 HistoryService

**File:** `tests/unit/test_history.py` (exists, needs expansion)

**Current coverage:**
- `test_add_command` ✅
- `test_undo` ✅
- `test_redo` ✅
- `test_clear` ✅

**Missing tests:**
```python
def test_undo_empty_stack():
    """Undo on empty stack returns None."""

def test_redo_empty_stack():
    """Redo on empty stack returns None."""

def test_max_entries_limit():
    """History respects max_entries limit."""

def test_redo_cleared_on_new_command():
    """Redo stack cleared when new command added."""

def test_can_undo_redo():
    """can_undo/can_redo return correct booleans."""

def test_len():
    """len() returns correct count."""
```

---

## Priority 2: Repository Layer Tests

### 2.1 SingerRepository

**File:** `tests/unit/test_singer_repository.py` (NEW)

```python
"""Tests for SingerRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import SingerRepository


class TestSingerRepository:
    """Tests for Singer CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return SingerRepository(db)

    def test_create_singer(self, repo):
        """Create a new singer."""
        singer = repo.create(full_name="Test Singer", voice_group="Sopran 1")
        assert singer.id
        assert singer.full_name == "Test Singer"

    def test_get_by_id(self, repo):
        """Get singer by ID."""
        created = repo.create(full_name="Alice")
        found = repo.get_by_id(created.id)
        assert found is not None
        assert found.full_name == "Alice"

    def test_get_by_id_not_found(self, repo):
        """Get nonexistent singer returns None."""
        assert repo.get_by_id("nonexistent") is None

    def test_get_all(self, repo):
        """Get all singers."""
        repo.create(full_name="Alice")
        repo.create(full_name="Bob")
        singers = repo.get_all()
        assert len(singers) == 2

    def test_update_singer(self, repo):
        """Update singer fields."""
        singer = repo.create(full_name="Alice")
        updated = repo.update(singer.id, full_name="Alice Updated")
        assert updated.full_name == "Alice Updated"

    def test_delete_singer(self, repo):
        """Delete singer."""
        singer = repo.create(full_name="Alice")
        assert repo.delete(singer.id) is True
        assert repo.get_by_id(singer.id) is None

    def test_delete_nonexistent(self, repo):
        """Delete nonexistent singer returns False."""
        assert repo.delete("nonexistent") is False

    def test_search(self, repo):
        """Search singers by name."""
        repo.create(full_name="Alice Smith")
        repo.create(full_name="Bob Jones")
        results = repo.search("Alice")
        assert len(results) == 1
        assert results[0].full_name == "Alice Smith"

    def test_get_by_voice_group(self, repo):
        """Filter singers by voice group."""
        repo.create(full_name="Alice", voice_group="Sopran 1")
        repo.create(full_name="Bob", voice_group="Bass 1")
        sopran = repo.get_by_voice_group("Sopran 1")
        assert len(sopran) == 1

    def test_get_active(self, repo):
        """Get active singers (no left_date)."""
        repo.create(full_name="Alice")
        repo.create(full_name="Bob", left_year=2024)
        active = repo.get_active()
        assert len(active) == 1
```

### 2.2 EventRepository

**File:** `tests/unit/test_event_repository.py` (NEW)

```python
"""Tests for EventRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import EventRepository


class TestEventRepository:
    """Tests for Event CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return EventRepository(db)

    def test_create_event(self, repo):
        """Create a new event."""
        event = repo.create(name="Test Event", date="2026-05-15", event_type="gp")
        assert event.id
        assert event.name == "Test Event"

    def test_get_all_sorted_by_date(self, repo):
        """Events sorted by date descending."""
        repo.create(name="Event 1", date="2026-06-01", event_type="gp")
        repo.create(name="Event 2", date="2026-05-01", event_type="gp")
        events = repo.get_all()
        assert events[0].date > events[1].date

    def test_update_event(self, repo):
        """Update event fields."""
        event = repo.create(name="Old Name", date="2026-05-15", event_type="gp")
        updated = repo.update(event.id, name="New Name")
        assert updated.name == "New Name"

    def test_delete_event(self, repo):
        """Delete event."""
        event = repo.create(name="Test", date="2026-05-15", event_type="gp")
        assert repo.delete(event.id) is True
```

### 2.3 AvailabilityRepository

**File:** `tests/unit/test_availability_repository.py` (NEW)

```python
"""Tests for AvailabilityRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import SingerRepository, EventRepository, AvailabilityRepository


class TestAvailabilityRepository:
    """Tests for Availability CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repos(self, db):
        singer_repo = SingerRepository(db)
        event_repo = EventRepository(db)
        avail_repo = AvailabilityRepository(db)
        singer = singer_repo.create(full_name="Alice")
        event = event_repo.create(name="Concert", date="2026-06-01", event_type="konzert")
        return avail_repo, singer, event

    def test_create_availability(self, repos):
        """Create availability entry."""
        avail_repo, singer, event = repos
        avail = avail_repo.create(singer_id=singer.id, event_id=event.id, status="yes")
        assert avail.status == "yes"

    def test_upsert_availability(self, repos):
        """Update existing availability via upsert."""
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avail_repo.update(singer.id, event.id, "no")
        avail = avail_repo.get_by_ids(singer.id, event.id)
        assert avail.status == "no"

    def test_get_by_event(self, repos):
        """Get all availability for an event."""
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        avails = avail_repo.get_by_event(event.id)
        assert len(avails) == 1

    def test_delete_availability(self, repos):
        """Delete availability entry."""
        avail_repo, singer, event = repos
        avail_repo.update(singer.id, event.id, "yes")
        assert avail_repo.delete(singer.id, event.id) is True
```

### 2.4 ProjectRepository

**File:** `tests/unit/test_project_repository.py` (NEW)

```python
"""Tests for ProjectRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import ProjectRepository


class TestProjectRepository:
    """Tests for Project CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return ProjectRepository(db)

    def test_create_project(self, repo):
        """Create a new project."""
        project = repo.create(name="Test Project")
        assert project.id
        assert project.name == "Test Project"

    def test_set_active(self, repo):
        """Set project as active."""
        p1 = repo.create(name="Project 1")
        p2 = repo.create(name="Project 2")
        repo.set_active(p1.id)
        active = repo.get_active()
        assert active.id == p1.id

    def test_set_active_clears_others(self, repo):
        """Setting active clears previous active."""
        p1 = repo.create(name="Project 1")
        p2 = repo.create(name="Project 2")
        repo.set_active(p1.id)
        repo.set_active(p2.id)
        active = repo.get_active()
        assert active.id == p2.id
```

### 2.5 BesetzungRepository

**File:** `tests/unit/test_besetzung_repository.py` (NEW)

```python
"""Tests for BesetzungRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import BesetzungRepository, ProjectRepository


class TestBesetzungRepository:
    """Tests for Besetzung CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return BesetzungRepository(db)

    def test_create_besetzung(self, repo):
        """Create a new besetzung."""
        besetzung = repo.create(name="Main Choir", project_id="proj1", singer_ids=["s1", "s2"])
        assert besetzung.id
        assert besetzung.name == "Main Choir"

    def test_get_singer_ids(self, repo):
        """Parse singer IDs from JSON."""
        besetzung = repo.create(name="Test", project_id="p1", singer_ids=["s1", "s2", "s3"])
        ids = besetzung.get_singer_ids()
        assert len(ids) == 3

    def test_get_by_project(self, repo):
        """Get besetzungen by project."""
        repo.create(name="B1", project_id="p1", singer_ids=[])
        repo.create(name="B2", project_id="p1", singer_ids=[])
        repo.create(name="B3", project_id="p2", singer_ids=[])
        result = repo.get_by_project("p1")
        assert len(result) == 2
```

### 2.6 RepertoireRepository

**File:** `tests/unit/test_repertoire_repository.py` (NEW)

```python
"""Tests for RepertoireRepository."""

import pytest
from chormanager.data.database import Database
from chormanager.domain.repository import RepertoireRepository


class TestRepertoireRepository:
    """Tests for Repertoire CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        yield db
        db.close()

    @pytest.fixture
    def repo(self, db):
        return RepertoireRepository(db)

    def test_create_repertoire(self, repo):
        """Create a new repertoire entry."""
        entry = repo.create(composer="Mozart", title="Requiem")
        assert entry.id
        assert entry.composer == "Mozart"

    def test_get_by_project_id(self, repo):
        """Get repertoire by project."""
        repo.create(composer="Mozart", title="Requiem", project_id="p1")
        repo.create(composer="Bach", title="Mass", project_id="p2")
        result = repo.get_by_project_id("p1")
        assert len(result) == 1
```

---

## Priority 3: Database Migration Tests

### 3.1 Schema Migration Tests

**File:** `tests/unit/test_migrations.py` (NEW)

```python
"""Tests for database schema migrations."""

import pytest
import sqlite3
from chormanager.data.database import Database


class TestDatabaseMigrations:
    """Tests for schema creation and migration."""

    def test_create_tables_creates_all_tables(self, tmp_path):
        """All expected tables are created."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        
        cursor = db.get_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        
        expected = {"singers", "events", "projects", "availability", "besetzung", "repertoire", "selbstdarstellung"}
        assert expected.issubset(tables)
        
        db.close()

    def test_create_tables_idempotent(self, tmp_path):
        """Calling create_tables twice doesn't error."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        db.create_tables()  # Should not raise
        db.close()

    def test_add_column_idempotent(self, tmp_path):
        """ALTER TABLE ADD COLUMN is idempotent."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        db.create_tables()  # Second call tries to add columns again
        db.close()

    def test_foreign_keys_enabled(self, tmp_path):
        """Foreign keys are enforced."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        
        result = db.get_connection().execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1
        
        db.close()

    def test_indexes_created(self, tmp_path):
        """Database indexes are created."""
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        
        cursor = db.get_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        
        assert "idx_events_project_id" in indexes
        assert "idx_singers_voice_group" in indexes
        
        db.close()
```

---

## Priority 4: Integration Tests

### 4.1 Config Integration

**File:** `tests/integration/test_config.py` (NEW)

```python
"""Integration tests for configuration loading."""

import pytest
import yaml
from pathlib import Path
from chormanager.config import load_app_config, load_voice_groups, load_fields, reload_config


class TestConfigIntegration:
    """Tests for config loading with real files."""

    def test_load_app_config_returns_defaults(self):
        """load_app_config returns defaults when file missing."""
        config = load_app_config()
        assert "database" in config
        assert "backup" in config

    def test_load_voice_groups(self):
        """load_voice_groups returns sorted list."""
        groups = load_voice_groups()
        assert len(groups) > 0
        assert groups[0]["name"] == "Sopran 1"

    def test_load_fields(self):
        """load_fields returns sorted list."""
        fields = load_fields()
        assert len(fields) > 0
        assert fields[0]["name"] == "full_name"

    def test_config_caching(self):
        """Config is cached after first load."""
        reload_config()
        config1 = load_app_config()
        config2 = load_app_config()
        assert config1 is config2  # Same object due to lru_cache
```

### 4.2 Export Integration

**File:** `tests/integration/test_export_integration.py` (NEW)

```python
"""Integration tests for export workflows."""

import pytest
import tempfile
from pathlib import Path
from chormanager.data.database import Database
from chormanager.domain.repository import SingerRepository
from chormanager.core.export_service import ExportService


class TestExportIntegration:
    """Tests for end-to-end export workflows."""

    @pytest.fixture
    def db_with_singers(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.connect()
        db.create_tables()
        repo = SingerRepository(db)
        repo.create(full_name="Alice", voice_group="Sopran 1", email="alice@test.de")
        repo.create(full_name="Bob", voice_group="Bass 1", phone="12345")
        yield db
        db.close()

    def test_csv_export_workflow(self, db_with_singers):
        """Full CSV export workflow."""
        service = ExportService()
        repo = SingerRepository(db_with_singers)
        singers = repo.get_all()
        data = service.get_export_data(singers, ["full_name", "voice_group"])
        csv = service.export_to_csv(data, ["full_name", "voice_group"])
        
        assert "Alice" in csv
        assert "Sopran 1" in csv

    def test_libreoffice_export_workflow(self, db_with_singers):
        """Full LibreOffice export workflow."""
        service = ExportService()
        repo = SingerRepository(db_with_singers)
        singers = repo.get_all()
        data = service.get_export_data(singers, ["full_name", "voice_group"])
        html = service.export_to_libreoffice_writer(data, ["full_name", "voice_group"])
        
        assert "<html>" in html
        assert "Alice" in html
```

---

## Priority 5: UI Dialog Tests (pytest-qt)

### 5.1 SingerDialog Tests

**File:** `tests/gui/test_singer_dialog.py` (NEW)

```python
"""Tests for SingerDialog."""

import pytest
from chormanager.ui.main_window import SingerDialog


class TestSingerDialog:
    """Tests for Singer creation/editing dialog."""

    def test_dialog_creates_empty(self, qtbot):
        """Dialog opens with empty fields."""
        dialog = SingerDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Sänger hinzufügen"

    def test_dialog_populates_singer(self, qtbot, sample_singers):
        """Dialog populates fields from singer."""
        from chormanager.domain.models import Singer
        singer = Singer(full_name="Alice", voice_group="Sopran 1")
        dialog = SingerDialog(singer=singer)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Sänger bearbeiten"

    def test_get_data_returns_dict(self, qtbot):
        """get_data returns dictionary."""
        dialog = SingerDialog()
        qtbot.addWidget(dialog)
        data = dialog.get_data()
        assert isinstance(data, dict)
```

### 5.2 EventDialog Tests

**File:** `tests/gui/test_event_dialog.py` (NEW)

```python
"""Tests for EventDialog."""

import pytest
from chormanager.ui.dialogs import EventDialog


class TestEventDialog:
    """Tests for Event creation/editing dialog."""

    def test_dialog_creates_empty(self, qtbot):
        """Dialog opens with empty fields."""
        dialog = EventDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Termin hinzufügen"

    def test_get_data_returns_required_fields(self, qtbot):
        """get_data returns name, date, type."""
        dialog = EventDialog()
        qtbot.addWidget(dialog)
        data = dialog.get_data()
        assert "name" in data
        assert "date" in data
        assert "event_type" in data
```

### 5.3 ExportDialog Tests

**File:** `tests/gui/test_export_dialog.py` (NEW)

```python
"""Tests for ExportDialog."""

import pytest
from chormanager.ui.export_dialog import ExportDialog


class TestExportDialog:
    """Tests for export format selection dialog."""

    def test_dialog_shows_fields(self, qtbot):
        """Dialog displays available fields."""
        fields = [{"name": "name", "label": "Name"}, {"name": "vg", "label": "Stimmgruppe"}]
        dialog = ExportDialog(fields)
        qtbot.addWidget(dialog)
        assert dialog.get_selected_fields() is not None

    def test_get_export_format_default(self, qtbot):
        """Default export format is CSV."""
        dialog = ExportDialog([{"name": "name", "label": "Name"}])
        qtbot.addWidget(dialog)
        fmt = dialog.get_export_format()
        assert fmt in ("csv", "writer", "calc")
```

---

## Test File Summary

### New Test Files to Create

| File | Tests | Priority |
|------|:-----:|:--------:|
| `tests/unit/test_singer_repository.py` | 10 | P2 |
| `tests/unit/test_event_repository.py` | 5 | P2 |
| `tests/unit/test_availability_repository.py` | 4 | P2 |
| `tests/unit/test_project_repository.py` | 3 | P2 |
| `tests/unit/test_besetzung_repository.py` | 3 | P2 |
| `tests/unit/test_repertoire_repository.py` | 2 | P2 |
| `tests/unit/test_backup_service.py` | 7 | P1 |
| `tests/unit/test_migrations.py` | 5 | P3 |
| `tests/integration/test_config.py` | 4 | P3 |
| `tests/integration/test_export_integration.py` | 2 | P3 |
| `tests/gui/test_singer_dialog.py` | 3 | P5 |
| `tests/gui/test_event_dialog.py` | 2 | P5 |
| `tests/gui/test_export_dialog.py` | 2 | P5 |

### Existing Test Files to Expand

| File | Current | Missing |
|------|:-------:|:-------:|
| `tests/unit/test_export_service.py` | 5 | 6 edge cases |
| `tests/unit/test_backup.py` | 5 | 8 edge cases |
| `tests/unit/test_history.py` | 4 | 6 edge cases |
| `tests/unit/test_database.py` | 3 | 2 more |
| `tests/unit/test_config.py` | 3 | 2 more |

### Total New Tests

| Category | Count |
|----------|:-----:|
| New repository tests | 27 |
| New service tests | 13 |
| New migration tests | 5 |
| New integration tests | 6 |
| New GUI tests | 7 |
| Edge case additions | 24 |
| **Total** | **82** |

---

## Implementation Order

```
Phase 1 (Repository tests - foundation):
  test_singer_repository.py
  test_event_repository.py
  test_availability_repository.py
  test_project_repository.py
  test_besetzung_repository.py
  test_repertoire_repository.py

Phase 2 (Service tests):
  test_backup_service.py (ApplicationBackupService)
  Expand test_export_service.py
  Expand test_backup.py
  Expand test_history.py

Phase 3 (Infrastructure tests):
  test_migrations.py
  test_config.py (integration)
  test_export_integration.py

Phase 4 (GUI tests):
  test_singer_dialog.py
  test_event_dialog.py
  test_export_dialog.py
```

---

## Success Criteria

After all tests are implemented:

- [ ] All 82 new tests pass
- [ ] Total test count: 262+ (up from 180)
- [ ] Every repository class has CRUD tests
- [ ] Every service class has unit tests
- [ ] Database migrations are tested
- [ ] Export workflows are tested end-to-end
- [ ] Critical dialogs have basic smoke tests
- [ ] Edge cases (empty inputs, None values, missing files) are covered
