"""Sprint 2 Regression-Tests: SubprocessRunner + M1-FIX-A API surface.

Tests run with a Qt event loop (pytest-qt). We use simple `echo`-style
subprocesses (or a small Python subprocess) to verify the async runner.
"""
from __future__ import annotations

import sys
import time

import pytest

from chormanager.ui.subprocess_runner import SubprocessRunner, SubprocessResult


# Skip the whole module on non-Linux (echo behaves differently)
pytestmark = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="echo on Linux/macOS only"
)


# ---------------------------------------------------------------------------
# Smoke / import
# ---------------------------------------------------------------------------

def test_runner_imports_cleanly():
    from chormanager.ui.subprocess_runner import SubprocessRunner
    assert SubprocessRunner is not None


def test_runner_has_expected_signals():
    runner = SubprocessRunner()
    # Signals exist as attributes on QObject subclasses
    assert hasattr(runner, "started")
    assert hasattr(runner, "finished")
    assert hasattr(runner, "stdout_chunk")
    assert hasattr(runner, "stderr_chunk")


# ---------------------------------------------------------------------------
# Real subprocess execution
# ---------------------------------------------------------------------------

def test_run_async_completes_with_success(qtbot):
    """Run `python -c 'print(2+2)'` and verify exit_code=0, stdout=4."""
    runner = SubprocessRunner()
    results = []
    runner.finished.connect(lambda r: results.append(r))

    runner.run_async([sys.executable, "-c", "print(2+2)"], capture_output=True)

    qtbot.waitUntil(lambda: len(results) == 1, timeout=5000)
    result = results[0]
    assert isinstance(result, SubprocessResult)
    assert result.exit_code == 0
    assert result.success is True
    assert "4" in result.stdout


def test_run_async_nonzero_exit(qtbot):
    """Run a subprocess that returns exit code 7 — verify success=False."""
    runner = SubprocessRunner()
    results = []
    runner.finished.connect(lambda r: results.append(r))

    runner.run_async([sys.executable, "-c", "import sys; sys.exit(7)"])

    qtbot.waitUntil(lambda: len(results) == 1, timeout=5000)
    result = results[0]
    assert result.exit_code == 7
    assert result.success is False


def test_run_async_on_done_callback(qtbot):
    """The on_done callable is invoked exactly once with the result."""
    runner = SubprocessRunner()
    captured = []
    runner.run_async(
        [sys.executable, "-c", "print('hello')"],
        on_done=lambda r: captured.append(r),
    )
    qtbot.waitUntil(lambda: len(captured) == 1, timeout=5000)
    assert captured[0].exit_code == 0
    assert "hello" in captured[0].stdout


def test_run_async_rejects_empty_cmd():
    """Calling run_async with empty list is a no-op (logs warning, doesn't crash)."""
    runner = SubprocessRunner()
    runner.run_async([])  # must not raise
    assert not runner.is_running()


def test_run_async_ignores_during_running(qtbot):
    """If a subprocess is already running, second call is ignored."""
    runner = SubprocessRunner()
    # Use sleep 1 as long-running cmd
    runner.run_async([sys.executable, "-c", "import time; time.sleep(1)"])
    assert runner.is_running()
    # Second call should be ignored
    runner.run_async([sys.executable, "-c", "print('x')"])
    qtbot.wait(200)  # short wait
    # Cleanup
    runner.cancel()
    qtbot.wait(1500)


# ---------------------------------------------------------------------------
# Sprint 2 P1 fixes (R6, M2, M7, A5+M5)
# ---------------------------------------------------------------------------

def test_chormanager_bridge_logs_error_on_bad_json(tmp_path, caplog):
    """M-2 Fix: bad JSON triggers logger.error, not print."""
    from chormanager.choraufstellung.chormanager_bridge import ChorManagerBridge

    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    host = type("H", (), {"_loaded_metadata": None, "singers": [], "pool": type("P", (), {"singers": [], "update_singers": lambda self, s, p: None})(), "grid": type("G", (), {"get_placed_singer_ids": lambda self: set()})(), "_is_modified": False})()
    bridge = ChorManagerBridge(host)
    with caplog.at_level("ERROR"):
        result = bridge.load_from_json(str(bad))
    assert result is False
    # Logger was used (not print)
    assert any("Error reading event data file" in rec.message for rec in caplog.records)


def test_validate_choraufstellung_path_nonexistent(tmp_path, caplog):
    """M-7 Fix: nonexistent path logs a warning."""
    from chormanager.ui.choraufstellung_launcher import validate_choraufstellung_path

    fake = str(tmp_path / "does_not_exist")
    with caplog.at_level("WARNING"):
        result = validate_choraufstellung_path(fake)
    assert result is False
    assert any("choraufstellung_path" in rec.message for rec in caplog.records)


def test_validate_choraufstellung_path_valid(tmp_path):
    """M-7 Fix: real choraufstellung/ with __main__.py is valid."""
    from chormanager.ui.choraufstellung_launcher import validate_choraufstellung_path

    real = "chormanager/choraufstellung"
    assert validate_choraufstellung_path(real) is True


# ---------------------------------------------------------------------------
# Sprint 2.4 Hotfix: _rehydrate_singers muss Singer-Instanzen tolerieren
# ---------------------------------------------------------------------------

def test_rehydrate_singers_accepts_singer_instances():
    """A-5/M-5 Hotfix: _rehydrate_singers darf nicht scheitern,
    wenn ``data["singers"]`` bereits hydrierte Singer-Instanzen enthaelt
    (z. B. Recovery-Pfad)."""
    from chormanager.choraufstellung.file_io import FormationFileIO
    from chormanager.choraufstellung.singer_model import Singer, VoiceGroup

    real_singer = Singer(
        name="X",
        voice_group=VoiceGroup("Sopran 1"),
        height=170,
        singer_id="abc",
        row=0,
        col=0,
    )
    payload = [real_singer]
    runner = FormationFileIO.__new__(FormationFileIO)  # avoid __init__
    out = runner._rehydrate_singers(payload)
    assert len(out) == 1
    # Duck-Type-Check statt isinstance, weil Singer ueber zwei verschiedene
    # Modul-Pfade geladen werden kann.
    assert out[0] is real_singer  # unchanged passthrough
    assert out[0].name == "X"
    assert out[0].singer_id == "abc"


def test_rehydrate_singers_handles_dict_payload():
    """A-5/M-5: dict-Payload wird via Singer.from_dict hydriert."""
    from chormanager.choraufstellung.file_io import FormationFileIO

    payload = [{
        "name": "DictSinger",
        "voice_group": "Sopran 1",
        "height": 170,
        "singer_id": "x1",
        "row": 1,
        "col": 2,
    }]
    runner = FormationFileIO.__new__(FormationFileIO)
    out = runner._rehydrate_singers(payload)
    assert len(out) == 1
    # Duck-Type-Check
    assert out[0].name == "DictSinger"
    assert out[0].singer_id == "x1"
    assert out[0].row == 1
    assert out[0].col == 2


def test_rehydrate_singers_skips_invalid_entries():
    """A-5/M-5: None / unerwartete Typen werden uebersprungen, nicht gecrasht."""
    from chormanager.choraufstellung.file_io import FormationFileIO

    payload = [None, "string", 42, {"name": "OK", "voice_group": "Sopran 1"}]
    runner = FormationFileIO.__new__(FormationFileIO)
    out = runner._rehydrate_singers(payload)
    # None, str, int werden uebersprungen; das dict wird hydriert
    assert len(out) == 1
    assert out[0].name == "OK"


def test_load_formation_data_with_mixed_singers_does_not_crash():
    """Reproduziert den Sprint-2.4-App-Start-Bug.

    Vor dem Hotfix: ``_rehydrate_singers`` rief ``Singer.from_dict(p)`` mit
    ``p`` als bereits-hydrierter Singer-Instanz auf und warf
    ``AttributeError: 'Singer' object has no attribute 'get'``.

    Erwartet nach Fix: gemischte Liste wird verarbeitet, kein Crash.
    """
    from chormanager.choraufstellung.file_io import FormationFileIO
    from chormanager.choraufstellung.singer_model import Singer, VoiceGroup

    runner = FormationFileIO.__new__(FormationFileIO)

    real_singer = Singer(
        name="Real",
        voice_group=VoiceGroup("Sopran 1"),
        height=170,
        singer_id="r1",
        row=0,
        col=0,
    )
    mixed = [
        real_singer,
        {"name": "Dict", "voice_group": "Sopran 1", "height": 170,
         "singer_id": "d1", "row": 0, "col": 1},
    ]
    out = runner._rehydrate_singers(mixed)
    assert len(out) == 2
    # Erste Position: original-Instanz unveraendert
    assert out[0] is real_singer
    # Zweite Position: hydratisierter Singer
    assert out[1].name == "Dict"
    assert out[1].singer_id == "d1"
    assert out[1].row == 0
    assert out[1].col == 1
