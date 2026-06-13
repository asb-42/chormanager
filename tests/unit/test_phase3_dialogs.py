# TDD PHASE 3: Coverage tests for the remaining 3 dialogs in dialogs.py.
#
# - SingerSelectionDialog (244 lines, multi-select singers with filters)
# - NewFormationDialog (77 lines, project+event picker)
# - RepertoireDialog (111 lines, repertoire CRUD)
#
# Headless: QT_QPA_PLATFORM=offscreen. Modal popups (QMessageBox,
# ExportDialog) werden via unittest.mock.patch entschärft.

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path) -> Iterator[Path]:
    """Create a real SQLite database with the full ChorManager schema."""
    p = tmp_path / "chor.db"
    conn = sqlite3.connect(str(p))
    try:
        conn.executescript("""
            CREATE TABLE singers (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                short_name TEXT,
                birth_date TEXT,
                voice_group TEXT,
                height INTEGER,
                email TEXT,
                phone TEXT,
                street TEXT,
                postal_code TEXT,
                city TEXT,
                gender TEXT,
                guardian1 TEXT,
                guardian1_phone TEXT,
                guardian2 TEXT,
                guardian2_phone TEXT,
                social_contacts TEXT,
                joined_year INTEGER,
                joined_month INTEGER,
                left_year INTEGER,
                left_month INTEGER,
                affinity_uuid TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                location TEXT,
                description TEXT,
                project_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 0,
                spielzeit TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE selbstdarstellung (
                id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE availability (
                id TEXT PRIMARY KEY,
                singer_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(singer_id, event_id)
            );
            CREATE TABLE besetzung (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                project_id TEXT,
                singer_ids TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE repertoire (
                id TEXT PRIMARY KEY,
                composer TEXT,
                title TEXT NOT NULL,
                dates TEXT,
                country TEXT,
                publisher TEXT,
                arrangement TEXT,
                location TEXT,
                project_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()
    yield p


@pytest.fixture
def database(db_path):
    """Returns a connected chormanager.data.database.Database."""
    from chormanager.data.database import Database
    db = Database(str(db_path))
    db.connect()
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def seeded_database(database):
    """Database with 1 project, 2 events, 3 singers for filter tests."""
    now = "2026-01-01T00:00:00"
    database.execute(
        "INSERT INTO projects (id, name, is_active, created_at, updated_at) "
        "VALUES (?, ?, 1, ?, ?)",
        ("p1", "Sommer 2026", now, now),
    )
    database.execute(
        "INSERT INTO projects (id, name, is_active, created_at, updated_at) "
        "VALUES (?, ?, 0, ?, ?)",
        ("p2", "Winter 2026", now, now),
    )
    database.execute(
        "INSERT INTO events (id, name, date, event_type, project_id, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("e1", "Probe 1", "2026-06-01T18:00:00", "Probe", "p1", now, now),
    )
    database.execute(
        "INSERT INTO events (id, name, date, event_type, project_id, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("e2", "Konzert", "2026-07-15T19:30:00", "Konzert", "p2", now, now),
    )
    database.execute(
        "INSERT INTO singers (id, full_name, short_name, voice_group, "
        "birth_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s1", "Anna Axt", "Anna", "Sopran", "1990-05-15", now, now),
    )
    database.execute(
        "INSERT INTO singers (id, full_name, short_name, voice_group, "
        "birth_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s2", "Bert Borke", "Bert", "Bass", "2010-03-20", now, now),
    )
    database.execute(
        "INSERT INTO singers (id, full_name, short_name, voice_group, "
        "birth_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s3", "Carla Cassel", "Carla", "Sopran", "2005-11-30", now, now),
    )
    database.commit()
    return database


# ===========================================================================
# SingerSelectionDialog
# ===========================================================================


class TestSingerSelectionDialogInit:
    def test_starts_empty_when_no_singers(self, qtbot, database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.selected_ids == set()
        assert dlg.table.rowCount() == 0
        assert dlg.windowTitle() == "Sänger auswählen"
        assert dlg.minimumWidth() == 700
        assert dlg.minimumHeight() == 500

    def test_loads_singers_into_table(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 3

    def test_pre_selected_ids_seeds_state(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(
            db=seeded_database, pre_selected_ids=["s1", "s3"],
        )
        qtbot.addWidget(dlg)
        assert "s1" in dlg.selected_ids
        assert "s3" in dlg.selected_ids
        assert "s2" not in dlg.selected_ids

    def test_pre_selected_defaults_to_empty_list(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database, pre_selected_ids=None)
        qtbot.addWidget(dlg)
        assert dlg.selected_ids == set()

    def test_besetzung_name_default(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        assert dlg.besetzung_name == "besetzung"

    def test_voice_filter_populated(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        with patch(
            "chormanager.ui.dialogs._singer_selection.load_voice_groups",
            return_value=[{"name": "Sopran"}, {"name": "Bass"}],
        ):
            dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        assert dlg.voice_filter.count() == 3


class TestSingerSelectionDialogFiltering:
    def test_voice_filter_narrows_table(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        with patch(
            "chormanager.ui.dialogs._singer_selection.load_voice_groups",
            return_value=[{"name": "Sopran"}, {"name": "Bass"}],
        ):
            dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        idx = dlg.voice_filter.findData("Sopran")
        dlg.voice_filter.setCurrentIndex(idx)
        assert dlg.table.rowCount() == 2

    def test_search_box_filters_by_short_name(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        dlg.search_box.setText("Bert")
        assert dlg.table.rowCount() == 1

    def test_search_box_filters_by_full_name(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        dlg.search_box.setText("Carla")
        assert dlg.table.rowCount() == 1

    def test_search_box_is_case_insensitive(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        dlg.search_box.setText("anna")
        assert dlg.table.rowCount() == 1

    def test_status_filter_active_excludes_left_members(self, qtbot, database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        now = "2026-01-01T00:00:00"
        database.execute(
            "INSERT INTO singers (id, full_name, short_name, voice_group, "
            "left_year, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("gone", "Gabi Gone", "Gabi", "Sopran", 2024, now, now),
        )
        database.execute(
            "INSERT INTO singers (id, full_name, short_name, voice_group, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("here", "Hans Hier", "Hans", "Bass", now, now),
        )
        database.commit()
        dlg = SingerSelectionDialog(db=database)
        qtbot.addWidget(dlg)
        dlg.status_filter.setCurrentIndex(
            dlg.status_filter.findData("active"),
        )
        assert dlg.table.rowCount() == 1

    def test_status_filter_minor_excludes_adults(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        dlg.status_filter.setCurrentIndex(
            dlg.status_filter.findData("minor"),
        )
        # Today is 2026-06-12. Anna (b.1990) is 36, Carla (b.2005)
        # is 20, Bert (b.2010) is 16. Only Bert is a minor.
        assert dlg.table.rowCount() == 1


class TestSingerSelectionDialogSelection:
    def test_select_all_marks_everyone(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        dlg._select_all()
        assert dlg.selected_ids == {"s1", "s2", "s3"}

    def test_deselect_all_clears_everyone(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(
            db=seeded_database, pre_selected_ids=["s1", "s2", "s3"],
        )
        qtbot.addWidget(dlg)
        dlg._deselect_all()
        assert dlg.selected_ids == set()

    def test_get_selected_ids_returns_list(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        dlg._select_all()
        ids = dlg.get_selected_ids()
        assert isinstance(ids, list)
        assert sorted(ids) == ["s1", "s2", "s3"]

    def test_export_with_no_selection_shows_warning(
        self, qtbot, seeded_database
    ):
        from chormanager.ui.dialogs import SingerSelectionDialog
        dlg = SingerSelectionDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        with patch("chormanager.ui.dialogs._singer_selection.QMessageBox.warning") as w:
            dlg._export_singers()
        w.assert_called_once()


# ===========================================================================
# NewFormationDialog
# ===========================================================================


class TestNewFormationDialogInit:
    def test_window_title(self, qtbot, database):
        from chormanager.ui.dialogs import NewFormationDialog
        dlg = NewFormationDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Neue Choraufstellung"

    def test_minimum_width(self, qtbot, database):
        from chormanager.ui.dialogs import NewFormationDialog
        dlg = NewFormationDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.minimumWidth() == 400

    def test_no_event_selected_initially(self, qtbot, database):
        from chormanager.ui.dialogs import NewFormationDialog
        dlg = NewFormationDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.selected_event is None
        assert dlg.get_event() is None


class TestNewFormationDialogWithProjects:
    def test_loads_projects_into_combo(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import NewFormationDialog
        dlg = NewFormationDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        assert dlg.project_combo.count() == 3

    def test_current_project_locks_combo(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import NewFormationDialog
        from chormanager.domain.repository import ProjectRepository
        repo = ProjectRepository(seeded_database)
        project = repo.get_by_id("p1")
        dlg = NewFormationDialog(
            db=seeded_database, current_project=project,
        )
        qtbot.addWidget(dlg)
        assert dlg.project_combo.count() == 1
        assert not dlg.project_combo.isEnabled()

    def test_project_change_filters_events(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import NewFormationDialog
        dlg = NewFormationDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        # _load_projects() auto-selects index 1 (first project),
        # so initial events combo already shows only p1's events.
        assert dlg.event_combo.count() == 1
        # Switch to "Alle Projekte" (index 0) -> all events visible.
        dlg.project_combo.setCurrentIndex(0)
        assert dlg.event_combo.count() == 2
        # Switch to project p2 (combo: 0=Alle, 1=Sommer 2026, 2=Winter 2026).
        # findData on custom Project objects is unreliable in PyQt,
        # so we go by display text instead.
        idx = dlg.project_combo.findText("Winter 2026")
        assert idx == 2
        dlg.project_combo.setCurrentIndex(idx)
        assert dlg.event_combo.count() == 1


class TestNewFormationDialogAccept:
    def test_accept_without_event_shows_warning(self, qtbot, database):
        from chormanager.ui.dialogs import NewFormationDialog
        dlg = NewFormationDialog(db=database)
        qtbot.addWidget(dlg)
        with patch("chormanager.ui.dialogs._new_formation.QMessageBox.warning") as w:
            dlg._on_accept()
        w.assert_called_once()
        assert dlg.selected_event is None

    def test_accept_with_event_sets_selected(self, qtbot, seeded_database):
        from chormanager.ui.dialogs import NewFormationDialog
        from chormanager.domain.repository import EventRepository
        dlg = NewFormationDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        repo = EventRepository(seeded_database)
        repo.get_by_id("e1")
        dlg.event_combo.setCurrentIndex(0)
        dlg._on_accept()
        assert dlg.selected_event is not None
        assert dlg.get_event() is not None


# ===========================================================================
# RepertoireDialog
# ===========================================================================


class TestRepertoireDialogInit:
    def test_new_repertoire_window_title(self, qtbot, database):
        from chormanager.ui.dialogs import RepertoireDialog
        dlg = RepertoireDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Neues Repertoire"

    def test_minimum_width(self, qtbot, database):
        from chormanager.ui.dialogs import RepertoireDialog
        dlg = RepertoireDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.minimumWidth() == 400

    def test_all_input_fields_exist(self, qtbot, database):
        from chormanager.ui.dialogs import RepertoireDialog
        dlg = RepertoireDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.composer_input is not None
        assert dlg.title_input is not None
        assert dlg.dates_input is not None
        assert dlg.country_input is not None
        assert dlg.publisher_input is not None
        assert dlg.arrangement_input is not None
        assert dlg.location_input is not None
        assert dlg.program_combo is not None

    def test_program_combo_has_empty_default(self, qtbot, database):
        from chormanager.ui.dialogs import RepertoireDialog
        dlg = RepertoireDialog(db=database)
        qtbot.addWidget(dlg)
        assert dlg.program_combo.itemData(0) == ""


class TestRepertoireDialogEdit:
    def test_existing_repertoire_window_title(self, qtbot, database):
        from chormanager.domain.repository import RepertoireRepository
        from chormanager.ui.dialogs import RepertoireDialog
        repo = RepertoireRepository(database)
        rep = repo.create(
            composer="Bach", title="Matthaeus-Passion",
        )
        dlg = RepertoireDialog(db=database, repertoire=rep)
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Repertoire bearbeiten"

    def test_existing_repertoire_populates_fields(self, qtbot, database):
        from chormanager.domain.repository import RepertoireRepository
        from chormanager.ui.dialogs import RepertoireDialog
        repo = RepertoireRepository(database)
        rep = repo.create(
            composer="Bach", title="Matthaeus-Passion",
            dates="1685-1750", country="Deutschland",
            publisher="Baerenreiter", arrangement="Chor + Orchester",
            location="Regal 3",
        )
        dlg = RepertoireDialog(db=database, repertoire=rep)
        qtbot.addWidget(dlg)
        assert dlg.composer_input.text() == "Bach"
        assert dlg.title_input.text() == "Matthaeus-Passion"
        assert dlg.dates_input.text() == "1685-1750"
        assert dlg.country_input.text() == "Deutschland"
        assert dlg.publisher_input.text() == "Baerenreiter"
        assert dlg.arrangement_input.text() == "Chor + Orchester"
        assert dlg.location_input.text() == "Regal 3"


class TestRepertoireDialogAccept:
    def test_accept_with_empty_title_shows_warning(self, qtbot, database):
        from chormanager.ui.dialogs import RepertoireDialog
        dlg = RepertoireDialog(db=database)
        qtbot.addWidget(dlg)
        with patch("chormanager.ui.dialogs._repertoire.QMessageBox.warning") as w:
            dlg._on_accept()
        w.assert_called_once()
        from chormanager.domain.repository import RepertoireRepository
        repo = RepertoireRepository(database)
        assert repo.get_all() == []

    def test_accept_with_title_creates_repertoire(self, qtbot, database):
        from chormanager.ui.dialogs import RepertoireDialog
        from chormanager.domain.repository import RepertoireRepository
        dlg = RepertoireDialog(db=database)
        qtbot.addWidget(dlg)
        dlg.composer_input.setText("Mozart")
        dlg.title_input.setText("Requiem")
        dlg._on_accept()
        repo = RepertoireRepository(database)
        items = repo.get_all()
        assert len(items) == 1
        assert items[0].composer == "Mozart"
        assert items[0].title == "Requiem"

    def test_accept_with_existing_repertoire_updates(
        self, qtbot, database
    ):
        from chormanager.domain.repository import RepertoireRepository
        from chormanager.ui.dialogs import RepertoireDialog
        repo = RepertoireRepository(database)
        rep = repo.create(composer="Bach", title="Alt")
        dlg = RepertoireDialog(db=database, repertoire=rep)
        qtbot.addWidget(dlg)
        dlg.title_input.setText("Matthaeus-Passion")
        dlg._on_accept()
        updated = repo.get_by_id(rep.id)
        assert updated.title == "Matthaeus-Passion"
        assert updated.composer == "Bach"

    def test_program_combo_selection_persists(self, qtbot, seeded_database):
        from chormanager.domain.repository import RepertoireRepository
        from chormanager.ui.dialogs import RepertoireDialog
        dlg = RepertoireDialog(db=seeded_database)
        qtbot.addWidget(dlg)
        idx = dlg.program_combo.findData("p1")
        dlg.program_combo.setCurrentIndex(idx)
        dlg.title_input.setText("Bach-Kantate")
        dlg._on_accept()
        repo = RepertoireRepository(seeded_database)
        items = repo.get_all()
        assert items[0].project_id == "p1"
