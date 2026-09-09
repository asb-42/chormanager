"""Tests for PDF export functionality."""

import os
import tempfile
import pytest
from singer_model import Singer, VoiceGroup


class TestPDFExport:
    """Tests for PDFExporter.export_formation()."""

    @pytest.fixture
    def pdf_exporter(self):
        """Create a PDFExporter instance."""
        from pdf_export import PDFExporter
        return PDFExporter()

    @pytest.fixture
    def sample_singers(self):
        """Create sample singers for testing."""
        singers = [
            Singer("Anna", VoiceGroup.SOPRAN_1, height=165, singer_id="s1", row=0, col=0),
            Singer("BERT", VoiceGroup.SOPRAN_2, height=160, singer_id="s2", row=0, col=1),
            Singer("Clara", VoiceGroup.ALT_1, height=170, singer_id="s3", row=1, col=0),
            Singer("David", VoiceGroup.TENOR_1, height=175, singer_id="s4", row=1, col=1),
        ]
        return singers

    def test_pdf_export_returns_true_for_valid_data(self, pdf_exporter, sample_singers, tmp_path):
        """Should return True for valid export data."""
        filepath = str(tmp_path / "test.pdf")
        result = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=filepath
        )
        assert result is True

    def test_pdf_export_creates_file_with_expected_header(self, pdf_exporter, sample_singers, tmp_path):
        """Should create a PDF file with correct header."""
        filepath = str(tmp_path / "test.pdf")
        pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=filepath
        )
        with open(filepath, 'rb') as f:
            header = f.read(5)
        assert header == b'%PDF-'

    def test_pdf_export_handles_empty_singers(self, pdf_exporter, tmp_path):
        """Should handle empty singers list."""
        filepath = str(tmp_path / "empty.pdf")
        result = pdf_exporter.export_formation(
            [], rows=2, cols=2, filename=filepath
        )
        assert result is True

    def test_pdf_export_handles_staggered_grid(self, pdf_exporter, sample_singers, tmp_path):
        """Should handle staggered grid layout."""
        filepath = str(tmp_path / "staggered.pdf")
        result = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=filepath,
            staggered=True
        )
        assert result is True
        assert os.path.exists(filepath)

    def test_pdf_export_handles_color_and_bw_modes(self, pdf_exporter, sample_singers, tmp_path):
        """Should handle both color and black-white modes."""
        color_path = str(tmp_path / "color.pdf")
        bw_path = str(tmp_path / "bw.pdf")

        result_color = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=color_path,
            color_mode="color"
        )
        result_bw = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=bw_path,
            color_mode="bw"
        )

        assert result_color is True
        assert result_bw is True
        assert os.path.getsize(color_path) > 0
        assert os.path.getsize(bw_path) > 0

    def test_pdf_export_handles_rotated_text(self, pdf_exporter, sample_singers, tmp_path):
        """Should handle vertical text rotation."""
        filepath = str(tmp_path / "rotated.pdf")
        result = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=filepath,
            text_rotation="vertical"
        )
        assert result is True
        assert os.path.exists(filepath)

    def test_pdf_export_handles_portrait_orientation(self, pdf_exporter, sample_singers, tmp_path):
        """Should handle portrait orientation."""
        filepath = str(tmp_path / "portrait.pdf")
        result = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=filepath,
            orientation="portrait"
        )
        assert result is True

    def test_pdf_export_includes_title_and_subtitle(self, pdf_exporter, sample_singers, tmp_path):
        """Should include title and subtitle in PDF."""
        filepath = str(tmp_path / "titled.pdf")
        result = pdf_exporter.export_formation(
            sample_singers, rows=2, cols=2, filename=filepath,
            title="Test Title", subtitle="Test Subtitle"
        )
        assert result is True
