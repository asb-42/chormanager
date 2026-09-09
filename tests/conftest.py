# TDD: Test fixtures for Choraufstellung test suite
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_choraufstellung_path = str(Path(__file__).parent.parent / "chormanager" / "choraufstellung")
if _choraufstellung_path not in sys.path:
    sys.path.insert(0, _choraufstellung_path)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


@pytest.fixture(autouse=True)
def isolated_state_file(tmp_path, monkeypatch):
    """Redirect ``config.get_state_file`` to a per-test temp file.

    PR-Review R2 (2026-09-09): widgets persist UI state via
    ``chormanager.config.save_state`` (``set_last_active_*``, theme
    switches). Unpatched tests wrote silently to the developer's real
    ``data/state.json`` -- e.g. ``ProjectsTab.set_current_project``
    leaked ``last_active_project_id`` from unit tests.

    ``get_state_file`` is resolved *inside* ``chormanager.config`` by
    ``load_state``/``save_state``, so redirecting it here isolates
    every consumer. Tests that seed a specific state monkey-patch
    ``config.get_state_file`` again -- the later (inner) patch wins.

    Args:
        tmp_path: pytest per-test temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        pathlib.Path: the isolated state file path (no state yet).
    """
    from chormanager import config

    state_file = tmp_path / "state.json"
    monkeypatch.setattr(config, "get_state_file", lambda: state_file)
    return state_file


@pytest.fixture(autouse=True)
def isolated_choraufstellung_data_dir(tmp_path, monkeypatch):
    """Redirect ChorAufstellung's data dir to a per-test temp dir.

    PR #4 follow-up (2026-09-10): the choraufstellung sub-app resolves
    its data directory in TWO places --
    * ``choraufstellung/config.py:get_data_dir`` (imported by main.py)
    * ``choraufstellung/storage.py:_get_data_dir`` (own definition,
      used by FormationStorage for autosaves/backups)
    and, due to the ``sys.path`` shim in
    ``choraufstellung/__init__.py``, each module exists TWICE (top
    level ``storage`` and ``chormanager.choraufstellung.storage``).

    Unpatched, a real ``MainWindow`` under test ran its recovery flow
    against the developer's REAL autosaves in
    ``choraufstellung/data/backups`` and the modal "Wiederherstellen?"
    dialog blocked the offscreen suite forever (unit test
    ``test_choraufstellung_close_event_modified.py`` hung whenever
    genuine user autosaves existed).

    Args:
        tmp_path: pytest per-test temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        pathlib.Path: the isolated choraufstellung data dir (empty).
    """
    import importlib
    import sys

    ca_data_dir = tmp_path / "choraufstellung-data"

    # Import both module instances eagerly: on a fresh session the
    # choraufstellung package may not be loaded yet when the first
    # test runs, and patching sys.modules-only would silently miss.
    for mod_name in (
        "storage", "chormanager.choraufstellung.storage",
        "config", "chormanager.choraufstellung.config",
    ):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        target_attr = (
            "_get_data_dir" if hasattr(mod, "_get_data_dir")
            else "get_data_dir" if hasattr(mod, "get_data_dir")
            else None
        )
        if target_attr is not None:
            monkeypatch.setattr(
                mod, target_attr, lambda _d=ca_data_dir: str(_d)
            )

    return ca_data_dir


@pytest.fixture
def temp_dir():
    """Provides a temporary directory that is cleaned up after the test."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_singers():
    """Provides a list of sample Singer-like dataclasses for testing."""
    from core.rules import SingerRef

    return [
        SingerRef(singer_id="s1", name="Anna Alt", voice_group="Alt 1", height=165, row=0, col=0),
        SingerRef(singer_id="s2", name="Berthold Bass", voice_group="Bass 1", height=182, row=0, col=1),
        SingerRef(singer_id="s3", name="Clara Sopran", voice_group="Sopran 1", height=158, row=1, col=0),
        SingerRef(singer_id="s4", name="Dieter Tenor", voice_group="Tenor 1", height=175, row=1, col=1),
        SingerRef(singer_id="s5", name="Eva Sopran", voice_group="Sopran 2", height=162, row=2, col=0),
        SingerRef(singer_id="s6", name="Fritz Bass", voice_group="Bass 2", height=185, row=2, col=1),
    ]


@pytest.fixture
def sample_singers_with_affinity(sample_singers):
    """Provides sample singers with bidirectional affinity pairs."""
    s1, s2, s3, s4, s5, s6 = sample_singers

    s1.affinity = "s3"
    s3.affinity = "s1"

    s2.affinity = "s4"
    s4.affinity = "s2"

    return sample_singers


@pytest.fixture
def mock_storage(temp_dir):
    """Provides a mock storage that writes to a temporary directory."""
    storage_data = {}

    class MockStorage:
        def save_formation(self, singers, rows, cols, fp, placed, staggered, cfg):
            try:
                placed_ids = set()
                placed_data = []
                for singer, row, col in placed:
                    placed_ids.add(singer.singer_id)
                    placed_data.append({
                        "singer": singer.to_dict() if hasattr(singer, 'to_dict') else singer,
                        "row": row,
                        "col": col
                    })
                
                singers_data = []
                for singer in singers:
                    if singer.singer_id not in placed_ids:
                        singers_data.append(singer.to_dict() if hasattr(singer, 'to_dict') else singer)
                
                data = {
                    "rows": rows,
                    "cols": cols,
                    "staggered": staggered,
                    "voicing_config": cfg or [],
                    "singers": singers_data,
                    "placed": placed_data
                }
                storage_data[fp] = data
                with open(fp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                print(f"MockStorage save error: {e}")
                return False

        def load_formation(self, fp):
            if fp in storage_data:
                data = storage_data[fp]
                
                from singer_model import Singer
                
                all_singers = []
                placed_list = []
                
                for placed in data.get("placed", []):
                    singer_data = placed.get("singer", {})
                    sid = singer_data.get("singer_id", "")
                    row = placed.get("row", 0)
                    col = placed.get("col", 0)
                    
                    if sid:
                        singer = Singer.from_dict(singer_data)
                        singer.row = row
                        singer.col = col
                        all_singers.append(singer)
                        placed_list.append((singer, row, col))
                
                for singer_data in data.get("singers", []):
                    singer = Singer.from_dict(singer_data)
                    if singer.row < 0 and singer.col < 0:
                        all_singers.append(singer)
                
                return {
                    "rows": data.get("rows", 3),
                    "cols": data.get("cols", 4),
                    "staggered": data.get("staggered", False),
                    "voicing_config": data.get("voicing_config", []),
                    "singers": all_singers,
                    "placed": placed_list
                }
            try:
                if os.path.exists(fp):
                    with open(fp, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as e:
                print(f"MockStorage load error: {e}")
            return None

        def save_autosave(self, data, max_keep=5):
            return True

        def get_latest_autosave_path(self):
            return None

        def get_latest_autosave_mtime(self):
            return None

    return MockStorage()


@pytest.fixture
def grid_config():
    """Provides a standard GridConfig for testing."""
    from core.grid_engine import GridConfig
    return GridConfig(rows=4, cols=5, staggered=False)


@pytest.fixture
def grid_config_staggered():
    """Provides a GridConfig with staggered enabled."""
    from core.grid_engine import GridConfig
    return GridConfig(rows=4, cols=5, staggered=True)


@pytest.fixture
def mock_qapp():
    """Provides a mock QApplication for headless testing."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def empty_undo_stack():
    """Provides an empty UndoStack for testing."""
    from core.commands import UndoStack
    return UndoStack()


@pytest.fixture
def sample_json_file(temp_dir):
    """Provides a path to a temporary JSON file."""
    path = os.path.join(temp_dir, "test_formation.json")
    return path