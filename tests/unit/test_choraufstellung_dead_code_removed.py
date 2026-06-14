"""TDD RED: DEADCODE-FIX-A — _menu_legenda and other dead code.

The legacy ``MainWindow._menu_legenda`` method in
``chormanager/choraufstellung/main.py`` is an empty function: its two
nested ``for`` loops have no body. It is only called from
``main_menu.py`` behind a ``hasattr`` guard, so removing it is safe.
"""
from __future__ import annotations

import pytest


def test_menu_legenda_removed_from_main_window_source():
    """The empty ``_menu_legenda`` method must be gone."""
    import inspect
    from chormanager.choraufstellung import main

    src = inspect.getsource(main.MainWindow)
    assert "_menu_legenda" not in src, (
        "DEADCODE-FIX-A: _menu_legenda is dead code and must be removed"
    )


def test_main_menu_no_longer_calls_legenda():
    """The caller in main_menu.py used ``hasattr(self._host, '_menu_legenda')``;
    the active code must no longer call it. A passing comment is fine.
    """
    import re
    from pathlib import Path
    src_path = Path("chormanager/choraufstellung/main_menu.py")
    text = src_path.read_text(encoding="utf-8")
    # Strip comments so the test tolerates historical breadcrumbs.
    non_comment = re.sub(r"#.*", "", text)
    assert "_menu_legenda" not in non_comment, (
        "DEADCODE-FIX-A: main_menu.py must no longer CALL _menu_legenda"
    )
