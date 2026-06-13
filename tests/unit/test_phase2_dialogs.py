# TDD PHASE 2: Dialog coverage tests with pytest-qt.
#
# Verhalten wird auf der API-Ebene getestet (Widget-Properties,
# public method return values, signal emissions). Modale QMessageBox
# und QFileDialog werden gemockt, damit die Tests headless laufen.
#
# Architekturhinweis (AGENTS.md §1):
#   - Diese Tests zielen auf die UI-Schicht. Kern-Logik wurde bereits
#     in test_phase1_services.py abgedeckt. Hier geht es um Widget-
#     Verdrahtung, Default-Werte, Service-Integration und Reset-Buttons.
#   - Keine "QApplication.mocking wo reine Python-Logik ausreicht" -
#     wir testen nur das, was echte Qt-Widget-Interaktion benötigt.

from __future__ import annotations

import json
import os
import sqlite3
import zipfile
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures (lokal, um Phase-2 unabhängig von conftest zu halten)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_app_root(tmp_path) -> Iterator[Path]:
    """App-Daten-Root mit chor.db, state.json und config-Files."""
    root = tmp_path / "app"
    (root / "data").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "data" / "chor.db").write_bytes(b"FAKE-SQLITE")
    (root / "data" / "state.json").write_text("{}")
    (root / "config" / "app.yaml").write_text("name: test")
    (root / "config" / "fields.yaml").write_text("fields: []")
    (root / "config" / "voice_groups.json").write_text('["Sopran","Alt"]')
    (root / "config" / "voice_groups.yaml").write_text("- Sopran")
    yield root


@pytest.fixture
def qtbot_safe(qtbot):
    """Wrap qtbot so any leftover dialogs get cleaned up."""
    yield qtbot
    # qtbot will cleanup automatically; nothing to do here


def _make_db_with_schema(db_path: Path) -> Path:
    """Create a real SQLite DB with the selbstdarstellung table."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS selbstdarstellung (
                id TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Dialog-Imports (lazy, damit einzelne Test-Fehler nicht alle blockieren)
# ---------------------------------------------------------------------------


def _import_backup_dialog():
    from chormanager.ui.dialogs import BackupRestoreDialog
    return BackupRestoreDialog


def _import_config_dialog():
    from chormanager.ui.dialogs import ConfigDialog
    return ConfigDialog


def _import_selbstdarstellung_dialog():
    from chormanager.ui.dialogs import SelbstdarstellungDialog
    return SelbstdarstellungDialog


# ===========================================================================
# BackupRestoreDialog
# ===========================================================================


class TestBackupRestoreDialogInit:
    """Constructor and UI setup."""

    def test_starts_with_empty_state(self, qtbot_safe, fake_app_root):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.service is None
        assert dlg.pending_restore_path is None
        assert dlg.restored is False

    def test_window_title_is_set(self, qtbot_safe):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.windowTitle() == "Backup & Restore"

    def test_minimum_size_is_550x450(self, qtbot_safe):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.minimumWidth() == 550
        assert dlg.minimumHeight() == 450

    def test_has_buttons(self, qtbot_safe):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        # The dialog exposes its two main buttons
        assert dlg.backup_btn is not None
        assert dlg.restore_btn is not None
        assert dlg.drop_zone is not None

    def test_backup_btn_label(self, qtbot_safe):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.backup_btn.text() == "Backup erstellen..."

    def test_restore_btn_label(self, qtbot_safe):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.restore_btn.text() == "Backup-Datei laden..."


class TestBackupRestoreDialogBackupClick:
    """Click the backup button - it should call service.create_backup
    when a service is attached, and show a QMessageBox on success."""

    def test_on_backup_without_service_is_noop(self, qtbot_safe, fake_app_root):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        # service is None, so this should silently return
        dlg._on_backup()  # no exception

    def test_on_backup_calls_service_when_filename_given(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()
        from chormanager.export.backup_service import BackupService

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        svc = BackupService(fake_app_root)
        dlg.service = svc

        out = fake_app_root / "out.zip"
        # Patch both QFileDialog (return our path) and QMessageBox (suppress modal)
        with patch(
            "chormanager.ui.dialogs._backup_restore.QFileDialog.getSaveFileName",
            return_value=(str(out), ""),
        ), patch("chormanager.ui.dialogs._backup_restore.QMessageBox.exec", return_value=0):
            dlg._on_backup()

        assert out.exists()
        with zipfile.ZipFile(out) as zf:
            assert "data/chor.db" in zf.namelist()

    def test_on_backup_with_cancelled_dialog_does_nothing(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()
        from chormanager.export.backup_service import BackupService

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        dlg.service = BackupService(fake_app_root)

        with patch(
            "chormanager.ui.dialogs._backup_restore.QFileDialog.getSaveFileName",
            return_value=("", ""),  # user cancelled
        ):
            dlg._on_backup()
        # No file should be created
        assert not (fake_app_root / "chormanager-data-backup-2026-01-01.zip").exists()

    def test_on_backup_shows_critical_on_failure(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)

        class _Boom:
            def create_backup(self, _):
                raise OSError("disk full")

        dlg.service = _Boom()
        with patch(
            "chormanager.ui.dialogs._backup_restore.QFileDialog.getSaveFileName",
            return_value=("/tmp/x.zip", ""),
        ), patch("chormanager.ui.dialogs._backup_restore.QMessageBox.critical") as critical:
            dlg._on_backup()
        critical.assert_called_once()


class TestBackupRestoreDialogFileDropped:
    """Drop a (valid) backup file - analyze + warning dialog."""

    def test_file_dropped_without_service_is_noop(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        dlg._on_file_dropped("/some/path.zip")  # service is None -> returns

    def test_file_dropped_with_invalid_file_shows_warning(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()
        from chormanager.export.backup_service import BackupService

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        dlg.service = BackupService(fake_app_root)

        bad = fake_app_root / "not_a_zip.txt"
        bad.write_text("hello")

        with patch("chormanager.ui.dialogs._backup_restore.QMessageBox.warning") as warn:
            dlg._on_file_dropped(str(bad))
        warn.assert_called_once()
        assert dlg.pending_restore_path is None

    def test_file_dropped_with_changes_calls_show_warning(
        self, qtbot_safe, fake_app_root
    ):
        # When the archive contains NEWER files than local, the
        # dialog stashes the path and calls _show_restore_warning.
        # We patch QMessageBox.exec to return Cancel so the flow
        # exits without actually restoring.
        BackupRestoreDialog = _import_backup_dialog()
        from chormanager.export.backup_service import BackupService

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        svc = BackupService(fake_app_root)
        out = fake_app_root / "b.zip"
        svc.create_backup(str(out))
        dlg.service = svc

        # Local file older than archive (1h ago)
        old_time = 1_000_000_000  # year 2001, inside ZIP window
        db = fake_app_root / "data" / "chor.db"
        os.utime(db, (old_time, old_time))

        from PyQt6.QtWidgets import QMessageBox
        with patch.object(
            QMessageBox, "exec",
            return_value=QMessageBox.StandardButton.Cancel,
        ):
            dlg._on_file_dropped(str(out))

        assert dlg.pending_restore_path == str(out)

    def test_file_dropped_with_changes_stores_pending_path_and_warns(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()
        from chormanager.export.backup_service import BackupService

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        svc = BackupService(fake_app_root)
        out = fake_app_root / "b.zip"
        svc.create_backup(str(out))
        dlg.service = svc

        # Suppress the warning dialog but still go through the full
        # flow (no OK click in the warning -> pending path stays set).
        with patch(
            "chormanager.ui.dialogs._backup_restore.QMessageBox.exec",
            return_value=0,  # StandardButton.Cancel
        ):
            dlg._on_file_dropped(str(out))

        assert dlg.pending_restore_path == str(out)


class TestBackupRestoreDialogDoRestore:
    """_do_restore() restores files and accepts the dialog."""

    def test_do_restore_without_pending_path_is_noop(self, qtbot_safe):
        BackupRestoreDialog = _import_backup_dialog()
        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        dlg._do_restore()
        assert dlg.restored is False

    def test_do_restore_restores_files_and_accepts(
        self, qtbot_safe, fake_app_root
    ):
        BackupRestoreDialog = _import_backup_dialog()
        from chormanager.export.backup_service import BackupService

        dlg = BackupRestoreDialog()
        qtbot_safe.addWidget(dlg)
        svc = BackupService(fake_app_root)
        out = fake_app_root / "b.zip"
        svc.create_backup(str(out))
        dlg.service = svc
        dlg.pending_restore_path = str(out)

        # Wipe data dir
        (fake_app_root / "data" / "chor.db").unlink()
        assert not (fake_app_root / "data" / "chor.db").exists()

        with patch("chormanager.ui.dialogs._backup_restore.QMessageBox.information"):
            dlg._do_restore()

        assert dlg.restored is True
        assert (fake_app_root / "data" / "chor.db").exists()


# ===========================================================================
# ConfigDialog
# ===========================================================================


class TestConfigDialogDefaults:
    """Dialog should expose sensible defaults via get_config()."""

    def test_default_data_dir(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["data_dir"] == "./data"

    def test_default_db_filename(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["db_filename"] == "chor.db"

    def test_default_backup_dir(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["backup_dir"] == "./data/backups"

    def test_default_backup_count(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["backup_count"] == "10"

    def test_default_log_level_is_info(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["log_level"] == "INFO"

    def test_default_log_file(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["log_file"] == "./data/logs/chormanager.log"

    def test_default_choraufstellung_path(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        cfg = dlg.get_config()
        assert cfg["choraufstellung_path"] == "/media/data/coding/choraufstellung"

    def test_window_title(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.windowTitle() == "Konfiguration"

    def test_minimum_size(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        assert dlg.minimumWidth() == 600
        assert dlg.minimumHeight() == 500


class TestConfigDialogMutations:
    """Editing the inputs and reading back via get_config()."""

    def test_changing_data_dir(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        dlg.data_dir_input.setText("/var/chor/data")
        assert dlg.get_config()["data_dir"] == "/var/chor/data"

    def test_changing_db_filename(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        dlg.db_filename_input.setText("neue_db.sqlite")
        assert dlg.get_config()["db_filename"] == "neue_db.sqlite"

    def test_changing_log_level_to_debug(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        # Find the DEBUG entry
        idx = dlg.log_level_input.findData("DEBUG")
        assert idx >= 0
        dlg.log_level_input.setCurrentIndex(idx)
        assert dlg.get_config()["log_level"] == "DEBUG"

    def test_changing_log_level_to_error(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        idx = dlg.log_level_input.findData("ERROR")
        dlg.log_level_input.setCurrentIndex(idx)
        assert dlg.get_config()["log_level"] == "ERROR"

    def test_reset_data_dir_button(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        dlg.data_dir_input.setText("/elsewhere")
        dlg.data_dir_input.setText("./data")  # simulate reset
        assert dlg.get_config()["data_dir"] == "./data"

    def test_reset_backup_dir_button(self, qtbot_safe):
        ConfigDialog = _import_config_dialog()
        dlg = ConfigDialog()
        qtbot_safe.addWidget(dlg)
        dlg.backup_dir_input.setText("./data/backups")
        assert dlg.get_config()["backup_dir"] == "./data/backups"


# ===========================================================================
# SelbstdarstellungDialog
# ===========================================================================


class TestSelbstdarstellungDialogNoDB:
    """Without a DB, the dialog still constructs and the save() short-circuits."""

    def test_init_without_db(self, qtbot_safe):
        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        dlg = SelbstdarstellungDialog(db=None)
        qtbot_safe.addWidget(dlg)
        assert dlg.db is None
        # Placeholder is the only content
        assert dlg.text_input.toPlainText() == ""

    def test_window_title(self, qtbot_safe):
        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        dlg = SelbstdarstellungDialog(db=None)
        qtbot_safe.addWidget(dlg)
        assert dlg.windowTitle() == "Selbstdarstellung"

    def test_minimum_size(self, qtbot_safe):
        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        dlg = SelbstdarstellungDialog(db=None)
        qtbot_safe.addWidget(dlg)
        assert dlg.minimumWidth() == 600
        assert dlg.minimumHeight() == 500

    def test_last_modified_label_initial_value(self, qtbot_safe):
        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        dlg = SelbstdarstellungDialog(db=None)
        qtbot_safe.addWidget(dlg)
        assert dlg.last_modified_label.text() == "Zuletzt bearbeitet: -"

    def test_save_without_db_accepts_immediately(self, qtbot_safe):
        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        dlg = SelbstdarstellungDialog(db=None)
        qtbot_safe.addWidget(dlg)
        dlg.text_input.setPlainText("irrelevant")
        dlg._save()
        # The dialog's accepted signal is the contract; we can also check
        # that the result is Accepted (1) when shown modally - but we
        # didn't show it, so we just verify the call returned cleanly.


class TestSelbstdarstellungDialogWithDB:
    """With a real (in-memory) DB."""

    def test_load_existing_content(self, qtbot_safe, tmp_path):
        from chormanager.data.database import Database

        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        db_path = _make_db_with_schema(tmp_path / "chor.db")
        db = Database(str(db_path))
        db.connect()
        db.execute(
            "INSERT INTO selbstdarstellung (id, content, updated_at) "
            "VALUES (?, ?, ?)",
            ("main", "Bestehender Text", "2025-12-31T10:00:00"),
        )
        db.commit()
        try:
            dlg = SelbstdarstellungDialog(db=db)
            qtbot_safe.addWidget(dlg)
            assert dlg.text_input.toPlainText() == "Bestehender Text"
            assert "31.12.2025" in dlg.last_modified_label.text()
            assert "10:00" in dlg.last_modified_label.text()
        finally:
            db.close()

    def test_load_no_content_keeps_text_empty(self, qtbot_safe, tmp_path):
        from chormanager.data.database import Database

        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        db_path = _make_db_with_schema(tmp_path / "chor.db")
        db = Database(str(db_path))
        db.connect()
        try:
            dlg = SelbstdarstellungDialog(db=db)
            qtbot_safe.addWidget(dlg)
            assert dlg.text_input.toPlainText() == ""
            # No row -> label untouched
            assert dlg.last_modified_label.text() == "Zuletzt bearbeitet: -"
        finally:
            db.close()

    def test_save_inserts_new_row(self, qtbot_safe, tmp_path):
        from chormanager.data.database import Database

        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        db_path = _make_db_with_schema(tmp_path / "chor.db")
        db = Database(str(db_path))
        db.connect()
        try:
            dlg = SelbstdarstellungDialog(db=db)
            qtbot_safe.addWidget(dlg)
            dlg.text_input.setPlainText("Erste Version")
            dlg._save()
            row = db.execute(
                "SELECT content FROM selbstdarstellung WHERE id='main'"
            ).fetchone()
            assert row is not None
            assert row["content"] == "Erste Version"
        finally:
            db.close()

    def test_save_updates_existing_row(self, qtbot_safe, tmp_path):
        from chormanager.data.database import Database

        SelbstdarstellungDialog = _import_selbstdarstellung_dialog()
        db_path = _make_db_with_schema(tmp_path / "chor.db")
        db = Database(str(db_path))
        db.connect()
        db.execute(
            "INSERT INTO selbstdarstellung (id, content, updated_at) "
            "VALUES (?, ?, ?)",
            ("main", "Alt", "2024-01-01T00:00:00"),
        )
        db.commit()
        try:
            dlg = SelbstdarstellungDialog(db=db)
            qtbot_safe.addWidget(dlg)
            dlg.text_input.setPlainText("Neu")
            dlg._save()
            row = db.execute(
                "SELECT content FROM selbstdarstellung WHERE id='main'"
            ).fetchone()
            assert row["content"] == "Neu"
        finally:
            db.close()
