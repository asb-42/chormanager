"""Centralized async subprocess runner (M-1).

Sprint 2 deliverable: A single QObject-based subprocess runner that all
hot-paths in the application should use instead of blocking
``subprocess.run`` calls. Currently the module ships the runner; the
migration of the 7 hot-paths (``choraufstellung_launcher.py``,
``update_controller.py``, ``export_controller.py``, ``main_window.py``
git-describe) is planned for Sprint 3.

Why QProcess?
------------
QProcess is the Qt-native non-blocking subprocess wrapper. It integrates
with the Qt event loop without manual thread management and supports
signals for stdout/stderr chunks, finished-state, and error reporting.

This module deliberately has zero project-internal imports so it can be
tested in complete isolation (no Qt, no domain).
"""
from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass
class SubprocessResult:
    """Outcome of a finished subprocess invocation.

    Attributes:
        exit_code: Process exit code (``0`` typically means success).
        stdout: Captured stdout as str (only populated when ``capture_output`` is True).
        stderr: Captured stderr as str (only populated when ``capture_output`` is True).
        success: True iff ``exit_code == 0``.
        error_message: Optional human-readable error description (timeout, missing binary, etc.).
    """

    exit_code: int
    stdout: str
    stderr: str
    success: bool
    error_message: Optional[str] = None


class SubprocessRunner(QObject):
    """Async subprocess runner backed by :class:`QProcess`.

    Signals:
        started(): Emitted when the subprocess actually starts.
        stdout_chunk(str): Emitted for each stdout line (best-effort).
        stderr_chunk(str): Emitted for each stderr line (best-effort).
        finished(SubprocessResult): Emitted exactly once when the process ends.
    """

    started = pyqtSignal()
    stdout_chunk = pyqtSignal(str)
    stderr_chunk = pyqtSignal(str)
    finished = pyqtSignal(object)  # SubprocessResult

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._stdout_buf: str = ""
        self._stderr_buf: str = ""
        self._capture: bool = True
        self._on_done: Optional[Callable[[SubprocessResult], None]] = None
        self._timeout_ms: Optional[int] = None
        self._timeout_timer = None  # type: ignore[var-annotated]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_async(
        self,
        cmd: Sequence[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        on_done: Optional[Callable[[SubprocessResult], None]] = None,
    ) -> None:
        """Start ``cmd`` asynchronously. Returns immediately.

        Args:
            cmd: Argument list (preferred over shell=True to avoid injection).
            cwd: Optional working directory.
            env: Optional environment variables (merged with current env).
            timeout: Optional timeout in seconds; the process is killed on timeout.
            capture_output: If True, stdout/stderr are captured for the result.
            on_done: Optional callback invoked with the :class:`SubprocessResult`
                when the process finishes. Equivalent to connecting to the
                ``finished`` signal but a bit more ergonomic for one-shot calls.
        """
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            logger.warning("M-1: run_async called while another process is running; ignoring")
            return
        if not cmd:
            logger.warning("M-1: run_async called with empty command; ignoring")
            return

        # M-1 safety: shell-injection-Prävention. Wir akzeptieren NUR Listen.
        # (Defensive Programmering — Caller koennten versehentlich str übergeben.)
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)

        self._capture = capture_output
        self._stdout_buf = ""
        self._stderr_buf = ""
        self._on_done = on_done
        self._timeout_ms = int(timeout * 1000) if timeout else None

        proc = QProcess(self)
        if cwd:
            proc.setWorkingDirectory(cwd)
        if env is not None:
            import os
            merged = os.environ.copy()
            merged.update({str(k): str(v) for k, v in env.items()})
            proc.setEnvironment([f"{k}={v}" for k, v in merged.items()])

        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.readyReadStandardError.connect(self._on_stderr)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        proc.started.connect(self.started.emit)

        self._process = proc
        # QProcess.start erwartet (program, arguments)
        program, *args = list(cmd)
        proc.start(program, args)

        if self._timeout_ms is not None:
            self._start_timeout(self._timeout_ms)

    def is_running(self) -> bool:
        """Return True iff a subprocess is currently running."""
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def cancel(self) -> None:
        """Kill the running subprocess (if any)."""
        if self._process is not None and self.is_running():
            self._process.kill()

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------
    def _on_stdout(self) -> None:
        if self._process is None:
            return
        chunk = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not chunk:
            return
        if self._capture:
            self._stdout_buf += chunk
        for line in chunk.splitlines():
            self.stdout_chunk.emit(line)

    def _on_stderr(self) -> None:
        if self._process is None:
            return
        chunk = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        if not chunk:
            return
        if self._capture:
            self._stderr_buf += chunk
        for line in chunk.splitlines():
            self.stderr_chunk.emit(line)

    def _on_finished(self, exit_code: int, exit_status) -> None:
        self._cancel_timeout()
        # Drain remaining buffered output
        self._on_stdout()
        self._on_stderr()
        result = SubprocessResult(
            exit_code=int(exit_code),
            stdout=self._stdout_buf,
            stderr=self._stderr_buf,
            success=(int(exit_code) == 0 and exit_status == QProcess.ExitStatus.NormalExit),
        )
        if self._on_done is not None:
            try:
                self._on_done(result)
            except Exception as exc:  # noqa: BLE001
                logger.error("M-1: on_done callback raised: %s", exc)
        self.finished.emit(result)
        self._reset()

    def _on_error(self, error) -> None:
        # errorOccurred wird auch bei "normalen" Fehlern emittiert (z. B. FailedToStart).
        # Wir loggen es; finished wird danach i. d. R. auch emittiert.
        logger.warning("M-1: QProcess error: %s", error)

    def _start_timeout(self, timeout_ms: int) -> None:
        from PyQt6.QtCore import QTimer
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._on_timeout)
        timer.start(timeout_ms)
        self._timeout_timer = timer

    def _cancel_timeout(self) -> None:
        if self._timeout_timer is not None:
            self._timeout_timer.stop()
            self._timeout_timer = None

    def _on_timeout(self) -> None:
        if self.is_running():
            logger.warning("M-1: subprocess timeout reached; killing")
            self.cancel()

    def _reset(self) -> None:
        if self._process is not None:
            try:
                self._process.deleteLater()
            except RuntimeError:
                pass
        self._process = None
        self._on_done = None
        self._timeout_ms = None
        self._capture = True
        self._stdout_buf = ""
        self._stderr_buf = ""
