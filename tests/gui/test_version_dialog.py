"""TDD RED: Version-Dialog zeigt echte Version + kein hardcoded cwd.

User request (2026-09-10, im Zuge des v0.1-Releases)::

    „schIB nach, ob der chormanager im Code irgendwo versioniert ist —
    falls ja, setzen wir das auf v0.1"

Findings dabei:
* ``chormanager/__init__.py`` pflegt ``__version__ = "0.1.0"``, aber der
  „Version prüfen"-Dialog zeigt hartkodiert „Aktuelle Version:
  Unbekannt" — die gepflegte Version erreicht den Nutzer nie.
* ``update_controller.py`` hardcodet ``cwd="/media/data/coding/
  chormanager"`` (zweimal) — auf dem Zielrechner
  (``/mnt/.../Jugendchor/chormanager``) schlagen Update-Check und
  ``git pull`` damit fehl (gleiche Bug-Klasse wie der ``_show_about``-
  Fix aus PR #2).

Contracts pinned here:

* ``VersionCheckDialog`` zeigt ``chormanager.__version__`` an.
* Weder Dialog noch Worker-Instanziierung enthalten einen absolut
  hardcodeden Repo-Pfad; das Arbeitsverzeichnis wird aus der eigenen
  Moduldatei abgeleitet (``Path(__file__).parent.parent.parent``).
* Die Ableitung ist robust: sie funktioniert unabhängig vom
  Installationsort (Entwickler-Rechner, Zielrechner, Test-Worktree).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


_UPDATE_CTRL = (
    Path(__file__).parent.parent.parent
    / "chormanager" / "ui" / "update_controller.py"
)


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


def test_dialog_shows_real_version(qapp):
    """Der Dialog muss chormanager.__version__ anzeigen, nicht
    hartkodiert 'Unbekannt'."""
    from chormanager import __version__
    from chormanager.ui.update_controller import VersionCheckDialog

    dlg = VersionCheckDialog()
    try:
        text = dlg.info_label.text()
        assert __version__ in text, (
            f"Version-Dialog zeigt '{text}' — enthält aber nicht die "
            f"gepflegte __version__ {__version__!r}."
        )
        assert "Unbekannt" not in text
    finally:
        dlg.deleteLater()


def test_dialog_info_label_initialized_with_version(qapp, qtbot=None):
    """Bereits die Initialisierung nutzt __version__ (kein 'Unbekannt'
    als Platzhalter, der nie ersetzt wird)."""
    from chormanager import __version__
    from chormanager.ui.update_controller import VersionCheckDialog

    dlg = VersionCheckDialog()
    try:
        assert dlg.info_label.text() == f"Aktuelle Version: {__version__}"
    finally:
        dlg.deleteLater()


def test_no_hardcoded_absolute_repo_path():
    """Kein absoluter Maschinen-Pfad im update_controller.

    Der Zielrechner-Report zeigte den Code unter
    ``/mnt/.../Jugendchor/chormanager`` — jede Verbatim-Referenz auf
    ``/media/data/coding/chormanager`` bricht dort.
    """
    src = _UPDATE_CTRL.read_text(encoding="utf-8")
    assert '"/media/data' not in src and "'/media/data" not in src, (
        "update_controller.py enthält weiterhin einen absolut "
        "hardcodeden Pfad des Entwickler-Rechners."
    )


def test_workers_derive_cwd_from_module_file(qapp, monkeypatch, tmp_path):
    """_check_version leitet den git-cwd aus __file__ ab.

    Wir patchen VersionCheckWorker, um den übergebenen cwd zu
    prüfen, ohne echten Netzwerk-Traffic. Erwartet: das
    Repo-Wurzelverzeichnis (chormanager/..) anhand der Moduldatei.
    """
    from chormanager.ui import update_controller as uc

    captured = {}

    class _FakeWorker:
        """Signal-Duck-Typ: finished-Attribut reicht für _check_version."""

        def __init__(self, repo=None, branch=None, cwd=None, parent=None):
            captured["cwd"] = cwd
            captured["repo"] = repo
            captured["branch"] = branch
            # .connect(...) wird aufgerufen — noop-Objekt genügt.
            self.finished = type("_Sig", (), {"connect": staticmethod(lambda *a, **k: None)})()

        def start(self):
            pass

    monkeypatch.setattr(uc, "VersionCheckWorker", _FakeWorker)

    dlg = uc.VersionCheckDialog()
    try:
        dlg._check_version()
        assert "cwd" in captured, "VersionCheckWorker wurde nicht aufgerufen"
        expected_root = Path(uc.__file__).resolve().parent.parent.parent.parent
        assert Path(captured["cwd"]).resolve() == expected_root, (
            f"cwd={captured['cwd']!r} ist nicht die aus __file__ "
            "abgeleitete Repo-Wurzel."
        )
    finally:
        dlg.deleteLater()


def test_update_pull_derives_cwd_from_module_file(qapp, monkeypatch):
    """Auch _do_update (git pull) darf kein hardcoded cwd nutzen."""
    from chormanager.ui import update_controller as uc

    captured = {}

    class _FakePullWorker:
        def __init__(self, cmd=None, cwd=None, timeout=60, parent=None):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            self.finished = type("_Sig", (), {"connect": staticmethod(lambda *a, **k: None)})()

        def start(self):
            pass

    monkeypatch.setattr(uc, "UpdateWorker", _FakePullWorker)

    dlg = uc.VersionCheckDialog()
    try:
        dlg._do_update()
        assert "cwd" in captured, "UpdateWorker wurde nicht aufgerufen"
        expected_root = Path(uc.__file__).resolve().parent.parent.parent.parent
        assert Path(captured["cwd"]).resolve() == expected_root
    finally:
        dlg.deleteLater()
