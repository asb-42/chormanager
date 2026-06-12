# TDD RED: Regression tests for M-1 Schritt 7c — ExportTabSpecificMixin.
#
# Three tab-specific export methods move into
# ``chormanager.ui.export_controller.ExportTabSpecificMixin``:
#
#   * ``_export_besetzung``
#   * ``_export_termine``
#   * ``_export_aufstellung``
#
# Each method:
#   1. Defines a hard-coded list of fields for the tab.
#   2. Opens an ``ExportDialog`` (user picks fields + format).
#   3. Pulls data from the corresponding tab's repo.
#   4. Calls the appropriate ``ExportService`` method (writer/calc/csv).
#   5. Asks for a save file via ``QFileDialog``.
#   6. Writes the file and shows a status message.

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. The Mixin exists and exposes the three methods.
# ---------------------------------------------------------------------------

class TestExportTabSpecificMixinExists:
    def test_module_exports_mixin(self):
        mod = importlib.import_module("chormanager.ui.export_controller")
        assert hasattr(mod, "ExportTabSpecificMixin")

    def test_mixin_has_all_tab_specific_methods(self):
        from chormanager.ui.export_controller import ExportTabSpecificMixin
        for name in (
            "_export_besetzung",
            "_export_termine",
            "_export_aufstellung",
        ):
            assert hasattr(ExportTabSpecificMixin, name), (
                f"ExportTabSpecificMixin is missing {name}"
            )


# ---------------------------------------------------------------------------
# 2. MainWindow inherits the Mixin.
# ---------------------------------------------------------------------------

class TestMainWindowInheritsTabSpecificMixin:
    def test_main_window_inherits(self):
        from chormanager.ui.main_window import MainWindow
        from chormanager.ui.export_controller import ExportTabSpecificMixin
        assert issubclass(MainWindow, ExportTabSpecificMixin)


# ---------------------------------------------------------------------------
# 3. Methods *defined* in the Mixin.
# ---------------------------------------------------------------------------

class TestTabSpecificMethodsMovedToMixin:
    def _qualname(self, name):
        from chormanager.ui.export_controller import ExportTabSpecificMixin
        return getattr(ExportTabSpecificMixin, name).__qualname__

    def test_export_besetzung_defined_in_mixin(self):
        assert self._qualname("_export_besetzung").startswith(
            "ExportTabSpecificMixin."
        )

    def test_export_termine_defined_in_mixin(self):
        assert self._qualname("_export_termine").startswith(
            "ExportTabSpecificMixin."
        )

    def test_export_aufstellung_defined_in_mixin(self):
        assert self._qualname("_export_aufstellung").startswith(
            "ExportTabSpecificMixin."
        )


# ---------------------------------------------------------------------------
# 4. Behavioural tests with a stub.
# ---------------------------------------------------------------------------

class _StubExportDialog:
    """Stand-in for ``ExportDialog``: lets the test control the
    user's selection of fields and format."""

    def __init__(self, fields, parent, *, accept=True, fmt="csv",
                 selected=None):
        self.fields = fields
        self._accept = accept
        self._fmt = fmt
        self._selected = selected if selected is not None else [f["name"] for f in fields]

    def exec(self):
        from PyQt6.QtWidgets import QDialog
        return QDialog.DialogCode.Accepted if self._accept else QDialog.DialogCode.Rejected

    def get_selected_fields(self):
        return self._selected

    def get_export_format(self):
        return self._fmt


class _StubMainWindow:
    def __init__(self) -> None:
        self.db = object()
        self.db_path = "/tmp/test-chor.db"
        self.statusBar_calls = []
        # Each tab exposes the relevant repo via .<name>_repo
        self.besetzung_tab = type(
            "B", (), {"besetzung_repo": type("R", (), {"get_all": lambda self_: []})()}
        )()
        self.events_tab = type(
            "E", (), {"event_repo": type("R", (), {"get_all": lambda self_: []})()}
        )()
        self.choraufstellung_tab = type(
            "C", (), {"_data_dir": str(tmp_path) if False else "/tmp/choraufstellung"}
        )()
        # In real runs the choraufstellung_tab._data_dir is set to a
        # real data directory; here we just point it at /tmp.

    def statusBar(self):
        outer = self

        class _B:
            def showMessage(self_, msg):
                outer.statusBar_calls.append(msg)

        return _B()


def _patch_msgboxes(monkeypatch):
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
    from chormanager.ui.export_controller import ExportTabSpecificMixin

    class W(_StubMainWindow, ExportTabSpecificMixin):
        pass

    yield W()


def _patch_export_service(monkeypatch, content="<html>body</html>"):
    """Patch ExportService methods to return predictable content."""
    from chormanager.core.export_service import ExportService

    monkeypatch.setattr(
        ExportService, "get_table_fields",
        lambda self_, conn, table: [
            {"name": "id"}, {"name": "name"}, {"name": "value"},
        ],
    )
    monkeypatch.setattr(
        ExportService, "get_export_data",
        lambda self_, items, fields: [{"id": "1", "name": "x", "value": "v"}],
    )
    monkeypatch.setattr(
        ExportService, "export_to_csv",
        lambda self_, data, fields: "id,name,value\n1,x,v\n",
    )
    monkeypatch.setattr(
        ExportService, "export_to_libreoffice_writer",
        lambda self_, data, fields: content,
    )
    monkeypatch.setattr(
        ExportService, "export_to_libreoffice_calc",
        lambda self_, data, fields: content,
    )


# ---------------------------------------------------------------------------
# 5. Per-method behavioural tests
# ---------------------------------------------------------------------------

class TestExportBesetzung:
    def test_user_cancel_does_nothing(
        self, stub_window, tmp_path, monkeypatch
    ):
        from PyQt6.QtWidgets import QFileDialog
        _patch_msgboxes(monkeypatch)

        monkeypatch.setattr(
            "chormanager.ui.export_controller.ExportDialog",
            lambda fields, parent: _StubExportDialog(
                fields, parent, accept=False
            ),
        )
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: ("", "")),
        )
        # Must not raise and must not write any file
        with patch("builtins.open") as open_patch:
            stub_window._export_besetzung()
        assert not open_patch.called

    def test_csv_writes_file_and_status(
        self, stub_window, tmp_path, monkeypatch
    ):
        _patch_msgboxes(monkeypatch)
        _patch_export_service(monkeypatch)
        from PyQt6.QtWidgets import QFileDialog

        out = str(tmp_path / "besetzung.csv")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: (out, "CSV (*.csv)")),
        )
        monkeypatch.setattr(
            "chormanager.ui.export_controller.ExportDialog",
            lambda fields, parent: _StubExportDialog(
                fields, parent, accept=True, fmt="csv",
            ),
        )
        # Patch the workdir mkdir
        monkeypatch.setattr(
            "chormanager.ui.export_controller.Path",
            lambda p: Path(tmp_path),
        )
        # Patch export_to_csv so it returns something deterministic
        with patch(
            "chormanager.core.export_service.ExportService.export_to_csv",
            return_value="id,name,value\n1,x,v\n",
        ):
            stub_window._export_besetzung()
        # The file must have been written
        assert Path(out).exists()
        assert Path(out).read_text(encoding="utf-8").startswith("id,name,value")


class TestExportTermine:
    def test_writer_writes_html(
        self, stub_window, tmp_path, monkeypatch
    ):
        _patch_msgboxes(monkeypatch)
        from PyQt6.QtWidgets import QFileDialog

        out = str(tmp_path / "termine.html")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: (out, "LibreOffice Writer (*.odt)")),
        )
        monkeypatch.setattr(
            "chormanager.ui.export_controller.ExportDialog",
            lambda fields, parent: _StubExportDialog(
                fields, parent, accept=True, fmt="writer",
            ),
        )
        monkeypatch.setattr(
            "chormanager.ui.export_controller.Path",
            lambda p: Path(tmp_path),
        )
        with patch(
            "chormanager.core.export_service.ExportService.export_to_libreoffice_writer",
            return_value="<html><body>termine</body></html>",
        ):
            stub_window._export_termine()
        assert Path(out).exists()
        assert "termine" in Path(out).read_text(encoding="utf-8")


class TestExportAufstellung:
    def test_calc_writes_file(
        self, stub_window, tmp_path, monkeypatch
    ):
        _patch_msgboxes(monkeypatch)
        from PyQt6.QtWidgets import QFileDialog

        out = str(tmp_path / "aufstellung.ods")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: (out, "LibreOffice Calc (*.ods)")),
        )
        monkeypatch.setattr(
            "chormanager.ui.export_controller.ExportDialog",
            lambda fields, parent: _StubExportDialog(
                fields, parent, accept=True, fmt="calc",
            ),
        )
        monkeypatch.setattr(
            "chormanager.ui.export_controller.Path",
            lambda p: Path(tmp_path),
        )
        with patch(
            "chormanager.core.export_service.ExportService.export_to_libreoffice_calc",
            return_value="sep=;\n1;x;v\n",
        ):
            stub_window._export_aufstellung()
        assert Path(out).exists()
        assert "sep" in Path(out).read_text(encoding="utf-8")
