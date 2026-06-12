# TDD M-2 Schritt 2: DraggableListWidget + DraggableTableWidget
# extracted from chormanager/choraufstellung/main.py (Z. 42-78) into
# chormanager/choraufstellung/widgets/draggable_list.py.
#
# These tests pin the *richest* semantics (the one in main.py):
#   - DraggableListWidget.startDrag() emits MIME "singer:<id>" if an item
#     is currently selected and carries a Singer in UserRole, else
#     delegates to QListWidget.startDrag().
#   - DraggableTableWidget.startDrag() aggregates ALL selectedItems() and
#     emits "singer:<id>" for a single selection or
#     "singer:<id>:group:<id1>,<id2>..." for a multi-selection.
#   - If no item is selected the method returns silently (no exception).
"""
Regression tests for M-2 Schritt 2 (extraction of draggable widgets).

The widgets live in :mod:`chormanager.choraufstellung.widgets.draggable_list`
which is a brand new module; this test file is the contract.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Qt6 / Qt5 cross-compat: we import the same way main.py does.
qt_compat = pytest.importorskip("qt_compat")


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------


class TestDraggableListModuleExists:
    """The new module must exist and re-export the two widget classes."""

    def test_module_imports(self):
        from chormanager.choraufstellung.widgets import draggable_list

        assert draggable_list is not None

    def test_module_exports_draggable_list_widget(self):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableListWidget,
        )

        assert DraggableListWidget is not None

    def test_module_exports_draggable_table_widget(self):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        assert DraggableTableWidget is not None


# ---------------------------------------------------------------------------
# DraggableListWidget
# ---------------------------------------------------------------------------


class TestDraggableListWidgetBase:
    """DraggableListWidget is a QListWidget subclass."""

    def test_is_qlistwidget_subclass(self):
        from PyQt6.QtWidgets import QListWidget
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableListWidget,
        )

        assert issubclass(DraggableListWidget, QListWidget)

    def test_can_be_instantiated(self, qtbot):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableListWidget,
        )

        w = DraggableListWidget()
        qtbot.addWidget(w)
        assert w is not None


class TestDraggableListWidgetStartDrag:
    """DraggableListWidget.startDrag() builds a single-singer MIME payload."""

    def test_start_drag_without_current_item_delegates_to_super(
        self, qtbot
    ):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableListWidget,
        )

        w = DraggableListWidget()
        qtbot.addWidget(w)
        # No current item, no selection -> should call super().startDrag()
        with patch.object(
            DraggableListWidget.__bases__[0], "startDrag"
        ) as mock_super:
            w.startDrag(0)  # action argument is irrelevant
            mock_super.assert_called_once()

    def test_start_drag_with_singer_emits_singer_mime(self, qtbot):
        from PyQt6.QtCore import Qt
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableListWidget,
        )

        w = DraggableListWidget()
        qtbot.addWidget(w)
        # Populate with a fake singer
        fake_singer = MagicMock()
        fake_singer.singer_id = "42"
        item = MagicMock()
        item.data.return_value = fake_singer
        w.currentItem = MagicMock(return_value=item)

        # Patch QDrag and QMimeData to capture what is sent
        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls, patch(
            "chormanager.choraufstellung.widgets.draggable_list.QMimeData"
        ) as mock_mime_cls:
            mock_drag = MagicMock()
            mock_drag_cls.return_value = mock_drag
            mock_mime = MagicMock()
            mock_mime_cls.return_value = mock_mime

            w.startDrag(0)

        # The MIME must contain "singer:42"
        mock_mime.setText.assert_called_once_with("singer:42")
        mock_drag.setMimeData.assert_called_once_with(mock_mime)
        mock_drag.exec.assert_called_once()


# ---------------------------------------------------------------------------
# DraggableTableWidget
# ---------------------------------------------------------------------------


class TestDraggableTableWidgetBase:
    """DraggableTableWidget is a QTableWidget subclass."""

    def test_is_qtablewidget_subclass(self):
        from PyQt6.QtWidgets import QTableWidget
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        assert issubclass(DraggableTableWidget, QTableWidget)

    def test_can_be_instantiated(self, qtbot):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        assert w is not None


class TestDraggableTableWidgetStartDrag:
    """DraggableTableWidget.startDrag() supports single + group drag."""

    def test_start_drag_with_no_selection_returns_silently(self, qtbot):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        w.selectedItems = MagicMock(return_value=[])

        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls:
            w.startDrag(0)
            mock_drag_cls.assert_not_called()

    def test_start_drag_single_singer_emits_simple_mime(self, qtbot):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        # Build a fake selected item
        fake_singer = MagicMock()
        fake_singer.singer_id = "7"
        item = MagicMock()
        item.data.return_value = fake_singer
        w.selectedItems = MagicMock(return_value=[item])

        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls, patch(
            "chormanager.choraufstellung.widgets.draggable_list.QMimeData"
        ) as mock_mime_cls:
            mock_drag = MagicMock()
            mock_drag_cls.return_value = mock_drag
            mock_mime = MagicMock()
            mock_mime_cls.return_value = mock_mime

            w.startDrag(0)

        mock_mime.setText.assert_called_once_with("singer:7")
        mock_drag.exec.assert_called_once()

    def test_start_drag_multi_singer_emits_group_mime(self, qtbot):
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        # Build 3 fake selected items
        s1, s2, s3 = (
            MagicMock(singer_id="1"),
            MagicMock(singer_id="2"),
            MagicMock(singer_id="3"),
        )
        items = []
        for singer in (s1, s2, s3):
            it = MagicMock()
            it.data.return_value = singer
            items.append(it)
        w.selectedItems = MagicMock(return_value=items)

        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls, patch(
            "chormanager.choraufstellung.widgets.draggable_list.QMimeData"
        ) as mock_mime_cls:
            mock_drag = MagicMock()
            mock_drag_cls.return_value = mock_drag
            mock_mime = MagicMock()
            mock_mime_cls.return_value = mock_mime

            w.startDrag(0)

        # Group MIME: first id + ":group:" + remaining ids
        # We expect: "singer:1:group:1,2,3"  (main.py semantics)
        args, _ = mock_mime.setText.call_args
        mime_text = args[0]
        assert mime_text.startswith("singer:1:group:")
        for sid in ("1", "2", "3"):
            assert sid in mime_text
        mock_drag.exec.assert_called_once()

    def test_start_drag_ignores_items_without_singer(self, qtbot):
        """An item with UserRole=None must be silently skipped."""
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        # Two items: one with a singer, one with None
        good_singer = MagicMock(singer_id="11")
        good_item = MagicMock()
        good_item.data.return_value = good_singer
        none_item = MagicMock()
        none_item.data.return_value = None
        w.selectedItems = MagicMock(return_value=[none_item, good_item])

        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls, patch(
            "chormanager.choraufstellung.widgets.draggable_list.QMimeData"
        ) as mock_mime_cls:
            mock_drag = MagicMock()
            mock_drag_cls.return_value = mock_drag
            mock_mime = MagicMock()
            mock_mime_cls.return_value = mock_mime

            w.startDrag(0)

        mock_mime.setText.assert_called_once_with("singer:11")

    def test_start_drag_dedups_repeated_singer_ids(self, qtbot):
        """The same singer_id must not appear twice in the group payload."""
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        # Two items that both point at the SAME singer_id "5"
        s = MagicMock(singer_id="5")
        i1 = MagicMock(); i1.data.return_value = s
        i2 = MagicMock(); i2.data.return_value = s
        w.selectedItems = MagicMock(return_value=[i1, i2])

        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls, patch(
            "chormanager.choraufstellung.widgets.draggable_list.QMimeData"
        ) as mock_mime_cls:
            mock_drag = MagicMock()
            mock_drag_cls.return_value = mock_drag
            mock_mime = MagicMock()
            mock_mime_cls.return_value = mock_mime

            w.startDrag(0)

        # Single-singer path -> plain "singer:5" (no group prefix)
        mock_mime.setText.assert_called_once_with("singer:5")

    def test_start_drag_no_singer_in_any_item_returns_silently(self, qtbot):
        """If every selected item lacks a singer, the drag is a no-op."""
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget,
        )

        w = DraggableTableWidget()
        qtbot.addWidget(w)
        i1 = MagicMock(); i1.data.return_value = None
        i2 = MagicMock(); i2.data.return_value = None
        w.selectedItems = MagicMock(return_value=[i1, i2])

        with patch(
            "chormanager.choraufstellung.widgets.draggable_list.QDrag"
        ) as mock_drag_cls:
            w.startDrag(0)
            mock_drag_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Backward-compat: main.py must still be able to import them by name
# ---------------------------------------------------------------------------


class TestMainPyBackwardCompat:
    """main.py historically defined these classes inline. They are now
    re-exported from the widgets package so external imports keep working.
    """

    def test_main_py_still_reexports_draggable_list_widget(self):
        from chormanager.choraufstellung.main import DraggableListWidget

        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableListWidget as RealDLW,
        )

        assert DraggableListWidget is RealDLW

    def test_main_py_still_reexports_draggable_table_widget(self):
        from chormanager.choraufstellung.main import DraggableTableWidget

        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget as RealDTW,
        )

        assert DraggableTableWidget is RealDTW

    def test_pool_widget_still_uses_extracted_class(self):
        """ui/pool_widget.py:228 instantiates DraggableTableWidget - this
        must resolve to the SAME class as the one from widgets/.
        """
        from chormanager.choraufstellung.ui import pool_widget
        from chormanager.choraufstellung.widgets.draggable_list import (
            DraggableTableWidget as RealDTW,
        )

        assert pool_widget.DraggableTableWidget is RealDTW
