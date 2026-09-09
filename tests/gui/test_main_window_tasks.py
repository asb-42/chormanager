"""Integration tests: MainWindow lands on the Aufgaben view and starts
the TaskWizard from there."""

import pytest


@pytest.fixture
def main_window(qtbot, tmp_path):
    """Create the real MainWindow against a temporary database."""
    from chormanager.ui.main_window import MainWindow

    window = MainWindow(db_path=str(tmp_path / "integration.db"))
    qtbot.addWidget(window)
    yield window
    window.close()


class TestTasksIntegration:
    def test_landing_view_is_aufgaben(self, main_window):
        assert main_window.content_stack.currentIndex() == 6
        assert main_window.nav_tasks.isChecked()
        assert not main_window.nav_projects.isChecked()

    def test_switching_back_and_forth_works(self, main_window):
        main_window._switch_view(0)
        assert main_window.content_stack.currentIndex() == 0
        main_window._switch_view(6)
        assert main_window.content_stack.currentIndex() == 6

    def test_start_button_opens_task_wizard(self, qtbot, main_window):
        card = main_window.tasks_view.cards[0]
        card.start_button.click()

        from chormanager.ui.dialogs import TaskWizard

        wizards = [
            child
            for child in main_window.findChildren(TaskWizard)
            if child.parent() is main_window or child.isVisible()
        ]
        assert wizards, "TaskWizard wurde nicht geöffnet"
        assert wizards[0].task.id == "aufstellung_planen"
