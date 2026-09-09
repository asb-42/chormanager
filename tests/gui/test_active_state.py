"""GUI regression tests: restoring/keeping the "Aktiv" state stays safe.

Pinned user-visible regressions (2026-09 audit):

Bug 1 (crash class): ``EventsTab._restore_active_event`` raised
``NameError`` (unbound local ``event``) whenever no
``last_active_event_id`` was stored while the events table had rows —
e.g. first launch with existing data, or after the referenced event
was deleted.

Bug 2 (stale ids): deleting a project/event/besetzung never cleared
the matching ``last_active_*_id`` config key. The next start silently
dropped the restore (``get_by_id`` -> None), so the info bar showed
"Keines" — the user-reported "Aktiv-Parameter verschwinden manchmal".

Bug 4 (stale label): the besetzung info label is only ever written by
the ``active_besetzung_changed`` signal handler — ``_update_info_labels``
ignored it, so after a project switch a besetzung from another project
kept being displayed.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def db(tmp_path):
    from chormanager.data.database import Database

    database = Database(str(tmp_path / "active_state.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


@pytest.fixture
def seeded(db):
    """Seed one project, one event and one besetzung; return ids."""
    from chormanager.domain.repository import (
        BesetzungRepository,
        EventRepository,
        ProjectRepository,
    )

    project = ProjectRepository(db).create(name="Hoffmann 2026")
    event = EventRepository(db).create(
        name="Konzert", date="2026-09-01",
        event_type="konzert", project_id=project.id,
    )
    besetzung = BesetzungRepository(db).create(
        name="Konzertbesetzung", project_id=project.id, singer_ids=[]
    )
    return project, event, besetzung


class TestRestoreActiveEventSafe:
    """Bug 1: _restore_active_event must never raise NameError."""

    def test_no_stored_id_with_populated_table_does_not_crash(
        self, qtbot, db, seeded, monkeypatch
    ):
        from chormanager.ui.views.events_tab import EventsTab

        monkeypatch.setattr(
            "chormanager.ui.views.events_tab.get_last_active_event_id",
            lambda: None,
        )
        tab = EventsTab(db)
        qtbot.addWidget(tab)
        try:
            tab._restore_active_event()  # must not raise
        finally:
            tab.deleteLater()

    def test_stored_id_of_deleted_event_does_not_crash(
        self, qtbot, db, seeded, monkeypatch
    ):
        from chormanager.domain.repository import EventRepository
        from chormanager.ui.views.events_tab import EventsTab

        _, event, _ = seeded
        EventRepository(db).delete(event.id)

        monkeypatch.setattr(
            "chormanager.ui.views.events_tab.get_last_active_event_id",
            lambda: event.id,
        )
        tab = EventsTab(db)
        qtbot.addWidget(tab)
        try:
            tab._restore_active_event()  # must not raise
        finally:
            tab.deleteLater()

    def test_valid_id_selects_row(self, qtbot, db, seeded, monkeypatch):
        from chormanager.ui.views.events_tab import EventsTab

        _, event, _ = seeded
        monkeypatch.setattr(
            "chormanager.ui.views.events_tab.get_last_active_event_id",
            lambda: event.id,
        )
        tab = EventsTab(db)
        qtbot.addWidget(tab)
        try:
            tab._restore_active_event()
            assert tab.table.currentRow() >= 0
            item = tab.table.item(tab.table.currentRow(), 0)
            assert item is not None
            assert item.data(0x0100) == event.id  # Qt.ItemDataRole.UserRole
        finally:
            tab.deleteLater()


class TestDeleteClearsActiveIds:
    """Bug 2: deleting an entity clears its stale last_active_* id."""

    def test_delete_selected_event_clears_last_active_event_id(
        self, qtbot, db, seeded, monkeypatch
    ):
        from chormanager.ui.views import events_tab as et_module
        from chormanager.ui.views.events_tab import EventsTab

        _, event, _ = seeded

        stored = {"value": event.id}
        monkeypatch.setattr(
            "chormanager.ui.views.events_tab.get_last_active_event_id",
            lambda: stored["value"],
        )
        monkeypatch.setattr(
            et_module, "set_last_active_event_id",
            lambda new_id: stored.__setitem__("value", new_id),
        )

        tab = EventsTab(db)
        qtbot.addWidget(tab)
        # Selektiere die Zeile des Events, dann löschen (Dialog stubben).
        for row in range(tab.table.rowCount()):
            item = tab.table.item(row, 0)
            if item and item.data(0x0100) == event.id:
                tab.table.selectRow(row)
                break

        from unittest.mock import patch
        with patch(
            "PyQt6.QtWidgets.QMessageBox"
        ) as box:
            box.question.return_value = box.StandardButton.Yes
            tab._delete_event()

        assert stored["value"] is None, (
            "Deleting the referenced event must clear "
            "last_active_event_id, otherwise the restore on the next "
            "start silently drops it ('Aktiv-Parameter verschwinden')."
        )
        tab.deleteLater()

    def test_delete_besetzung_clears_last_active_besetzung_id(
        self, qtbot, db, seeded, monkeypatch
    ):
        from unittest.mock import patch

        from chormanager.ui.views import besetzung_tab as bt_module
        from chormanager.ui.views.besetzung_tab import BesetzungTab

        _, _, besetzung = seeded

        stored = {"value": besetzung.id}
        monkeypatch.setattr(
            bt_module, "get_last_active_besetzung_id",
            lambda: stored["value"],
        )
        monkeypatch.setattr(
            bt_module, "set_last_active_besetzung_id",
            lambda new_id: stored.__setitem__("value", new_id),
        )

        tab = BesetzungTab(db)
        qtbot.addWidget(tab)
        for row in range(tab.table.rowCount()):
            item = tab.table.item(row, 0)
            if item and item.text() == besetzung.name:
                tab.table.selectRow(row)
                break

        with patch.object(bt_module, "QMessageBox") as box:
            from PyQt6.QtWidgets import QMessageBox as _RealBox

            box.StandardButton = _RealBox.StandardButton
            box.question.return_value = _RealBox.StandardButton.Yes
            tab._delete_besetzung()

        assert stored["value"] is None, (
            "Deleting the referenced besetzung must clear "
            "last_active_besetzung_id."
        )
        tab.deleteLater()

    def test_delete_project_clears_last_active_project_id(
        self, qtbot, db, seeded, monkeypatch
    ):
        from unittest.mock import patch

        from chormanager.ui.views import projects_tab as pt_module
        from chormanager.ui.views.projects_tab import ProjectsTab

        project, _, _ = seeded

        stored = {"value": project.id}
        monkeypatch.setattr(
            pt_module, "get_last_active_project_id",
            lambda: stored["value"],
        )
        monkeypatch.setattr(
            pt_module, "set_last_active_project_id",
            lambda new_id: stored.__setitem__("value", new_id),
        )

        tab = ProjectsTab(db)
        qtbot.addWidget(tab)
        for row in range(tab.table.rowCount()):
            item = tab.table.item(row, 1)
            if item and item.text() == project.name:
                tab.table.selectRow(row)
                break

        with patch(
            "PyQt6.QtWidgets.QMessageBox"
        ) as box:
            box.question.return_value = box.StandardButton.Yes
            tab._delete_project()

        assert stored["value"] is None, (
            "Deleting the active project must clear "
            "last_active_project_id."
        )
        assert tab.current_project is None, (
            "current_project must not keep referencing the deleted "
            "project (bug 3)."
        )
        tab.deleteLater()


class TestBesetzungInfoLabel:
    """Bug 4: the besetzung label must be part of _update_info_labels.

    Before the fix the label was ONLY written by the
    ``active_besetzung_changed`` signal handler. After a restart or a
    project switch ``_update_info_labels`` never refreshed it — a
    besetzung of ANOTHER project kept being displayed (stale) or the
    label stayed "Keine" although a valid besetzung was configured.
    """

    def test_update_info_labels_shows_saved_besetzung(
        self, qtbot, tmp_path, monkeypatch
    ):
        from chormanager.ui.main_window import MainWindow

        db_path = str(tmp_path / "label.db")
        window = MainWindow(db_path=db_path)
        qtbot.addWidget(window)

        from chormanager.domain.repository import (
            BesetzungRepository,
            ProjectRepository,
        )
        project = ProjectRepository(window.db).create(name="Hoffmann")
        besetzung = BesetzungRepository(window.db).create(
            name="Konzertbesetzung", project_id=project.id, singer_ids=[]
        )

        monkeypatch.setattr(
            "chormanager.config.get_last_active_besetzung_id",
            lambda: besetzung.id,
        )
        try:
            window._update_info_labels()
            label_text = window.besetzung_info_label.text()
            assert besetzung.name in label_text, (
                "_update_info_labels must show the saved active "
                "besetzung, not a stale 'Keine'."
            )
            assert window.besetzung_info_label.isVisible() or not window.besetzung_info_label.isHidden()
        finally:
            window.close()

    def test_update_info_labels_shows_keine_without_besetzung(
        self, qtbot, tmp_path, monkeypatch
    ):
        from chormanager.ui.main_window import MainWindow

        monkeypatch.setattr(
            "chormanager.config.get_last_active_besetzung_id",
            lambda: None,
        )
        db_path = str(tmp_path / "label2.db")
        window = MainWindow(db_path=db_path)
        qtbot.addWidget(window)
        try:
            window._update_info_labels()
            assert window.besetzung_info_label.text() == "Keine"
        finally:
            window.close()

    def test_update_info_labels_handles_deleted_besetzung(
        self, qtbot, tmp_path, seeded, monkeypatch
    ):
        """A saved id that no longer resolves shows 'Keine' (bug 2 face)."""
        from chormanager.ui.main_window import MainWindow

        monkeypatch.setattr(
            "chormanager.config.get_last_active_besetzung_id",
            lambda: "does-not-exist",
        )
        db_path = str(tmp_path / "label3.db")
        window = MainWindow(db_path=db_path)
        qtbot.addWidget(window)
        try:
            window._update_info_labels()
            assert window.besetzung_info_label.text() == "Keine"
        finally:
            window.close()

    def test_project_switch_invalidates_foreign_besetzung(
        self, qtbot, tmp_path, monkeypatch
    ):
        """Switching the project must not keep another project's besetzung.

        Bug 4 (stale label): the besetzung label previously only
        changed on the ``active_besetzung_changed`` signal. A project
        switch left a besetzung of the PREVIOUS project displayed.
        """
        from chormanager.ui.main_window import MainWindow

        db_path = str(tmp_path / "switch.db")
        window = MainWindow(db_path=db_path)
        qtbot.addWidget(window)

        from chormanager.domain.repository import (
            BesetzungRepository,
            ProjectRepository,
        )
        repo = ProjectRepository(window.db)
        project_a = repo.create(name="Projekt A")
        project_b = repo.create(name="Projekt B")
        besetzung_a = BesetzungRepository(window.db).create(
            name="Besetzung A", project_id=project_a.id, singer_ids=[]
        )

        monkeypatch.setattr(
            "chormanager.config.get_last_active_besetzung_id",
            lambda: besetzung_a.id,
        )

        # User switches to project B.
        window.projects_tab.set_current_project(project_b)

        window._update_info_labels()
        assert window.besetzung_info_label.text() == "Keine", (
            "A besetzung of another project must not survive a "
            "project switch in the info bar."
        )
        window.close()
