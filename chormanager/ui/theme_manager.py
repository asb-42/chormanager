"""Theme manager: light and dark Qt stylesheets.

Extracted from chormanager.ui.main_window as part of M-1 (God-Class
refactor, see plans/2026-06-12_m1_main_window_refactor.md step 4).

The class is a Mixin that contributes two methods - ``set_light_theme``
and ``set_dark_theme`` - to the host widget. ``MainWindow`` inherits
from both ``QMainWindow`` and ``ThemeMixin``; the two methods are
called via ``self.setStyleSheet(...)`` and ``self.statusBar()...``, so
they must be mixed in (not delegated) to preserve access to the
host widget's Qt API.

The mixin is kept byte-for-byte identical to the previous
implementation; only the location changed. There is no re-export
at the original location because the methods are now inherited, not
imported.
"""
from __future__ import annotations

from ..config import set_theme


class ThemeMixin:
    """Mixin that provides the two theme-switching methods.

    Any widget that needs them must inherit from this mixin AND from
    a QWidget-derived class (so that ``self.setStyleSheet`` and
    ``self.statusBar()`` resolve to real Qt API).
    """

    def _set_light_theme(self):
        """Set professional light theme."""
        light_style = """
        /* ===== LIGHT THEME ===== */

        /* Main application colors */
        QMainWindow, QWidget {
            background-color: #f8f9fa;
            color: #212529;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Table styling */
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            gridline-color: #dee2e6;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }

        QTableWidget::item {
            padding: 12px 8px;
            border-bottom: 1px solid #e9ecef;
        }

        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }

        QHeaderView::section {
            padding: 10px;
            background-color: #f1f3f4;
            border: none;
            border-bottom: 2px solid #1976d2;
            font-weight: bold;
        }

        QHeaderView::section {
            background-color: #f8f9fa;
            color: #495057;
            padding: 12px 8px;
            border: 1px solid #dee2e6;
            border-left: none;
            font-weight: 600;
            font-size: 13px;
        }

        QHeaderView::section:vertical {
            padding: 8px 16px;
        }

        /* Button styling */
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 8px 16px;
            color: #495057;
            font-weight: 500;
        }

        QPushButton:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }

        QPushButton:pressed {
            background-color: #dee2e6;
        }

        /* Menu styling */
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #dee2e6;
            color: #495057;
        }

        QMenuBar::item {
            padding: 8px 12px;
            background-color: transparent;
        }

        QMenuBar::item:selected {
            background-color: #e9ecef;
        }

        QMenu {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            color: #495057;
        }

        QMenu::item {
            padding: 8px 20px;
            border-radius: 2px;
        }

        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }

        /* Status bar */
        QStatusBar {
            background-color: #f8f9fa;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
        }

        /* Tool bar */
        QToolBar {
            background-color: #f8f9fa;
            border: none;
            border-bottom: 1px solid #dee2e6;
        }

        /* Info labels - custom colors maintained */
        QLabel#projectInfoLabel {
            background-color: #4a90d9;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        QLabel#eventInfoLabel {
            background-color: #e67e22;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        /* Form controls */
        QLineEdit, QComboBox, QTextEdit {
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 8px 12px;
            background-color: #ffffff;
            color: #495057;
        }

        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
            border-color: #4a90d9;
            outline: none;
        }

        /* Scroll bars */
        QScrollBar:vertical {
            background-color: #f8f9fa;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #adb5bd;
            border-radius: 6px;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #6c757d;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        QLabel#pageTitle {
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
            padding: 14px 15px 10px 15px;
            background-color: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }
        """
        self.setStyleSheet(light_style)
        set_theme("light")
        self.statusBar().showMessage("Helles Theme aktiviert")

    def _set_dark_theme(self):
        """Set professional dark theme."""
        dark_style = """
        /* ===== DARK THEME ===== */

        /* Info bar - augenfreundlich im Dark Mode */
        QWidget#infoBarWidget {
            background-color: #1e2832;
            border-bottom: 2px solid #4a90d9;
            padding: 8px;
        }
        QLabel {
            color: #e0e0e0;
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 4px;
        }
        QLabel#projectInfoLabel {
            background-color: #1565c0;
            color: white;
        }
        QLabel#eventInfoLabel {
            background-color: #e65100;
            color: white;
        }
        QLabel#pageTitle {
            background-color: #2d2d2d;
            color: #ffffff;
            font-size: 22px;
            font-weight: bold;
            padding: 14px 15px 10px 15px;
            border-bottom: 2px solid #404040;
        }

        /* Main application colors */
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Table styling */
        QTableWidget {
            background-color: #2d2d2d;
            alternate-background-color: #262626;
            gridline-color: #404040;
            border: 1px solid #404040;
            border-radius: 4px;
        }

        QTableWidget::item {
            padding: 6px 8px;
            border-bottom: 1px solid #333333;
            color: #e0e0e0;
        }

        QTableWidget::item:selected {
            background-color: #1e3a5f;
            color: #64b5f6;
        }

        QHeaderView::section {
            background-color: #333333;
            color: #ffffff;
            padding: 12px 8px;
            border: 1px solid #404040;
            border-left: none;
            font-weight: 600;
            font-size: 13px;
        }

        QHeaderView::section:vertical {
            padding: 8px 16px;
        }

        /* Button styling */
        QPushButton {
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            color: #e0e0e0;
            font-weight: 500;
        }

        QPushButton:hover {
            background-color: #404040;
            border-color: #666666;
        }

        QPushButton:pressed {
            background-color: #262626;
        }

        /* Checkbox styling for dark theme */
        QCheckBox {
            background-color: transparent;
            color: #e0e0e0;
            padding: 4px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #666666;
            border-radius: 3px;
            background-color: #2d2d2d;
        }
        QCheckBox::indicator:checked {
            background-color: #1565c0;
            border-color: #1976d2;
        }
        QCheckBox::indicator:indeterminate {
            background-color: #4a4a4a;
        }

        /* Menu styling */
        QMenuBar {
            background-color: #2d2d2d;
            border-bottom: 1px solid #404040;
            color: #e0e0e0;
        }

        QMenuBar::item {
            padding: 8px 12px;
            background-color: transparent;
        }

        QMenuBar::item:selected {
            background-color: #404040;
        }

        QMenu {
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #e0e0e0;
        }

        QMenu::item {
            padding: 8px 20px;
            border-radius: 2px;
        }

        QMenu::item:selected {
            background-color: #1e3a5f;
            color: #64b5f6;
        }

        /* Status bar */
        QStatusBar {
            background-color: #1a1a1a;
            border-top: 1px solid #404040;
            color: #b0b0b0;
        }

        /* Tool bar */
        QToolBar {
            background-color: #2d2d2d;
            border: none;
            border-bottom: 1px solid #404040;
            color: #e0e0e0;
        }

        /* Info labels - custom colors maintained */
        QLabel#projectInfoLabel {
            background-color: #4a90d9;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        QLabel#eventInfoLabel {
            background-color: #e67e22;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        /* Form controls */
        QLineEdit, QComboBox, QTextEdit {
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 12px;
            background-color: #333333;
            color: #e0e0e0;
        }

        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
            border-color: #4a90d9;
            outline: none;
        }

        /* Scroll bars */
        QScrollBar:vertical {
            background-color: #1a1a1a;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }

        /* Additional dark theme refinements */
        QSplitter::handle {
            background-color: #404040;
        }

        QSplitter::handle:hover {
            background-color: #555555;
        }
        QLabel#pageTitle {
            font-size: 22px;
            font-weight: bold;
            color: #ffffff;
            padding: 14px 15px 10px 15px;
            background-color: #2d2d2d;
            border-bottom: 2px solid #404040;
        }
        """
        self.setStyleSheet(dark_style)
        set_theme("dark")
        self.statusBar().showMessage("Dunkles Theme aktiviert")
