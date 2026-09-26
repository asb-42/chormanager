"""Smoke 2 (MS4): Termin + Verfügbarkeit + Zusagen-PDF (M0-Spec).

Quelle: docs/plans/2026-09-26_m0_erd-openapi.md §4.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Web-App (M1-M5) ausstehend: Smoke 2 aktiv ab M4"
)


def test_create_event_and_set_availability_bulk(web_page, seeded_formation):
    """Termin anlegen → Verfügbarkeits-Matrix bulk setzen
    (``PUT /events/{id}/availability``); Stimmgruppen-Zusammenfassung
    aktualisiert sich (``GET /projects/{id}/summary``)."""


def test_zusagen_pdf_download(web_page, seeded_formation):
    """``GET /export/zusagen.pdf``: Status 200, ``%PDF``-Header;
    Qualitätskriterien Analyse §5.3 (Zentrierung, S/W-Tauglichkeit,
    Schriften, Kopf) werden in M4 gegen Desktop-Referenz-PDFs
    geprüft."""
