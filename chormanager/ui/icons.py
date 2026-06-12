"""Shared icon helper used by ``MainWindow`` and its Mixins.

Extracted from ``chormanager.ui.main_window`` during M-1 step 5 so that
``tab_router`` (and any future Mixin / module that builds ``QAction``
instances) can call ``get_icon`` without creating a circular import
back into ``main_window``.

The implementation is byte-for-byte identical to the original;
only the location changed. ``main_window`` re-exports ``get_icon``
for backward compatibility with any code that imports it from there.
"""
from __future__ import annotations


def get_icon(icon_name: str, fallback_pixmap):
    """Load icon from system theme with fallback to Qt standard pixmap.

    Args:
        icon_name: System icon name (e.g., "document-new", "list-add")
        fallback_pixmap: QStyle.StandardPixmap to use if theme icon not found

    Returns:
        QIcon instance
    """
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        style = QApplication.instance().style() if QApplication.instance() else None
        if style:
            icon = style.standardIcon(fallback_pixmap)
    return icon
