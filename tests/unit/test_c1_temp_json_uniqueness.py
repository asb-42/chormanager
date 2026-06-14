"""TDD: C1.3 \u2014 Unique temp-file per spawn (C-1 Sub-Plan Quick-Win).

Previously, every call to
:meth:`ChorAufstellungLauncherMixin._open_choraufstellung_for_event`
wrote to the **hardcoded** path
``{tempfile.gettempdir()}/choraufstellung_event.json``. Two
simultaneous spawns from the same user would clobber each other
and leak the file on crash (no cleanup).

C1.3 replaces this with a unique temp-file name
(``choraufstellung_event-<pid>-<uuid8>.json``).
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import pytest


def test_source_uses_unique_temp_path_not_hardcoded():
    """The hardcoded ``choraufstellung_event.json`` must be gone."""
    from chormanager.ui import choraufstellung_launcher
    src = Path(choraufstellung_launcher.__file__).read_text(encoding="utf-8")
    assert '"choraufstellung_event.json"' not in src, (
        "C1.3: temp-file path must be unique per call, not a hardcoded name"
    )
    # New pattern: must include a unique suffix.
    assert "_make_event_temp_path" in src, (
        "C1.3: the launcher must call _make_event_temp_path()"
    )


def test_make_event_temp_path_returns_unique_paths():
    """Two successive calls must return two distinct paths."""
    from chormanager.ui.choraufstellung_launcher import _make_event_temp_path
    p1 = _make_event_temp_path()
    p2 = _make_event_temp_path()
    assert p1 != p2, "Two calls must return distinct paths"


def test_make_event_temp_path_lives_in_system_tempdir():
    from chormanager.ui.choraufstellung_launcher import _make_event_temp_path
    p = _make_event_temp_path()
    assert p.startswith(tempfile.gettempdir())
    assert p.endswith(".json")
    assert not os.path.exists(p), "Path must not exist before use"


def test_make_event_temp_path_includes_pid_and_uuid():
    """The path encodes the PID for forensics and a UUID4-like suffix."""
    from chormanager.ui.choraufstellung_launcher import _make_event_temp_path
    p = _make_event_temp_path()
    pattern = rf"choraufstellung_event-{os.getpid()}-\w{{8}}\.json$"
    assert re.search(pattern, p), (
        f"path {p!r} does not match expected pattern {pattern!r}"
    )


def test_make_event_temp_path_collision_free_under_burst():
    """1000 calls in a tight loop must all return unique paths."""
    from chormanager.ui.choraufstellung_launcher import _make_event_temp_path
    paths = {_make_event_temp_path() for _ in range(1000)}
    assert len(paths) == 1000
