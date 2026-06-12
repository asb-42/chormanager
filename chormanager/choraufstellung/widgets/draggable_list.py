"""Draggable Qt widgets used by the ChorAufstellung UI.

Extracted from :mod:`chormanager.choraufstellung.main` (Z. 42-78) during
the M-2 refactoring.

The two widget classes are:

* :class:`DraggableListWidget` — a :class:`QListWidget` whose
  ``startDrag`` emits a MIME payload of the form ``"singer:<id>"`` for
  the currently selected item (which must carry a :class:`Singer` (or
  duck-typed equivalent) in its ``Qt.ItemDataRole.UserRole``).  When
  no item is current, the call is delegated to
  :meth:`QListWidget.startDrag`.

* :class:`DraggableTableWidget` — a :class:`QTableWidget` whose
  ``startDrag`` aggregates *all* selected items and produces either a
  single-singer MIME payload ``"singer:<id>"`` or, when more than one
  singer is selected, a group payload
  ``"singer:<primary>:group:<id1>,<id2>,..."``.  Items without a
  singer in their UserRole are silently skipped, and duplicate
  ``singer_id`` values are de-duplicated.

Both classes use the choraufstellung's own ``qt_compat`` helpers for
PyQt5 / PyQt6 cross compatibility (see
:mod:`chormanager.choraufstellung.qt_compat`).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Qt imports (PyQt5/PyQt6 cross-compat)
# ---------------------------------------------------------------------------
# QMimeData lives in QtCore in BOTH PyQt5 and PyQt6, so we import it
# from QtCore in both branches to mirror the pattern used in main.py.
try:
    from PyQt6.QtWidgets import QListWidget, QTableWidget
    from PyQt6.QtCore import Qt, QMimeData
    from PyQt6.QtGui import QDrag
except ImportError:  # PyQt5 fallback
    from PyQt5.QtWidgets import QListWidget, QTableWidget  # noqa: F401
    from PyQt5.QtCore import Qt, QMimeData  # noqa: F401
    from PyQt5.QtGui import QDrag  # noqa: F401

from qt_compat import QT_VERSION  # noqa: F401  -- re-exported for callers


# ---------------------------------------------------------------------------
# MIME payload helpers
# ---------------------------------------------------------------------------
#: Prefix for a single-singer MIME payload.
SINGER_MIME_PREFIX = "singer:"
#: Separator between the primary id and the group of remaining ids.
_GROUP_SEP = ":group:"


def _build_singer_mime(singer_id: str) -> str:
    """Build a single-singer MIME payload."""
    return f"{SINGER_MIME_PREFIX}{singer_id}"


def _build_group_mime(primary_id: str, all_ids: list) -> str:
    """Build a group MIME payload.

    Format: ``"singer:<primary>:group:<id1>,<id2>,..."``
    """
    return f"{SINGER_MIME_PREFIX}{primary_id}{_GROUP_SEP}{','.join(all_ids)}"


# ---------------------------------------------------------------------------
# Widget classes
# ---------------------------------------------------------------------------


class DraggableListWidget(QListWidget):
    """QListWidget that emits a singer MIME payload on drag-start.

    The current item's ``Qt.ItemDataRole.UserRole`` must contain an
    object exposing a ``singer_id`` attribute (e.g. a
    :class:`singer_model.Singer`).  If no item is current, the call
    is delegated to :meth:`QListWidget.startDrag`.
    """

    def startDrag(self, actions):  # type: ignore[override]
        item = self.currentItem()
        if item:
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(_build_singer_mime(singer.singer_id))
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.CopyAction)
        else:
            super().startDrag(actions)


class DraggableTableWidget(QTableWidget):
    """QTableWidget that supports single- and multi-singer drag payloads.

    All currently selected items are scanned.  Items without a singer
    in their ``Qt.ItemDataRole.UserRole`` are silently skipped, and
    duplicate ``singer_id`` values are de-duplicated (preserving the
    order of first appearance).

    * One unique singer: MIME = ``"singer:<id>"``
    * Multiple singers:    MIME = ``"singer:<primary>:group:<ids...>"``

    If no items are selected, or no selected item contains a singer,
    the method is a no-op (no exception, no drag).
    """

    def startDrag(self, actions):  # type: ignore[override]
        selected = self.selectedItems()
        if not selected:
            return

        # Collect unique singer ids, preserving order of first appearance.
        sids = []
        for item in selected:
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer and singer.singer_id not in sids:
                sids.append(singer.singer_id)

        if not sids:
            return

        drag = QDrag(self)
        mime = QMimeData()
        if len(sids) == 1:
            mime.setText(_build_singer_mime(sids[0]))
        else:
            mime.setText(_build_group_mime(sids[0], sids))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
