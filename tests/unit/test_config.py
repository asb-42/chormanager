"""Tests for config loader."""

import pytest
from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestVoiceGroups:
    """Tests for voice group configuration."""

    def test_load_voice_groups(self):
        """Test loading voice groups from YAML."""
        from chormanager.config import load_voice_groups
        
        groups = load_voice_groups()
        assert len(groups) == 8
        assert groups[0]["name"] == "Sopran 1"
        assert groups[0]["short"] == "S1"

    def test_voice_groups_have_required_fields(self):
        """Test that each voice group has required fields."""
        from chormanager.config import load_voice_groups
        
        groups = load_voice_groups()
        for group in groups:
            assert "name" in group
            assert "short" in group
            assert "order" in group

    def test_voice_groups_sorted_by_order(self):
        """Test that voice groups are sorted by order."""
        from chormanager.config import load_voice_groups
        
        groups = load_voice_groups()
        orders = [g["order"] for g in groups]
        assert orders == sorted(orders)


class TestFieldDefinitions:
    """Tests for field definitions."""

    def test_load_fields(self):
        """Test loading field definitions."""
        from chormanager.config import load_fields
        
        fields = load_fields()
        assert len(fields) > 0
        assert any(f["name"] == "full_name" for f in fields)

    def test_required_fields_exist(self):
        """Test that required base fields exist."""
        from chormanager.config import load_fields
        
        field_names = [f["name"] for f in load_fields()]
        assert "full_name" in field_names
        assert "email" in field_names

    def test_field_structure(self):
        """Test that fields have correct structure."""
        from chormanager.config import load_fields
        
        fields = load_fields()
        for field in fields:
            assert "name" in field
            assert "label" in field
            assert "type" in field
            assert "order" in field


class TestAppConfig:
    """Tests for app configuration."""

    def test_load_app_config(self):
        """Test loading app configuration."""
        from chormanager.config import load_app_config
        
        config = load_app_config()
        assert "app" in config
        assert "database" in config
        assert "backup" in config

    def test_backup_settings(self):
        """Test backup settings are loaded."""
        from chormanager.config import load_app_config
        
        config = load_app_config()
        backup = config["backup"]
        assert backup["enabled"] is True
        assert backup["max_backups"] == 10
