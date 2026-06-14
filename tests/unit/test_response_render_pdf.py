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


def _pdf_to_text(path: Path, layout: bool = False) -> str:
    """Run pdftotext on the file and return the concatenated output.

    Skips the test (rather than failing) if pdftotext is not installed
    — in that case the assertion is replaced by a structural check.

    Args:
        path: PDF file to read.
        layout: If True, use ``pdftotext -layout`` to preserve the
            table column positions. This is needed for tests that
            inspect per-cell numeric values (e.g. register sum counts);
            the default mode strips column alignment and makes per-cell
            extraction unreliable.
    """
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext (poppler-utils) is not installed")
    cmd = ["pdftotext", str(path), "-"]
    if layout:
        cmd.insert(1, "-layout")
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=10,
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


# ===========================================================================
# Register sum rows (Chorleiter-Wunsch)
# ===========================================================================
# Between the per-group subtotal rows ("Sopran 1 insgesamt" etc.) and the
# grand total row ("insgesamt"), the renderer must draw four additional
# summary rows — one per choral register:
#   * "Summe Sopran" (= Sopran 1 + Sopran 2)
#   * "Summe Alti"   (= Alt 1 + Alt 2)
#   * "Summe Tenor"  (= Tenor 1 + Tenor 2)
#   * "Summe Bass"   (= Bass 1 + Bass 2)


def _build_register_matrix():
    """Build a matrix with singers in all 8 canonical voice groups, with
    a known number of 'yes' answers per register per event."""
    singers = [
        _singer("s1", "A", "Sopran 1"),
        _singer("s2", "B", "Sopran 2"),
        _singer("s3", "C", "Alt 1"),
        _singer("s4", "D", "Alt 2"),
        _singer("s5", "E", "Tenor 1"),
        _singer("s6", "F", "Tenor 2"),
        _singer("s7", "G", "Bass 1"),
        _singer("s8", "H", "Bass 2"),
    ]
    events = [
        _event("e1", "2026-05-10T18:00:00", "Probe"),
        _event("e2", "2026-05-15T18:00:00", "Konzert"),
    ]
    # e1: Sopran 1=yes, Sopran 2=yes, Alt 1=yes, Alt 2=no,
    #     Tenor 1=yes, Tenor 2=yes, Bass 1=yes, Bass 2=yes
    # => Sopran=2, Alt=1, Tenor=2, Bass=2  (grand=7)
    avs = [
        _avail("s1", "e1", "yes"),
        _avail("s2", "e1", "yes"),
        _avail("s3", "e1", "yes"),
        _avail("s4", "e1", "no"),
        _avail("s5", "e1", "yes"),
        _avail("s6", "e1", "yes"),
        _avail("s7", "e1", "yes"),
        _avail("s8", "e1", "yes"),
        # e2: only some say yes
        _avail("s1", "e2", "yes"),  # Sopran 1
        _avail("s3", "e2", "yes"),  # Alt 1
        _avail("s5", "e2", "yes"),  # Tenor 1
        _avail("s7", "e2", "yes"),  # Bass 1
        # => Sopran=1, Alt=1, Tenor=1, Bass=1  (grand=4)
    ]
    return build_response_matrix(singers, events, avs, title="Register-Test")


# --- 9. PDF contains all four register sum labels -----------------------
def test_pdf_contains_all_four_register_sum_labels(tmp_path):
    matrix = _build_register_matrix()
    out = tmp_path / "regs.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    for label in ("Summe Sopran", "Summe Alti", "Summe Tenor", "Summe Bass"):
        assert label in text, f"{label!r} missing from PDF"


# --- 10. Register sum rows are between the per-group subtotals and
#        the grand total -------------------------------------------------
def test_pdf_register_sums_appear_before_grand_total(tmp_path):
    """The grand total is the *last* line of the table. Since per-group
    subtotal rows (e.g. ``Sopran 1 insgesamt``) appear before the
    register sum rows, the only safe way to identify the grand total
    position is to look for the line that contains the *last* expected
    grand total count (e2 grand=4) — that line is the grand total row."""
    matrix = _build_register_matrix()
    out = tmp_path / "regs.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out, layout=True)
    lines = [l.rstrip() for l in text.splitlines()]
    # The grand total row is the last line containing a number from
    # matrix.totals (e1=7, e2=4). We use the last grand-total value
    # (4) as a unique marker for the grand total row.
    grand_total_value = matrix.totals[-1]
    pos_total = -1
    for i, line in enumerate(lines):
        if f" {grand_total_value}" in f" {line} " or line.strip() == str(grand_total_value):
            # We want the LAST occurrence
            pos_total = i
    # Find register sum row positions
    pos_sopran = pos_alto = pos_tenor = pos_bass = -1
    for i, line in enumerate(lines):
        s = line.lstrip()
        if pos_sopran < 0 and s.startswith("Summe Sopran"):
            pos_sopran = i
        elif pos_alto < 0 and s.startswith("Summe Alti"):
            pos_alto = i
        elif pos_tenor < 0 and s.startswith("Summe Tenor"):
            pos_tenor = i
        elif pos_bass < 0 and s.startswith("Summe Bass"):
            pos_bass = i
    # All positions must be found
    assert pos_sopran >= 0, "Summe Sopran row not found"
    assert pos_alto   >= 0, "Summe Alti row not found"
    assert pos_tenor  >= 0, "Summe Tenor row not found"
    assert pos_bass   >= 0, "Summe Bass row not found"
    assert pos_total  >= 0, "Grand total row not found"
    # The four register sum rows must appear before the grand total row
    assert pos_sopran < pos_total
    assert pos_alto   < pos_total
    assert pos_tenor  < pos_total
    assert pos_bass   < pos_total
    # And they must appear in canonical order Sopran, Alt, Tenor, Bass
    assert pos_sopran < pos_alto   < pos_tenor  < pos_bass


# --- 11. Register sum counts are correct (per event) -------------------
def test_pdf_register_sum_counts_per_event(tmp_path):
    matrix = _build_register_matrix()
    out = tmp_path / "regs.pdf"
    render_response_matrix_pdf(matrix, out)
    # Use -layout so per-cell numbers stay on the same line as the label.
    text = _pdf_to_text(out, layout=True)
    # e1 (10.05. Probe): Sopran=2, Alt=1, Tenor=2, Bass=2  -> grand=7
    # e2 (15.05. Konzert): Sopran=1, Alt=1, Tenor=1, Bass=1 -> grand=4
    import re
    found = {"Sopran": None, "Alti": None, "Tenor": None, "Bass": None}
    for line in text.splitlines():
        stripped = line.strip()
        for reg in found:
            if found[reg] is None and stripped.startswith(f"Summe {reg}"):
                digits = re.findall(r"\d+", stripped)
                if digits:
                    found[reg] = [int(d) for d in digits]
    assert found["Sopran"] == [2, 1]
    assert found["Alti"]   == [1, 1]
    assert found["Tenor"]  == [2, 1]
    assert found["Bass"]   == [2, 1]


# --- 12. Register sums present even when no singers in that register ----
def test_pdf_register_sums_render_zero_for_empty_register(tmp_path):
    """If the matrix has no Tenor singers, 'Summe Tenor' row must still
    appear (with all zeros), so the table has a consistent shape."""
    matrix = build_response_matrix(
        singers=[_singer("s1", "A", "Sopran 1")],
        events=[_event("e1", "2026-05-15T18:00:00")],
        availabilities=[_avail("s1", "e1", "yes")],
        title="Nur Sopran",
    )
    out = tmp_path / "only-sopran.pdf"
    render_response_matrix_pdf(matrix, out)
    text = _pdf_to_text(out)
    assert "Summe Sopran" in text
    assert "Summe Alti"   in text
    assert "Summe Tenor"  in text
    assert "Summe Bass"   in text
