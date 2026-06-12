# TDD RED: Regression tests for M-1 Schritt 7a — Export-Core Mixin.
#
# We extract the "core" export methods into
# ``chormanager.ui.export_controller.ExportCoreMixin``:
#
#   * ``_export_csv``                     → CSV via QFileDialog
#   * ``_export_pdf``                     → PDF via reportlab
#   * ``_export_libreoffice``             → ODT/ODS via ExportService
#   * ``_export_response_matrix``         → PDF or ODT response matrix
#   * ``_get_export_config_for_current_tab`` → tab → (table, tab_attr, repo_attr, name)
#   * ``_export_tab_generic``             → dispatch via _get_export_config_for_current_tab
#   * ``_export_project_libreoffice``     → switches to tab 0 + generic
#   * ``_export_project_csv``             → switches to tab 0 + generic
#   * ``_export_tab``                     → switches to given tab + generic
#   * ``_export_tab_csv``                 → switches to given tab + generic
#
# All ten methods must survive the extraction byte-for-byte.
#
# Tests run WITHOUT writing real files — QFileDialog, ExportDialog and
# the QMessageBox are all patched.

from __future__ import annotations

import importlib
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# 1. The Mixin exists and exposes the core methods.
# ---------------------------------------------------------------------------

class TestExportCoreMixinExists:
    """M-1 step 7a: the Export-Core methods must now live in
    ``chormanager.ui.export_controller.ExportCoreMixin``."""

    def test_module_exists(self):
        mod = importlib.import_module("chormanager.ui.export_controller")
        assert hasattr(mod, "ExportCoreMixin"), (
            "ExportCoreMixin must be exported from "
            "chormanager.ui.export_controller"
        )

    def test_mixin_has_all_core_methods(self):
        from chormanager.ui.export_controller import ExportCoreMixin
        for name in (
            "_export_csv",
            "_export_pdf",
            "_export_libreoffice",
            "_export_response_matrix",
            "_get_export_config_for_current_tab",
            "_export_tab_generic",
            "_export_project_libreoffice",
            "_export_project_csv",
            "_export_tab",
            "_export_tab_csv",
        ):
            assert hasattr(ExportCoreMixin, name), (
                f"ExportCoreMixin is missing {name}"
            )


# ---------------------------------------------------------------------------
# 2. MainWindow inherits the Mixin.
# ---------------------------------------------------------------------------

class TestMainWindowInheritsCoreMixin:
    def test_main_window_inherits_core_mixin(self):
        from chormanager.ui.main_window import MainWindow
        from chormanager.ui.export_controller import ExportCoreMixin
        assert issubclass(MainWindow, ExportCoreMixin), (
            "MainWindow must inherit from ExportCoreMixin"
        )


# ---------------------------------------------------------------------------
# 3. Methods *defined* in the Mixin (proves extraction, not duplication).
# ---------------------------------------------------------------------------

class TestCoreMethodsMovedToMixin:
    def _qualname(self, name):
        from chormanager.ui.export_controller import ExportCoreMixin
        return getattr(ExportCoreMixin, name).__qualname__

    def test_export_csv_defined_in_mixin(self):
        assert self._qualname("_export_csv").startswith("ExportCoreMixin.")

    def test_export_pdf_defined_in_mixin(self):
        assert self._qualname("_export_pdf").startswith("ExportCoreMixin.")

    def test_export_libreoffice_defined_in_mixin(self):
        assert self._qualname("_export_libreoffice").startswith("ExportCoreMixin.")

    def test_export_response_matrix_defined_in_mixin(self):
        assert self._qualname("_export_response_matrix").startswith(
            "ExportCoreMixin."
        )

    def test_get_export_config_defined_in_mixin(self):
        assert self._qualname(
            "_get_export_config_for_current_tab"
        ).startswith("ExportCoreMixin.")

    def test_export_tab_generic_defined_in_mixin(self):
        assert self._qualname("_export_tab_generic").startswith(
            "ExportCoreMixin."
        )

    def test_export_project_libreoffice_defined_in_mixin(self):
        assert self._qualname("_export_project_libreoffice").startswith(
            "ExportCoreMixin."
        )

    def test_export_project_csv_defined_in_mixin(self):
        assert self._qualname("_export_project_csv").startswith(
            "ExportCoreMixin."
        )

    def test_export_tab_defined_in_mixin(self):
        assert self._qualname("_export_tab").startswith("ExportCoreMixin.")

    def test_export_tab_csv_defined_in_mixin(self):
        assert self._qualname("_export_tab_csv").startswith("ExportCoreMixin.")


# ---------------------------------------------------------------------------
# 4. Tab-export-config is preserved.
# ---------------------------------------------------------------------------

class TestTabExportConfig:
    """The four-tab export configuration must remain the same
    shape, in the same place. Other code may import the mapping
    via the Mixin (the production code reads it as
    ``self._TAB_EXPORT_CONFIG``)."""

    def test_mixin_exposes_tab_export_config(self):
        from chormanager.ui.export_controller import ExportCoreMixin
        assert hasattr(ExportCoreMixin, "_TAB_EXPORT_CONFIG")
        cfg = ExportCoreMixin._TAB_EXPORT_CONFIG
        # Sanity: four well-known keys
        for key in ("projekte", "saenger", "besetzung", "termine"):
            assert key in cfg
            table, tab_attr, repo_attr, label = cfg[key]
            assert isinstance(table, str)
            assert isinstance(tab_attr, str)
            assert isinstance(repo_attr, str)
            assert isinstance(label, str)


# ---------------------------------------------------------------------------
# 5. Behaviour: helpers return the right config for a tab index.
# ---------------------------------------------------------------------------

class _StubStack:
    """Stub for ``QStackedWidget``: stores the current index and
    records every ``setCurrentIndex`` call."""

    def __init__(self, tab_index: int = 0) -> None:
        self._tab_index = tab_index
        self.set_calls = []

    def currentIndex(self) -> int:
        return self._tab_index

    def setCurrentIndex(self, index: int) -> None:
        self.set_calls.append(index)
        self._tab_index = index


class _StubMainWindow:
    """Bare object that records calls and stores attributes used by
    the Mixin methods. The ``QMessageBox`` calls inside the mixin
    accept this object as a parent (it is not a real QWidget but
    ``information()``/``critical()`` will short-circuit on the
    ``None`` parent check via our patch).
    """

    def __init__(self, tab_index: int = 0) -> None:
        self._tab_index = tab_index
        self.content_stack = _StubStack(tab_index)
        self.statusBar_calls = []

    def statusBar(self):
        outer = self

        class _B:
            def showMessage(self_, msg):
                outer.statusBar_calls.append(msg)

        return _B()


@pytest.fixture
def stub_window() -> Iterator[_StubMainWindow]:
    from chormanager.ui.export_controller import ExportCoreMixin

    class W(_StubMainWindow, ExportCoreMixin):
        pass

    yield W()


class TestGetExportConfigForCurrentTab:
    @pytest.mark.parametrize(
        "tab_index, expected_key",
        [
            (0, "projekte"),
            (1, "saenger"),
            (2, "besetzung"),
            (3, "termine"),
        ],
    )
    def test_known_tabs_return_their_config(
        self, stub_window, tab_index, expected_key
    ):
        from chormanager.ui.export_controller import ExportCoreMixin
        stub_window.content_stack._tab_index = tab_index
        cfg = stub_window._get_export_config_for_current_tab()
        assert cfg is not None
        assert cfg == ExportCoreMixin._TAB_EXPORT_CONFIG[expected_key]

    def test_unknown_tab_returns_none(self, stub_window):
        stub_window.content_stack._tab_index = 99
        assert stub_window._get_export_config_for_current_tab() is None


# ---------------------------------------------------------------------------
# 6. Behaviour: the tab switcher helpers switch the stack and call
#    _export_tab_generic.
# ---------------------------------------------------------------------------

class TestTabSwitcherHelpers:
    def test_export_project_libreoffice_switches_to_tab_0(
        self, stub_window
    ):
        with patch.object(
            stub_window, "_export_tab_generic"
        ) as gen:
            stub_window._export_project_libreoffice()
        gen.assert_called_once_with()
        assert stub_window.content_stack.set_calls == [0]

    def test_export_project_csv_switches_to_tab_0(self, stub_window):
        with patch.object(
            stub_window, "_export_tab_generic"
        ) as gen:
            stub_window._export_project_csv()
        gen.assert_called_once_with()
        assert stub_window.content_stack.set_calls == [0]

    def test_export_tab_switches_to_given_index(self, stub_window):
        with patch.object(
            stub_window, "_export_tab_generic"
        ) as gen:
            stub_window._export_tab(2)
        gen.assert_called_once_with()
        assert stub_window.content_stack.set_calls == [2]

    def test_export_tab_csv_switches_to_given_index(self, stub_window):
        with patch.object(
            stub_window, "_export_tab_generic"
        ) as gen:
            stub_window._export_tab_csv(3)
        gen.assert_called_once_with()
        assert stub_window.content_stack.set_calls == [3]


# ---------------------------------------------------------------------------
# 7. CSV export writes a real CSV file via QFileDialog-cancel path.
# ---------------------------------------------------------------------------

class TestExportCsvNoopOnCancel:
    def test_export_csv_does_nothing_when_user_cancels(
        self, stub_window, tmp_path, monkeypatch
    ):
        # Provide a singer_repo with no entries
        stub_window.singer_repo = type(
            "R", (), {"get_all": lambda self_: []}
        )()
        stub_window.singers_tab = type(
            "T", (), {"visible_fields": [{"name": "full_name"}]}
        )()
        # User cancels the dialog
        from PyQt6.QtWidgets import QFileDialog

        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *a, **kw: ("", "")),
        )
        # Patch open() to detect any (unwanted) call
        with patch("builtins.open") as open_patch:
            stub_window._export_csv()
        assert not open_patch.called, (
            "If the user cancels the file dialog, no file may be written."
        )


# ---------------------------------------------------------------------------
# 8. Response-matrix export calls build_response_matrix and writes a file
# ---------------------------------------------------------------------------

class TestExportResponseMatrixHappyPath:
    def test_export_response_matrix_calls_renderers(
        self, stub_window, tmp_path, monkeypatch
    ):
        """Walking through the happy path: project is set, user
        picks PDF, the renderer writes a real file. We patch:
          * ``ExportFormatDialog`` (.exec → Accepted, .selected_format
            → 'pdf', .get_save_path → real tmp file)
          * ``build_response_matrix`` → returns a fake matrix with
            one column
          * ``render_response_matrix_pdf`` → writes a fixed byte
            string to the destination
        """
        from PyQt6.QtWidgets import QDialog

        out_pdf = str(tmp_path / "matrix.pdf")

        # Fake current project
        class _P:
            id = "p1"
            name = "TestChor"

        stub_window.current_project = _P()

        # projects_tab stub: only current_project is read
        stub_window.projects_tab = type("P", (), {"current_project": _P()})()

        # Mock db: connection is passed to get_table_fields etc.
        # (not actually called in this test, but referenced)
        stub_window.db = type("D", (), {"get_connection": lambda self_: None})()

        # ---- Patch the heavy pieces ----------------------------------
        # 1) build_response_matrix returns a matrix-like object with
        #    ``.columns`` (so the early-return is skipped) and whatever
        #    else the renderer needs.
        class _FakeMatrix:
            columns = ["2026-06-12"]
            rows = []

        monkeypatch.setattr(
            "chormanager.core.response_matrix.build_response_matrix",
            lambda **kw: _FakeMatrix(),
        )

        # 2) ExportFormatDialog: exec → Accepted, selected_format → 'pdf'
        class _FakeFmtDlg:
            def __init__(self, *a, **kw):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            @property
            def selected_format(self):
                return "pdf"

            @staticmethod
            def get_save_path(parent, fmt, default_name):
                return out_pdf

        # The mixin imports ExportFormatDialog lazily inside the
        # method, so we patch the source module's name.
        monkeypatch.setattr(
            "chormanager.ui.export_format_dialog.ExportFormatDialog",
            _FakeFmtDlg,
        )

        # 3) render_response_matrix_pdf: write our magic bytes
        def _fake_render_pdf(matrix, path):
            with open(path, "wb") as f:
                f.write(b"%PDF-1.4 stub")

        monkeypatch.setattr(
            "chormanager.core.response_render_pdf.render_response_matrix_pdf",
            _fake_render_pdf,
        )

        # 4) repositories: each returns an empty result.
        class _R:
            def __init__(self, *a, **kw):
                pass

            def get_active(self):
                return []

            def get_all(self):
                return []

            def get_by_event(self, eid):
                return []

        monkeypatch.setattr(
            "chormanager.domain.repository.SingerRepository", _R
        )
        monkeypatch.setattr(
            "chormanager.domain.repository.EventRepository", _R
        )
        monkeypatch.setattr(
            "chormanager.domain.repository.AvailabilityRepository", _R
        )
        monkeypatch.setattr(
            "chormanager.domain.repository.BesetzungRepository", _R
        )

        # 5) get_last_active_besetzung_id returns None
        monkeypatch.setattr(
            "chormanager.config.get_last_active_besetzung_id",
            lambda: None,
        )

        stub_window._export_response_matrix()

        # File was written by the patched renderer
        with open(out_pdf, "rb") as f:
            assert b"PDF" in f.read()
