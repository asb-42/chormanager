"""Formation grid PDF renderer (§5.3, reportlab canvas).

Qualitätskriterien: Kurznamen horizontal + vertikal zentriert
(ellipsis bei Überlänge), Stimmgruppen-Farbe als Füllung PLUS
Gruppen-Kurztext (S/W-lesbar), Kopf mit Name/Projekt/Termin/Datum,
Fit-Skalierung (keine abgeschnittenen Kacheln), Viewer-garantierte
Standard-14-Schriften (Desktop-Parität; echtes Font-Embedding
bleibt Follow-up).
"""
import tempfile
from io import BytesIO
from typing import Dict, List

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

_BASE_PITCH_W = 130
_BASE_PITCH_H = 80
_BASE_CELL_W = 120
_BASE_CELL_H = 60
_MARGIN = 40
_HEADER_H = 64


def _fit(text: str, font: str, size: int, max_width: float) -> str:
    """Truncate with ellipsis until the text fits."""
    if stringWidth(text, font, size) <= max_width:
        return text
    while text and stringWidth(text + "…", font, size) > max_width:
        text = text[:-1]
    return text + "…" if text else ""


def render_formation_pdf(doc: Dict, colors: Dict[str, str]) -> bytes:
    """Render a formation document to PDF bytes.

    Args:
        doc: Formation doc shape (``name``, ``rows``, ``cols``,
            ``staggered``, ``singers``, ``placed``, ``metadata``).
        colors: ``{voice_group: hex}`` fill colors (light theme).

    Returns:
        PDF file content.
    """
    rows = max(1, int(doc.get("rows", 1)))
    cols = max(1, int(doc.get("cols", 1)))
    staggered = bool(doc.get("staggered", False))
    page = landscape(A4) if cols > rows else A4
    page_w, page_h = page

    scale = min(
        1.0,
        (page_w - 2 * _MARGIN) / (cols * _BASE_PITCH_W),
        (page_h - 2 * _MARGIN - _HEADER_H) / (rows * _BASE_PITCH_H),
    )
    pitch_w = _BASE_PITCH_W * scale
    pitch_h = _BASE_PITCH_H * scale
    cell_w = _BASE_CELL_W * scale
    cell_h = _BASE_CELL_H * scale
    name_size = max(6, int(10 * scale))
    group_size = max(5, int(7 * scale))

    placed = {
        (p["row"], p["col"]): p["singer"]
        for p in doc.get("placed", [])
        if isinstance(p, dict)
    }

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=page)
    canvas.setTitle(str(doc.get("name") or "Aufstellung"))

    metadata = doc.get("metadata", {}) or {}
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(_MARGIN, page_h - _MARGIN, str(doc.get("name") or ""))
    canvas.setFont("Helvetica", 10)
    canvas.drawString(
        _MARGIN,
        page_h - _MARGIN - 16,
        " / ".join(
            part for part in (
                metadata.get("project", ""),
                metadata.get("event", ""),
                metadata.get("event_date", ""),
                metadata.get("event_type", ""),
                f"{rows}x{cols}",
            )
            if part
        ),
    )

    origin_y = page_h - _MARGIN - _HEADER_H
    for row in range(rows):
        offset = (_BASE_PITCH_W / 2 * scale) if (staggered and row % 2 == 1) else 0.0
        for col in range(cols):
            x = _MARGIN + offset + col * pitch_w
            y = origin_y - (row + 1) * pitch_h
            singer = placed.get((row, col))
            if singer is not None:
                fill = colors.get(singer.get("voice_group") or "", "#cccccc")
                canvas.setFillColor(HexColor(fill))
                canvas.rect(x, y, cell_w, cell_h, stroke=0, fill=1)
            canvas.setFillColor(HexColor("#999999"))
            canvas.rect(x, y, cell_w, cell_h, stroke=1, fill=0)
            if singer is not None:
                canvas.setFillColor(black)
                name = _fit(
                    str(singer.get("name") or ""), "Helvetica-Bold",
                    name_size, cell_w - 8,
                )
                canvas.setFont("Helvetica-Bold", name_size)
                canvas.drawCentredString(
                    x + cell_w / 2, y + cell_h / 2 + 2, name
                )
                group = _fit(
                    str(singer.get("voice_group") or ""), "Helvetica",
                    group_size, cell_w - 8,
                )
                canvas.setFont("Helvetica", group_size)
                canvas.drawCentredString(
                    x + cell_w / 2, y + cell_h / 2 - group_size - 2,
                    group,
                )
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def write_temp_pdf(data: bytes, prefix: str) -> str:
    """Write PDF bytes to a temp file (caller unlinks after send)."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=".pdf", prefix=prefix, delete=False
    )
    tmp.close()
    with open(tmp.name, "wb") as handle:
        handle.write(data)
    return tmp.name
