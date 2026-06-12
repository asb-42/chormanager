# TDD RED: Unit tests for the ODT renderer of ResponseMatrix.
#
# The renderer is pure-Python (no Qt). It writes a valid ODT file
# (ZIP with mimetype, content.xml, styles.xml, META-INF/manifest.xml)
# that LibreOffice and other OASIS consumers can open.
#
# Validation strategy: extract the resulting ODT, parse content.xml,
# and assert structural properties (title, table dimensions, header
# row, group rows, subtotal row, grand total row).
import os
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chormanager.core.response_matrix import (
    build_response_matrix,
    ResponseMatrix,
)
from chormanager.core.response_render_odt import render_response_matrix_odt


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
    """Build a small but realistic ResponseMatrix for renderer tests."""
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


def _open_odt(path: Path):
    """Return a dict with 'mimetype' and parsed 'content' (ElementTree)."""
    with zipfile.ZipFile(path, "r") as zf:
        mimetype = zf.read("mimetype").decode("ascii").strip()
        content = ET.fromstring(zf.read("content.xml"))
    return {"mimetype": mimetype, "content": content}


NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text":   "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table":  "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}


# --- 1. File is created ---------------------------------------------------
def test_odt_file_is_created(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    assert out.exists()
    assert out.stat().st_size > 0


# --- 2. The file is a valid ZIP with the right mimetype -------------------
def test_odt_has_correct_mimetype(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    assert odt["mimetype"] == "application/vnd.oasis.opendocument.text"


# --- 3. The ODT contains a manifest.xml ----------------------------------
def test_odt_contains_manifest(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
    assert "META-INF/manifest.xml" in names
    assert "content.xml" in names
    assert "styles.xml" in names


# --- 4. Title is rendered as a top-level paragraph -----------------------
def test_title_appears_in_content_xml(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    body = odt["content"].find("office:body", NS)
    assert body is not None
    # Concatenate all <text:p> text in the body
    paragraphs = body.findall(".//text:p", NS)
    all_text = "\n".join(
        "".join(t.text or "" for t in p.iter() if t.text) for p in paragraphs
    )
    assert "Konzert Hoffmann OKO" in all_text


# --- 5. Table has the right number of columns and rows -------------------
def test_table_dimensions_match_matrix(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    # The first <table:table> in the body
    table = odt["content"].find(".//table:table", NS)
    assert table is not None
    # The header row has 1 + len(columns) cells
    header_rows = table.findall("table:table-header-rows/table:table-row", NS)
    assert len(header_rows) == 1
    header_cells = header_rows[0].findall("table:table-cell", NS)
    assert len(header_cells) == 1 + len(matrix.columns)  # name + N events
    # Header text contains the event labels
    header_texts = [
        "".join(t.text or "" for t in c.iter() if t.text).strip()
        for c in header_cells
    ]
    assert "15.05. Probe" in header_texts
    assert "16.05. Konzert" in header_texts


# --- 6. Each singer appears as a row -------------------------------------
def test_singer_rows_are_present(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    table = odt["content"].find(".//table:table", NS)
    body_rows = table.findall("table:table-row", NS)
    # Concatenate all cell text per row, look for singer names
    row_texts = []
    for r in body_rows:
        cells = r.findall("table:table-cell", NS)
        txt = "|".join(
            "".join(t.text or "" for t in c.iter() if t.text).strip()
            for c in cells
        )
        row_texts.append(txt)
    joined = "\n".join(row_texts)
    for name in ("Anna", "Bea", "Carla", "Doris"):
        assert name in joined, f"Singer {name} missing from ODT output"


# --- 7. Status labels are rendered (X, -, X?) ----------------------------
def test_status_labels_are_rendered_in_cells(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    table = odt["content"].find(".//table:table", NS)
    body_rows = table.findall("table:table-row", NS)
    # Find Anna's row (soprano) and assert cell contents
    for r in body_rows:
        cells = r.findall("table:table-cell", NS)
        first_text = "".join(
            t.text or "" for t in cells[0].iter() if t.text
        ).strip()
        if first_text == "Anna":
            labels = [
                "".join(t.text or "" for t in c.iter() if t.text).strip()
                for c in cells[1:]
            ]
            # Anna said yes for e1, conditional for e2
            assert labels == ["X", "X?"]
            break
    else:
        pytest.fail("Anna's row not found in ODT output")


# --- 8. Subtotal row contains the correct "yes" counts -------------------
def test_subtotal_row_for_sopran_present(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    table = odt["content"].find(".//table:table", NS)
    body_rows = table.findall("table:table-row", NS)
    found = False
    for r in body_rows:
        cells = r.findall("table:table-cell", NS)
        first_text = "".join(
            t.text or "" for t in cells[0].iter() if t.text
        ).strip()
        if first_text.startswith("Sopran 1 insgesamt"):
            numbers = [
                "".join(t.text or "" for t in c.iter() if t.text).strip()
                for c in cells[1:]
            ]
            # Anna: yes/conditional, Bea: no/-, so 1 yes for e1, 0 for e2
            assert numbers == ["1", "0"]
            found = True
            break
    assert found, "Subtotal row 'Sopran insgesamt' not found"


# --- 9. Grand total row contains the correct overall counts ---------------
def test_grand_total_row_present(tmp_path):
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    table = odt["content"].find(".//table:table", NS)
    body_rows = table.findall("table:table-row", NS)
    for r in body_rows:
        cells = r.findall("table:table-cell", NS)
        first_text = "".join(
            t.text or "" for t in cells[0].iter() if t.text
        ).strip()
        if first_text == "insgesamt":
            numbers = [
                "".join(t.text or "" for t in c.iter() if t.text).strip()
                for c in cells[1:]
            ]
            # e1: Anna/Carla/Doris yes => 3
            # e2: Carla yes            => 1
            assert numbers == ["3", "1"]
            return
    pytest.fail("Grand total row 'insgesamt' not found")


# --- 10. Empty matrix produces a valid (but tiny) ODT ---------------------
def test_empty_matrix_produces_valid_odt(tmp_path):
    matrix = build_response_matrix([], [], [], title="Leer")
    out = tmp_path / "empty.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    assert odt["mimetype"] == "application/vnd.oasis.opendocument.text"
    # Title must still be rendered
    paragraphs = odt["content"].findall(".//text:p", NS)
    all_text = "\n".join(
        "".join(t.text or "" for t in p.iter() if t.text) for p in paragraphs
    )
    assert "Leer" in all_text


# --- Regression guard: must be wrapped in <office:text> ----------
def test_body_is_wrapped_in_office_text(tmp_path):
    """The ODF spec requires text content to be wrapped in
    <office:text> inside <office:body>. Without it, LibreOffice opens
    the file but renders an empty page (regression discovered 2026-06-12)."""
    matrix = _build_sample_matrix()
    out = tmp_path / "out.odt"
    render_response_matrix_odt(matrix, out)
    odt = _open_odt(out)
    body = odt["content"].find("office:body", NS)
    assert body is not None
    # The first child of <office:body> must be <office:text>
    assert len(list(body)) > 0
    assert list(body)[0].tag.endswith("}text"), (
        f"Expected <office:text> as first child of <office:body>, "
        f"got {list(body)[0].tag}"
    )
    # No direct <text:p> children of <office:body> (they must be inside the wrapper)
    direct_paragraphs = [
        c for c in list(body) if c.tag.endswith("}p")
    ]
    assert direct_paragraphs == [], (
        "<text:p> must not be a direct child of <office:body>"
    )
