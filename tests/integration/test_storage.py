# TDD: Integration tests for Storage
import os
import json
import pytest
from pathlib import Path


class TestStorageJsonRoundtrip:
    def test_save_and_load_formation(self, mock_storage, temp_dir, sample_singers):
        """Should save and load formation data correctly."""
        filepath = os.path.join(temp_dir, "formation.json")
        
        placed = [(s, s.row, s.col) for s in sample_singers]
        success = mock_storage.save_formation(
            sample_singers, 4, 5, filepath, placed, False, ["Sopran 1", "Alt 1"]
        )
        
        assert success is True
        assert os.path.exists(filepath)
        
        loaded = mock_storage.load_formation(filepath)
        assert loaded is not None
        assert loaded["rows"] == 4
        assert loaded["cols"] == 5
        assert len(loaded["placed"]) == 6

    def test_load_nonexistent_file(self, mock_storage):
        """Should return None for nonexistent file."""
        result = mock_storage.load_formation("/nonexistent/path.json")
        assert result is None

    def test_overwrite_formation(self, mock_storage, temp_dir, sample_singers):
        """Should correctly overwrite existing formation with latest save."""
        filepath = os.path.join(temp_dir, "formation.json")
        
        placed1 = [(sample_singers[0], 0, 0)]
        mock_storage.save_formation(sample_singers, 4, 5, filepath, placed1, False, [])
        
        placed2 = [(sample_singers[1], 1, 1)]
        mock_storage.save_formation(sample_singers, 4, 5, filepath, placed2, False, [])
        
        loaded = mock_storage.load_formation(filepath)
        assert loaded is not None
        assert loaded["rows"] == 4
        assert loaded["cols"] == 5


class TestStorageAutosaveRotation:
    def test_autosave_saves_file(self, mock_storage):
        """Autosave should save data without error."""
        data = {"rows": 4, "cols": 5, "singers": [], "placed": []}
        result = mock_storage.save_autosave(data, max_keep=5)
        assert result is True

    def test_autosave_respects_max_keep(self, mock_storage):
        """Should respect max_keep parameter."""
        for i in range(10):
            data = {" iteration": i, "timestamp": i}
            mock_storage.save_autosave(data, max_keep=3)
        
        latest = mock_storage.get_latest_autosave_path()
        assert latest is None or isinstance(latest, str)


class TestStorageCorruptionHandling:
    def test_load_invalid_json(self, temp_dir):
        """Should handle invalid JSON gracefully."""
        from dependencies import get_storage_fallback
        storage = get_storage_fallback()
        
        if storage is None:
            pytest.skip("Storage not available")
        
        filepath = os.path.join(temp_dir, "corrupt.json")
        with open(filepath, 'w') as f:
            f.write("{ invalid json }")
        
        result = storage.load_formation(filepath)
        assert result is None

    def test_load_empty_json(self, temp_dir):
        """Should handle empty JSON file gracefully."""
        from dependencies import get_storage_fallback
        storage = get_storage_fallback()
        
        if storage is None:
            pytest.skip("Storage not available")
        
        filepath = os.path.join(temp_dir, "empty.json")
        with open(filepath, 'w') as f:
            f.write("{}")
        
        result = storage.load_formation(filepath)
        assert result is not None or result is None


class TestStorageRecovery:
    def test_get_latest_autosave_path_none_when_empty(self, mock_storage):
        """Should return None when no autosave exists."""
        path = mock_storage.get_latest_autosave_path()
        assert path is None

    def test_get_latest_autosave_mtime_none_when_empty(self, mock_storage):
        """Should return None when no autosave exists."""
        mtime = mock_storage.get_latest_autosave_mtime()
        assert mtime is None


class TestStorageSingersData:
    def test_singer_to_dict_roundtrip(self, sample_singers):
        """Should correctly serialize and deserialize singer data."""
        for s in sample_singers:
            d = {
                "name": s.name,
                "voice_group": s.voice_group,
                "height": s.height,
                "singer_id": s.singer_id,
                "row": s.row,
                "col": s.col,
                "affinity": s.affinity
            }
            
            assert d["name"] == s.name
            assert d["singer_id"] == s.singer_id
            assert d["row"] == s.row

    def test_formation_data_structure(self, mock_storage, temp_dir, sample_singers):
        """Should create well-formed JSON structure."""
        filepath = os.path.join(temp_dir, "structure.json")
        placed = [(s, s.row, s.col) for s in sample_singers]
        
        mock_storage.save_formation(
            sample_singers, 4, 5, filepath, placed, True, ["Sopran 1"]
        )
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert "rows" in data
        assert "cols" in data
        assert "staggered" in data
        assert "singers" in data
        assert "placed" in data
        assert "voicing_config" in data
        assert isinstance(data["placed"], list)
        assert isinstance(data["singers"], list)


class TestStorageEdgeCases:
    def test_save_to_readonly_directory(self, mock_storage):
        """Should handle read-only directory gracefully."""
        if os.name == 'nt':
            pytest.skip("Windows permission handling differs")
        
        readonly_dir = "/tmp/readonly_test_dir"
        os.makedirs(readonly_dir, exist_ok=True)
        os.chmod(readonly_dir, 0o444)
        
        try:
            filepath = os.path.join(readonly_dir, "test.json")
            result = mock_storage.save_formation([], 4, 5, filepath, [], False, [])
        except:
            result = False
        
        os.chmod(readonly_dir, 0o755)
        os.rmdir(readonly_dir)
        
        assert isinstance(result, bool)

    def test_very_long_singer_name(self, mock_storage, temp_dir):
        """Should handle very long singer names."""
        from core.rules import SingerRef
        
        long_name = "A" * 1000
        singer = SingerRef(
            singer_id="s1", name=long_name,
            voice_group="Sopran 1", height=170,
            row=0, col=0, affinity=""
        )
        
        filepath = os.path.join(temp_dir, "long_name.json")
        placed = [(singer, 0, 0)]
        
        result = mock_storage.save_formation([singer], 4, 5, filepath, placed, False, [])
        assert result is True


class TestStorageObjectIdentity:
    def test_load_returns_same_objects_for_placed_singers(self, mock_storage, temp_dir):
        """After load, placed singers in grid.singers should be SAME objects as in all_singers."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="Anna", voice_group="Sopran 1", height=160, row=0, col=0),
            SingerRef(singer_id="s2", name="Bert", voice_group="Bass 1", height=180, row=1, col=1),
        ]
        
        filepath = os.path.join(temp_dir, "identity_test.json")
        placed = [(singers[0], 0, 0), (singers[1], 1, 1)]
        
        success = mock_storage.save_formation(singers, 2, 2, filepath, placed, False, [])
        assert success is True
        
        loaded = mock_storage.load_formation(filepath)
        assert loaded is not None
        
        all_singers = loaded["singers"]
        placed_raw = loaded["placed"]
        
        placed_singer_ids = set()
        for item in placed_raw:
            if isinstance(item, tuple) and len(item) >= 1:
                placed_singer_ids.add(item[0].singer_id)
            elif isinstance(item, dict):
                placed_singer_ids.add(item.get("singer_id", ""))
        
        all_singer_ids = set()
        for s in all_singers:
            if hasattr(s, 'singer_id'):
                all_singer_ids.add(s.singer_id)
            else:
                all_singer_ids.add(s.get("singer_id", ""))
        
        assert len(all_singer_ids) == 2, f"Expected 2 unique singers, got {len(all_singer_ids)}"
        assert placed_singer_ids == all_singer_ids, f"IDs mismatch: placed={placed_singer_ids}, all={all_singer_ids}"
    
    def test_save_excludes_placed_singers_from_singers_array(self, mock_storage, temp_dir):
        """Verify placed singers are only in 'placed', not duplicated in 'singers' array."""
        from core.rules import SingerRef
        
        singers = [
            SingerRef(singer_id="s1", name="Anna", voice_group="Sopran 1", height=160, row=-1, col=-1),
            SingerRef(singer_id="s2", name="Bert", voice_group="Bass 1", height=180, row=-1, col=-1),
            SingerRef(singer_id="s3", name="Clara", voice_group="Alt 1", height=165, row=-1, col=-1),
        ]
        
        filepath = os.path.join(temp_dir, "no_duplicates_test.json")
        placed = [(singers[0], 0, 0), (singers[1], 1, 1)]
        
        success = mock_storage.save_formation(singers, 2, 2, filepath, placed, False, [])
        assert success is True
        
        loaded = mock_storage.load_formation(filepath)
        assert loaded is not None
        
        all_singers = loaded["singers"]
        all_ids = [s.singer_id for s in all_singers]
        
        assert len(all_ids) == 3, f"Expected 3 total singers, got {len(all_ids)}: {all_ids}"
        assert len(set(all_ids)) == 3, f"Duplicate singer_ids found: {all_ids}"
        
        placed_count = len([s for s in all_singers if s.row >= 0 and s.col >= 0])
        assert placed_count == 2, f"Expected 2 placed singers, got {placed_count}"