"""TDD RED: S2-FIX-A — TLS-Cert-Hinweis in der Doku.

``urllib.request.urlopen`` akzeptiert den System-Cert-Store. In
Firmen-Netzwerken mit MITM-Proxy (Zscaler, Palo Alto etc.) wird das
CA-Bundle aus ``SSL_CERT_FILE`` akzeptiert — ein kompromittierter
Proxy könnte eine gefälschte GitHub-Antwort liefern.

S2-FIX-A ergänzt ``docs/benutzerhandbuch.md`` um einen klaren
Sicherheits-Hinweis in der ``## Problemlösung``-Sektion, der diese
Limitation dokumentiert.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_benutzerhandbuch_has_tls_section():
    doc = Path("docs/benutzerhandbuch.md").read_text(encoding="utf-8")
    assert "TLS" in doc or "MITM" in doc or "Zertifikat" in doc.lower(), (
        "S2-FIX-A: docs/benutzerhandbuch.md must mention the TLS / "
        "MITM-proxy limitation of the update checker"
    )


def test_benutzerhandbuch_tls_note_in_problemlosung_chapter():
    """The TLS note must live in the 'Problemlösung' chapter so users
    find it when troubleshooting."""
    doc = Path("docs/benutzerhandbuch.md").read_text(encoding="utf-8")
    # Find the start of the "Problemlösung" chapter and the next "## " heading.
    start = doc.find("## Problemlösung")
    assert start != -1, "Problemlösung chapter missing"
    next_chapter = doc.find("\n## ", start + 1)
    section = doc[start:next_chapter if next_chapter != -1 else None]
    assert "TLS" in section or "MITM" in section or "Zertifikat" in section.lower(), (
        "S2-FIX-A: the TLS note must live in the Problemlösung chapter"
    )
