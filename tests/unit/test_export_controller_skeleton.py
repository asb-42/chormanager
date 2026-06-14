"""TDD: A-1 ExportController(QObject) skeleton.

Verifies the new ``ExportController`` class is importable, has
the required signals, and can be instantiated with a host.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def test_export_controller_is_qobject(qapp):
    from chormanager.ui.export_controller import ExportController
    from PyQt6.QtCore import QObject
    assert issubclass(ExportController, QObject)


def test_export_controller_has_required_signals(qapp):
    from chormanager.ui.export_controller import ExportController
    assert hasattr(ExportController, "export_finished")
    assert hasattr(ExportController, "export_failed")


def test_export_controller_can_be_constructed_with_host(qapp):
    from chormanager.ui.export_controller import ExportController
    host = object()  # minimal stand-in for MainWindow
    ec = ExportController(host)
    assert ec.parent() is None
    assert ec._host is host


def test_export_csv_emits_finished_signal(qapp, tmp_path):
    from chormanager.ui.export_controller import ExportController
    ec = ExportController(object())
    received = []
    ec.export_finished.connect(received.append)
    target = str(tmp_path / "out.csv")
    assert ec.export_csv(target) is True
    assert received == [target]
    # File was actually written.
    assert os.path.exists(target)


def test_export_csv_emits_failed_signal_on_permission_error(qapp):
    from chormanager.ui.export_controller import ExportController
    ec = ExportController(object())
    received = []
    ec.export_failed.connect(received.append)
    # ``/dev/null/x.csv`` is not writable on Linux; the test is
    # best-effort: if the OS allows it, the test is a no-op.
    import os as _os
    if _os.name == "posix" and _os.path.exists("/dev/full"):
        target = "/dev/full/out.csv"
    else:
        # Use a path that is not writable: a non-existent dir.
        target = "/this/path/does/not/exist/out.csv"
    assert ec.export_csv(target) is False
    assert len(received) == 1
