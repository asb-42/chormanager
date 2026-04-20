# TDD: UI Components - Draggable widgets and SingerTile
try:
    from PyQt6.QtWidgets import (
        QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
        QFrame, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QMenu,
        QHeaderView
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QRect
    from PyQt6.QtGui import QDrag, QColor, QFont, QGraphicsDropShadowEffect
except ImportError:
    from PyQt5.QtWidgets import (
        QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
        QFrame, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QMenu,
        QHeaderView
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QRect
    from PyQt5.QtGui import QDrag, QColor, QFont, QGraphicsDropShadowEffect

from qt_compat import exec_qt


class DraggableListWidget(QListWidget):
    def startDrag(self, actions):
        item = self.currentItem()
        if item:
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(f"singer:{singer.singer_id}")
                drag.setMimeData(mime)
                drag.exec(Qt.DragAction.Copy)
        else:
            super().startDrag(actions)


class DraggableTableWidget(QTableWidget):
    def startDrag(self, actions):
        row = self.currentRow()
        if row >= 0:
            item = self.item(row, 0)
            if item:
                singer = item.data(Qt.ItemDataRole.UserRole)
                if singer:
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setText(f"singer:{singer.singer_id}")
                    drag.setMimeData(mime)
                    drag.exec(Qt.DragAction.Copy)


class SingerTile(QFrame):
    removed = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    affinity_requested = pyqtSignal(object)

    def __init__(self, singer, parent=None):
        super().__init__(parent)
        self.singer = singer
        self.position = None
        self._drag_start_pos = None
        self.setFixedSize(120, 70)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._setup_ui()

    def _setup_ui(self):
        bg = voice_group_color(self.singer.voice_group)
        self.setStyleSheet(f"background-color: {bg}; border: 1px solid #888; border-radius: 4px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        n = QLabel(self.singer.name)
        n.setAlignment(Qt.AlignCenter)
        n.setStyleSheet("background: transparent; color: #222; font-weight: bold; font-size: 9pt;")
        lay.addWidget(n)
        vg = self.singer.voice_group.value if hasattr(self.singer.voice_group, 'value') else str(self.singer.voice_group)
        v = QLabel(vg)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet("background: transparent; color: #333; font-size: 8pt;")
        lay.addWidget(v)
        if self.singer.height > 0:
            h = QLabel(f"{self.singer.height} cm")
            h.setAlignment(Qt.AlignCenter)
            h.setStyleSheet("background: transparent; color: #555; font-size: 7pt;")
            lay.addWidget(h)
        btn = QPushButton("×")
        btn.setFixedSize(14, 14)
        btn.setStyleSheet("font-size: 10pt; padding: 0; background: transparent; border: none;")
        btn.clicked.connect(self.on_remove)
        lay.addWidget(btn, alignment=Qt.AlignRight | Qt.AlignTop)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setXOffset(2)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 35))
        self.setGraphicsEffect(shadow)

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

    def set_selected(self, selected: bool):
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
        self.style().polish(self)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ControlModifier:
                e.ignore()
                return

            parent_grid = self.parent()
            if isinstance(parent_grid, FormationGrid) and len(parent_grid.selected_ids) > 1 and self.singer.singer_id in parent_grid.selected_ids:
                parent_grid.is_group_dragging = True
                parent_grid.drag_start_pos = e.pos()

            self._drag_start_pos = e.globalPos()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and hasattr(self, '_drag_start_pos'):
            if (e.globalPos() - self._drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()

                parent_grid = self.parent()
                if isinstance(parent_grid, FormationGrid) and len(parent_grid.selected_ids) > 1 and self.singer.singer_id in parent_grid.selected_ids:
                    group_ids = ",".join(parent_grid.selected_ids)
                    mime.setText(f"singer:{self.singer.singer_id}:group:{group_ids}")
                else:
                    pos_info = f":pos:{self.position[0]},{self.position[1]}" if self.position else ""
                    mime.setText(f"singer:{self.singer.singer_id}{pos_info}")

                drag.setMimeData(mime)
                drag.setPixmap(self.grab())

                self.hide()
                action = drag.exec(Qt.DragAction.Move)
                self.show()

                if hasattr(self, '_drag_start_pos'):
                    del self._drag_start_pos
                return
        super().mouseMoveEvent(e)


# Forward reference for type hints
FormationGrid = None


def set_formation_grid_class(cls):
    global FormationGrid
    FormationGrid = cls