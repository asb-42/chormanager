"""Theme-Applier for ChorAufstellung (M-2 Schritt 12).

Encapsulates the QSS strings + the post-apply refresh that were
previously inlined in :meth:`MainWindow._apply_theme` (Z. 725–764 in
the legacy main.py).

The applier:

* Sets a QSS on the host window (light or dark)
* Clears the voice-group color cache
* Triggers ``host.grid.refresh_grid()`` and
  ``host.pool.update_singers(...)`` so the new theme colors
  propagate immediately

The QSS strings are exposed as class constants so they can be
inspected, overridden, or replaced by a future user-theme system.

Design
------
* **Theme-agnostic API:** ``apply(theme)`` accepts ``"light"``,
  ``"dark"`` or anything else (falls back to light).
* **Lazy-resolve:** the ``clear_color_cache`` function is looked up
  via the module-level handle so tests can patch it.
* **No side effects beyond QSS:** the applier never imports
  PyQt5/PyQt6 itself — the host owns the actual ``QWidget`` and
  the grid / pool duck-typed objects.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    pass


# Module-level handle so tests can patch the cache-clear function.
clear_color_cache: Any = None


def _resolve_clear_color_cache() -> Any:
    """Lazy lookup of :func:`clear_color_cache` (cached in module globals)."""
    global clear_color_cache
    if clear_color_cache is None:
        from config import clear_color_cache as _ccc  # type: ignore
        clear_color_cache = _ccc
    return clear_color_cache


class ThemeApplier:
    """Apply a light or dark QSS theme to the host window."""

    LIGHT_STYLESHEET: str = """
        QMainWindow, QWidget { background: #f8f4eb; color: #1A1A1A; }
        QLabel { color: #1A1A1A; }
        QTableWidget { background: #ffffff; color: #1A1A1A; gridline-color: #d4c9b8; }
        QTableWidget::item:selected { background: #d4c9b8; color: #1A1A1A; }
        QHeaderView::section { background: #f0ebe0; color: #1A1A1A; border: 1px solid #d4c9b8; }
        QLineEdit, QComboBox { background: #ffffff; color: #1A1A1A; border: 1px solid #d4c9b8; }
        QPushButton { background: #e8e0d4; color: #1A1A1A; border: 1px solid #d4c9b8; padding: 4px; }
        QPushButton:hover { background: #d4c9b8; }
        QMenuBar { background: #f0ebe0; color: #1A1A1A; }
        QMenuBar::item:selected { background: #d4c9b8; }
        QMenu { background: #f0ebe0; color: #1A1A1A; border: 1px solid #d4c9b8; }
        QMenu::item:selected { background: #d4c9b8; }
        QRadioButton { color: #1A1A1A; }
        QCheckBox { color: #1A1A1A; }
    """

    DARK_STYLESHEET: str = """
        QMainWindow, QWidget { background: #2b2b2b; color: #F0F0F0; }
        QLabel { color: #F0F0F0; }
        QTableWidget { background: #3b3b3b; color: #F0F0F0; gridline-color: #555; }
        QTableWidget::item:selected { background: #4a4a4a; color: #fff; }
        QHeaderView::section { background: #3b3b3b; color: #F0F0F0; border: 1px solid #555; }
        QLineEdit, QComboBox { background: #3b3b3b; color: #F0F0F0; border: 1px solid #555; }
        QPushButton { background: #4a4a4a; color: #F0F0F0; border: 1px solid #555; padding: 4px; }
        QPushButton:hover { background: #5a5a5a; }
        QMenuBar { background: #3b3b3b; color: #F0F0F0; }
        QMenuBar::item:selected { background: #4a4a4a; }
        QMenu { background: #3b3b3b; color: #F0F0F0; border: 1px solid #555; }
        QMenu::item:selected { background: #4a4a4a; }
        QRadioButton { color: #F0F0F0; }
        QCheckBox { color: #F0F0F0; }
    """

    def __init__(self, host: Any) -> None:
        """Store the host (MainWindow or any object with setStyleSheet)."""
        self._host = host

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def apply(self, theme: str) -> None:
        """Apply ``theme`` to the host (light, dark, or anything -> light)."""
        if theme == "dark":
            qss = self.DARK_STYLESHEET
        else:
            qss = self.LIGHT_STYLESHEET

        self._host.setStyleSheet(qss)
        _resolve_clear_color_cache()()

        # Refresh widgets so the new theme colors propagate immediately
        self._host.grid.refresh_grid()
        self._host.pool.update_singers(
            self._host.singers, self._host.pool.placed_singer_ids
        )
