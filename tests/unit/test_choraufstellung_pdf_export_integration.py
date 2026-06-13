"""TDD RED: Regression tests for M-2 Schritt 9 — PDFExportBridge extrahieren.

The bridge encapsulates ``MainWindow.export_pdf`` so that the menu
action and any future programmatic caller (ChorManager launcher,
command-line exporter) all go through a single, testable class.

Public surface:
* ``PDFExportBridge(host, pdf, grid)``         — constructor
* ``PDFExportBridge.run(event_info=None)``    — show dialog + write PDF
* ``PDFExportBridge.default_filename()``      — deterministic file name
* ``PDFExportBridge.default_subtitle()``      — ``"{project}: {name} - {date}"``
* ``PDFExportBridge.workdir()``               — ``<data-dir>/../workdir`` (created)

The class is **lazy-Qt**: only the ``run()`` method touches Qt
widgets.  The non-Qt helpers are unit-tested without an event loop.
"""
from __future__ import annotations

import os
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pytest


# --- helpers ----------------------------------------------------------------

class _FakeSinger:
    def __init__(self, name: str = "Muster, Max", singer_id: str = "1"):
        self.name = name
        self.singer_id = singer_id
        self.row = -1
        self.col = -1


class _FakeGrid:
    def __init__(self, rows: int = 3, cols: int = 4, singers: Optional[list] = None):
        self.rows = rows
        self.cols = cols
        self.singers = singers or []
        self.staggered = False


class _FakePdfExporter:
    """Records calls to ``export_formation``; returns ``ok`` flag."""

    def __init__(self, *, ok: bool = True):
        self.ok = ok
        self.calls: List[dict] = []

    def export_formation(self, singers, rows, cols, filepath, **kwargs) -> bool:
        self.calls.append({
            "singers": singers, "rows": rows, "cols": cols,
            "filepath": filepath, "kwargs": kwargs,
        })
        return self.ok


class _FakeHost:
    """Stand-in for MainWindow with only the attributes the bridge reads."""

    def __init__(self, pdf: _FakePdfExporter, grid: _FakeGrid,
                 singers: Optional[list] = None,
                 event_date: str = "", event_name: str = "",
                 project_name: str = ""):
        self.pdf = pdf
        self.grid = grid
        self.singers = singers if singers is not None else []
        self.event_date = event_date
        self.event_name = event_name
        self.project_name = project_name
        # The bridge may open the workdir in the file system
        self._opened_urls: List[str] = []
        self._infos: List[tuple] = []
        self._warnings: List[tuple] = []
        # The bridge may monkey-patch a "PDFExportDialog" mock; we expose
        # the dialog factory via attribute so tests can swap it.
        self.dialog_calls: List[dict] = []

    def open_url(self, url: str) -> None:
        self._opened_urls.append(url)


# --- tests -------------------------------------------------------------------

class TestModuleShape:
    def test_pdf_export_integration_module_exists(self):
        try:
            from pdf_export_integration import PDFExportBridge  # noqa: F401
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"pdf_export_integration module missing: {exc}")

    def test_pdf_export_bridge_is_a_class(self):
        from pdf_export_integration import PDFExportBridge
        assert isinstance(PDFExportBridge, type)

    def test_pdf_export_bridge_api(self):
        from pdf_export_integration import PDFExportBridge
        for name in ("run", "default_filename", "default_subtitle", "workdir"):
            assert hasattr(PDFExportBridge, name), f"missing method: {name}"


class TestDefaultFilename:
    def test_uses_event_date_when_available(self):
        from pdf_export_integration import PDFExportBridge
        host = _FakeHost(_FakePdfExporter(), _FakeGrid(), event_date="2026-12-24")
        bridge = PDFExportBridge(host)
        name = bridge.default_filename()
        assert name.startswith("choraufstellung-2026-12-24-version-")
        assert name.endswith(".pdf")

    def test_falls_back_to_today_when_no_event_date(self):
        from pdf_export_integration import PDFExportBridge
        host = _FakeHost(_FakePdfExporter(), _FakeGrid())
        bridge = PDFExportBridge(host)
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in bridge.default_filename()


class TestDefaultSubtitle:
    def test_empty_when_no_event_metadata(self):
        from pdf_export_integration import PDFExportBridge
        bridge = PDFExportBridge(_FakeHost(_FakePdfExporter(), _FakeGrid()))
        assert bridge.default_subtitle() == ""

    def test_contains_event_name(self):
        from pdf_export_integration import PDFExportBridge
        host = _FakeHost(_FakePdfExporter(), _FakeGrid(),
                         event_name="Weihnachtskonzert")
        bridge = PDFExportBridge(host)
        assert "Weihnachtskonzert" in bridge.default_subtitle()

    def test_contains_event_date(self):
        from pdf_export_integration import PDFExportBridge
        host = _FakeHost(_FakePdfExporter(), _FakeGrid(),
                         event_date="2026-12-24")
        bridge = PDFExportBridge(host)
        assert "2026-12-24" in bridge.default_subtitle()

    def test_project_name_prefixes_subtitle(self):
        from pdf_export_integration import PDFExportBridge
        host = _FakeHost(_FakePdfExporter(), _FakeGrid(),
                         project_name="Chor A",
                         event_name="Konzert", event_date="2026-12-24")
        bridge = PDFExportBridge(host)
        subtitle = bridge.default_subtitle()
        assert subtitle.startswith("Chor A:")


class TestWorkdir:
    def test_workdir_creates_directory(self, tmp_path: Path, monkeypatch):
        from pdf_export_integration import PDFExportBridge
        # Provide a fake config.get_data_dir that returns tmp/data
        data_dir = tmp_path / "data"
        workdir = tmp_path / "workdir"
        # The bridge calls ``get_data_dir()`` from the local config module
        # We monkey-patch that import inside the bridge module.
        monkeypatch.setattr(
            "pdf_export_integration.get_data_dir",
            lambda: str(data_dir),
            raising=False,
        )
        host = _FakeHost(_FakePdfExporter(), _FakeGrid())
        bridge = PDFExportBridge(host)
        wd = bridge.workdir()
        assert Path(wd).exists()
        # workdir should be a sibling of data_dir
        assert wd.endswith("workdir")


class TestRunWritesFile:
    """``run()`` integrates dialog + write — we monkey-patch the dialog."""

    def test_run_writes_file_when_dialog_accepted(self, tmp_path: Path, monkeypatch):
        from pdf_export_integration import PDFExportBridge
        pdf = _FakePdfExporter(ok=True)
        grid = _FakeGrid()
        host = _FakeHost(pdf, grid, singers=[_FakeSinger()])
        bridge = PDFExportBridge(host)

        # Stub the dialog factory
        class _AcceptedDialog:
            def __init__(self, *a, **kw):
                pass
            def exec(self):
                return 1  # Accepted
            def get_settings(self):
                return {
                    "filename": "out.pdf",
                    "orientation": "landscape",
                    "color_mode": "color",
                    "text_rotation": "horizontal",
                }

        monkeypatch.setattr(
            "pdf_export_integration._PDFExportDialog",
            _AcceptedDialog,
            raising=False,
        )
        monkeypatch.setattr(
            "pdf_export_integration.get_data_dir",
            lambda: str(tmp_path / "data"),
            raising=False,
        )

        # We must also stub QMessageBox.information and QDesktopServices.openUrl
        # for the success path. Since the bridge imports them lazily, we
        # patch the bridge module's references after import.
        import pdf_export_integration as mod  # noqa: WPS433
        infos: list = []
        warnings: list = []
        monkeypatch.setattr(mod, "QMessageBox",
                            types.SimpleNamespace(
                                information=lambda *a, **k: infos.append(a) or 0,
                                warning=lambda *a, **k: warnings.append(a) or 0,
                            ), raising=False)
        monkeypatch.setattr(mod, "QDesktopServices",
                            types.SimpleNamespace(openUrl=lambda url: None),
                            raising=False)

        bridge.run()

        # The bridge must have called the PDF exporter exactly once
        assert len(pdf.calls) == 1
        call = pdf.calls[0]
        assert call["rows"] == 3
        assert call["cols"] == 4
        assert call["filepath"].endswith("out.pdf")
        assert call["kwargs"]["orientation"] == "landscape"

    def test_run_is_noop_when_dialog_cancelled(self, tmp_path: Path, monkeypatch):
        from pdf_export_integration import PDFExportBridge
        pdf = _FakePdfExporter(ok=True)
        host = _FakeHost(pdf, _FakeGrid())
        bridge = PDFExportBridge(host)

        class _CancelledDialog:
            def __init__(self, *a, **kw):
                pass
            def exec(self):
                return 0  # Rejected
            def get_settings(self):
                raise AssertionError("should not be called")

        monkeypatch.setattr(
            "pdf_export_integration._PDFExportDialog",
            _CancelledDialog,
            raising=False,
        )
        monkeypatch.setattr(
            "pdf_export_integration.get_data_dir",
            lambda: str(tmp_path / "data"),
            raising=False,
        )

        bridge.run()
        # No PDF was written
        assert pdf.calls == []

    def test_run_shows_warning_when_pdf_export_fails(self, tmp_path: Path, monkeypatch):
        from pdf_export_integration import PDFExportBridge
        pdf = _FakePdfExporter(ok=False)
        host = _FakeHost(pdf, _FakeGrid())
        bridge = PDFExportBridge(host)

        class _AcceptedDialog:
            def __init__(self, *a, **kw):
                pass
            def exec(self):
                return 1
            def get_settings(self):
                return {
                    "filename": "out.pdf",
                    "orientation": "landscape",
                    "color_mode": "color",
                    "text_rotation": "horizontal",
                }

        monkeypatch.setattr(
            "pdf_export_integration._PDFExportDialog",
            _AcceptedDialog,
            raising=False,
        )
        monkeypatch.setattr(
            "pdf_export_integration.get_data_dir",
            lambda: str(tmp_path / "data"),
            raising=False,
        )

        import pdf_export_integration as mod  # noqa: WPS433
        warnings: list = []
        monkeypatch.setattr(mod, "QMessageBox",
                            types.SimpleNamespace(
                                information=lambda *a, **k: 0,
                                warning=lambda *a, **k: warnings.append(a) or 0,
                            ), raising=False)
        monkeypatch.setattr(mod, "QDesktopServices",
                            types.SimpleNamespace(openUrl=lambda url: None),
                            raising=False)

        bridge.run()
        # A warning was shown
        assert len(warnings) == 1
        # QMessageBox.warning(parent, title, text) — message text is at [2]
        assert "fehlgeschlagen" in warnings[0][2].lower()
