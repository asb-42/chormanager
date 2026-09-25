"""M0 Phase 2 (increment 3/3): no temp JSON, no subprocess.

Supersedes C1.3 (unique temp-file per spawn): the whole temp-JSON +
subprocess layer is gone — ``_open_choraufstellung_for_event`` seeds
the embedded tab editor directly from the repositories. These tests
guard the removal (helper gone, no spawn/CHOR_* plumbing left in the
launcher module).
"""
from __future__ import annotations

from pathlib import Path

LAUNCHER = Path("chormanager/ui/choraufstellung_launcher.py")


def _code_without_docstrings_and_comments() -> str:
    import re

    src = LAUNCHER.read_text(encoding="utf-8")
    code = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
    code = re.sub(r"#.*", "", code)
    return code


def test_make_event_temp_path_helper_removed():
    """The temp-file helper must be gone with the layer it served."""
    from chormanager.ui import choraufstellung_launcher

    assert not hasattr(choraufstellung_launcher, "_make_event_temp_path")


def test_no_temp_json_plumbing_in_launcher():
    code = _code_without_docstrings_and_comments()
    assert "tempfile" not in code
    assert "choraufstellung_event-" not in code


def test_no_subprocess_or_chor_env_in_launcher():
    code = _code_without_docstrings_and_comments()
    assert "subprocess" not in code
    assert "CHOR_EVENT_DATA" not in code
    assert "CHOR_FILE" not in code
    assert "CHOR_DB_PATH" not in code
