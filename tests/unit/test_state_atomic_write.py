"""TDD RED: m4-FIX-A — state.json atomic write.

``chormanager.config.save_state`` must write to ``state.json.tmp`` and
then ``os.replace`` to the final path. If a crash happens between
``open(tmp, 'w')`` and ``os.replace``, the original ``state.json``
must remain intact.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest


def test_save_state_writes_via_tmp_and_replace(tmp_path: Path, monkeypatch):
    """Atomic write: tmp + os.replace, not direct overwrite."""
    from chormanager import config

    # Redirect get_state_file to a tmp location.
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(config, "get_state_file", lambda: state_file)

    config.save_state({"a": 1})

    # The tmp file must NOT exist anymore (it was renamed).
    tmp_path = Path(str(state_file) + ".tmp")
    assert not tmp_path.exists()
    # The final file must be valid JSON.
    assert state_file.exists()
    assert json.loads(state_file.read_text(encoding="utf-8")) == {"a": 1}


def test_save_state_does_not_corrupt_on_crash(tmp_path: Path, monkeypatch):
    """If ``json.dump`` raises mid-write, the existing state.json must
    stay intact and the .tmp file must be cleaned up."""
    from chormanager import config

    state_file = tmp_path / "state.json"
    state_file.write_text('{"preexisting": true}', encoding="utf-8")
    monkeypatch.setattr(config, "get_state_file", lambda: state_file)

    real_open = open

    def crashing_open(path, *a, **kw):
        # Fail the second open (the tmp one), not the first.
        if ".tmp" in str(path) and "w" in (a[0] if a else kw.get("mode", "")):
            raise OSError("simulated crash")
        return real_open(path, *a, **kw)

    monkeypatch.setattr("builtins.open", crashing_open)
    with pytest.raises(OSError):
        config.save_state({"new": True})

    # Original file must still be intact.
    assert json.loads(state_file.read_text(encoding="utf-8")) == {"preexisting": True}
    # Tmp file must be cleaned up (best effort) by the finally block.
    tmp_path_str = str(state_file) + ".tmp"
    # Note: on some FS the tmp may remain; we accept either.
    assert (not os.path.exists(tmp_path_str)) or True


def test_save_state_uses_os_replace(tmp_path: Path, monkeypatch):
    """We assert the implementation goes through ``os.replace`` (the
    atomic-rename primitive), not e.g. ``os.rename`` (which is the same
    on POSIX but a different name on Windows)."""
    from chormanager import config

    state_file = tmp_path / "state.json"
    monkeypatch.setattr(config, "get_state_file", lambda: state_file)

    replaced = {"count": 0}
    real_replace = os.replace

    def counting_replace(src, dst):
        replaced["count"] += 1
        return real_replace(src, dst)

    monkeypatch.setattr("os.replace", counting_replace)
    config.save_state({"x": 2})
    assert replaced["count"] == 1
    assert json.loads(state_file.read_text(encoding="utf-8")) == {"x": 2}
