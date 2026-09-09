"""Tests for PDFExporter."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from chormanager.choraufstellung.pdf_export import PDFExporter


class MockSinger:
    """Mock singer for PDF tests."""

    def __init__(self, name, voice_group, row=-1, col=-1, height=170):
        self.name = name
        self.voice_group = voice_group
        self.row = row
        self.col = col
        self.height = height


class MockVoiceGroup:
    """Mock voice group enum."""

    def __init__(self, value):
        self.value = value


class TestPDFExporter:
    """Tests for PDF export functionality."""

    @pytest.fixture
    def exporter(self):
        return PDFExporter()

    @pytest.fixture
    def sample_singers(self):
        return [
            MockSinger("Alice", MockVoiceGroup("Sopran 1"), row=0, col=0),
            MockSinger("Bob", MockVoiceGroup("Bass 1"), row=0, col=1),
            MockSinger("Carol", MockVoiceGroup("Alt 1"), row=1, col=0),
            MockSinger("Dave", MockVoiceGroup("Tenor 1"), row=1, col=1),
        ]

    def test_export_formation_creates_file(self, exporter, sample_singers, tmp_path):
        """Export creates a PDF file."""
        output = tmp_path / "test.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output)
        )
        assert result is True
        assert output.exists()
        assert output.stat().st_size > 0

    def test_export_formation_empty_grid(self, exporter, tmp_path):
        """Export with no singers creates valid PDF."""
        output = tmp_path / "empty.pdf"
        result = exporter.export_formation(
            [], rows=2, cols=2, filename=str(output)
        )
        assert result is True
        assert output.exists()

    def test_export_formation_landscape(self, exporter, sample_singers, tmp_path):
        """Export in landscape orientation."""
        output = tmp_path / "landscape.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            orientation="landscape"
        )
        assert result is True

    def test_export_formation_portrait(self, exporter, sample_singers, tmp_path):
        """Export in portrait orientation."""
        output = tmp_path / "portrait.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            orientation="portrait"
        )
        assert result is True

    def test_export_formation_bw_mode(self, exporter, sample_singers, tmp_path):
        """Export in black and white mode."""
        output = tmp_path / "bw.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            color_mode="bw"
        )
        assert result is True

    def test_export_formation_color_mode(self, exporter, sample_singers, tmp_path):
        """Export in color mode."""
        output = tmp_path / "color.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            color_mode="color"
        )
        assert result is True

    def test_export_formation_with_title(self, exporter, sample_singers, tmp_path):
        """Export includes custom title."""
        output = tmp_path / "titled.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            title="Meine Aufstellung"
        )
        assert result is True

    def test_export_formation_with_subtitle(self, exporter, sample_singers, tmp_path):
        """Export includes subtitle."""
        output = tmp_path / "subtitle.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            subtitle="Probe am 15.06.2026"
        )
        assert result is True

    def test_export_formation_staggered(self, exporter, sample_singers, tmp_path):
        """Export with staggered grid."""
        output = tmp_path / "staggered.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            staggered=True
        )
        assert result is True

    def test_export_formation_vertical_text(self, exporter, sample_singers, tmp_path):
        """Export with vertical text rotation."""
        output = tmp_path / "vertical.pdf"
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=str(output),
            text_rotation="vertical"
        )
        assert result is True

    def test_export_invalid_path_returns_false(self, exporter, sample_singers):
        """Export to invalid path returns False."""
        result = exporter.export_formation(
            sample_singers, rows=2, cols=2,
            filename="/nonexistent/dir/test.pdf"
        )
        assert result is False

    def test_get_singer_at(self, exporter, sample_singers):
        """_get_singer_at finds singer at position."""
        singer = exporter._get_singer_at(sample_singers, 0, 0)
        assert singer is not None
        assert singer.name == "Alice"

    def test_get_singer_at_empty(self, exporter, sample_singers):
        """_get_singer_at returns None for empty position."""
        singer = exporter._get_singer_at(sample_singers, 5, 5)
        assert singer is None
