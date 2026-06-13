"""TDD RED: Regression tests for M-2 Schritt 10 — ChorManagerBridge extrahieren.

The bridge encapsulates the two ways ChorAufstellung can be seeded
with singers from the parent ChorManager app:

* **Temp JSON file** (preferred): the launcher writes
  ``CHOR_EVENT_DATA=/tmp/chor_event_<id>.json`` and the bridge reads
  ``{event: {...}, singers: [...]}``.
* **SQLite DB** (fallback): the bridge opens the ChorManager DB and
  runs the ``availability`` + ``singers`` join filtered by ``event_id``.

Public surface:
* ``ChorManagerBridge(host)``              — constructor
* ``ChorManagerBridge.load_from_env()``    — auto-dispatch (env → file → db)
* ``ChorManagerBridge.load_from_json(path)``   — pure-Python, easy to test
* ``ChorManagerBridge.load_from_db(path, event_id)`` — uses sqlite3

The host is mutated by the bridge (sets ``self.singers``,
``self.pool.singers``, ``self._is_modified``). The bridge
**does not** import :class:`MainWindow` — it relies on duck typing.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import types
from pathlib import Path
from typing import Any, List, Optional

import pytest


# --- helpers ----------------------------------------------------------------

class _FakeSinger:
    """Stand-in for :class:`singer_model.Singer`."""

    def __init__(self, name: str, voice_group, height: int = 0,
                 singer_id: str = "", affinity: str = ""):
        self.name = name
        self.voice_group = voice_group
        self.height = height
        self.singer_id = singer_id
        self.affinity = affinity
        self.row = -1
        self.col = -1


class _FakePool:
    def __init__(self):
        self.singers: list = []
        self.placed_singer_ids: set = set()
        self.update_calls: list = []

    def update_singers(self, singers, placed_ids=None) -> None:
        self.update_calls.append((singers, placed_ids))


class _FakeHost:
    """Stand-in for :class:`MainWindow`."""

    def __init__(self):
        self.singers: list = []
        self.pool = _FakePool()
        self._is_modified = True
        self._loaded_metadata: dict = {}
        self.event_id: str = ""
        self.event_date: str = ""
        self.event_name: str = ""


def _populate_db(db_path: Path) -> None:
    """Create a tiny ChorManager-style DB and return the path."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE singers (id TEXT PRIMARY KEY, full_name TEXT, "
        "short_name TEXT, voice_group TEXT, affinity_uuid TEXT, height INTEGER)"
    )
    cur.execute(
        "CREATE TABLE availability (singer_id TEXT, event_id TEXT, status TEXT)"
    )
    cur.executemany(
        "INSERT INTO singers VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("1", "Anna Müller", "Anna", "Sopran 1", "", 165),
            ("2", "Beate Schmidt", "Beate", "Sopran 2", "", 170),
            ("3", "Carla Weber", "Carla", "Alt 1", "uuid-1", 160),
            ("4", "Doris Klein", "Doris", "Tenor 1", "uuid-2", 175),
        ],
    )
    cur.executemany(
        "INSERT INTO availability VALUES (?, ?, ?)",
        [
            ("1", "evt-1", "yes"),
            ("2", "evt-1", "yes"),
            ("3", "evt-1", "conditional"),
            ("4", "evt-1", "no"),
        ],
    )
    conn.commit()
    conn.close()


# --- tests -------------------------------------------------------------------

class TestModuleShape:
    def test_chormanager_bridge_module_exists(self):
        try:
            from chormanager_bridge import ChorManagerBridge  # noqa: F401
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"chormanager_bridge module missing: {exc}")

    def test_chormanager_bridge_is_a_class(self):
        from chormanager_bridge import ChorManagerBridge
        assert isinstance(ChorManagerBridge, type)

    def test_chormanager_bridge_api(self):
        from chormanager_bridge import ChorManagerBridge
        for name in ("load_from_env", "load_from_json", "load_from_db"):
            assert hasattr(ChorManagerBridge, name), f"missing method: {name}"


class TestLoadFromJson:
    def test_load_from_json_reads_singers(self, tmp_path: Path):
        from chormanager_bridge import ChorManagerBridge
        data = {
            "event": {"name": "Weihnachtskonzert", "date": "2026-12-24",
                      "event_type": "Konzert"},
            "project": "Chor A",
            "singers": [
                {"short_name": "Anna", "voice_group": "Sopran 1",
                 "singer_id": "1", "height": 165},
                {"short_name": "Beate", "voice_group": "Sopran 2",
                 "singer_id": "2", "height": 170},
            ],
        }
        fp = tmp_path / "event.json"
        fp.write_text(json.dumps(data), encoding="utf-8")
        host = _FakeHost()
        bridge = ChorManagerBridge(host)

        result = bridge.load_from_json(str(fp))
        assert result is True
        assert len(host.singers) == 2
        assert host.singers[0].name == "Anna"
        assert host._is_modified is False
        # Pool updated
        assert host.pool.singers == host.singers
        # Metadata loaded
        assert host._loaded_metadata.get("event") == "Weihnachtskonzert"
        assert host._loaded_metadata.get("event_date") == "2026-12-24"

    def test_load_from_json_missing_file_returns_false(self, tmp_path: Path):
        from chormanager_bridge import ChorManagerBridge
        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_json(str(tmp_path / "missing.json"))
        assert result is False
        assert host.singers == []
        # State remains unchanged
        assert host._is_modified is True

    def test_load_from_json_corrupt_file_does_not_crash(self, tmp_path: Path):
        from chormanager_bridge import ChorManagerBridge
        fp = tmp_path / "bad.json"
        fp.write_text("{this is not json", encoding="utf-8")
        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        # Must return False (or None) and never raise
        result = bridge.load_from_json(str(fp))
        assert result is False
        assert host.singers == []


class TestLoadFromDb:
    def test_load_from_db_filters_by_event_id(self, tmp_path: Path):
        from chormanager_bridge import ChorManagerBridge
        db = tmp_path / "chor.db"
        _populate_db(db)

        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_db(str(db), event_id="evt-1")
        assert result is True
        # Only 'yes' + 'conditional' singers, NOT 'no'
        assert len(host.singers) == 3
        names = [s.name for s in host.singers]
        assert "Doris Klein" not in names
        assert host._is_modified is False

    def test_load_from_db_no_event_id_returns_all_singers(self, tmp_path: Path):
        from chormanager_bridge import ChorManagerBridge
        db = tmp_path / "chor.db"
        _populate_db(db)

        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_db(str(db), event_id="")
        assert result is True
        # No event filter: all 4 singers
        assert len(host.singers) == 4

    def test_load_from_db_missing_file_returns_false(self, tmp_path: Path):
        from chormanager_bridge import ChorManagerBridge
        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_db(str(tmp_path / "missing.db"), event_id="evt-1")
        assert result is False
        assert host.singers == []


class TestLoadFromEnv:
    def test_load_from_env_prefers_json_file(self, tmp_path: Path, monkeypatch):
        from chormanager_bridge import ChorManagerBridge
        data = {
            "event": {"name": "E", "date": "2026-01-15", "event_type": "Konzert"},
            "singers": [
                {"short_name": "Anna", "voice_group": "Sopran 1",
                 "singer_id": "1", "height": 165},
            ],
        }
        fp = tmp_path / "event.json"
        fp.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setenv("CHOR_EVENT_DATA", str(fp))

        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_env()
        assert result is True
        assert len(host.singers) == 1

    def test_load_from_env_falls_back_to_db(self, tmp_path: Path, monkeypatch):
        from chormanager_bridge import ChorManagerBridge
        db = tmp_path / "chor.db"
        _populate_db(db)
        # No CHOR_EVENT_DATA env var, but CHOR_DB_PATH is set
        monkeypatch.delenv("CHOR_EVENT_DATA", raising=False)
        monkeypatch.setenv("CHOR_DB_PATH", str(db))
        monkeypatch.setenv("CHOR_EVENT_ID", "evt-1")

        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_env()
        assert result is True
        # Filter by event_id
        assert len(host.singers) == 3

    def test_load_from_env_with_nothing_set_is_noop(self, monkeypatch):
        from chormanager_bridge import ChorManagerBridge
        monkeypatch.delenv("CHOR_EVENT_DATA", raising=False)
        monkeypatch.delenv("CHOR_DB_PATH", raising=False)
        monkeypatch.delenv("CHOR_EVENT_ID", raising=False)

        host = _FakeHost()
        bridge = ChorManagerBridge(host)
        result = bridge.load_from_env()
        assert result is False
        assert host.singers == []
