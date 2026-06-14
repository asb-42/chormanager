"""TDD RED: Regression tests for M-2 Schritt 8 — FormationFileIO extrahieren.

These tests pin the public surface of the new file_io module:
- ``FormationFileIO.new(parent, is_modified)``  – prompt + reset
- ``FormationFileIO.open(parent)``              – file dialog + load
- ``FormationFileIO.save(parent, grid, file)``  – save to known path or fall through to save_as
- ``FormationFileIO.save_as(parent, grid)``     – file dialog + save
- ``FormationFileIO.save_to_path(path, grid, metadata)`` – atomic write
- ``FormationFileIO.generate_filename(date, name)`` – deterministic filename
- ``FormationFileIO.load_formation_data(data)`` – mutate grid & pool from dict

The class must be Qt-agnostic in its *core* methods (save_to_path,
generate_filename) so they can be unit-tested without a Qt event loop.
The dialog/show methods take a ``parent`` (a ``QWidget``) and use it
only for ``QFileDialog``/``QMessageBox`` parents; they are exercised
via ``monkeypatch`` of those classes in the GUI tests.
"""
from __future__ import annotations

import json
import os
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pytest


# --- helpers ----------------------------------------------------------------

class _FakeSinger:
    """Stand-in for ``singer_model.Singer`` used by FormationStorage."""

    def __init__(self, name: str = "Muster, Max", vg: str = "Sopran 1",
                 height: int = 0, singer_id: str = "1", affinity: str = ""):
        self.name = name
        self.voice_group = vg
        self.height = height
        self.singer_id = singer_id
        self.affinity = affinity
        self.row = -1
        self.col = -1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "voice_group": self.voice_group,
            "height": self.height,
            "singer_id": self.singer_id,
            "affinity": self.affinity,
        }


class _FakeStorage:
    """Recording stand-in for ``FormationStorage``."""

    def __init__(self, *, save_ok: bool = True, load_data: Optional[dict] = None):
        self.save_ok = save_ok
        self.load_data = load_data
        self.calls: List[dict] = []

    def save_formation(self, singers, rows, cols, filepath, placed_singers,
                       staggered, **kwargs) -> bool:
        # Mirrors FormationStorage.save_formation signature (placed_singers kwarg).
        self.calls.append({
            "singers": singers, "rows": rows, "cols": cols,
            "filepath": filepath, "placed_singers": placed_singers,
            "staggered": staggered, "kwargs": kwargs,
        })
        return self.save_ok

    def load_formation(self, filepath: str) -> Optional[dict]:
        self.calls.append({"load": filepath})
        return self.load_data


class _FakeGrid:
    """Minimal stand-in for ``FormationGrid``."""

    def __init__(self, rows: int = 3, cols: int = 4, singers: Optional[list] = None):
        self.rows = rows
        self.cols = cols
        self.singers = singers or []
        self.staggered = False
        self.refresh_calls: int = 0

    def get_placed_singers(self) -> List[Tuple[Any, int, int]]:
        out: List[Tuple[Any, int, int]] = []
        for s in self.singers:
            if getattr(s, "row", -1) >= 0:
                out.append((s, s.row, s.col))
        return out

    def get_placed_singer_ids(self) -> set:
        return {s.singer_id for s in self.singers if getattr(s, "row", -1) >= 0}

    def refresh_grid(self) -> None:
        self.refresh_calls += 1


# --- tests -------------------------------------------------------------------

class TestModuleShape:
    def test_file_io_module_exists(self):
        try:
            from file_io import FormationFileIO  # noqa: F401
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"file_io module missing or import fails: {exc}")

    def test_formation_file_io_is_a_class(self):
        from file_io import FormationFileIO
        assert isinstance(FormationFileIO, type)

    def test_formation_file_io_api(self):
        from file_io import FormationFileIO
        for name in (
            "new", "open", "save", "save_as", "save_to_path",
            "generate_filename", "load_formation_data",
        ):
            assert hasattr(FormationFileIO, name), f"missing method: {name}"


class TestGenerateFilename:
    """``generate_filename`` is pure — easy to test without Qt."""

    def test_includes_event_date(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())
        name = fio.generate_filename("2026-12-24", "Weihnachtskonzert")
        assert name.startswith("choraufstellung-2026-12-24-version-")
        assert name.endswith(".json")

    def test_falls_back_to_today_when_no_event_date(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())
        today = datetime.now().strftime("%Y-%m-%d")
        name = fio.generate_filename("", "irgendwas")
        assert today in name

    def test_event_name_is_optional(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())
        # must not crash when event_name is None
        name = fio.generate_filename("2026-01-15", None)
        assert name.endswith(".json")


class TestSaveToPath:
    """``save_to_path`` is the headless heart of the module."""

    def test_calls_storage_save_formation(self, tmp_path: Path):
        from file_io import FormationFileIO
        storage = _FakeStorage(save_ok=True)
        fio = FormationFileIO(storage)
        singers = [_FakeSinger(singer_id="1"), _FakeSinger(singer_id="2")]
        grid = _FakeGrid(rows=3, cols=4, singers=singers)
        result = fio.save_to_path(str(tmp_path / "out.json"), grid, metadata={"event": "X"})
        assert result is True
        assert len(storage.calls) == 1
        call = storage.calls[0]
        assert call["rows"] == 3
        assert call["cols"] == 4
        assert call["kwargs"].get("metadata") == {"event": "X"}

    def test_propagates_storage_failure(self, tmp_path: Path):
        from file_io import FormationFileIO
        storage = _FakeStorage(save_ok=False)
        fio = FormationFileIO(storage)
        grid = _FakeGrid()
        result = fio.save_to_path(str(tmp_path / "out.json"), grid, metadata=None)
        assert result is False

    def test_metadata_none_is_passed_through(self, tmp_path: Path):
        from file_io import FormationFileIO
        storage = _FakeStorage()
        fio = FormationFileIO(storage)
        grid = _FakeGrid()
        fio.save_to_path(str(tmp_path / "out.json"), grid, metadata=None)
        # metadata must reach the storage layer, not silently disappear
        assert "metadata" in storage.calls[0]["kwargs"]


class TestLoadFormationData:
    """``load_formation_data`` mutates the host window from a dict."""

    def test_sets_grid_dimensions(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())

        class _Host:
            def __init__(self):
                self.singers: list = []
                self.grid = _FakeGrid()
                self.pool = types.SimpleNamespace(
                    singers=[], placed_singer_ids=set(), update_singers=lambda *a, **k: None,
                )
                self._is_modified = True
                self.update_grid_count = lambda: None
                self.rs = None
                self.cs = None

        host = _Host()
        data = {
            "singers": [_FakeSinger(singer_id="7").to_dict()],
            "rows": 5, "cols": 8, "staggered": True,
        }
        # The factory must restore fields like .row / .col from the dict
        # (we don't test that round-trip here; only the grid-dim wiring).
        fio.load_formation_data(host, data)
        assert host.grid.rows == 5
        assert host.grid.cols == 8
        assert host.grid.staggered is True
        assert host._is_modified is False

    def test_defaults_when_keys_missing(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())

        class _Host:
            def __init__(self):
                self.singers: list = []
                self.grid = _FakeGrid()
                self.pool = types.SimpleNamespace(
                    singers=[], placed_singer_ids=set(), update_singers=lambda *a, **k: None,
                )
                self._is_modified = True
                self.update_grid_count = lambda: None
                self.rs = None
                self.cs = None

        host = _Host()
        fio.load_formation_data(host, {})
        assert host.grid.rows == 3
        assert host.grid.cols == 4
        assert host.grid.staggered is False


class TestValidateDimensions:
    """M5-FIX-A: ``_validate_dimensions`` enforces 1 <= value <= 50."""

    def _host(self):
        class _Host:
            def __init__(self):
                self.singers: list = []
                self.grid = _FakeGrid()
                self.pool = types.SimpleNamespace(
                    singers=[], placed_singer_ids=set(), update_singers=lambda *a, **k: None,
                )
                self._is_modified = True
                self.update_grid_count = lambda: None
                self.rs = None
                self.cs = None
        return _Host()

    def test_valid_dimensions_pass(self):
        from file_io import FormationFileIO, _validate_dimensions
        # Should not raise
        assert _validate_dimensions(1, 1) == (1, 1)
        assert _validate_dimensions(50, 50) == (50, 50)
        assert _validate_dimensions(3, 4) == (3, 4)

    def test_rows_below_minimum_raises_value_error(self):
        from file_io import _validate_dimensions
        with pytest.raises(ValueError, match="rows"):
            _validate_dimensions(0, 4)

    def test_rows_above_maximum_raises_value_error(self):
        from file_io import _validate_dimensions
        with pytest.raises(ValueError, match="rows"):
            _validate_dimensions(51, 4)

    def test_cols_below_minimum_raises_value_error(self):
        from file_io import _validate_dimensions
        with pytest.raises(ValueError, match="cols"):
            _validate_dimensions(3, 0)

    def test_cols_above_maximum_raises_value_error(self):
        from file_io import _validate_dimensions
        with pytest.raises(ValueError, match="cols"):
            _validate_dimensions(3, 51)

    def test_negative_rows_raises_value_error(self):
        from file_io import _validate_dimensions
        with pytest.raises(ValueError, match="rows"):
            _validate_dimensions(-1, 4)

    def test_load_formation_data_rejects_out_of_bounds(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())
        host = self._host()
        # Snapshot the host BEFORE the call (default _FakeGrid rows=3, cols=4).
        original_rows = host.grid.rows
        original_cols = host.grid.cols
        data = {"rows": 100, "cols": 4, "singers": []}
        with pytest.raises(ValueError, match="rows"):
            fio.load_formation_data(host, data)
        # host.grid must NOT have been mutated
        assert host.grid.rows == original_rows
        assert host.grid.cols == original_cols
        assert host.singers == []
        assert host._is_modified is True

    def test_load_formation_data_accepts_boundary_values(self):
        from file_io import FormationFileIO
        fio = FormationFileIO(_FakeStorage())
        host = self._host()
        data = {"rows": 1, "cols": 50, "singers": []}
        fio.load_formation_data(host, data)
        assert host.grid.rows == 1
        assert host.grid.cols == 50
