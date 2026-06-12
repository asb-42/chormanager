# TDD PHASE 5: Coverage tests for ui/views/*_tab.py modules.
#
# Three tab widgets, all with similar table + context-menu patterns.
# Strategy: exercise the load/sort/filter public methods and the
# state setters, while mocking modal dialogs.

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures (shared with phase 3/4 patterns)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path) -> Iterator[Path]:
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
    from chormanager.data.database import Database
    db = Database(str(db_path))
    db.connect()
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def seeded(database):
    """Database with 2 projects, 3 events, 3 singers, 1 besetzung."""
    now = "2026-01-01T00:00:00"
    database.execute(
        "INSERT INTO projects (id, name, description, spielzeit, is_active, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("p1", "Sommer 2026", "Konzerte im Sommer", "2025/26", 1, now, now),
    )
    database.execute(
        "INSERT INTO projects (id, name, description, spielzeit, is_active, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("p2", "Winter 2026", "Konzerte im Winter", "2026/27", 0, now, now),
    )
    for eid, name, date_, etype, pid in [
        ("e1", "Probe 1", "2026-06-01T18:00", "Probe", "p1"),
        ("e2", "Konzert", "2026-07-15T19:30", "Konzert", "p1"),
        ("e3", "Probe 2", "2026-12-01T18:00", "Probe", "p2"),
    ]:
        database.execute(
            "INSERT INTO events (id, name, date, event_type, project_id, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, name, date_, etype, pid, now, now),
        )
    for sid, sn, fn, vg in [
        ("s1", "Anna", "Anna Axt", "Sopran"),
        ("s2", "Bert", "Bert Borke", "Bass"),
        ("s3", "Carla", "Carla Cassel", "Alt"),
    ]:
        database.execute(
            "INSERT INTO singers (id, full_name, short_name, voice_group, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sid, fn, sn, vg, now, now),
        )
    database.execute(
        "INSERT INTO besetzung (id, name, project_id, singer_ids, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("b1", "Standard", "p1", '["s1","s2"]', now, now),
    )
    database.commit()
    return database


# ===========================================================================
# BesetzungTab
# ===========================================================================


class TestBesetzungTabInit:
    def test_init_empty(self, qtbot, database):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=database)
        qtbot.addWidget(dlg)
        assert dlg.table.columnCount() == 4
        assert dlg.table.rowCount() == 0
        assert dlg.current_project is None
        assert dlg.get_active_besetzung() is None

    def test_init_loads_besetzungen(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 1
        # First row, first column = "Standard"
        assert dlg.table.item(0, 0).text() == "Standard"
        # Singer count = 2 (Anna + Bert)
        assert dlg.table.item(0, 2).text() == "2"

    def test_set_project_filters_besetzungen(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        from chormanager.domain.repository import ProjectRepository
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        project = ProjectRepository(seeded).get_by_id("p2")
        dlg.set_project(project)
        # p2 has no besetzungen
        assert dlg.table.rowCount() == 0

    def test_set_project_p1_shows_besetzung(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        from chormanager.domain.repository import ProjectRepository
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        project = ProjectRepository(seeded).get_by_id("p1")
        dlg.set_project(project)
        assert dlg.table.rowCount() == 1

    def test_set_active_besetzung_id(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        dlg.set_active_besetzung("b1")
        assert dlg.get_active_besetzung() is not None
        assert dlg.get_active_besetzung().id == "b1"

    def test_get_besetzung_for_project(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        result = dlg.get_besetzung_for_project("p1")
        assert len(result) == 1
        assert result[0].id == "b1"

    def test_get_besetzung_for_project_empty(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        assert dlg.get_besetzung_for_project("p2") == []

    def test_active_besetzung_signal_emitted(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        received = []
        dlg.active_besetzung_changed.connect(lambda b: received.append(b))
        # Test the signal-emission path via _restore_active_besetzung
        with patch(
            "chormanager.ui.views.besetzung_tab.get_last_active_besetzung_id",
            return_value="b1",
        ):
            dlg._restore_active_besetzung()
        assert len(received) == 1
        assert received[0].id == "b1"

    def test_new_besetzung_without_project_warns(self, qtbot, database):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=database)
        qtbot.addWidget(dlg)
        with patch(
            "chormanager.ui.views.besetzung_tab.QMessageBox.warning"
        ) as w:
            dlg._new_besetzung()
        w.assert_called_once()

    def test_delete_besetzung_without_row_warns(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        with patch(
            "chormanager.ui.views.besetzung_tab.QMessageBox.warning"
        ) as w:
            dlg._delete_besetzung()
        w.assert_called_once()

    def test_set_active_besetzung_without_row_warns(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        with patch(
            "chormanager.ui.views.besetzung_tab.QMessageBox.warning"
        ) as w:
            dlg._set_active_besetzung()
        w.assert_called_once()

    def test_edit_besetzung_without_row_warns(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        with patch(
            "chormanager.ui.views.besetzung_tab.QMessageBox.warning"
        ) as w:
            dlg._edit_besetzung()
        w.assert_called_once()

    def test_delete_besetzung_with_yes_removes_row(self, qtbot, seeded):
        from chormanager.ui.views.besetzung_tab import BesetzungTab
        from PyQt6.QtWidgets import QMessageBox
        dlg = BesetzungTab(db=seeded)
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 1
        dlg.table.selectRow(0)
        with patch.object(
            QMessageBox, "question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            dlg._delete_besetzung()
        assert dlg.table.rowCount() == 0


# ===========================================================================
# ProjectsTab
# ===========================================================================


class TestProjectsTabInit:
    def test_init_empty(self, qtbot, database):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=database)
        qtbot.addWidget(dlg)
        assert dlg.table.columnCount() == 5
        assert dlg.table.rowCount() == 0
        assert dlg.current_project is None

    def test_init_loads_projects(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 2

    def test_search_box_narrows_table(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        dlg.search_box.setText("Sommer")
        assert dlg.table.rowCount() == 1
        # First column = Spielzeit "2025/26"
        assert dlg.table.item(0, 0).text() == "2025/26"

    def test_search_box_case_insensitive(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        dlg.search_box.setText("sommer")
        assert dlg.table.rowCount() == 1

    def test_set_current_project_persists(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        from chormanager.domain.repository import ProjectRepository
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        project = ProjectRepository(seeded).get_by_id("p1")
        dlg.set_current_project(project)
        assert dlg.current_project is not None
        assert dlg.current_project.id == "p1"

    def test_set_current_project_emits_signal(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        from chormanager.domain.repository import ProjectRepository
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        received = []
        dlg.current_project_changed.connect(lambda: received.append(True))
        project = ProjectRepository(seeded).get_by_id("p1")
        dlg.set_current_project(project)
        assert received == [True]

    def test_sort_by_name(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        # Default sort is spielzeit descending; switch to name ascending
        dlg.sort_field.setCurrentIndex(0)
        dlg.sort_order.setCurrentIndex(0)  # ascending
        names = [
            dlg.table.item(row, 1).text()
            for row in range(dlg.table.rowCount())
        ]
        assert names == sorted(names)

    def test_event_count_in_last_column(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        # p1 has 2 events, p2 has 1 event
        # We don't know the order (sorted by spielzeit), so just check
        # the counts appear in the table somewhere
        counts = []
        for row in range(dlg.table.rowCount()):
            item = dlg.table.item(row, 4)
            counts.append(int(item.text()))
        assert sorted(counts) == [1, 2]

    def test_add_project_creates_row(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        from chormanager.ui.views.projects_tab import ProjectDialog
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        with patch.object(ProjectDialog, "exec", return_value=True), \
             patch.object(
                 ProjectDialog, "get_data",
                 return_value={"name": "Neues Projekt",
                               "description": "x", "spielzeit": "2027/28"},
             ):
            dlg._add_project()
        assert dlg.table.rowCount() == 3

    def test_add_project_without_name_noop(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        from chormanager.ui.views.projects_tab import ProjectDialog
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        with patch.object(ProjectDialog, "exec", return_value=True), \
             patch.object(
                 ProjectDialog, "get_data",
                 return_value={"name": "", "description": "",
                               "spielzeit": ""},
             ):
            dlg._add_project()
        assert dlg.table.rowCount() == 2  # unchanged

    def test_duplicate_project_creates_copy(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        from chormanager.ui.views.projects_tab import ProjectDialog
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        dlg.table.selectRow(0)
        with patch.object(ProjectDialog, "exec", return_value=False):
            dlg._duplicate_project()
        # Should have 3 rows now (new copy + original 2)
        assert dlg.table.rowCount() == 3

    def test_set_active_updates_current_project(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectsTab
        dlg = ProjectsTab(db=seeded)
        qtbot.addWidget(dlg)
        dlg.table.selectRow(0)
        dlg._set_active()
        assert dlg.current_project is not None


class TestProjectDialog:
    """Tests for the inner ProjectDialog class."""

    def test_new_project_title(self, qtbot, database):
        from chormanager.ui.views.projects_tab import ProjectDialog
        dlg = ProjectDialog(db=database)
        qtbot.addWidget(dlg.dialog)
        assert dlg.dialog.windowTitle() == "Neues Projekt"

    def test_edit_project_title(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectDialog
        from chormanager.domain.repository import ProjectRepository
        project = ProjectRepository(seeded).get_by_id("p1")
        dlg = ProjectDialog(db=seeded, project=project)
        qtbot.addWidget(dlg.dialog)
        assert dlg.dialog.windowTitle() == "Projekt bearbeiten"

    def test_existing_project_populates_fields(self, qtbot, seeded):
        from chormanager.ui.views.projects_tab import ProjectDialog
        from chormanager.domain.repository import ProjectRepository
        project = ProjectRepository(seeded).get_by_id("p1")
        dlg = ProjectDialog(db=seeded, project=project)
        qtbot.addWidget(dlg.dialog)
        assert dlg.name_input.text() == "Sommer 2026"
        assert dlg.spielzeit_input.text() == "2025/26"
        assert "Sommer" in dlg.description_input.toPlainText()

    def test_get_data_strips_whitespace(self, qtbot, database):
        from chormanager.ui.views.projects_tab import ProjectDialog
        dlg = ProjectDialog(db=database)
        qtbot.addWidget(dlg.dialog)
        dlg.name_input.setText("  Mein Projekt  ")
        data = dlg.get_data()
        assert data["name"] == "Mein Projekt"
