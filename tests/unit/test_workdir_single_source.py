"""M0 Struktur-Bereinigung (§7): genau EIN Export-Verzeichnis.

Plan ref: docs/plans/2026-09-25_web-migration-analyse.md §7.
Befund: Exporte landeten je nach Aufrufer in ``./workdir/``,
``chormanager/workdir/`` oder einem absolut hartcodierten
``/media/...``-Pfad. Single Source ist ``config.get_workdir()``
(Repo-Root + ``workdir``); relativer Pfad, kein Hardcode.
"""
from __future__ import annotations


def test_get_workdir_resolves_to_repo_root_workdir():
    from pathlib import Path

    from chormanager.config import get_app_dir, get_workdir

    assert get_workdir() == get_app_dir() / "workdir"
    assert isinstance(get_workdir(), Path)


def test_no_absolute_media_path_in_source():
    """Portabilität: kein /media/-Hardcode mehr im Prod-Code."""
    from pathlib import Path

    for rel in (
        "chormanager/ui/export_controller.py",
        "chormanager/ui/dialogs/_event_availability.py",
        "chormanager/ui/dialogs/_singer_selection.py",
    ):
        src = Path(rel).read_text(encoding="utf-8")
        assert "/media/" not in src, f"absoluter Pfad in {rel}"


def test_workdir_literal_only_in_config():
    """Alle Aufrufer nutzen get_workdir(); das 'workdir'-Literal
    lebt nur in chormanager/config.py (Guards gegen Regression)."""
    from pathlib import Path

    offenders = []
    for rel in (
        "chormanager/ui/export_controller.py",
        "chormanager/ui/dialogs/_event_availability.py",
        "chormanager/ui/dialogs/_singer_selection.py",
    ):
        for i, line in enumerate(
            Path(rel).read_text(encoding="utf-8").splitlines(), 1
        ):
            stripped = line.split("#", 1)[0]
            if '"workdir"' in stripped or "'workdir'" in stripped:
                offenders.append(f"{rel}:{i}")
    assert offenders == [], f"workdir-Literal ausserhalb config.py: {offenders}"
