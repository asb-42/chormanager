"""PDF renderer for a :class:`ResponseMatrix`.

Pure-Python, Qt-free. Uses :mod:`reportlab.platypus` to lay out the
matrix in a table-style flow that closely mirrors the ODT version.

The renderer is designed to be a near visual twin of
:mod:`chormanager.core.response_render_odt` so the two outputs feel
familiar to the user.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .response_matrix import GroupBlock, ResponseMatrix


def _make_styles():
    """Build the ParagraphStyles we use for the PDF body."""
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title", parent=base["Heading1"], fontSize=14, spaceAfter=10,
    )
    header = ParagraphStyle(
        "Header", parent=base["Normal"], fontSize=9, fontName="Helvetica-Bold",
        alignment=1,  # CENTER
    )
    cell = ParagraphStyle(
        "Cell", parent=base["Normal"], fontSize=9, alignment=1,
    )
    name_cell = ParagraphStyle(
        "NameCell", parent=base["Normal"], fontSize=9, alignment=0,  # LEFT
    )
    group_label = ParagraphStyle(
        "GroupLabel", parent=base["Normal"], fontSize=9,
        fontName="Helvetica-Bold", leftIndent=0,
    )
    subtotal_label = ParagraphStyle(
        "SubtotalLabel", parent=base["Normal"], fontSize=9,
        fontName="Helvetica-Bold",
    )
    return title, header, cell, name_cell, group_label, subtotal_label


def _build_table_data(matrix: ResponseMatrix):
    """Build the raw cell data + TableStyle for the matrix."""
    # Header row: empty name cell, then one column per event
    header_row = [""] + [col.label for col in matrix.columns]
    body: List[List] = [header_row]
    style_cmds = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    row_idx = 1  # running index in the body list
    for group in matrix.groups:
        # Group label row
        grp_row = [group.voice_group] + [""] * len(matrix.columns)
        body.append(grp_row)
        style_cmds.append(
            ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
        )
        style_cmds.append(
            ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.whitesmoke)
        )
        row_idx += 1

        # Singer rows
        for singer in group.rows:
            row = [singer.name] + [c.label for c in singer.cells]
            body.append(row)
            row_idx += 1

        # Subtotal row
        sub_row = [f"{group.voice_group} insgesamt"] + [
            str(n) for n in group.subtotal
        ]
        body.append(sub_row)
        style_cmds.append(
            ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
        )
        style_cmds.append(
            ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.lightgrey)
        )
        row_idx += 1

    # Grand total row
    grand_row = ["insgesamt"] + [str(n) for n in matrix.totals]
    body.append(grand_row)
    style_cmds.append(
        ("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
    )
    style_cmds.append(
        ("BACKGROUND", (0, row_idx), (-1, row_idx), colors.darkgrey),
    )
    style_cmds.append(
        ("TEXTCOLOR", (0, row_idx), (-1, row_idx), colors.white),
    )

    return body, TableStyle(style_cmds)


def render_response_matrix_pdf(
    matrix: ResponseMatrix,
    out_path: os.PathLike | str,
) -> Path:
    """Render the response matrix to a PDF file.

    Args:
        matrix: A :class:`ResponseMatrix` from
            :func:`chormanager.core.response_matrix.build_response_matrix`.
        out_path: Destination file. Parent directory will be created
            if it doesn't exist.

    Returns:
        The resolved output path.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Use landscape A4 if there are many columns
    n_cols = 1 + len(matrix.columns)
    page_size = A4 if n_cols <= 8 else landscape(A4)

    doc = SimpleDocTemplate(
        str(out),
        pagesize=page_size,
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )

    title_style, header_style, cell_style, name_style, grp_style, sub_style = _make_styles()

    story = []
    if matrix.title:
        story.append(Paragraph(matrix.title, title_style))
        story.append(Spacer(1, 0.3 * cm))

    data, table_style = _build_table_data(matrix)

    # Wrap cell strings in Paragraphs so we can apply the styles
    if matrix.title or data:
        header_paragraphs = [
            Paragraph(str(c), header_style) for c in data[0]
        ]
        body_paragraphs = [header_paragraphs]
        for row in data[1:]:
            cells = []
            for j, val in enumerate(row):
                if j == 0:
                    # First column: name or label (left-aligned)
                    if "insgesamt" in str(val):
                        cells.append(Paragraph(str(val), sub_style))
                    else:
                        cells.append(Paragraph(str(val), name_style))
                else:
                    cells.append(Paragraph(str(val), cell_style))
            body_paragraphs.append(cells)
        data = body_paragraphs

    col_widths = [3.5 * cm] + [1.6 * cm] * len(matrix.columns)
    table = Table(data, colWidths=col_widths)
    table.setStyle(table_style)
    story.append(table)

    doc.build(story)
    return out
