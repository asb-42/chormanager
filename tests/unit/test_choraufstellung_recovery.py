"""TDD RED: Regression tests for M-2 Schritt 11 — RecoveryController extrahieren.

The controller encapsulates the autosave-recovery flow:

* ask :class:`FormationStorage` for the latest autosave path
* compare its mtime to ``host.last_manual_save_mtime``
* if newer, show a "Wiederherstellen?" question
* on "Yes", call back into the host's ``_load_formation_data`` and
  mark the formation as modified

The class is **lazy-Qt**: only the dialog call requires a running
QApplication. The "has autosave?" / "is it newer?" decision is pure
Python and unit-tested with a fake storage and a fake host.
"""
from __future__ import annotations

import os
import sys
import time
import types
from pathlib import Path
from typing import Any, List, Optional

import pytest


# --- helpers ----------------------------------------------------------------

class _FakeStorage:
    """Recording stand-in for :class:`FormationStorage`."""

    def __init__(self, autosave_path: Optional[str] = None,
                 autosave_mtime: float = 0.0,
                 load_payload: Optional[dict] = None):
        self._autosave_path = autosave_path
        self._autosave_mtime = autosave_mtime
        self._load_payload = load_payload
        self.load_calls: List[str] = []
        self.get_latest_calls: int = 0

    def get_latest_autosave_path(self) -> Optional[str]:
        self.get_latest_calls += 1
        return self._autosave_path

    def get_latest_autosave_mtime(self) -> float:
        return self._autosave_mtime

    def load_formation(self, filepath: str) -> Optional[dict]:
        self.load_calls.append(filepath)
        return self._load_payload


class _FakeHost:
    """Stand-in for :class:`MainWindow`."""

    def __init__(self, last_manual_save_mtime: float = 0.0):
        self.last_manual_save_mtime = last_manual_save_mtime
        self.file: Optional[str] = None
        self._is_modified: bool = False
        self._loaded_metadata: dict = {}
        self._load_formation_data_calls: List[dict] = []

    def _load_formation_data(self, data: dict) -> None:
        self._load_formation_data_calls.append(data)


# --- tests -------------------------------------------------------------------

class TestModuleShape:
    def test_recovery_module_exists(self):
        try:
            from recovery import RecoveryController  # noqa: F401
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"recovery module missing: {exc}")

    def test_recovery_controller_is_a_class(self):
        from recovery import RecoveryController
        assert isinstance(RecoveryController, type)

    def test_recovery_controller_api(self):
        from recovery import RecoveryController
        for name in ("check",):
            assert hasattr(RecoveryController, name), f"missing method: {name}"


class TestCheckSilentWhenNoAutosave:
    def test_no_autosave_path_returns_false_without_dialog(self, monkeypatch):
        from recovery import RecoveryController
        storage = _FakeStorage(autosave_path=None)
        host = _FakeHost()

        # QMessageBox must NOT be imported (no dialog)
        import recovery as _rec  # noqa: WPS433
        monkeypatch.setattr(_rec, "QMessageBox", None, raising=False)

        ctrl = RecoveryController(storage=storage, host=host)
        result = ctrl.check()
        assert result is False
        assert host._load_formation_data_calls == []


class TestCheckSilentWhenAutosaveNotNewer:
    def test_autosave_older_or_equal_to_manual_save_is_silent(self, monkeypatch):
        from recovery import RecoveryController
        # mtime 100 vs last_manual_save_mtime 200 → autosave NOT newer
        storage = _FakeStorage(
            autosave_path="/tmp/autosave.json",
            autosave_mtime=100.0,
        )
        host = _FakeHost(last_manual_save_mtime=200.0)

        import recovery as _rec  # noqa: WPS433
        monkeypatch.setattr(_rec, "QMessageBox", None, raising=False)

        ctrl = RecoveryController(storage=storage, host=host)
        result = ctrl.check()
        assert result is False
        assert host._load_formation_data_calls == []


class TestCheckOffersRestoreWhenNewer:
    def test_newer_autosave_calls_question(self, monkeypatch):
        from recovery import RecoveryController
        storage = _FakeStorage(
            autosave_path="/tmp/autosave.json",
            autosave_mtime=500.0,
        )
        host = _FakeHost(last_manual_save_mtime=100.0)

        # Stub QMessageBox.question to return a sentinel value
        question_calls: list = []
        def fake_question(*args, **kwargs):
            question_calls.append((args, kwargs))
            return 0  # treat as "no"
        monkeypatch.setattr(
            "recovery.QMessageBox",
            types.SimpleNamespace(
                question=fake_question,
                StandardButton=types.SimpleNamespace(Yes=0x4000, No=0x10000),
            ),
            raising=False,
        )

        ctrl = RecoveryController(storage=storage, host=host)
        result = ctrl.check()
        # question was called exactly once
        assert len(question_calls) == 1
        # user said "no" → no restore
        assert result is False
        assert host._load_formation_data_calls == []


class TestCheckUserYesRestores:
    def test_user_yes_calls_load_formation_data(self, monkeypatch):
        from recovery import RecoveryController
        storage = _FakeStorage(
            autosave_path="/tmp/autosave.json",
            autosave_mtime=500.0,
            load_payload={"singers": [], "rows": 3, "cols": 4, "staggered": False},
        )
        host = _FakeHost(last_manual_save_mtime=100.0)

        YES_BTN = 0x4000
        def fake_question(*args, **kwargs):
            return YES_BTN
        monkeypatch.setattr(
            "recovery.QMessageBox",
            types.SimpleNamespace(
                question=fake_question,
                StandardButton=types.SimpleNamespace(Yes=YES_BTN, No=0x10000),
            ),
            raising=False,
        )

        ctrl = RecoveryController(storage=storage, host=host)
        result = ctrl.check()
        assert result is True
        # _load_formation_data was called with the storage payload
        assert len(host._load_formation_data_calls) == 1
        assert host._load_formation_data_calls[0]["rows"] == 3
        # file was updated and modified flag set
        assert host.file == "/tmp/autosave.json"
        assert host._is_modified is True
        # storage.load_formation was called
        assert storage.load_calls == ["/tmp/autosave.json"]


class TestCheckUserNoSkips:
    def test_user_no_skips_silently(self, monkeypatch):
        from recovery import RecoveryController
        storage = _FakeStorage(
            autosave_path="/tmp/autosave.json",
            autosave_mtime=500.0,
            load_payload={"singers": []},
        )
        host = _FakeHost(last_manual_save_mtime=100.0)

        def fake_question(*args, **kwargs):
            return 0x10000  # No
        monkeypatch.setattr(
            "recovery.QMessageBox",
            types.SimpleNamespace(
                question=fake_question,
                StandardButton=types.SimpleNamespace(Yes=0x4000, No=0x10000),
            ),
            raising=False,
        )

        ctrl = RecoveryController(storage=storage, host=host)
        result = ctrl.check()
        assert result is False
        # No load happened
        assert host._load_formation_data_calls == []
        assert storage.load_calls == []


class TestCheckStorageFails:
    def test_load_returns_none_does_not_crash(self, monkeypatch):
        from recovery import RecoveryController
        storage = _FakeStorage(
            autosave_path="/tmp/autosave.json",
            autosave_mtime=500.0,
            load_payload=None,  # simulate load failure
        )
        host = _FakeHost(last_manual_save_mtime=100.0)

        def fake_question(*args, **kwargs):
            return 0x4000  # Yes
        monkeypatch.setattr(
            "recovery.QMessageBox",
            types.SimpleNamespace(
                question=fake_question,
                StandardButton=types.SimpleNamespace(Yes=0x4000, No=0x10000),
            ),
            raising=False,
        )

        ctrl = RecoveryController(storage=storage, host=host)
        result = ctrl.check()
        # Storage returned None → controller returns False
        assert result is False
        # Host was NOT touched
        assert host._load_formation_data_calls == []
