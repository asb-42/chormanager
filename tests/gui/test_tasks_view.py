"""GUI tests for the Aufgaben view (tasks_view.py).

Runs headless via QT_QPA_PLATFORM=offscreen (set in conftest).
"""

import pytest

from chormanager.data.database import Database


@pytest.fixture
def db(tmp_path):
    """Create a fresh test database."""
    database = Database(str(tmp_path / "tasks_view.db"))
    database.connect()
    database.create_tables()
    yield database
    database.close()


@pytest.fixture
def view(qtbot, db):
    """Create the TasksView under test."""
    from chormanager.ui.views.tasks_view import TasksView

    widget = TasksView(db)
    qtbot.addWidget(widget)
    widget.refresh()
    return widget


class TestTasksView:
    def test_creates_one_card_per_catalog_task(self, view):
        assert len(view.cards) == 4

    def test_cards_follow_catalog_order(self, view):
        titles = [card.task.title for card in view.cards]
        expected_first = "Eine Aufstellung für einen Auftritt planen"
        assert titles[0] == expected_first

    def test_progress_label_reflects_empty_db(self, view):
        card = view.cards[0]
        assert "0 von 5" in card.progress_label.text()

    def test_progress_updates_after_prerequisites_met(self, view, db):
        from chormanager.domain.repository import (
            BesetzungRepository,
            EventRepository,
            ProjectRepository,
        )

        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Testprojekt")
        project_repo.set_active(project.id)

        event = EventRepository(db).create(
            name="Konzert", date="2026-09-01",
            event_type="konzert", project_id=project.id,
        )
        BesetzungRepository(db).create(
            name="Besetzung", project_id=project.id, singer_ids=[]
        )

        from chormanager.domain.repository import (
            AvailabilityRepository,
            SingerRepository,
        )
        singer = SingerRepository(db).create(
            full_name="Anna Alt", voice_group="Alt 1"
        )
        AvailabilityRepository(db).update(singer.id, event.id, "yes")

        view.refresh()

        # projekt + termin + besetzung + verfuegbarkeit done;
        # final action step stays open.
        assert "4 von 5" in view.cards[0].progress_label.text()

    def test_start_button_emits_task_started(self, qtbot, view):
        card = view.cards[0]
        with qtbot.waitSignal(view.task_started, timeout=2000) as blocker:
            card.start_button.click()
        assert blocker.args == ["aufstellung_planen"]

    def test_refresh_is_safe_repeatedly(self, view):
        view.refresh()
        view.refresh()
        assert len(view.cards) == 4


class TestDarkThemeSupport:
    """The Aufgaben view must respect the app's dark theme.

    Regression: the card stylesheet hardcoded light-theme hex colors
    which override the window-wide dark stylesheet.
    """

    def test_card_stylesheet_uses_palette_roles_not_hex_colors(self, view):
        sheet = view.cards[0].styleSheet()
        assert "palette(base)" in sheet
        assert "#ffffff" not in sheet
        assert "#2c3e50" not in sheet
        assert "#555555" not in sheet

    def test_intro_label_has_no_hardcoded_text_color(self, view):
        intro_sheet = view.intro_label.styleSheet()
        # Only layout hints allowed; text color must come from theme.
        assert "color" not in intro_sheet.lower()

    def test_style_change_event_triggers_refresh(self, view):
        from PyQt6.QtCore import QEvent

        calls = []
        original = view.refresh

        def counting_refresh():
            calls.append(1)
            original()

        view.refresh = counting_refresh  # type: ignore[method-assign]
        view.changeEvent(QEvent(QEvent.Type.StyleChange))

        assert len(calls) == 1
