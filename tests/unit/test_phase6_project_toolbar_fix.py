# TDD PHASE 6: Regression test for the "Set active project" button bug.
#
# Bug: After clicking a project row in the projects table, the context
# toolbar did NOT show the "Als aktives Projekt setzen" action.
#
# Root cause: MainWindow._emit_selection(0) only read
# `projects_tab.current_project` (set programmatically via
# set_current_project), not the table's current row. Other tabs
# (Singers, Besetzung, Events) used `currentRow()` correctly.
#
# This test creates a MainWindow with a seeded project, simulates a
# table selection, and asserts the toolbar updates.

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

import pytest


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
        now = "2026-01-01T00:00:00"
        conn.execute(
            "INSERT INTO projects (id, name, spielzeit, is_active, "
            "created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)",
            ("p1", "Hoffmann OKO", "2025/26", now, now),
        )
        conn.commit()
    finally:
        conn.close()
    yield p


@pytest.fixture
def main_window(qtbot, db_path):
    from chormanager.ui.main_window import MainWindow
    window = MainWindow(db_path=str(db_path))
    qtbot.addWidget(window)
    yield window
    window.close()


def _toolbar_action_labels(window):
    """Return the visible action labels of the context toolbar."""
    from PyQt6.QtWidgets import QToolBar
    toolbars = window.findChildren(QToolBar)
    toolbar = next((t for t in toolbars if t.windowTitle() == "Aktionen"), None)
    assert toolbar is not None, "Context toolbar 'Aktionen' not found"
    return [a.text() for a in toolbar.actions() if a.text()]


class TestProjectSelectionUpdatesToolbar:
    def test_emit_selection_without_row_shows_no_project_actions(
        self, main_window
    ):
        """Without a table row selected, no project-specific actions
        should appear (this was the baseline behavior)."""
        main_window._emit_selection(0)
        labels = _toolbar_action_labels(main_window)
        # "Hinzufuegen" + "Aktualisieren" are always present
        assert "Hinzufügen" in labels
        assert "Aktualisieren" in labels
        # "Als aktives Projekt setzen" must NOT be there yet
        assert "Als aktives Projekt setzen" not in labels

    def test_emit_selection_with_row_shows_project_actions(
        self, main_window
    ):
        """After the user clicks a project row, the context toolbar
        must show project-specific actions (Bearbeiten, Loeschen, etc.)
        — the regression test for the missing-button bug."""
        # Simulate user clicking the first row of the projects table
        main_window.projects_tab.table.selectRow(0)
        # Trigger the selection-changed callback explicitly
        main_window._emit_selection(0)

        labels = _toolbar_action_labels(main_window)
        # The "Als aktives Projekt setzen" action MUST now appear
        assert "Als aktives Projekt setzen" in labels, (
            f"Toolbar missing 'Als aktives Projekt setzen'. "
            f"Got: {labels}"
        )
        # And so should the other selection-dependent actions
        assert "Bearbeiten" in labels
        assert "Duplizieren" in labels
        assert "Löschen" in labels

    def test_emit_selection_for_projects_uses_table_row(
        self, main_window
    ):
        """When the table has a selected row, the selection argument
        must be the corresponding Project instance (not None)."""
        main_window.projects_tab.table.selectRow(0)
        main_window._emit_selection(0)
        # Internal state: the toolbar actions should now reflect
        # a non-None selection. We can verify by checking that the
        # selection-dependent actions were added.
        labels = _toolbar_action_labels(main_window)
        assert "Als aktives Projekt setzen" in labels
