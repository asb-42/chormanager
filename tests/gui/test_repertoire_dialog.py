"""Tests for RepertoireDialog."""

import pytest
from chormanager.data.database import Database
from chormanager.ui.dialogs import RepertoireDialog
from chormanager.domain.repository import ProjectRepository, RepertoireRepository


@pytest.fixture
def db(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.create_tables()
    yield db
    db.close()


class TestRepertoireDialog:
    """Tests for repertoire creation/editing dialog."""

    def test_dialog_creates_new(self, qtbot, db):
        """Dialog opens for new repertoire entry."""
        dialog = RepertoireDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Neues Repertoire"

    def test_dialog_edit_mode(self, qtbot, db):
        """Dialog opens in edit mode."""
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Project 1")
        repo = RepertoireRepository(db)
        entry = repo.create(composer="Mozart", title="Requiem", project_id=project.id)
        dialog = RepertoireDialog(db, repertoire=entry)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Repertoire bearbeiten"

    def test_dialog_populates_fields(self, qtbot, db):
        """Dialog populates fields from existing entry."""
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Project 1")
        repo = RepertoireRepository(db)
        entry = repo.create(
            composer="Mozart", title="Requiem",
            dates="1756-1791", country="Österreich",
            publisher="Breitkopf", arrangement="Gemischter Chor",
            location="Archiv", project_id=project.id
        )
        dialog = RepertoireDialog(db, repertoire=entry)
        qtbot.addWidget(dialog)
        assert dialog.composer_input.text() == "Mozart"
        assert dialog.title_input.text() == "Requiem"
        assert dialog.dates_input.text() == "1756-1791"
        assert dialog.country_input.text() == "Österreich"

    def test_dialog_has_project_combo(self, qtbot, db):
        """Dialog has project selection combo box."""
        dialog = RepertoireDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.program_combo.count() >= 1  # At least the empty item

    def test_dialog_with_project(self, qtbot, db):
        """Dialog loads projects into combo box."""
        project_repo = ProjectRepository(db)
        project_repo.create(name="Project 1")
        project_repo.create(name="Project 2")
        dialog = RepertoireDialog(db)
        qtbot.addWidget(dialog)
        assert dialog.program_combo.count() == 3  # 2 projects + empty

    def test_on_accept_empty_title_no_save(self, qtbot, db):
        """Accept with empty title does not save."""
        dialog = RepertoireDialog(db)
        qtbot.addWidget(dialog)
        dialog.title_input.setText("")
        repo = RepertoireRepository(db)
        count_before = len(repo.get_all())
        # Mock QMessageBox to prevent blocking
        from unittest.mock import patch
        with patch("chormanager.ui.dialogs._repertoire.QMessageBox"):
            dialog._on_accept()
        count_after = len(repo.get_all())
        assert count_after == count_before

    def test_on_accept_with_title(self, qtbot, db):
        """Accept creates repertoire when title is provided."""
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Project 1")
        dialog = RepertoireDialog(db)
        qtbot.addWidget(dialog)
        dialog.composer_input.setText("Bach")
        dialog.title_input.setText("Mass in B Minor")
        dialog.program_combo.setCurrentIndex(1)  # Select the project
        dialog._on_accept()

        repo = RepertoireRepository(db)
        entries = repo.get_all()
        assert len(entries) == 1
        assert entries[0].composer == "Bach"
        assert entries[0].title == "Mass in B Minor"

    def test_on_accept_updates_existing(self, qtbot, db):
        """Accept updates existing repertoire entry."""
        project_repo = ProjectRepository(db)
        project = project_repo.create(name="Project 1")
        repo = RepertoireRepository(db)
        entry = repo.create(composer="Old", title="Old Title", project_id=project.id)

        dialog = RepertoireDialog(db, repertoire=entry)
        qtbot.addWidget(dialog)
        dialog.title_input.setText("New Title")
        dialog._on_accept()

        updated = repo.get_by_id(entry.id)
        assert updated.title == "New Title"
