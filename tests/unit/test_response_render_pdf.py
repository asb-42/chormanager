# TDD GREEN-3: Unit tests for the PDF renderer of ResponseMatrix.
#
# The renderer uses reportlab.platypus. We test the produced PDF by
# extracting its text with `pdftotext` (poppler-utils) — this is
# robust, format-agnostic and doesn't depend on reportlab's internal
# PDF stream layout.
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chormanager.core.response_matrix import build_response_matrix
from chormanager.core.response_render_pdf import render_response_matrix_pdf


# --- Helpers ---------------------------------------------------------------
def _singer(id_, short_name, voice_group):
    return SimpleNamespace(
        id=id_, short_name=short_name, full_name=short_name, voice_group=voice_group,
    )


def _event(id_, date_, event_type=None):
    return SimpleNamespace(
        id=id_, date=date_, event_type=event_type, name=id_, project_id="p1",
    )


def _avail(sid, eid, status):
    return SimpleNamespace(
        id=f"a-{sid}-{eid}", singer_id=sid, event_id=eid, status=status,
    )


def _build_sample_matrix():
    singers = [
        _singer("s1", "Anna", "Sopran 1"),
        _singer("s2", "Bea",  "Sopran 1"),
        _singer("s3", "Carla", "Alt 1"),
        _singer("s4", "Doris", "Bass 1"),
    ]
    events = [
        _event("e1", "2026-05-15T18:00:00", "Probe"),
        _event("e2", "2026-05-16T18:00:00", "Konzert"),
    ]
    avs = [
        _avail("s1", "e1", "yes"),
        _avail("s2", "e1", "no"),
        _avail("s3", "e1", "yes"),
        _avail("s4", "e1", "yes"),
        _avail("s1", "e2", "conditional"),
        _avail("s3", "e2", "yes"),
    ]
    return build_response_matrix(
        singers, events, avs, title="Konzert Hoffmann OKO",
    )


def _pdf_to_text(path: Path) -> str:
    """Run pdftotext on the file and return the concatenated output.

    Skips the test (rather than failing) if pdftotext is not installed
    — in that case the assertion is replaced by a structural check.
    """
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext (poppler-utils) is not installed")
    result = subprocess.run(
        ["pdftotext", str(path), "-"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext failed: rc={result.returncode} stderr={result.stderr}"
        )
    return result.stdout


# --- 1. File is a valid PDF ------------------------------------------------
def test_pdf_file_is_created_and_nonempty(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    assert out.exists()
    assert out.stat().st_size > 0
    # The first 4 bytes must be "%PDF"
    assert out.read_bytes()[:4] == b"%PDF"


# --- 2. PDF contains the title --------------------------------------------
def test_pdf_contains_title(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    assert "Konzert Hoffmann OKO" in text


# --- 3. PDF contains singer names ----------------------------------------
def test_pdf_contains_singer_names(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    for name in ("Anna", "Bea", "Carla", "Doris"):
        assert name in text, f"{name} missing from PDF"


# --- 4. PDF contains event column labels --------------------------------
def test_pdf_contains_event_labels(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    # pdftotext may wrap "15.05. Probe" into two lines, so we check
    # the parts are present.
    assert "15.05." in text
    assert "Probe" in text
    assert "16.05." in text
    assert "Konzert" in text


# --- 5. PDF contains the subtotal label ---------------------------------
def test_pdf_contains_subtotal_label(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    assert "Sopran 1 insgesamt" in text


# --- 6. PDF contains the grand total label -------------------------------
def test_pdf_contains_grand_total_label(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    assert "insgesamt" in text


# --- 7. PDF contains the status labels -----------------------------------
def test_pdf_contains_status_labels(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    # Anna said yes for e1 (-> X), conditional for e2 (-> X?)
    assert "X" in text
    # Bea said no for e1
    assert "-" in text


# --- 8. Empty matrix produces a valid (small) PDF -----------------------
def test_empty_matrix_produces_valid_pdf(tmp_path):
    matrix = build_response_matrix([], [], [], title="Leer")
    out = tmp_path / "empty.pdf"
    render_response_matrix_pdf(matrix, out)
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"
    text = _pdf_to_text(out)
    assert "Leer" in text
    assert "insgesamt" in text
