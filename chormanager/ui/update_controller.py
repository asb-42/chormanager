"""Update controller: version check and self-update dialog.

C-3 (subplan_update_controller.md): the blocking HTTP + git
operations run in :class:`VersionCheckWorker` and
:class:`UpdateWorker` (both QThread subclasses). The legacy
``QApplication.processEvents()`` workaround is removed.

A re-export at the original location
(``chormanager.ui.main_window.VersionCheckDialog``) is preserved
for backward compatibility with any external import.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class VersionCheckDialog(QDialog):
    """Dialog for checking application version (QThread-based, C-3)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Version prüfen")
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Aktuelle Version: Unbekannt")
        self.info_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.info_label)

        self.status_label = QLabel("Bereit zur Prüfung...")
        self.status_label.setStyleSheet("padding: 10px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        button_box = QDialogButtonBox()
        self.check_btn = QPushButton("Auf neue Version prüfen")
        self.check_btn.clicked.connect(self._check_version)
        button_box.addButton(self.check_btn, QDialogButtonBox.ButtonRole.ActionRole)

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.reject)
        button_box.addButton(close_btn, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(button_box)

    def _check_version(self):
        """Check GitHub for newer version on branch 'main'.

        Delegates to :class:`VersionCheckWorker` so the UI thread
        is never blocked.
        """
        self.status_label.setText("Prüfe GitHub Repository...")
        self._worker = VersionCheckWorker(
            repo="asb-42/chormanager", branch="main",
            cwd="/media/data/coding/chormanager",
        )
        self._worker.finished.connect(self._on_check_finished)
        self._worker.start()

    def _on_check_finished(self, result: dict) -> None:
        if "error" in result:
            self.status_label.setText(f"Fehler bei der Prüfung: {result['error']}")
            return
        local_sha = result.get("local_sha", "?")
        remote_sha = result.get("remote_sha", "?")
        self.info_label.setText(f"Lokal: {local_sha} | Remote: {remote_sha}")
        if remote_sha != local_sha:
            self.status_label.setText(f"Update verfügbar: {remote_sha}")
            self.check_btn.setText("Update durchführen")
            try:
                self.check_btn.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.check_btn.clicked.connect(self._do_update)
        else:
            self.status_label.setText("Code ist aktuell")

    def _do_update(self):
        """Pull new code from GitHub (QThread, C-3, timeout=60)."""
        self.status_label.setText("Aktualisiere von GitHub...")
        self._pull_worker = UpdateWorker(
            cmd=['git', 'pull', 'origin', 'main'],
            cwd="/media/data/coding/chormanager",
        )
        self._pull_worker.finished.connect(self._on_pull_finished)
        self._pull_worker.start()

    def _on_pull_finished(self, result: dict) -> None:
        if result.get("ok"):
            self.status_label.setText("Aktualisierung erfolgreich! Bitte App neu starten.")
            self.check_btn.setEnabled(False)
        else:
            self.status_label.setText(
                f"Update fehlgeschlagen: {result.get('error', '?')}"
            )


class VersionCheckWorker(QThread):
    """HTTP GET to GitHub + local ``git rev-parse`` in a worker thread.

    Emits ``finished(dict)`` with either
    ``{"local_sha": "...", "remote_sha": "..."}`` on success, or
    ``{"error": "..."}`` on any failure.
    """

    finished = pyqtSignal(dict)

    def __init__(self, repo: str, branch: str, cwd: str, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._branch = branch
        self._cwd = cwd

    def run(self) -> None:  # QThread entry point
        try:
            import json
            import subprocess
            import urllib.request

            url = f"https://api.github.com/repos/{self._repo}/branches/{self._branch}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "ChorManager")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                remote_sha = data["commit"]["sha"].strip()[:7]

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self._cwd, timeout=10,
            )
            local_sha = result.stdout.strip()[:7]
            self.finished.emit({"local_sha": local_sha, "remote_sha": remote_sha})
        except Exception as exc:  # noqa: BLE001
            self.finished.emit({"error": str(exc)})


class UpdateWorker(QThread):
    """``git pull`` in a worker thread, with a hard 60 s timeout (C-3)."""

    finished = pyqtSignal(dict)

    def __init__(self, cmd: list, cwd: str, timeout: int = 60, parent=None):
        super().__init__(parent)
        self._cmd = cmd
        self._cwd = cwd
        self._timeout = timeout

    def run(self) -> None:
        try:
            import subprocess
            result = subprocess.run(
                self._cmd, capture_output=True, text=True,
                cwd=self._cwd, timeout=self._timeout,
            )
            if result.returncode == 0:
                self.finished.emit({"ok": True, "stdout": result.stdout})
            else:
                self.finished.emit(
                    {"ok": False, "error": result.stderr or "non-zero exit"}
                )
        except Exception as exc:  # noqa: BLE001
            self.finished.emit({"ok": False, "error": str(exc)})
