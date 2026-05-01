import pytest
import json
import os
import tempfile
from datetime import datetime


class TestMetadataSaving:
    def test_event_date_saved_correctly(self):
        """Test that event_date from dialog is saved in metadata, not from env vars."""
        from chormanager.choraufstellung.storage import FormationStorage
        from chormanager.choraufstellung.singer_model import Singer, VoiceGroup
        
        singers = [
            Singer("Test Singer", VoiceGroup.SOPRAN_1, 170, "singer1"),
        ]
        
        expected_event_date = "2026-06-15"
        expected_event_name = "Test Concert"
        expected_project = "Test Project"
        
        metadata = {
            "project": expected_project,
            "event": expected_event_name,
            "event_date": expected_event_date,
            "event_type": "konzert"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            storage = FormationStorage()
            placed = [(singers[0], 0, 0)]
            
            success = storage.save_formation(
                singers=singers,
                rows=2,
                cols=5,
                filepath=temp_path,
                placed_singers=placed,
                metadata=metadata
            )
            
            assert success is True
            
            with open(temp_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            assert "metadata" in saved_data
            assert saved_data["metadata"]["event_date"] == expected_event_date
            assert saved_data["metadata"]["event"] == expected_event_name
            assert saved_data["metadata"]["project"] == expected_project
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_event_date_not_from_env_var(self):
        """Test that event_date is taken from metadata parameter, not env vars."""
        from chormanager.choraufstellung.storage import FormationStorage
        from chormanager.choraufstellung.singer_model import Singer, VoiceGroup
        
        singers = [
            Singer("Test Singer", VoiceGroup.SOPRAN_1, 170, "singer1"),
        ]
        
        dialog_event_date = "2026-07-20"
        env_event_date = "2026-08-01"
        
        os.environ["CHOR_EVENT_DATE"] = env_event_date
        
        metadata = {
            "project": "Test",
            "event": "Test Event",
            "event_date": dialog_event_date,
            "event_type": "konzert"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            storage = FormationStorage()
            placed = [(singers[0], 0, 0)]
            
            success = storage.save_formation(
                singers=singers,
                rows=2,
                cols=5,
                filepath=temp_path,
                placed_singers=placed,
                metadata=metadata
            )
            
            assert success is True
            
            with open(temp_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            assert saved_data["metadata"]["event_date"] == dialog_event_date
            assert saved_data["metadata"]["event_date"] != env_event_date
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if "CHOR_EVENT_DATE" in os.environ:
                del os.environ["CHOR_EVENT_DATE"]
    
    def test_metadata_preserved_on_reload(self):
        """Test that metadata is preserved when saving and loading."""
        from chormanager.choraufstellung.storage import FormationStorage
        from chormanager.choraufstellung.singer_model import Singer, VoiceGroup
        
        singers = [
            Singer("Singer 1", VoiceGroup.SOPRAN_1, 165, "s1"),
            Singer("Singer 2", VoiceGroup.ALT_1, 170, "s2"),
        ]
        
        original_metadata = {
            "project": "My Project",
            "event": "Summer Concert",
            "event_date": "2026-07-15",
            "event_type": "konzert"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            storage = FormationStorage()
            placed = [(singers[0], 0, 0), (singers[1], 0, 1)]
            
            storage.save_formation(
                singers=singers,
                rows=2,
                cols=5,
                filepath=temp_path,
                placed_singers=placed,
                metadata=original_metadata
            )
            
            loaded_data = storage.load_formation(temp_path)
            
            assert loaded_data is not None
            assert loaded_data["rows"] == 2
            assert loaded_data["cols"] == 5
            assert len(loaded_data["singers"]) == 2
            
            with open(temp_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            assert raw_data["metadata"]["event_date"] == "2026-07-15"
            assert raw_data["metadata"]["event"] == "Summer Concert"
            assert raw_data["metadata"]["project"] == "My Project"
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_filename_matches_event_date(self):
        """Test that filename pattern matches event_date from metadata."""
        from chormanager.choraufstellung.storage import FormationStorage
        from chormanager.choraufstellung.singer_model import Singer, VoiceGroup
        
        event_date = "2026-08-25"
        today = datetime.now().strftime("%Y-%m-%d")
        expected_filename = f"choraufstellung-{event_date}-version-{today}.json"
        
        assert expected_filename == "choraufstellung-2026-08-25-version-" + today + ".json"


class TestMetadataFromEventFile:
    def test_metadata_updated_from_event_file(self):
        """Test that _loaded_metadata is updated when loading from temp event file."""
        import tempfile
        import os
        import json
        from PyQt6.QtWidgets import QApplication
        from chormanager.choraufstellung.main import MainWindow
        
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        
        event_data = {
            "project": "Test Project",
            "event": {
                "id": "evt123",
                "name": "Summer Concert",
                "date": "2026-07-20T19:00:00",
                "event_type": "konzert"
            },
            "singers": [
                {
                    "singer_id": "s1",
                    "name": "Test Singer",
                    "short_name": "T. Singer",
                    "voice_group": "Sopran 1",
                    "height": 170,
                    "affinity": ""
                }
            ],
            "created_at": "2026-05-01T10:00:00"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(event_data, f)
            temp_file = f.name
        
        try:
            os.environ["CHOR_EVENT_DATA"] = temp_file
            os.environ["CHOR_EVENT_DATE"] = "2026-08-01"
            os.environ["CHOR_EVENT_NAME"] = "Wrong Event"
            
            window = MainWindow(chormanager_mode=True)
            
            assert window._loaded_metadata["event_date"] == "2026-07-20"
            assert window._loaded_metadata["event"] == "Summer Concert"
            assert window._loaded_metadata["project"] == "Test Project"
            assert window._loaded_metadata["event_type"] == "konzert"
            
            assert window._loaded_metadata["event_date"] != "2026-08-01"
            assert window._loaded_metadata["event"] != "Wrong Event"
            
            window.close()
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            for key in ["CHOR_EVENT_DATA", "CHOR_EVENT_DATE", "CHOR_EVENT_NAME"]:
                if key in os.environ:
                    del os.environ[key]
    
    def test_metadata_not_from_env_when_event_file_exists(self):
        """Test that env vars are ignored when event file provides metadata."""
        import tempfile
        import os
        import json
        from PyQt6.QtWidgets import QApplication
        from chormanager.choraufstellung.main import MainWindow
        
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        
        event_data = {
            "project": "File Project",
            "event": {
                "id": "evt456",
                "name": "File Concert",
                "date": "2026-09-15T20:00:00",
                "event_type": "probe"
            },
            "singers": [],
            "created_at": "2026-05-01T10:00:00"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(event_data, f)
            temp_file = f.name
        
        try:
            os.environ["CHOR_EVENT_DATA"] = temp_file
            os.environ["CHOR_EVENT_DATE"] = "2026-12-25"
            os.environ["CHOR_EVENT_NAME"] = "Christmas Event"
            os.environ["CHOR_PROJECT"] = "Env Project"
            
            window = MainWindow(chormanager_mode=True)
            
            assert window._loaded_metadata["event_date"] == "2026-09-15"
            assert window._loaded_metadata["event"] == "File Concert"
            assert window._loaded_metadata["project"] == "File Project"
            assert window._loaded_metadata["event_type"] == "probe"
            
            window.close()
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            for key in ["CHOR_EVENT_DATA", "CHOR_EVENT_DATE", "CHOR_EVENT_NAME", "CHOR_PROJECT"]:
                if key in os.environ:
                    del os.environ[key]
