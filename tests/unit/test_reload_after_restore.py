# TDD RED: Tests for the database reload after backup-restore.
#
# These tests verify that a central "refresh tab repositories" helper
# leaves the application in a fully consistent state after a restore:
#   * The new Database is connected.
#   * All tabs reference the *new* Database instance (not the closed one).
#   * All repository instances held by tabs point at the new Database,
#     including the ones the original code forgot to refresh
#     (avail_repo, repertoire_repo).
#
# The fix lives in chormanager/ui/main_window.py: a single
# `refresh_tab_repositories(tab, new_db)` helper that re-applies self.db
# AND rebuilds every known repository on the tab. The production
# _reload_after_restore() calls this helper for each tab.
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chormanager.data.database import Database
from chormanager.domain.repository import (
    SingerRepository,
    EventRepository,
    ProjectRepository,
    BesetzungRepository,
    AvailabilityRepository,
    RepertoireRepository,
)
from chormanager.ui.main_window import refresh_tab_repositories


# --- Helper: create a real Database on disk --------------------------------
@pytest.fixture
def db_file(tmp_path):
    p = tmp_path / "chor.db"
    db = Database(str(p))
    db.connect()
    db.create_tables()
    db.close()
    return p


# --- 1. Database lifecycle: close + reopen works ---------------------------
def test_database_can_reconnect_after_close(db_file):
    d1 = Database(str(db_file))
    d1.connect()
    d1.execute(
        "INSERT INTO projects (id, name, created_at, updated_at) "
        "VALUES (?, ?, ?, ?)",
        ("p1", "Test", "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    d1.commit()
    d1.close()

    d2 = Database(str(db_file))
    d2.connect()
    rows = d2.execute("SELECT name FROM projects WHERE id = ?", ("p1",)).fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Test"
    d2.close()


# --- 2. Reconnect after close in a tight loop ------------------------------
def test_database_reconnect_on_same_instance(db_file):
    for i in range(3):
        db = Database(str(db_file))
        db.connect()
        db.execute(
            "INSERT OR REPLACE INTO projects (id, name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (
                f"p{i}",
                f"Project {i}",
                "2024-01-01T00:00:00",
                "2024-01-01T00:00:00",
            ),
        )
        db.commit()
        db.close()

    db = Database(str(db_file))
    db.connect()
    rows = db.execute("SELECT COUNT(*) AS c FROM projects").fetchall()
    assert rows[0]["c"] == 3
    db.close()


# --- 3. Repository reassignment contract ------------------------------------
def test_database_execute_raises_when_not_connected():
    db = Database()
    with pytest.raises(RuntimeError, match="Not connected to database"):
        db.get_connection()


# --- 4. EventsTab: ALL 4 repos must be refreshed (incl. avail_repo) -------
def test_events_tab_all_repos_refreshed(db_file):
    db_old = Database(str(db_file))
    db_old.connect()

    class FakeEventTab:
        """Mimics the real EventsTab's repository attributes."""
        def __init__(self, db):
            self.db = db
            self.event_repo = EventRepository(db)
            self.singer_repo = SingerRepository(db)
            self.avail_repo = AvailabilityRepository(db)
            self.project_repo = ProjectRepository(db)

    tab = FakeEventTab(db_old)
    db_old.close()  # simulate the old connection being gone

    db_new = Database(str(db_file))
    db_new.connect()

    # The fix in action:
    refresh_tab_repositories(tab, db_new)

    assert tab.db is db_new
    assert tab.event_repo.db is db_new
    assert tab.singer_repo.db is db_new
    assert tab.avail_repo.db is db_new   # <- the one the original code forgot
    assert tab.project_repo.db is db_new

    # And a query against the previously-stale avail_repo must not raise
    rows = tab.avail_repo.get_by_event("nonexistent-event")
    assert isinstance(rows, list)

    db_new.close()


# --- 5. BesetzungTab ------------------------------------------------------
def test_besetzung_tab_repos_refreshed(db_file):
    db_old = Database(str(db_file))
    db_old.connect()

    class FakeBesetzungTab:
        def __init__(self, db):
            self.db = db
            self.besetzung_repo = BesetzungRepository(db)
            self.project_repo = ProjectRepository(db)

    tab = FakeBesetzungTab(db_old)
    db_old.close()

    db_new = Database(str(db_file))
    db_new.connect()
    refresh_tab_repositories(tab, db_new)

    assert tab.besetzung_repo.db is db_new
    assert tab.project_repo.db is db_new
    assert isinstance(tab.besetzung_repo.get_all(), list)

    db_new.close()


# --- 6. RepertoireTab -----------------------------------------------------
def test_repertoire_tab_repo_refreshed(db_file):
    db_old = Database(str(db_file))
    db_old.connect()

    class FakeRepertoireTab:
        def __init__(self, db):
            self.db = db
            self.repertoire_repo = RepertoireRepository(db)

    tab = FakeRepertoireTab(db_old)
    db_old.close()

    db_new = Database(str(db_file))
    db_new.connect()
    refresh_tab_repositories(tab, db_new)

    assert tab.repertoire_repo.db is db_new
    assert isinstance(tab.repertoire_repo.get_all(), list)

    db_new.close()


# --- 7. ProjectsTab -------------------------------------------------------
def test_projects_tab_repos_refreshed(db_file):
    db_old = Database(str(db_file))
    db_old.connect()

    class FakeProjectsTab:
        def __init__(self, db):
            self.db = db
            self.project_repo = ProjectRepository(db)
            self.event_repo = EventRepository(db)

    tab = FakeProjectsTab(db_old)
    db_old.close()

    db_new = Database(str(db_file))
    db_new.connect()
    refresh_tab_repositories(tab, db_new)

    assert tab.project_repo.db is db_new
    assert tab.event_repo.db is db_new

    db_new.close()


# --- 8. SingersTab --------------------------------------------------------
def test_singers_tab_repo_refreshed(db_file):
    db_old = Database(str(db_file))
    db_old.connect()

    class FakeSingersTab:
        def __init__(self, db):
            self.db = db
            self.singer_repo = SingerRepository(db)

    tab = FakeSingersTab(db_old)
    db_old.close()

    db_new = Database(str(db_file))
    db_new.connect()
    refresh_tab_repositories(tab, db_new)

    assert tab.singer_repo.db is db_new
    assert isinstance(tab.singer_repo.get_all(), list)

    db_new.close()


# --- 9. Helper is a no-op for tabs that have no repositories --------------
def test_helper_works_on_minimal_object():
    """A tab that has no repository attributes should still get its .db
    attribute updated, without raising."""
    class MinimalTab:
        db = None  # main_window convention: every tab has .db

    db = Database(":memory:")
    db.connect()
    tab = MinimalTab()
    refresh_tab_repositories(tab, db)
    assert tab.db is db
    db.close()
