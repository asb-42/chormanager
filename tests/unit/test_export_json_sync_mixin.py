# TDD RED: Regression tests for M-1 Schritt 7b — ExportJsonSyncMixin.
#
# Five "sync" methods move into
# ``chormanager.ui.export_controller.ExportJsonSyncMixin``:
#
#   * ``_export_singers_json``
#   * ``_export_events_json``
#   * ``_export_availability_json``
#   * ``_export_singers_csv``
#   * ``_export_all_sync``
#
# All five wrap calls to ``chormanager.export.sync.*`` helpers.
# The Mixin must be inherited by ``MainWindow`` and the methods
# must be defined in the Mixin (not duplicated in main_window).

from __future__ import annotations

import importlib
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. The Mixin exists and exposes the JSON-sync methods.
# ---------------------------------------------------------------------------

class TestExportJsonSyncMixinExists:
    def test_module_exports_mixin(self):
        mod = importlib.import_module("chormanager.ui.export_controller")
        assert hasattr(mod, "ExportJsonSyncMixin"), (
            "ExportJsonSyncMixin must be exported from "
            "chormanager.ui.export_controller"
        )

    def test_mixin_has_all_json_sync_methods(self):
        from chormanager.ui.export_controller import ExportJsonSyncMixin
        for name in (
            "_export_singers_json",
            "_export_events_json",
            "_export_availability_json",
            "_export_singers_csv",
            "_export_all_sync",
        ):
            assert hasattr(ExportJsonSyncMixin, name), (
                f"ExportJsonSyncMixin is missing {name}"
            )


# ---------------------------------------------------------------------------
# 2. MainWindow inherits the Mixin.
# ---------------------------------------------------------------------------

class TestMainWindowInheritsJsonSyncMixin:
    def test_main_window_inherits_json_sync_mixin(self):
        from chormanager.ui.main_window import MainWindow
        from chormanager.ui.export_controller import ExportJsonSyncMixin
        assert issubclass(MainWindow, ExportJsonSyncMixin)


# ---------------------------------------------------------------------------
# 3. Methods *defined* in the Mixin (not duplicated).
# ---------------------------------------------------------------------------

class TestJsonSyncMethodsMovedToMixin:
    def _qualname(self, name):
        from chormanager.ui.export_controller import ExportJsonSyncMixin
        return getattr(ExportJsonSyncMixin, name).__qualname__

    def test_export_singers_json_defined_in_mixin(self):
        assert self._qualname("_export_singers_json").startswith(
            "ExportJsonSyncMixin."
        )

    def test_export_events_json_defined_in_mixin(self):
        assert self._qualname("_export_events_json").startswith(
            "ExportJsonSyncMixin."
        )

    def test_export_availability_json_defined_in_mixin(self):
        assert self._qualname("_export_availability_json").startswith(
            "ExportJsonSyncMixin."
        )

    def test_export_singers_csv_defined_in_mixin(self):
        assert self._qualname("_export_singers_csv").startswith(
            "ExportJsonSyncMixin."
        )

    def test_export_all_sync_defined_in_mixin(self):
        assert self._qualname("_export_all_sync").startswith(
            "ExportJsonSyncMixin."
        )


# ---------------------------------------------------------------------------
# 4. Behavioural tests with a stub window.
# ---------------------------------------------------------------------------

class _StubMainWindow:
    def __init__(self) -> None:
        self.db = object()
        self.db_path = "/tmp/test-chor.db"
        self.statusBar_calls = []

    def statusBar(self):
        outer = self

        class _B:
            def showMessage(self_, msg):
                outer.statusBar_calls.append(msg)

        return _B()


def _patch_msgboxes(monkeypatch):
    """Patch QMessageBox.information / .warning so the stub object
    (which is not a real QWidget) is accepted as parent."""
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda *a, **kw: None),
    )
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda *a, **kw: None),
    )


@pytest.fixture
def stub_window() -> Iterator[_StubMainWindow]:
    from chormanager.ui.export_controller import ExportJsonSyncMixin

    class W(_StubMainWindow, ExportJsonSyncMixin):
        pass

    yield W()


class TestExportJsonSingers:
    def test_calls_sync_helper_with_db_and_path(
        self, stub_window, tmp_path, monkeypatch
    ):
        from PyQt6.QtWidgets import QFileDialog
        _patch_msgboxes(monkeypatch)

        out = str(tmp_path / "singers.json")
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(
                lambda *a, **kw: (out, "JSON Dateien (*.json)")
            ),
        )
        with patch(
            "chormanager.export.sync.export_singers_json"
        ) as helper:
            stub_window._export_singers_json()
        from pathlib import Path
        helper.assert_called_once_with(stub_window.db, Path(out))
        assert any("exportiert" in m for m in stub_window.statusBar_calls)

    def test_user_cancel_does_nothing(
        self, stub_window, monkeypatch
    ):
        from PyQt6.QtWidgets import QFileDialog
        _patch_msgboxes(monkeypatch)

        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *a, **kw: ("", "")),
        )
        with patch(
            "chormanager.export.sync.export_singers_json"
        ) as helper:
            stub_window._export_singers_json()
        assert not helper.called


class TestExportJsonEvents:
    def test_calls_sync_helper(
        self, stub_window, tmp_path, monkeypatch
    ):
        from PyQt6.QtWidgets import QFileDialog
        _patch_msgboxes(monkeypatch)

        out = str(tmp_path / "events.json")
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(
                lambda *a, **kw: (out, "JSON Dateien (*.json)")
            ),
        )
        with patch(
            "chormanager.export.sync.export_events_json"
        ) as helper:
            stub_window._export_events_json()
        from pathlib import Path
        helper.assert_called_once_with(stub_window.db, Path(out))


class TestExportJsonAvailability:
    def test_calls_sync_helper(
        self, stub_window, tmp_path, monkeypatch
    ):
        from PyQt6.QtWidgets import QFileDialog
        _patch_msgboxes(monkeypatch)

        out = str(tmp_path / "availability.json")
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(
                lambda *a, **kw: (out, "JSON Dateien (*.json)")
            ),
        )
        with patch(
            "chormanager.export.sync.export_availability_json"
        ) as helper:
            stub_window._export_availability_json()
        from pathlib import Path
        helper.assert_called_once_with(stub_window.db, Path(out))


class TestExportSingersCsv:
    def test_calls_sync_helper(
        self, stub_window, tmp_path, monkeypatch
    ):
        from PyQt6.QtWidgets import QFileDialog
        _patch_msgboxes(monkeypatch)

        out = str(tmp_path / "singers.csv")
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(
                lambda *a, **kw: (out, "CSV Dateien (*.csv)")
            ),
        )
        with patch(
            "chormanager.export.sync.export_singers_csv"
        ) as helper:
            stub_window._export_singers_csv()
        from pathlib import Path
        helper.assert_called_once_with(stub_window.db, Path(out))


class TestExportAllSync:
    def test_calls_helper_and_shows_status(
        self, stub_window, monkeypatch
    ):
        _patch_msgboxes(monkeypatch)
        with patch(
            "chormanager.export.sync.export_all_sync",
            return_value={"singers": "/tmp/singers.json"},
        ) as helper:
            stub_window._export_all_sync()
        helper.assert_called_once_with(stub_window.db)
        # Status message must be shown with the file path
        assert any(
            "Alle Sync-Dateien" in m
            for m in stub_window.statusBar_calls
        )
