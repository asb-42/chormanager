# TDD PHASE 4: Coverage tests for EventAvailabilityDialog.
#
# This is the largest dialog in dialogs.py (590 lines). Strategy:
# - Headless via QT_QPA_PLATFORM=offscreen
# - Mock QFileDialog and QMessageBox for export methods
# - Test the public API: _load_availability, _save_availability_on_change,
#   accept(), and the besetzung_ids filter
# - Avoid testing the verbose PDF/ODT export body (already covered by
#   test_response_render_pdf / test_response_render_odt)

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel


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
    from chormanager.data.database import Database
    db = Database(str(db_path))
    db.connect()
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def seeded_availability_db(database):
    """Database with 1 event, 4 singers, 2 existing availability rows."""
    now = "2026-01-01T00:00:00"
    database.execute(
        "INSERT INTO events (id, name, date, event_type, created_at, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("e1", "Sommerkonzert", "2026-07-15T19:30:00", "Konzert", now, now),
    )
    # 4 active singers
    for sid, sn, fn, vg in [
        ("s1", "Anna", "Anna Axt", "Sopran 1"),
        ("s2", "Bert", "Bert Borke", "Bass 1"),
        ("s3", "Carla", "Carla Cassel", "Sopran 1"),
        ("s4", "Doris", "Doris Dackel", "Alt 1"),
    ]:
        database.execute(
            "INSERT INTO singers (id, full_name, short_name, voice_group, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sid, fn, sn, vg, now, now),
        )
    # 1 singer has left
    database.execute(
        "INSERT INTO singers (id, full_name, short_name, voice_group, "
        "left_year, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s5", "Egon Exit", "Egon", "Tenor", 2023, now, now),
    )
    # Availability: Anna=yes, Bert=no
    database.execute(
        "INSERT INTO availability (id, singer_id, event_id, status, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("a1", "s1", "e1", "yes", now, now),
    )
    database.execute(
        "INSERT INTO availability (id, singer_id, event_id, status, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("a2", "s2", "e1", "no", now, now),
    )
    database.commit()
    return database


def _make_event(database):
    """Helper to fetch the seeded event as an Event object."""
    from chormanager.domain.repository import EventRepository
    return EventRepository(database).get_by_id("e1")


# ---------------------------------------------------------------------------
# Lazy dialog import to avoid GUI module-level import issues
# ---------------------------------------------------------------------------


def _dlg():
    from chormanager.ui import dialogs as d
    return d


# ===========================================================================
# EventAvailabilityDialog: Init
# ===========================================================================


class TestEventAvailabilityDialogInit:
    def test_window_title_uses_event_name(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        assert "Sommerkonzert" in dlg.windowTitle()
        assert dlg.minimumWidth() == 900
        assert dlg.minimumHeight() == 600

    def test_has_table_with_three_columns(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        assert dlg.table.columnCount() == 3
        headers = [
            dlg.table.horizontalHeaderItem(i).text()
            for i in range(dlg.table.columnCount())
        ]
        assert headers == ["Kurzname", "Stimmgruppe", "Status"]

    def test_has_search_and_filters(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        assert dlg.search_box is not None
        assert dlg.voice_filter is not None
        assert dlg.sort_by_combo is not None
        assert dlg.sort_order_combo is not None

    def test_voice_filter_populated(self, qtbot, seeded_availability_db):
        d = _dlg()
        with patch(
            "chormanager.ui.dialogs._event_availability.load_voice_groups",
            return_value=[{"name": "Sopran 1"}, {"name": "Bass 1"}],
        ):
            dlg = d.EventAvailabilityDialog(
                seeded_availability_db, _make_event(seeded_availability_db),
            )
        qtbot.addWidget(dlg)
        # "Alle Stimmgruppen" + 2 voice groups
        assert dlg.voice_filter.count() == 3

    def test_besetzung_label_shown_when_name_given(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(
            seeded_availability_db, _make_event(seeded_availability_db),
            besetzung_name="Sommerbesetzung", besetzung_count=12,
        )
        qtbot.addWidget(dlg)
        # Find any QLabel whose text contains the besetzung name
        labels = dlg.findChildren(QLabel)
        assert any("Sommerbesetzung" in lbl.text() for lbl in labels)


# ===========================================================================
# EventAvailabilityDialog: _load_availability
# ===========================================================================


class TestEventAvailabilityDialogLoad:
    def test_loads_active_singers_only(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # 4 active singers (Egon is excluded because left_year=2023)
        assert dlg.table.rowCount() == 4

    def test_existing_status_preserved(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Find Anna's row (id=s1) and verify her status combo is "yes"
        anna_row = None
        for row in range(dlg.table.rowCount()):
            name_item = dlg.table.item(row, 0)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == "s1":
                anna_row = row
                break
        assert anna_row is not None
        status_combo = dlg.table.cellWidget(anna_row, 2)
        assert status_combo.currentData() == "yes"

    def test_no_existing_status_defaults_to_none(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Carla (s3) has no availability row
        carla_row = None
        for row in range(dlg.table.rowCount()):
            name_item = dlg.table.item(row, 0)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == "s3":
                carla_row = row
                break
        assert carla_row is not None
        status_combo = dlg.table.cellWidget(carla_row, 2)
        assert status_combo.currentData() == "none"

    def test_besetzung_ids_filter_includes_only_listed(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(
            seeded_availability_db, _make_event(seeded_availability_db),
            besetzung_ids=["s1", "s2"],  # only Anna + Bert
        )
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 2

    def test_besetzung_ids_empty_shows_no_rows(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(
            seeded_availability_db, _make_event(seeded_availability_db),
            besetzung_ids=[],
        )
        qtbot.addWidget(dlg)
        assert dlg.table.rowCount() == 0

    def test_search_box_filters_by_short_name(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        dlg.search_box.setText("Carla")
        assert dlg.table.rowCount() == 1

    def test_voice_filter_narrows_table(self, qtbot, seeded_availability_db):
        d = _dlg()
        with patch(
            "chormanager.ui.dialogs._event_availability.load_voice_groups",
            return_value=[{"name": "Sopran 1"}, {"name": "Bass 1"}],
        ):
            dlg = d.EventAvailabilityDialog(
                seeded_availability_db, _make_event(seeded_availability_db),
            )
        qtbot.addWidget(dlg)
        idx = dlg.voice_filter.findData("Bass 1")
        dlg.voice_filter.setCurrentIndex(idx)
        # Only Bert
        assert dlg.table.rowCount() == 1

    def test_sort_by_short_name_ascending(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Default sort is voice_group; switch to short_name
        dlg.sort_by_combo.setCurrentIndex(1)  # "Kurzname"
        names = [
            dlg.table.item(row, 0).text()
            for row in range(dlg.table.rowCount())
        ]
        assert names == sorted(names)

    def test_summary_label_populated(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Anna=yes, Bert=no, Carla/Doris=none
        # Summary should mention 1 verbindlich, 1 Absage, 2 offen
        assert "1" in dlg.summary_label.text()
        assert "verbindlich" in dlg.summary_label.text()
        assert "Absage" in dlg.summary_label.text()


# ===========================================================================
# EventAvailabilityDialog: _save_availability_on_change
# ===========================================================================


class TestEventAvailabilityDialogSaveOnChange:
    def test_save_creates_new_availability_row(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Find Carla (s3) and change her status to "yes"
        from chormanager.domain.repository import AvailabilityRepository
        avail_repo = AvailabilityRepository(seeded_availability_db)
        carla_combo = dlg.status_widgets["s3"][0]
        idx = carla_combo.findData("yes")
        carla_combo.setCurrentIndex(idx)
        # Verify
        avail = avail_repo.get_by_ids("s3", "e1")
        assert avail is not None
        assert avail.status == "yes"

    def test_save_updates_existing_availability(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Anna (s1) is currently "yes" -> change to "conditional"
        anna_combo = dlg.status_widgets["s1"][0]
        idx = anna_combo.findData("conditional")
        anna_combo.setCurrentIndex(idx)
        from chormanager.domain.repository import AvailabilityRepository
        avail_repo = AvailabilityRepository(seeded_availability_db)
        avail = avail_repo.get_by_ids("s1", "e1")
        assert avail.status == "conditional"

    def test_no_save_when_status_unchanged(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Patch avail_repo.update to detect calls
        with patch.object(dlg.avail_repo, "update") as upd:
            anna_combo = dlg.status_widgets["s1"][0]
            # Anna is already "yes"; re-setting same index should not call update
            idx = anna_combo.findData("yes")
            anna_combo.setCurrentIndex(idx)
        upd.assert_not_called()


# ===========================================================================
# EventAvailabilityDialog: accept() persistence
# ===========================================================================


class TestEventAvailabilityDialogAccept:
    def test_accept_persists_dropdown_state(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        # Change Bert (s2) from "no" to "yes" in the widget
        bert_combo = dlg.status_widgets["s2"][0]
        bert_combo.setCurrentIndex(bert_combo.findData("yes"))
        # Click OK
        dlg.accept()
        from chormanager.domain.repository import AvailabilityRepository
        avail_repo = AvailabilityRepository(seeded_availability_db)
        avail = avail_repo.get_by_ids("s2", "e1")
        assert avail.status == "yes"


# ===========================================================================
# EventAvailabilityDialog: Status widget structure
# ===========================================================================


class TestEventAvailabilityDialogStatusWidgets:
    def test_status_widgets_dict_populated(self, qtbot, seeded_availability_db):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        assert len(dlg.status_widgets) == 4
        for sid, (combo, current) in dlg.status_widgets.items():
            assert combo is not None
            # Combo has 6 entries (AVAILABILITY_STATUS)
            assert combo.count() == 6

    def test_each_status_combo_has_all_6_statuses(
        self, qtbot, seeded_availability_db
    ):
        d = _dlg()
        dlg = d.EventAvailabilityDialog(seeded_availability_db, _make_event(seeded_availability_db))
        qtbot.addWidget(dlg)
        codes = []
        for row in range(dlg.table.rowCount()):
            combo = dlg.table.cellWidget(row, 2)
            for i in range(combo.count()):
                codes.append(combo.itemData(i))
        # All 6 availability status codes are present
        assert set(codes) == {"yes", "no", "none", "conditional", "unknown", "maybe"}
