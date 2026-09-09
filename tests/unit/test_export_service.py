"""Unit tests for ExportService."""

import pytest
from chormanager.core.export_service import ExportService


class TestExportService:
    """Tests for ExportService."""

    @pytest.fixture
    def service(self):
        return ExportService()

    def test_export_to_csv(self, service):
        data = [
            {"name": "Alice", "voice_group": "Sopran 1"},
            {"name": "Bob", "voice_group": "Bass 1"},
        ]
        fields = ["name", "voice_group"]
        
        result = service.export_to_csv(data, fields)
        
        assert "name,voice_group" in result
        assert "Alice,Sopran 1" in result
        assert "Bob,Bass 1" in result

    def test_export_to_csv_empty(self, service):
        result = service.export_to_csv([], ["name"])
        assert result == ""

    def test_export_to_libreoffice_calc(self, service):
        data = [{"name": "Alice"}]
        fields = ["name"]
        
        result = service.export_to_libreoffice_calc(data, fields)
        
        assert "name" in result
        assert "Alice" in result

    def test_export_to_libreoffice_writer(self, service):
        data = [{"name": "Alice", "vg": "Sopran"}]
        fields = ["name", "vg"]
        
        result = service.export_to_libreoffice_writer(data, fields)
        
        assert "<html>" in result
        assert "<table" in result
        assert "Alice" in result

    def test_get_export_data(self, service):
        class MockItem:
            def __init__(self, name, voice_group):
                self.name = name
                self.voice_group = voice_group
        
        items = [MockItem("Alice", "Sopran 1"), MockItem("Bob", "Bass 1")]
        fields = ["name", "voice_group"]
        
        result = service.get_export_data(items, fields)
        
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["voice_group"] == "Sopran 1"
        assert result[1]["name"] == "Bob"
