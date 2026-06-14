"""ODT renderer for a :class:`ResponseMatrix`.

This module is pure-Python (no Qt, no reportlab-odt dependency). It
writes a minimal but valid OpenDocument Text file that LibreOffice
Writer, AbiWord, and other OASIS consumers can open.

The generated document contains:

  * A title paragraph (``text:p``).
  * One ``table:table`` with one ``table:table-header-rows`` block
    that contains the event labels.
  * Body rows grouped by voice group. Each group is followed by a
    subtotal row named ``"<VoiceGroup> insgesamt"``.
  * A grand-total row named ``"insgesamt"`` at the bottom.

We deliberately keep the file format minimal — no images, no
``table:table-header-rows`` repeat on each page, no automatic styles
beyond what's needed for the title and table borders. This is exactly
enough to be useful for the user's documented export workflow.

The file is a ZIP archive with these members:

  * ``mimetype`` (stored, not deflated, per the ODF spec).
  * ``content.xml`` (the document body).
  * ``styles.xml`` (a minimal stylesheet).
  * ``META-INF/manifest.xml`` (the package manifest).
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Iterable, List
from xml.sax.saxutils import escape

from .response_matrix import GroupBlock, ResponseMatrix


#: Display name for each register in the export table. The matrix-level
#: canonical names ("Sopran", "Alt", "Tenor", "Bass") are neutral; the
#: Chorleiter-Wunsch ("Summe Alti" etc.) requires the slightly different
#: plural form for "Alt" only.
REGISTER_DISPLAY_NAMES: dict = {
    "Sopran": "Summe Sopran",
    "Alt":    "Summe Alti",
    "Tenor":  "Summe Tenor",
    "Bass":   "Summe Bass",
}


# ---------------------------------------------------------------------------
# ODT XML building blocks
# ---------------------------------------------------------------------------

# Namespace map embedded in the root <office:document-content> element.
_NS_MAP = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"'
)


def _cell(text: str, header: bool = False) -> str:
    """Build a <table:table-cell> with the given text content."""
    style = "TableCellHeader" if header else "TableCell"
    para_style = "PHeader" if header else "PCell"
    safe = escape(text or "")
    return (
        f'<table:table-cell office:value-type="string" table:style-name="{style}">'
        f'<text:p text:style-name="{para_style}">{safe}</text:p>'
        f'</table:table-cell>'
    )


def _row(cells_xml: Iterable[str], repeated: bool = False) -> str:
    rep = ' table:number-rows-repeated="1"' if repeated else ""
    return f'<table:table-row{rep}>{"".join(cells_xml)}</table:table-row>'


# ---------------------------------------------------------------------------
# Document parts
# ---------------------------------------------------------------------------

def _build_styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<office:document-styles {_NS_MAP} office:version="1.2">'
        '<office:styles>'
        '<style:style style:name="Title" style:family="paragraph">'
        '<style:text-properties fo:font-size="14pt" fo:font-weight="bold"/>'
        '</style:style>'
        '<style:style style:name="PHeader" style:family="paragraph">'
        '<style:text-properties fo:font-weight="bold"/>'
        '<style:paragraph-properties fo:text-align="center"/>'
        '</style:style>'
        '<style:style style:name="PCell" style:family="paragraph">'
        '<style:paragraph-properties fo:text-align="center"/>'
        '</style:style>'
        '</office:styles>'
        '<office:automatic-styles>'
        '<style:style style:name="TableCell" style:family="table-cell">'
        '<style:table-cell-properties '
        'fo:border="0.5pt solid #000000" fo:padding="0.05cm"/>'
        '</style:style>'
        '<style:style style:name="TableCellHeader" style:family="table-cell">'
        '<style:table-cell-properties '
        'fo:border="0.5pt solid #000000" fo:background-color="#dddddd" '
        'fo:padding="0.05cm"/>'
        '</style:style>'
        '</office:automatic-styles>'
        '</office:document-styles>'
    )


def _build_content_xml(matrix: ResponseMatrix) -> str:
    """Build the content.xml document body."""
    # Title (escape for safety)
    title = escape(matrix.title or "")

    # Column header row
    header_cells = [_cell("", header=True)]  # singer-name column has no header
    header_cells.extend(_cell(col.label, header=True) for col in matrix.columns)
    header_row_xml = _row(header_cells)
    # Wrap into <table:table-header-rows>
    header_block = (
        f'<table:table-header-rows>{header_row_xml}</table:table-header-rows>'
    )

    # Body rows: per group -> singer rows, then a subtotal row.
    body_rows: List[str] = []
    for group in matrix.groups:
        # Group label row (one cell, but we still emit 1 + N cells for layout)
        grp_cells = [_cell(group.voice_group, header=False)]
        grp_cells.extend(_cell("", header=False) for _ in matrix.columns)
        body_rows.append(_row(grp_cells))

        for singer in group.rows:
            cells = [_cell(singer.name, header=False)]
            cells.extend(_cell(c.label, header=False) for c in singer.cells)
            body_rows.append(_row(cells))

        # Subtotal row: "<Group> insgesamt" + per-event "yes" counts
        sub_cells = [_cell(f"{group.voice_group} insgesamt", header=False)]
        sub_cells.extend(
            _cell(str(n), header=False) for n in group.subtotal
        )
        body_rows.append(_row(sub_cells))

    # Register sum rows (Chorleiter-Wunsch): one row per canonical
    # register, between the per-group subtotal rows and the grand total
    # row. Each row has one numeric cell per event column.
    for reg_sum in matrix.register_sums:
        display = REGISTER_DISPLAY_NAMES.get(
            reg_sum.register, f"Summe {reg_sum.register}"
        )
        reg_cells = [_cell(display, header=False)]
        reg_cells.extend(
            _cell(str(n), header=False) for n in reg_sum.counts
        )
        body_rows.append(_row(reg_cells))

    # Grand total row: "insgesamt" + matrix.totals per event
    grand_cells = [_cell("insgesamt", header=False)]
    grand_cells.extend(_cell(str(n), header=False) for n in matrix.totals)
    body_rows.append(_row(grand_cells))

    # The table needs at least one <table:table-column> per column.
    # We emit a fixed repeat-count column for the name column and
    # one per event.
    n_cols = 1 + len(matrix.columns)
    columns_xml = (
        f'<table:table-column table:number-columns-repeated="{n_cols}"/>'
    )

    table_xml = (
        '<table:table table:name="Zusagen">'
        f'{columns_xml}{header_block}{"".join(body_rows)}'
        '</table:table>'
    )

    # NOTE: The <office:text> wrapper inside <office:body> is required
    # by the ODF spec for text documents. Without it, LibreOffice and
    # other strict ODF consumers open the file but render an empty page
    # (because the body content is not classified as "text"). The
    # sample ODT used as reference includes this wrapper; our minimal
    # content.xml had it missing.
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<office:document-content {_NS_MAP} office:version="1.2">'
        '<office:body>'
        '<office:text text:use-soft-page-breaks="true">'
        f'<text:p text:style-name="Title">{title}</text:p>'
        f'{table_xml}'
        '</office:text>'
        '</office:body>'
        '</office:document-content>'
    )


def _build_manifest_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<manifest:manifest '
        'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.2">'
        '<manifest:file-entry manifest:full-path="/" '
        'manifest:media-type="application/vnd.oasis.opendocument.text"/>'
        '<manifest:file-entry manifest:full-path="content.xml" '
        'manifest:media-type="text/xml"/>'
        '<manifest:file-entry manifest:full-path="styles.xml" '
        'manifest:media-type="text/xml"/>'
        '</manifest:manifest>'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_response_matrix_odt(
    matrix: ResponseMatrix,
    out_path: os.PathLike | str,
) -> Path:
    """Render the response matrix to a valid ODT file.

    Args:
        matrix: A :class:`ResponseMatrix` (from
            :func:`chormanager.core.response_matrix.build_response_matrix`).
        out_path: Destination file. Parent directory will be created
            if it doesn't exist.

    Returns:
        The resolved output path.

    Raises:
        OSError: If the file cannot be written.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    content_xml = _build_content_xml(matrix)
    styles_xml = _build_styles_xml()
    manifest_xml = _build_manifest_xml()

    # Per the ODF spec, the "mimetype" member MUST be:
    #   1. The first entry in the archive.
    #   2. Stored uncompressed (ZIP_STORED, no DEFLATE).
    #   3. Carry the UTF-8 filename flag (0x800) so that LibreOffice and
    #      other strict ODF consumers can detect the format without
    #      scanning the whole archive. Without this flag, some readers
    #      fall back to a "no content" interpretation.
    mimetype_info = zipfile.ZipInfo("mimetype")
    mimetype_info.flag_bits |= 0x800  # UTF-8 filename flag
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        # Use open()+write() instead of writestr() because writestr()
        # internally constructs its own ZipInfo and ignores our flag_bits.
        with zf.open(mimetype_info, mode="w", force_zip64=False) as fp:
            fp.write(b"application/vnd.oasis.opendocument.text")
        zf.writestr("content.xml", content_xml)
        zf.writestr("styles.xml", styles_xml)
        zf.writestr("META-INF/manifest.xml", manifest_xml)

    return out
