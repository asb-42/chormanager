"""ChorAufstellung :class:`SingerTile` widget.

M-2 Schritt 5: extracted the ``SingerTile`` class from
``choraufstellung/main.py`` (formerly Z. 84-208).

A :class:`SingerTile` is a small ``QFrame`` that renders a single
:class:`Singer` and is used both inside the :class:`SingerPool` and
inside the :class:`FormationGrid`.  The class is intentionally kept
light on logic: drag/drop, parent-grid selection, context-menu and
shadow-effect setup all live here, but the heavyweight formation-grid
behaviour (place_singer, dropEvent handler, etc.) stays in
``FormationGrid`` itself.

The class uses a ``TYPE_CHECKING`` import for ``FormationGrid`` to
avoid the circular dependency: at runtime the parent reference is
duck-typed (``hasattr``/``isinstance``) and the type hint is only
needed for static analysis.

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 5.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

# PyQt5/PyQt6 cross-compat via the central ``qt_compat`` layer.
from qt_compat import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMenu,
    QDrag,
    QColor,
    QFont,
    QPoint,
    QApplication,
    QGraphicsDropShadowEffect,
    QMimeData,
    Qt,
    pyqtSignal,
)

# Domain model.  ``singer_model`` provides the ``voice_group_color``
# helper the tile uses to colour its background.
from singer_model import voice_group_color

if TYPE_CHECKING:
    # The tile's parent is often a :class:`FormationGrid`, but we
    # cannot import that at module-load time without creating a
    # circular dependency (the grid will live in
    # ``widgets/formation_grid.py`` and re-import ``SingerTile``).
    # The type hint is therefore only used by static checkers.
    from widgets.formation_grid import FormationGrid  # noqa: F401


class SingerTile(QFrame):
    """Visual tile for a single :class:`Singer` in the pool or grid.

    Emits:

    - ``removed`` (object)            — user clicked the × button
    - ``edit_requested`` (object)     — user picked "Bearbeiten" in the menu
    - ``affinity_requested`` (object) — user picked "Nähe setzen" in the menu
    """

    removed = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    affinity_requested = pyqtSignal(object)

    def __init__(self, singer, parent=None):
        super().__init__(parent)
        self.singer = singer
        self.position = None
        self._selected = False
        self.setFixedSize(120, 60)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self._bg = voice_group_color(singer.voice_group)
        self.setStyleSheet(
            f"background-color: {self._bg}; "
            f"border: 1px solid #888; border-radius: 4px;"
        )
        self.setAutoFillBackground(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(0)

        n = QLabel(f"<b>{singer.name}</b>")
        n.setAlignment(Qt.AlignCenter)
        n.setWordWrap(True)
        n.setStyleSheet(
            "background: transparent; color: #000; font-size: 9pt;"
        )
        lay.addWidget(n)

        vg = (
            singer.voice_group.value
            if hasattr(singer.voice_group, "value")
            else str(singer.voice_group)
        )
        v = QLabel(vg)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet(
            "background: transparent; color: #333; font-size: 8pt;"
        )
        lay.addWidget(v)

        if singer.height > 0:
            h = QLabel(f"{singer.height} cm")
            h.setAlignment(Qt.AlignCenter)
            h.setStyleSheet(
                "background: transparent; color: #555; font-size: 7pt;"
            )
            lay.addWidget(h)

        btn = QPushButton("×")
        btn.setFixedSize(14, 14)
        btn.setStyleSheet(
            "font-size: 10pt; padding: 0; "
            "background: transparent; border: none;"
        )
        btn.clicked.connect(self.on_remove)
        lay.addWidget(btn, alignment=Qt.AlignRight | Qt.AlignTop)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setXOffset(2)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 35))
        self.setGraphicsEffect(shadow)

    # ------------------------------------------------------------------
    # Context menu / signals
    # ------------------------------------------------------------------

    def show_context_menu(self, pos):
        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        affinity_action = menu.addAction("Nähe setzen")
        remove_action = menu.addAction("Entfernen")
        action = menu.exec(self.mapToGlobal(pos))
        if action == edit_action:
            self.edit_requested.emit(self)
        elif action == affinity_action:
            self.affinity_requested.emit(self)
        elif action == remove_action:
            self.on_remove()

    def on_remove(self):
        self.removed.emit(self)

    def set_selected(self, selected: bool) -> None:
        """Toggle the highlight border to indicate selection."""
        self._selected = selected
        bg = voice_group_color(self.singer.voice_group)
        if selected:
            self.setStyleSheet(
                f"background-color: {bg}; "
                f"border: 3px solid #0066cc; border-radius: 4px;"
            )
        else:
            self.setStyleSheet(
                f"background-color: {bg}; "
                f"border: 1px solid #888; border-radius: 4px;"
            )
        # ``style().polish`` is the documented way to force a re-apply
        # of the stylesheet without re-setting it.
        self.style().polish(self)

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start_pos = e.globalPosition()
            modifiers = QApplication.keyboardModifiers()
            parent_grid = self.parent()

            # Duck-typing the parent: instead of
            # ``isinstance(parent_grid, FormationGrid)`` (which would
            # require importing ``widgets.formation_grid`` and would
            # break the moment ``FormationGrid`` is in the middle of
            # being moved out of ``main.py``), we just check for the
            # attributes the tile needs.  This decouples the tile
            # from the exact grid class while keeping the same
            # behaviour: anything that quacks like a formation grid
            # (selected_ids, update_selection_visuals,
            # is_group_dragging) gets the selection handling.
            if (
                parent_grid is not None
                and hasattr(parent_grid, "selected_ids")
                and hasattr(parent_grid, "update_selection_visuals")
                and hasattr(parent_grid, "is_group_dragging")
            ):
                sid = self.singer.singer_id
                if modifiers & Qt.ControlModifier:
                    if sid in parent_grid.selected_ids:
                        parent_grid.selected_ids.remove(sid)
                    else:
                        parent_grid.selected_ids.add(sid)
                else:
                    if sid not in parent_grid.selected_ids:
                        parent_grid.selected_ids = {sid}

                parent_grid.update_selection_visuals()
                parent_grid.is_group_dragging = False

    def dragEnterEvent(self, e):
        e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        e.acceptProposedAction()
        parent = self.parent()
        if parent and hasattr(parent, "dropEvent"):
            parent.dropEvent(e)

    def mouseMoveEvent(self, e):
        if not hasattr(self, "_drag_start_pos"):
            super().mouseMoveEvent(e)
            return

        if not (e.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(e)
            return

        dist = (e.globalPosition() - self._drag_start_pos).manhattanLength()
        if dist > QApplication.startDragDistance():
            drag = QDrag(self)
            mime = QMimeData()

            parent_grid = self.parent()
            # Same duck-typing trick as in ``mousePressEvent``:
            # we don't import FormationGrid here, we just check for
            # the attributes the drag-init code needs.
            if (
                parent_grid is not None
                and hasattr(parent_grid, "selected_ids")
                and len(parent_grid.selected_ids) > 1
            ):
                group_ids = list(parent_grid.selected_ids)
                mime.setText(
                    f"singer:{self.singer.singer_id}"
                    f":group:{','.join(group_ids)}"
                )
            else:
                pos_info = (
                    f":pos:{self.position[0]},{self.position[1]}"
                    if self.position
                    else ""
                )
                mime.setText(
                    f"singer:{self.singer.singer_id}{pos_info}"
                )

            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(
                QPoint(self.width() // 2, self.height() // 2)
            )

            self.hide()
            action = drag.exec(Qt.DropAction.MoveAction)
            self.show()

            if hasattr(self, "_drag_start_pos"):
                del self._drag_start_pos
        else:
            super().mouseMoveEvent(e)
