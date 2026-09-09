"""Tests for chor_manager_data_service."""

import json
import os
import sqlite3
import tempfile
import pytest
from singer_model import Singer, VoiceGroup


class TestLoadSingersFromEventDataFile:
    """Tests for load_singers_from_event_data_file()."""

    def test_load_singers_from_event_data_file_valid_json(self, tmp_path):
        """Should load singers from valid JSON file."""
        from services.chor_manager_data_service import load_singers_from_event_data_file

        data = {
            "project": "Test Project",
            "event": {
                "name": "Test Event",
                "date": "2026-06-15",
                "event_type": "konzert"
            },
            "singers": [
                {"name": "Anna", "short_name": "Anna", "voice_group": "Sopran 1", "height": 165, "singer_id": "s1"},
                {"name": "BERT", "short_name": "BERT", "voice_group": "Alt 1", "height": 170, "singer_id": "s2"},
            ]
        }
        filepath = tmp_path / "event_data.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")

        result = load_singers_from_event_data_file(str(filepath))

        assert result is not None
        assert "singers" in result
        assert "metadata" in result
        assert len(result["singers"]) == 2
        assert result["singers"][0].name == "Anna"
        assert result["singers"][0].voice_group == VoiceGroup.SOPRAN_1
        assert result["metadata"]["event"] == "Test Event"

    def test_load_singers_from_event_data_file_missing_file_returns_none(self):
        """Should return None for missing file."""
        from services.chor_manager_data_service import load_singers_from_event_data_file

        result = load_singers_from_event_data_file("/nonexistent/path/file.json")
        assert result is None

    def test_load_singers_from_event_data_file_invalid_json_returns_none(self, tmp_path):
        """Should return None for invalid JSON."""
        from services.chor_manager_data_service import load_singers_from_event_data_file

        filepath = tmp_path / "invalid.json"
        filepath.write_text("{ invalid json }", encoding="utf-8")

        result = load_singers_from_event_data_file(str(filepath))
        assert result is None

    def test_load_singers_from_event_data_file_empty_singers(self, tmp_path):
        """Should handle empty singers list."""
        from services.chor_manager_data_service import load_singers_from_event_data_file

        data = {
            "project": "Test",
            "event": {"name": "Event", "date": "2026-01-01"},
            "singers": []
        }
        filepath = tmp_path / "empty_singers.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")

        result = load_singers_from_event_data_file(str(filepath))

        assert result is not None
        assert len(result["singers"]) == 0


class TestLoadSingersFromDB:
    """Tests for load_singers_from_db()."""

    def _create_test_db(self, tmp_path):
        """Create a test SQLite database with singers table."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE singers (
                id TEXT PRIMARY KEY,
                full_name TEXT,
                short_name TEXT,
                voice_group TEXT,
                height INTEGER,
                affinity_uuid TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO singers (id, full_name, short_name, voice_group, height, affinity_uuid)
            VALUES ('s1', 'Anna Schmidt', 'Anna', 'Sopran 1', 165, '')
        """)
        cursor.execute("""
            INSERT INTO singers (id, full_name, short_name, voice_group, height, affinity_uuid)
            VALUES ('s2', 'BERT Mueller', 'BERT', 'Alt 1', 170, 's1')
        """)
        conn.commit()
        conn.close()
        return str(db_path)

    def test_load_singers_from_db_valid_path(self, tmp_path):
        """Should load singers from valid database."""
        from services.chor_manager_data_service import load_singers_from_db

        db_path = self._create_test_db(tmp_path)
        singers = load_singers_from_db(db_path)

        assert singers is not None
        assert len(singers) == 2
        assert singers[0].name == "Anna"
        assert singers[0].voice_group == VoiceGroup.SOPRAN_1
        assert singers[1].affinity == "s1"

    def test_load_singers_from_db_nonexistent_path_returns_none(self):
        """Should return None for nonexistent database."""
        from services.chor_manager_data_service import load_singers_from_db

        result = load_singers_from_db("/nonexistent/path/db.sqlite")
        assert result is None


class TestParseSingerFromDBRow:
    """Tests for _parse_singer_from_db_row()."""

    def test_parse_singer_from_db_row(self, tmp_path):
        """Should parse singer fields correctly from DB row."""
        from services.chor_manager_data_service import _parse_singer_from_db_row

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE singers (
                id TEXT PRIMARY KEY,
                full_name TEXT,
                short_name TEXT,
                voice_group TEXT,
                height INTEGER,
                affinity_uuid TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO singers (id, full_name, short_name, voice_group, height, affinity_uuid)
            VALUES ('s1', 'Anna Schmidt', 'Anna', 'Sopran 1', 165, 's2')
        """)
        conn.commit()

        row = conn.execute("SELECT * FROM singers WHERE id = 's1'").fetchone()
        singer = _parse_singer_from_db_row(row)
        conn.close()

        assert singer.singer_id == "s1"
        assert singer.name == "Anna"
        assert singer.voice_group == VoiceGroup.SOPRAN_1
        assert singer.height == 165
        assert singer.affinity == "s2"
