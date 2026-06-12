# TDD PHASE 7: Regression test for the "Last active project" restoration.
#
# User-reported behavior (2026-06-12, after M-1 Schritt 5):
#   "Letztes aktives Projekt: wird nach App-Neustart wiederhergestellt?
#    sollte so sein, war aber auch schon bei den vorigen Refactoring-Schritten
#    immer ungesetzt (also nach Neustart: Aktives Projekt: Keines).
#    Sollte jetzt gefixed werden."
#
# Contract that must hold on MainWindow startup:
#   1. If `data/state.json` contains a `last_active_project_id` AND
#      that id still exists in the database, then
#        - ``projects_tab.current_project`` must be that Project
#        - ``project_info_label.text()`` must show its name (not "Keines")
#        - ``main_window.current_project`` must be the same Project
#   2. If the saved id does NOT exist in the database, the app must
#      gracefully fall back to "Keines" (no crash, no exception).
#
# The test does NOT rely on the user's real data/state.json; it
# monkey-patches ``get_state_file`` to point at a temp file and uses
# the auto-generated project id (ProjectRepository.create generates a
# UUID), so saved id and DB id match exactly.

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def seeded_db(tmp_path) -> Iterator[tuple[Path, str]]:
    """Create a real SQLite DB via Database.create_tables() and seed
    one project. Yields (db_path, project_id) so the test can refer to
    the real (auto-generated) project id."""
    from chormanager.data.database import Database
    from chormanager.domain.repository import ProjectRepository

    p = tmp_path / "chor.db"
    db = Database(str(p))
    db.connect()
    db.create_tables()
    repo = ProjectRepository(db)
    project = repo.create(name="Hoffmann OKO", spielzeit="2025/26")
    db.close()
    yield p, project.id


@pytest.fixture
def isolated_state(seeded_db, monkeypatch):
    """Point config.get_state_file() at a temp state file and seed it
    with the real project_id from seeded_db."""
    from chormanager import config

    db_path, project_id = seeded_db
    state_file = db_path.parent / "state.json"
    monkeypatch.setattr(config, "get_state_file", lambda: state_file)
    config.load_voice_groups.cache_clear()
    config.load_fields.cache_clear()
    config.load_app_config.cache_clear()
    config.set_last_active_project_id(project_id)
    return state_file, project_id


@pytest.fixture
def main_window(qtbot, seeded_db, isolated_state):
    db_path, _project_id = seeded_db
    from chormanager.ui.main_window import MainWindow
    window = MainWindow(db_path=str(db_path))
    qtbot.addWidget(window)
    yield window
    window.close()


class TestLastActiveProjectRestored:
    def test_projects_tab_current_project_is_set(
        self, main_window, isolated_state
    ):
        """ProjectsTab.current_project must equal the saved project."""
        _state_file, project_id = isolated_state
        assert main_window.projects_tab.current_project is not None
        assert main_window.projects_tab.current_project.id == project_id
        assert main_window.projects_tab.current_project.name == "Hoffmann OKO"

    def test_current_project_attribute_is_set(
        self, main_window, isolated_state
    ):
        """MainWindow.current_project must equal the saved project."""
        _state_file, project_id = isolated_state
        assert main_window.current_project is not None, (
            "main_window.current_project is None after restore"
        )
        assert main_window.current_project.id == project_id

    def test_info_label_shows_project_name(self, main_window):
        """The info bar must show the project name, not 'Keines'."""
        text = main_window.project_info_label.text()
        assert text == "Hoffmann OKO", (
            f"project_info_label was {text!r}, expected 'Hoffmann OKO'"
        )


class TestMissingSavedProjectDoesNotCrash:
    def test_missing_id_falls_back_to_keines(
        self, qtbot, seeded_db, monkeypatch
    ):
        """If the saved id no longer exists, app must start gracefully."""
        from chormanager import config

        db_path, _project_id = seeded_db
        state_file = db_path.parent / "state.json"
        monkeypatch.setattr(config, "get_state_file", lambda: state_file)
        config.load_voice_groups.cache_clear()
        config.load_fields.cache_clear()
        config.load_app_config.cache_clear()
        # Saved id points to a project that does NOT exist in the DB
        config.set_last_active_project_id("does-not-exist")

        from chormanager.ui.main_window import MainWindow
        window = MainWindow(db_path=str(db_path))
        qtbot.addWidget(window)
        try:
            # No current project on the projects tab
            assert window.projects_tab.current_project is None
            # The info bar must say "Keines" (not crash, not "None")
            assert window.project_info_label.text() == "Keines"
            # MainWindow.current_project must exist and be None.
            # It is initialised in MainWindow._create_central_widget
            # so that callers (e.g. line 1042 of main_window.py that
            # reads self.current_project.id) can rely on hasattr and
            # never hit an AttributeError when no project is active.
            assert hasattr(window, "current_project")
            assert window.current_project is None
        finally:
            window.close()
