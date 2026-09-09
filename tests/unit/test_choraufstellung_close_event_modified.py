"""Regression tests for the ``closeEvent`` modified-state bug (merge fix).

Bug (found while merging origin/main 2026-06): ``MainWindow.is_modified``
was converted from a plain attribute into the AutoSaveController protocol
*method* ``is_modified()`` (M-2 Schritt 7). ``closeEvent`` still evaluated
``if self.is_modified:`` — which is a bound method and therefore ALWAYS
truthy. As a result the "Ungespeichert" ``QMessageBox.question`` was
shown even for a pristine, unmodified window.

In offscreen/CI environments the modal question dialog blocks forever,
hanging the whole test suite.

Contract pinned by these tests:

* ``is_modified`` must be callable and return a ``bool``.
* ``closeEvent`` must consult the *return value* of ``is_modified()``,
  not the truthiness of the bound method.
* With ``is_modified() == False`` the close event must be accepted
  WITHOUT any dialog interaction (patched QMessageBox proves the
  question is never asked).
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest import mock

import pytest

from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestIsModifiedProtocol:
    """MainWindow must expose is_modified() as a callable returning bool."""

    def test_is_modified_is_callable_returning_bool(self, monkeypatch, tmp_path):
        from chormanager.choraufstellung.main import MainWindow

        monkeypatch.setattr(
            "chormanager.choraufstellung.config.get_data_dir",
            lambda: str(tmp_path),
        )
        w = MainWindow(chormanager_mode=False)
        try:
            assert callable(w.is_modified)
            result = w.is_modified()
            assert isinstance(result, bool)
            # A freshly created window must not be modified.
            assert result is False
        finally:
            w.deleteLater()

    def test_has_file_is_callable_returning_bool(self, monkeypatch, tmp_path):
        from chormanager.choraufstellung.main import MainWindow

        monkeypatch.setattr(
            "chormanager.choraufstellung.config.get_data_dir",
            lambda: str(tmp_path),
        )
        w = MainWindow(chormanager_mode=False)
        try:
            assert callable(w.has_file)
            assert isinstance(w.has_file(), bool)
            assert w.has_file() is False
        finally:
            w.deleteLater()


class TestCloseEventModifiedCheck:
    """closeEvent must evaluate is_modified() — not the bound method."""

    def test_close_event_accepts_without_dialog_when_not_modified(
        self, monkeypatch, tmp_path
    ):
        """With is_modified() == False the window must close silently.

        The QMessageBox.question must NOT be called. If closeEvent
        still evaluates the truthy bound method, the question dialog
        fires (and blocks forever offscreen) — the patched
        QMessageBox would catch the call and fail the assertion.
        """
        from chormanager.choraufstellung import main as ca_main
        from PyQt6.QtGui import QCloseEvent

        monkeypatch.setattr(
            "chormanager.choraufstellung.config.get_data_dir",
            lambda: str(tmp_path),
        )
        w = ca_main.MainWindow(chormanager_mode=False)
        assert w.is_modified() is False

        with mock.patch.object(ca_main.QMessageBox, "question") as q:
            event = QCloseEvent()
            w.closeEvent(event)
            assert q.called is False, (
                "closeEvent must not ask 'Änderungen speichern?' when "
                "is_modified() is False — the bound-method bug makes "
                "self.is_modified always truthy."
            )
            assert event.isAccepted(), (
                "closeEvent must accept the event for an unmodified window."
            )

    def test_close_event_asks_when_modified(self, monkeypatch, tmp_path):
        """With is_modified() == True the user MUST be asked."""
        from chormanager.choraufstellung import main as ca_main
        from PyQt6.QtGui import QCloseEvent
        from PyQt6.QtWidgets import QMessageBox

        monkeypatch.setattr(
            "chormanager.choraufstellung.config.get_data_dir",
            lambda: str(tmp_path),
        )
        w = ca_main.MainWindow(chormanager_mode=False)
        w._is_modified = True

        with mock.patch.object(
            ca_main.QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Discard,
        ) as q:
            event = QCloseEvent()
            w.closeEvent(event)
            assert q.called is True, (
                "closeEvent must ask 'Änderungen speichern?' when "
                "is_modified() is True."
            )
            assert event.isAccepted()
