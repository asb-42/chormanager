"""TDD RED: C-3 Sub-Plan \u2014 QThread-Wrapper f\u00fcr ``_check_version`` / ``_do_update``.

The legacy implementation runs ``urllib.request.urlopen`` and
``subprocess.run`` directly on the GUI thread, with
``QApplication.processEvents()`` as a workaround. C-3 (subplan_update_controller.md)
replaces this with a ``QThread`` worker so the UI stays responsive.

Acceptance:
* ``_check_version`` does not call ``QApplication.processEvents()``.
* ``subprocess.run`` for the git pull uses ``timeout=60``.
* A worker ``VersionCheckWorker(QObject, moveToThread)`` is available
  for the new async pipeline.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def test_check_version_does_not_call_processevents(qapp):
    """The legacy QApplication.processEvents() workaround must be gone."""
    from chormanager.ui.update_controller import VersionCheckDialog
    src_path = os.path.join(os.path.dirname(__file__), "..", "..", "chormanager", "ui", "update_controller.py")
    src_path = os.path.abspath(src_path)
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    # Allowed only in _do_update (legacy) \u2014 stricter: just assert it's gone.
    # We allow it in docstrings / comments but not in method bodies.
    # Heuristic: must not appear inside _check_version.
    if "def _check_version" in src:
        # Extract _check_version body and assert.
        start = src.find("def _check_version")
        end = src.find("\n    def ", start + 1)
        if end == -1:
            end = len(src)
        body = src[start:end]
        assert "QApplication.processEvents" not in body, (
            "C-3: _check_version must not use QApplication.processEvents(); "
            "the QThread-worker is the replacement."
        )


def test_do_update_subprocess_has_timeout(qapp):
    """The git pull must have a timeout so a hung network fails fast."""
    src_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "chormanager", "ui", "update_controller.py"
    ))
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    if "def _do_update" in src:
        start = src.find("def _do_update")
        end = src.find("\n    def ", start + 1)
        if end == -1:
            end = len(src)
        body = src[start:end]
        assert "timeout" in body, (
            "C-3: _do_update's subprocess.run must have a timeout argument"
        )


def test_version_check_worker_class_exists(qapp):
    """The new async worker must be importable."""
    try:
        from chormanager.ui.update_controller import VersionCheckWorker
        # We don't instantiate (would start a thread); just check the class.
        assert hasattr(VersionCheckWorker, "finished")
        assert hasattr(VersionCheckWorker, "run")
    except ImportError:
        pytest.fail(
            "C-3: VersionCheckWorker (QThread-migration) is not yet "
            "implemented; see subplan_update_controller.md."
        )


def test_dialog_check_version_does_not_block_ui(qapp, monkeypatch):
    """The legacy _check_version used to call QApplication.processEvents
    in a tight loop. The new pipeline must not: it must delegate to
    a worker and return immediately. We assert this by patching the
    underlying urllib.request to raise and verifying the dialog does
    NOT block forever."""
    from chormanager.ui.update_controller import VersionCheckDialog
    from PyQt6.QtCore import QTimer

    def boom(*a, **kw):
        raise RuntimeError("simulated network error")
    monkeypatch.setattr("urllib.request.urlopen", boom)

    dlg = VersionCheckDialog()
    # If the call blocks the GUI thread, this QTimer would never fire.
    timer_fired = {"v": False}
    def on_timeout():
        timer_fired["v"] = True
        dlg.reject()
    QTimer.singleShot(50, on_timeout)
    # Call _check_version; it must return without blocking.
    dlg._check_version()
    # Pump the event loop briefly to let the timer fire.
    from PyQt6.QtCore import QEventLoop
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()
    assert timer_fired["v"], (
        "C-3: _check_version blocked the GUI thread; the timer never fired."
    )
