"""Tests for SingerDialog."""

import pytest
from chormanager.data.database import Database
from chormanager.ui.main_window import SingerDialog


@pytest.fixture
def db(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.connect()
    db.create_tables()
    yield db
    db.close()


class TestSingerDialog:
    """Tests for Singer creation/editing dialog."""

    def test_dialog_creates_empty(self, qtbot, db):
        """Dialog opens with empty fields for new singer."""
        dialog = SingerDialog(db=db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Sänger hinzufügen"
        assert "full_name" in dialog.inputs

    def test_dialog_edit_mode(self, qtbot, db):
        """Dialog opens in edit mode with populated fields."""
        from chormanager.domain.models import Singer
        singer = Singer(full_name="Alice", voice_group="Sopran 1", short_name="Ali")
        dialog = SingerDialog(singer=singer, db=db)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Sänger bearbeiten"

    def test_get_data_returns_dict(self, qtbot, db):
        """get_data returns dictionary with expected keys."""
        dialog = SingerDialog(db=db)
        qtbot.addWidget(dialog)
        data = dialog.get_data()
        assert isinstance(data, dict)
        assert "full_name" in data

    def test_get_data_strips_whitespace(self, qtbot, db):
        """get_data strips whitespace from text inputs."""
        dialog = SingerDialog(db=db)
        qtbot.addWidget(dialog)
        dialog.inputs["full_name"].setText("  Alice  ")
        data = dialog.get_data()
        assert data["full_name"] == "Alice"

    def test_get_data_empty_name_returns_none(self, qtbot, db):
        """get_data returns None for empty required fields."""
        dialog = SingerDialog(db=db)
        qtbot.addWidget(dialog)
        dialog.inputs["full_name"].setText("")
        data = dialog.get_data()
        assert data["full_name"] is None

    def test_dialog_has_handled_fields(self, qtbot, db):
        """Dialog creates widgets for all handled field types."""
        dialog = SingerDialog(db=db)
        qtbot.addWidget(dialog)
        from chormanager.config import load_fields
        fields = load_fields()
        handled_types = {"string", "integer", "text", "date", "voice_group", "email", "singer_reference", "uuid"}
        for field in fields:
            if field["type"] in handled_types:
                assert field["name"] in dialog.inputs, f"Missing widget for {field['name']}"
            elif field["type"] == "yearmonth":
                assert f"{field['name']}_month" in dialog.inputs, f"Missing month widget for {field['name']}"
                assert f"{field['name']}_year" in dialog.inputs, f"Missing year widget for {field['name']}"
