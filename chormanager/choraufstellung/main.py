import sys
import os
import json

try:
    from qt_compat import exec_qt
except ImportError:
    def exec_qt(obj, action=None):
        if action is None:
            return obj.exec_()
        else:
            return obj.exec_(action)

# PyQt6 and PyQt5 compatibility - handle enum changes between versions
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QMenuBar, QMenu,
        QFileDialog, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidget,
        QListWidgetItem, QScrollArea, QMessageBox, QFrame, QCheckBox, QSplitter,
        QGraphicsDropShadowEffect, QRubberBand,
        QCompleter, QTableWidget, QTableWidgetItem, QHeaderView,
        QRadioButton
    )
    from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QRect, QTimer, QPoint
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
    from PyQt6.QtGui import QDrag, QColor, QPalette, QFont, QAction, QUndoStack, QUndoCommand, QActionGroup

    QFrame.Panel = QFrame.Shape.Panel
    QFrame.Raised = QFrame.Shadow.Raised
    QFrame.Sunken = QFrame.Shadow.Sunken
    QFrame.HLine = QFrame.Shape.HLine
    QFrame.VLine = QFrame.Shape.VLine
    QFrame.StyledPanel = QFrame.Shape.StyledPanel
    QFrame.NoFrame = QFrame.Shape.NoFrame

    Qt.Horizontal = Qt.Orientation.Horizontal
    Qt.Vertical = Qt.Orientation.Vertical
    Qt.AlignCenter = Qt.AlignmentFlag.AlignCenter
    Qt.AlignRight = Qt.AlignmentFlag.AlignRight
    Qt.AlignTop = Qt.AlignmentFlag.AlignTop
    Qt.LeftButton = Qt.MouseButton.LeftButton
    Qt.RightButton = Qt.MouseButton.RightButton
    Qt.ControlModifier = Qt.KeyboardModifier.ControlModifier

except ImportError:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QMenuBar, QMenu,
        QFileDialog, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidget,
        QListWidgetItem, QScrollArea, QMessageBox, QFrame, QCheckBox, QSplitter,
        QUndoStack, QUndoCommand, QGraphicsDropShadowEffect, QRubberBand,
        QCompleter, QTableWidget, QTableWidgetItem, QHeaderView,
        QRadioButton
    )
    from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QRect, QTimer
    from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
    from PyQt5.QtGui import QDrag, QColor, QPalette, QFont, QAction, QActionGroup

try:
    from config import load_settings, save_settings, load_voice_groups_config, get_valid_voice_groups, get_voice_group_color, get_data_dir, clear_color_cache
except ImportError:
    def load_settings(): return {"theme": "standard"}
    def save_settings(s): return True
    def load_voice_groups_config(): return []
    def get_valid_voice_groups(): return []
    def get_voice_group_color(v): return "#cccccc"
    def get_data_dir(): return "."
    def clear_color_cache(): pass

try:
    from PyQt6.QtWidgets import QDialog
except ImportError:
    from PyQt5.QtWidgets import QDialog

try:
    from singer_model import Singer, VoiceGroup, voice_group_color
    from storage import FormationStorage
    from pdf_export import PDFExporter
    from core.optimizer import FormationOptimizer
    from core.grid_engine import GridEngine, GridConfig
    from ui.optimizer_dialog import OptimizerDialog
except ImportError:
    from enum import Enum
    class VoiceGroup(Enum):
        SOPRAN_1 = "Sopran 1"
    def voice_group_color(vg): return "#cccccc"
    class Singer:
        def __init__(self, name, voice_group, height=0, singer_id="1"):
            self.name, self.voice_group, self.height, self.singer_id = name, voice_group, height, singer_id
    class FormationStorage:
        def load_formation(self, f): return None
        def save_formation(self, *a): return True
    class PDFExporter:
        def export_formation(self, *a): return True
    class FormationOptimizer:
        @staticmethod
        def run(*a): return None
    class OptimizerDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Optimierung nicht verfügbar")
    class GridEngine:
        def __init__(self, *a): pass

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
                drag.exec(Qt.DropAction.CopyAction)
        else:
            super().startDrag(actions)

class DraggableTableWidget(QTableWidget):
    def startDrag(self, actions):
        selected = self.selectedItems()
        if not selected:
            return
        
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
            mime.setText(f"singer:{sids[0]}")
        else:
            mime.setText(f"singer:{sids[0]}:group:{','.join(sids)}")
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

class SingerTile(QFrame):
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
        self.setStyleSheet(f"background-color: {self._bg}; border: 1px solid #888; border-radius: 4px;")
        self.setAutoFillBackground(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        lay = QVBoxLayout(self); lay.setContentsMargins(4,2,4,2); lay.setSpacing(0)
        n = QLabel(f"<b>{singer.name}</b>"); n.setAlignment(Qt.AlignCenter); n.setWordWrap(True)
        n.setStyleSheet("background: transparent; color: #000; font-size: 9pt;"); lay.addWidget(n)
        vg = singer.voice_group.value if hasattr(singer.voice_group, 'value') else str(singer.voice_group)
        v = QLabel(vg); v.setAlignment(Qt.AlignCenter); v.setStyleSheet("background: transparent; color: #333; font-size: 8pt;"); lay.addWidget(v)
        if singer.height > 0:
            h = QLabel(f"{singer.height} cm"); h.setAlignment(Qt.AlignCenter); h.setStyleSheet("background: transparent; color: #555; font-size: 7pt;"); lay.addWidget(h)
        btn = QPushButton("×"); btn.setFixedSize(14,14); btn.setStyleSheet("font-size: 10pt; padding: 0; background: transparent; border: none;")
        btn.clicked.connect(self.on_remove); lay.addWidget(btn, alignment=Qt.AlignRight | Qt.AlignTop)
        
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
    def on_remove(self): self.removed.emit(self)
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
            self._drag_start_pos = e.globalPosition()
            modifiers = QApplication.keyboardModifiers()
            parent_grid = self.parent()
            
            if isinstance(parent_grid, FormationGrid):
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
        if parent and hasattr(parent, 'dropEvent'):
            parent.dropEvent(e)
    def mouseMoveEvent(self, e):
        if not hasattr(self, '_drag_start_pos'):
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
            if isinstance(parent_grid, FormationGrid) and len(parent_grid.selected_ids) > 1:
                group_ids = list(parent_grid.selected_ids)
                mime.setText(f"singer:{self.singer.singer_id}:group:{','.join(group_ids)}")
            else:
                pos_info = f":pos:{self.position[0]},{self.position[1]}" if self.position else ""
                mime.setText(f"singer:{self.singer.singer_id}{pos_info}")
            
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(QPoint(self.width() // 2, self.height() // 2))
            
            self.hide()
            action = drag.exec(Qt.DropAction.MoveAction)
            self.show()
            
            if hasattr(self, '_drag_start_pos'):
                del self._drag_start_pos
        else:
            super().mouseMoveEvent(e)

class MoveSingerCommand(QUndoCommand):
    def __init__(self, singer, old_row, old_col, new_row, new_col, grid):
        super().__init__()
        self.singer = singer
        self.old_row = old_row
        self.old_col = old_col
        self.new_row = new_row
        self.new_col = new_col
        self.grid = grid
        self.setText("Sänger verschoben")
    
    def redo(self):
        self.singer.row = self.new_row
        self.singer.col = self.new_col
        self.grid.refresh_grid()
    
    def undo(self):
        self.singer.row = self.old_row
        self.singer.col = self.old_col
        self.grid.refresh_grid()

class SwapSingersCommand(QUndoCommand):
    def __init__(self, singer1, singer2, grid):
        super().__init__("Positionen getauscht")
        self.singer1 = singer1
        self.singer2 = singer2
        self.grid = grid
        self.old_row1, self.old_col1 = singer1.row, singer1.col
        self.old_row2, self.old_col2 = singer2.row, singer2.col
    
    def redo(self):
        self.singer1.row, self.singer2.row = self.old_row2, self.old_row1
        self.singer1.col, self.singer2.col = self.old_col2, self.old_col1
        self.grid.refresh_grid()
    
    def undo(self):
        self.singer1.row, self.singer2.row = self.old_row1, self.old_row2
        self.singer1.col, self.singer2.col = self.old_col1, self.old_col2
        self.grid.refresh_grid()

class MoveGroupCommand(QUndoCommand):
    def __init__(self, selected_ids, dx, dy, grid):
        super().__init__("Gruppe verschoben")
        self.selected_ids = selected_ids
        self.dx = dx
        self.dy = dy
        self.grid = grid
        self.old_positions = {}
        for sid in selected_ids:
            singer = next((s for s in grid.singers if s.singer_id == sid), None)
            if singer:
                self.old_positions[sid] = (singer.row, singer.col)

    def redo(self):
        for sid in self.selected_ids:
            singer = next((s for s in self.grid.singers if s.singer_id == sid), None)
            if singer:
                singer.row += self.dy
                singer.col += self.dx
        self.grid.refresh_grid()

    def undo(self):
        for sid in self.selected_ids:
            singer = next((s for s in self.grid.singers if s.singer_id == sid), None)
            if singer and sid in self.old_positions:
                singer.row, singer.col = self.old_positions[sid]
        self.grid.refresh_grid()

class FormationGrid(QWidget):
    singer_removed_from_grid = pyqtSignal(object)
    singer_edit_requested = pyqtSignal(object)
    singer_affinity_requested = pyqtSignal(object)
    selection_changed = pyqtSignal()
    
    CELL_WIDTH = 130
    CELL_HEIGHT = 80
    OFFSET = 65
    MARGIN_LEFT = 80
    MARGIN_TOP = 20
    
    def __init__(self, rows=4, cols=5, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            background: #f8f4eb;
            border: 1px solid #d4c9b8;
        """)
        self.rows = rows
        self.cols = cols
        self.staggered = False
        self.singers = []
        self.tiles = {}
        self.selected_ids = set()
        
        self.rubber_band = None
        self.drag_start_pos = None
        self.is_group_dragging = False
        self.undo_stack = QUndoStack(self)
        self.setAcceptDrops(True)
        self.setMinimumSize(self.cols * self.CELL_WIDTH + self.MARGIN_LEFT + 50, 
                           self.rows * self.CELL_HEIGHT + self.MARGIN_TOP + 50)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_grid_context_menu)
    
    def show_grid_context_menu(self, pos):
        menu = QMenu(self)
        
        if len(self.selected_ids) == 1:
            sid = list(self.selected_ids)[0]
            singer = next((s for s in self.singers if s.singer_id == sid), None)
            if singer and singer.affinity:
                partner = next((s for s in self.singers if s.singer_id == singer.affinity), None)
                if partner and partner.row >= 0 and singer.row >= 0:
                    affinity_action = menu.addAction(f" Nähe: {singer.name} → {partner.name} platzieren")
                    affinity_action.triggered.connect(lambda: self.apply_affinity_proximity(singer))
                    menu.addSeparator()
        
        if len(self.selected_ids) == 2:
            swap_action = menu.addAction("Positionen tauschen")
            swap_action.triggered.connect(self.swap_selected_singers)
            menu.addSeparator()
        
        undo_action = menu.addAction("Rückgängig")
        undo_action.setEnabled(self.undo_stack.canUndo())
        undo_action.triggered.connect(self.undo_stack.undo)
        
        redo_action = menu.addAction("Wiederholen")
        redo_action.setEnabled(self.undo_stack.canRedo())
        redo_action.triggered.connect(self.undo_stack.redo)
        
        menu.exec(self.mapToGlobal(pos))
    
    def set_dimensions(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.setMinimumSize(cols * self.CELL_WIDTH + self.MARGIN_LEFT + 50, 
                           rows * self.CELL_HEIGHT + self.MARGIN_TOP + 50)
        self.refresh_grid()
    
    def set_staggered(self, v):
        self.staggered = v
        self.refresh_grid()
    
    def update_selection_visuals(self):
        for tile in list(self.tiles.values()):
            if isinstance(tile, SingerTile):
                tile.set_selected(tile.singer.singer_id in self.selected_ids)
    
    def highlight_singer(self, singer, parent_window):
        if singer.singer_id not in self.tiles:
            return
        tile = self.tiles[singer.singer_id]
        
        self._search_pulse_count = 0
        self._search_pulse_max = 5
        self._search_pulse_timer = QTimer(self)
        self._search_pulse_timer.timeout.connect(lambda: self._pulse_step(tile, parent_window))
        self._search_pulse_timer.start(200)
    
    def _pulse_step(self, tile, parent_window):
        count = self._search_pulse_count
        if count >= self._search_pulse_max * 2:
            self._search_pulse_timer.stop()
            self._restore_tile_style(tile)
            if parent_window:
                parent_window.search_input.clear()
            return
        
        is_odd = count % 2 == 1
        vg_color = voice_group_color(tile.singer.voice_group)
        
        if is_odd:
            tile.setStyleSheet(f"""
                background-color: #FFD700;
                border: 3px solid #FF8C00;
                border-radius: 4px;
            """)
            self._pulse_bring_to_front(tile)
        else:
            self._restore_tile_style(tile)
        
        self._search_pulse_count += 1
    
    def _restore_tile_style(self, tile):
        tile.setStyleSheet("")
        vg_color = voice_group_color(tile.singer.voice_group)
        tile.set_selected(tile.singer.singer_id in self.selected_ids)
        tile.style().polish(tile)
    
    def _pulse_bring_to_front(self, tile):
        tile.raise_()
        tile.update()
    
    def clear_search_highlight(self):
        if hasattr(self, '_search_pulse_timer') and self._search_pulse_timer:
            self._search_pulse_timer.stop()
        for tile in list(self.tiles.values()):
            if isinstance(tile, SingerTile):
                self._restore_tile_style(tile)
    
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)

        widget = self.childAt(e.pos())
        if isinstance(widget, SingerTile):
            sid = widget.singer.singer_id
            modifiers = QApplication.keyboardModifiers()

            if modifiers & Qt.ControlModifier:
                if sid in self.selected_ids:
                    self.selected_ids.discard(sid)
                else:
                    self.selected_ids.add(sid)
                self.update_selection_visuals()
                self.selection_changed.emit()
                return

            if sid in self.selected_ids and len(self.selected_ids) > 1:
                self.is_group_dragging = True
                self.drag_start_pos = e.pos()
                return

            self.selected_ids.clear()
            self.selected_ids.add(sid)
            self.update_selection_visuals()
            self.selection_changed.emit()
            return

        self.selected_ids.clear()
        self.update_selection_visuals()
        self.selection_changed.emit()

        self.drag_start_pos = e.pos()
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.rubber_band.setGeometry(QRect(self.drag_start_pos, self.drag_start_pos))
        self.rubber_band.show()

    def mouseMoveEvent(self, e):
        if self.rubber_band and self.rubber_band.isVisible():
            rect = QRect(self.drag_start_pos, e.pos()).normalized()
            self.rubber_band.setGeometry(rect)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.rubber_band and self.rubber_band.isVisible():
            rect = self.rubber_band.geometry()
            self.rubber_band.hide()
            self.rubber_band = None

            for tile in list(self.tiles.values()):
                if rect.intersects(tile.geometry()):
                    self.selected_ids.add(tile.singer.singer_id)

            self.update_selection_visuals()
            self.selection_changed.emit()

        self.refresh_grid()
        super().mouseReleaseEvent(e)

    def swap_selected_singers(self):
        if len(self.selected_ids) != 2:
            QMessageBox.warning(self, "Fehler", "Bitte genau zwei Sänger auswählen (Ctrl+Klick).")
            return

        sid1, sid2 = list(self.selected_ids)
        singer1 = next((s for s in self.singers if s.singer_id == sid1), None)
        singer2 = next((s for s in self.singers if s.singer_id == sid2), None)

        if not singer1 or not singer2:
            return

        command = SwapSingersCommand(singer1, singer2, self)
        self.undo_stack.push(command)

        self.selected_ids.clear()
        self.refresh_grid()
    
    def apply_affinity_proximity(self, singer):
        if not singer.affinity:
            return False
        
        partner = next((s for s in self.singers if s.singer_id == singer.affinity), None)
        if not partner or partner.row < 0 or singer.row < 0:
            return False
        
        if singer.row != partner.row:
            return False
        
        if abs(singer.col - partner.col) == 1:
            return False
        
        target_col = singer.col + 1 if singer.col < partner.col else singer.col - 1
        
        if target_col < 0 or target_col >= self.cols:
            return False
        
        occupant = next((s for s in self.singers if s.row == singer.row and s.col == target_col), None)
        
        if occupant and occupant.singer_id != partner.singer_id:
            old_row, old_col = partner.row, partner.col
            partner.row, partner.col = occupant.row, occupant.col
            occupant.row, occupant.col = old_row, old_col
        elif not occupant:
            partner.row, partner.col = singer.row, target_col
        
        self.refresh_grid()
        return True
    
    def refresh_grid(self):
        for tile in list(self.tiles.values()):
            tile.deleteLater()
        self.tiles.clear()
        
        for label in list(self.findChildren(QLabel)):
            if label.text().startswith("Reihe "):
                label.deleteLater()
        
        for cell in list(self.findChildren(QFrame)):
            if hasattr(cell, '_is_grid_cell'):
                cell.deleteLater()
        
        for r in range(self.rows):
            for c in range(self.cols):
                cell = QFrame(self)
                cell._is_grid_cell = True
                x = self.MARGIN_LEFT + c * self.CELL_WIDTH
                if self.staggered and r % 2 == 1:
                    x += self.OFFSET
                y = self.MARGIN_TOP + r * self.CELL_HEIGHT
                cell.setGeometry(x, y, self.CELL_WIDTH - 5, self.CELL_HEIGHT - 5)
                cell.setFrameShape(QFrame.Panel)
                cell.setFrameShadow(QFrame.Sunken)
                cell.setStyleSheet("""
                    background-color: rgba(255,255,255, 0.65);
                    border: 1px solid #d4c9b8;
                    border-radius: 3px;
                """)
                cell.lower()
                cell.show()
        
        for singer in self.singers:
            if singer.row >= 0 and singer.col >= 0:
                tile = SingerTile(singer)
                tile.position = (singer.row, singer.col)
                tile.removed.connect(self.on_tile_removed)
                tile.edit_requested.connect(self.on_tile_edit_requested)
                tile.affinity_requested.connect(self.on_tile_affinity_requested)
                
                x = self.MARGIN_LEFT + singer.col * self.CELL_WIDTH
                if self.staggered and singer.row % 2 == 1:
                    x += self.OFFSET
                y = self.MARGIN_TOP + singer.row * self.CELL_HEIGHT
                
                tile.setParent(self)
                tile.move(x, y)
                tile.show()
                tile.installEventFilter(self)
                self.tiles[singer.singer_id] = tile
        
        self.update_selection_visuals()
        self.update()
        self.updateGeometry()
    
    def place_singer(self, singer):
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.is_occupied(r, c):
                    return self.place_singer_at(singer, r, c)
        return False
    
    def place_singer_at(self, singer, r, c):
        singer.row = r
        singer.col = c
        if singer not in self.singers:
            self.singers.append(singer)
        self.refresh_grid()
        return True
    
    def is_occupied(self, r, c):
        for s in self.singers:
            if s.row == r and s.col == c:
                return True
        return False
    
    def get_singer_at(self, r, c):
        for s in self.singers:
            if s.row == r and s.col == c:
                return s
        return None
    
    def on_tile_removed(self, tile):
        singer = tile.singer
        if singer in self.singers:
            singer.row = -1
            singer.col = -1
            self.singers.remove(singer)
        if singer.singer_id in self.tiles:
            del self.tiles[singer.singer_id]
        tile.deleteLater()
        self.refresh_grid()
        self.singer_removed_from_grid.emit(singer)
    
    def on_tile_edit_requested(self, tile):
        self.singer_edit_requested.emit(tile.singer)
    
    def on_tile_affinity_requested(self, tile):
        self.singer_affinity_requested.emit(tile.singer)
    
    def get_placed_singers(self):
        return [(s, s.row, s.col) for s in self.singers if s.row >= 0]
    
    def get_placed_singer_ids(self):
        return {s.singer_id for s in self.singers if s.row >= 0}
    
    def auto_arrange_by_height(self):
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'singers'):
            main_window = main_window.parent()
        
        if not main_window or not main_window.singers:
            return
        
        all_singers = main_window.singers
        sorted_singers = sorted(
            all_singers,
            key=lambda s: (-s.height, (s.voice_group.value if hasattr(s.voice_group, 'value') else str(s.voice_group)), s.name)
        )
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if idx < len(sorted_singers):
                    s = sorted_singers[idx]
                    s.row = r
                    s.col = c
                    idx += 1
                else:
                    break
        for s in all_singers:
            if s not in sorted_singers[:idx]:
                s.row = -1
                s.col = -1
        self.refresh_grid()
        if hasattr(main_window, 'update_grid_count'):
            main_window.update_grid_count()
        if hasattr(main_window, 'pool'):
            main_window.pool.update_singers(all_singers, self.get_placed_singer_ids())
    
    def auto_arrange_men_outer(self):
        if not self.singers:
            return
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)
        basses = [s for s in self.singers if "Bass" in get_vg(s.voice_group)]
        tenors = [s for s in self.singers if "Tenor" in get_vg(s.voice_group)]
        others = [s for s in self.singers if s not in basses and s not in tenors]
        basses.sort(key=lambda s: (get_vg(s.voice_group), s.name))
        tenors.sort(key=lambda s: (get_vg(s.voice_group), s.name))
        others.sort(key=lambda s: (get_vg(s.voice_group), s.name))
        idx = 0
        for s in basses[:len(basses)//2]:
            s.row = idx % self.rows
            s.col = 0
            idx += 1
        for s in tenors[:len(tenors)//2]:
            s.row = idx % self.rows
            s.col = 1
            idx += 1
        for s in basses[len(basses)//2:]:
            s.row = idx % self.rows
            s.col = self.cols - 1
            idx += 1
        for s in tenors[len(tenors)//2:]:
            s.row = idx % self.rows
            s.col = self.cols - 2
            idx += 1
        mid_col_start = 2
        mid_col_end = self.cols - 3
        for s in others:
            s.row = idx % self.rows
            s.col = mid_col_start + (idx % (mid_col_end - mid_col_start + 1))
            idx += 1
        for s in self.singers:
            if not (0 <= s.row < self.rows and 0 <= s.col < self.cols):
                s.row = s.col = -1
        self.refresh_grid()
    
    def auto_arrange_satb(self):
        if not self.singers:
            return
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)
        sopran = [s for s in self.singers if "Sopran" in get_vg(s.voice_group)]
        alt = [s for s in self.singers if "Alt" in get_vg(s.voice_group)]
        tenor = [s for s in self.singers if "Tenor" in get_vg(s.voice_group)]
        bass = [s for s in self.singers if "Bass" in get_vg(s.voice_group)]
        sopran.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)
        ordered = sopran + alt + tenor + bass
        idx = 0
        for col in range(self.cols):
            for row in range(self.rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    idx += 1
                else:
                    break
        for s in self.singers:
            if s not in ordered[:idx]:
                s.row = -1
                s.col = -1
        self.refresh_grid()
    
    def auto_arrange_sbta(self):
        if not self.singers:
            return
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)
        sopran = [s for s in self.singers if "Sopran" in get_vg(s.voice_group)]
        alt = [s for s in self.singers if "Alt" in get_vg(s.voice_group)]
        tenor = [s for s in self.singers if "Tenor" in get_vg(s.voice_group)]
        bass = [s for s in self.singers if "Bass" in get_vg(s.voice_group)]
        sopran.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)
        ordered = sopran + bass + tenor + alt
        idx = 0
        for col in range(self.cols):
            for row in range(self.rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    idx += 1
                else:
                    break
        for s in self.singers:
            if s not in ordered[:idx]:
                s.row = -1
                s.col = -1
        self.refresh_grid()
    
    def optimize(self, primary_rule=None, refinement_rules=None):
        rule_ids = []
        if primary_rule:
            rule_ids.append(primary_rule)
        if refinement_rules:
            rule_ids.extend(refinement_rules)
        
        if not rule_ids:
            return
        
        try:
            from core.optimizer import FormationOptimizer
            FormationOptimizer.run(self, rule_ids)
        except Exception as e:
            print(f"Optimization error: {e}")
    
    def dragMoveEvent(self, e):
        e.acceptProposedAction()
    
    def dragEnterEvent(self, e):
        e.acceptProposedAction()
    
    def dropEvent(self, e):
        e.acceptProposedAction()
        txt = e.mimeData().text()
        if not txt.startswith("singer:"):
            return

        is_group_move = ":group:" in txt
        sid = txt.split(":group:")[0].replace("singer:", "") if is_group_move else txt.replace("singer:", "")
        if ":pos:" in sid:
            sid = sid.split(":pos:")[0]

        dragged_singer = next((s for s in self.singers if s.singer_id == sid), None)
        if not dragged_singer:
            self.refresh_grid()
            return

        pos = e.position()
        row = int((pos.y() - self.MARGIN_TOP) / self.CELL_HEIGHT)
        col_offset = self.OFFSET if (self.staggered and row % 2 == 1) else 0
        col = int((pos.x() - self.MARGIN_LEFT - col_offset) / self.CELL_WIDTH)

        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            self.refresh_grid()
            return

        if is_group_move:
            group_ids = txt.split(":group:")[1].split(",")
            delta_row = row - dragged_singer.row
            delta_col = col - dragged_singer.col

            if delta_row == 0 and delta_col == 0:
                self.refresh_grid()
                return

            can_move = True
            for gid in group_ids:
                singer = next((s for s in self.singers if s.singer_id == gid), None)
                if singer is None:
                    can_move = False
                    break
                new_row = (singer.row or 0) + delta_row
                new_col = (singer.col or 0) + delta_col
                if new_row < 0 or new_row >= self.rows or new_col < 0 or new_col >= self.cols:
                    can_move = False
                    break
            
            if not can_move:
                QMessageBox.warning(self, "Rand erreicht", "Die Gruppe würde teilweise außerhalb des Rasters landen.")
                self.refresh_grid()
                return

            command = MoveGroupCommand(group_ids, delta_col, delta_row, self)
            self.undo_stack.push(command)

            self.selected_ids.clear()

        else:
            old_row = dragged_singer.row
            old_col = dragged_singer.col
            for s in self.singers:
                if s != dragged_singer and s.row == row and s.col == col:
                    if old_row >= 0:
                        s.row, s.col = old_row, old_col
                    else:
                        return
                    break

            dragged_singer.row = row
            dragged_singer.col = col

            if dragged_singer.row != old_row or dragged_singer.col != old_col:
                command = MoveSingerCommand(dragged_singer, old_row, old_col,
                                            dragged_singer.row, dragged_singer.col, self)
                self.undo_stack.push(command)

        self.refresh_grid()

    def auto_arrange_s1s2b2b1t2t1a2a1(self):
        if not self.singers:
            return
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)
        s1 = [s for s in self.singers if get_vg(s.voice_group) == "Sopran 1"]
        s2 = [s for s in self.singers if get_vg(s.voice_group) == "Sopran 2"]
        b2 = [s for s in self.singers if get_vg(s.voice_group) == "Bass 2"]
        b1 = [s for s in self.singers if get_vg(s.voice_group) == "Bass 1"]
        t2 = [s for s in self.singers if get_vg(s.voice_group) == "Tenor 2"]
        t1 = [s for s in self.singers if get_vg(s.voice_group) == "Tenor 1"]
        a2 = [s for s in self.singers if get_vg(s.voice_group) == "Alt 2"]
        a1 = [s for s in self.singers if get_vg(s.voice_group) == "Alt 1"]
        s1.sort(key=lambda s: s.name)
        s2.sort(key=lambda s: s.name)
        b2.sort(key=lambda s: s.name)
        b1.sort(key=lambda s: s.name)
        t2.sort(key=lambda s: s.name)
        t1.sort(key=lambda s: s.name)
        a2.sort(key=lambda s: s.name)
        a1.sort(key=lambda s: s.name)
        ordered = s1 + s2 + b2 + b1 + t2 + t1 + a2 + a1
        placed_ids = set()
        idx = 0
        for col in range(self.cols):
            for row in range(self.rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    placed_ids.add(s.singer_id)
                    idx += 1
                else:
                    break
        for s in self.singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1
        self.refresh_grid()

    def auto_arrange_s1s2a1a2t1t2b1b2(self):
        if not self.singers:
            return
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)
        s1 = [s for s in self.singers if get_vg(s.voice_group) == "Sopran 1"]
        s2 = [s for s in self.singers if get_vg(s.voice_group) == "Sopran 2"]
        a1 = [s for s in self.singers if get_vg(s.voice_group) == "Alt 1"]
        a2 = [s for s in self.singers if get_vg(s.voice_group) == "Alt 2"]
        t1 = [s for s in self.singers if get_vg(s.voice_group) == "Tenor 1"]
        t2 = [s for s in self.singers if get_vg(s.voice_group) == "Tenor 2"]
        b1 = [s for s in self.singers if get_vg(s.voice_group) == "Bass 1"]
        b2 = [s for s in self.singers if get_vg(s.voice_group) == "Bass 2"]
        s1.sort(key=lambda s: s.name)
        s2.sort(key=lambda s: s.name)
        a1.sort(key=lambda s: s.name)
        a2.sort(key=lambda s: s.name)
        t1.sort(key=lambda s: s.name)
        t2.sort(key=lambda s: s.name)
        b1.sort(key=lambda s: s.name)
        b2.sort(key=lambda s: s.name)
        ordered = s1 + s2 + a1 + a2 + t1 + t2 + b1 + b2
        placed_ids = set()
        idx = 0
        for col in range(self.cols):
            for row in range(self.rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    placed_ids.add(s.singer_id)
                    idx += 1
                else:
                    break
        for s in self.singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1
        self.refresh_grid()

    def auto_arrange_s1s2b1b2t1t2a1a2(self):
        if not self.singers:
            return
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)
        s1 = [s for s in self.singers if get_vg(s.voice_group) == "Sopran 1"]
        s2 = [s for s in self.singers if get_vg(s.voice_group) == "Sopran 2"]
        b1 = [s for s in self.singers if get_vg(s.voice_group) == "Bass 1"]
        b2 = [s for s in self.singers if get_vg(s.voice_group) == "Bass 2"]
        t1 = [s for s in self.singers if get_vg(s.voice_group) == "Tenor 1"]
        t2 = [s for s in self.singers if get_vg(s.voice_group) == "Tenor 2"]
        a1 = [s for s in self.singers if get_vg(s.voice_group) == "Alt 1"]
        a2 = [s for s in self.singers if get_vg(s.voice_group) == "Alt 2"]
        s1.sort(key=lambda s: s.name)
        s2.sort(key=lambda s: s.name)
        b1.sort(key=lambda s: s.name)
        b2.sort(key=lambda s: s.name)
        t1.sort(key=lambda s: s.name)
        t2.sort(key=lambda s: s.name)
        a1.sort(key=lambda s: s.name)
        a2.sort(key=lambda s: s.name)
        ordered = s1 + s2 + b1 + b2 + t1 + t2 + a1 + a2
        placed_ids = set()
        idx = 0
        for col in range(self.cols):
            for row in range(self.rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    placed_ids.add(s.singer_id)
                    idx += 1
                else:
                    break
        for s in self.singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1
        self.refresh_grid()

class SingerPool(QWidget):
    singer_selected = pyqtSignal(object); singer_added = pyqtSignal(object)
    singer_edit_requested = pyqtSignal(object)
    place_all_requested = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent); self.singers=[]
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<b>Sängerpool</b>"))
        self.pool_count_label = QLabel("0 Sänger")
        self.pool_count_label.setStyleSheet("color: #666; font-size: 9pt;")
        lay.addWidget(self.pool_count_label)
        lay.addWidget(QLabel("Doppelklick: automatisch\nDrag & Drop: manuell\nRechtsklick: Bearbeiten / Nähe"))
        self.table = DraggableTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Stimmgruppe", "Größe", "Nähe"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setDragDropMode(QTableWidget.DragDropMode.DragOnly)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.itemDoubleClicked.connect(self.on_dc)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellClicked.connect(self.on_cell_clicked)
        lay.addWidget(self.table)
        self.placed_singer_ids = set()
        
        btn_lay = QVBoxLayout()
        btn_lay.addWidget(QPushButton("Alle Sänger platzieren", clicked=self.place_all_requested.emit))
        btn_lay.addWidget(QPushButton("Einzelner Sänger", clicked=self.add_dialog))
        btn_lay.addWidget(QPushButton("Ausgewählten entfernen", clicked=self.remove_sel))
        lay.addLayout(btn_lay)
    
    def on_cell_clicked(self, row, col):
        singer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if singer:
            self.singer_selected.emit(singer)
    
    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            singer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if singer:
                menu = QMenu(self)
                edit_action = menu.addAction("Bearbeiten")
                affinity_action = menu.addAction("Nähe setzen")
                remove_action = menu.addAction("Entfernen")
                action = menu.exec(self.table.viewport().mapToGlobal(pos))
                if action == edit_action:
                    self.singer_edit_requested.emit(singer)
                elif action == affinity_action:
                    self.set_affinity(singer)
                elif action == remove_action:
                    self.table.selectRow(row)
                    self.remove_sel()
    
    def set_affinity(self, singer):
        d = AffinityDialog(self, singer=singer, all_singers=self.singers)
        if d.exec() == QDialog.DialogCode.Accepted:
            new_affinity_id = d.get_affinity_singer_id()
            old_affinity_id = singer.affinity
            
            if old_affinity_id:
                old_partner = next((s for s in self.singers if s.singer_id == old_affinity_id), None)
                if old_partner and old_partner.affinity == singer.singer_id:
                    old_partner.affinity = ""
            
            singer.affinity = new_affinity_id
            
            if new_affinity_id:
                partner = next((s for s in self.singers if s.singer_id == new_affinity_id), None)
                if partner:
                    partner.affinity = singer.singer_id
            
            self.update_singers(self.singers, self.placed_singer_ids)
            if hasattr(self.parent(), '_mark_modified'):
                self.parent()._mark_modified()
    
    def update_singers(self, singers, placed_ids=None):
        self.singers = singers
        if placed_ids is not None:
            self.placed_singer_ids = placed_ids
        self.table.setRowCount(0)
        for s in self.singers:
            if str(s.singer_id) in self.placed_singer_ids:
                continue
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)
            
            name_item = QTableWidgetItem(s.name)
            name_item.setData(Qt.ItemDataRole.UserRole, s)
            name_item.setFont(QFont("SansSerif", 9, QFont.Weight.Bold))
            vg_val = s.voice_group.value if hasattr(s.voice_group, 'value') else str(s.voice_group)
            vg_color = voice_group_color(s.voice_group)
            name_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 0, name_item)
            
            vg_item = QTableWidgetItem(vg_val)
            vg_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 1, vg_item)
            
            height_text = f"{s.height} cm" if s.height > 0 else ""
            height_item = QTableWidgetItem(height_text)
            height_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 2, height_item)
            
            affinity_name = ""
            if s.affinity:
                partner = next((p for p in self.singers if p.singer_id == s.affinity), None)
                if partner:
                    affinity_name = partner.name
            affinity_item = QTableWidgetItem(affinity_name)
            affinity_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 3, affinity_item)
        
        pool_count = self.table.rowCount()
        self.pool_count_label.setText(f"{pool_count} Sänger")
    
    def update_placed_singers(self, placed_ids):
        self.placed_singer_ids = placed_ids
        self.update_singers(self.singers, placed_ids)
    def add_singer(self, s): self.singers.append(s); self.update_singers(self.singers, self.placed_singer_ids)
    def add_dialog(self, singer=None):
        d = AddSingerDialog(self, singer=singer)
        if d.exec()==QDialog.DialogCode.Accepted:
            s = d.get_singer()
            if s: 
                if singer:
                    idx = next((i for i, x in enumerate(self.singers) if x.singer_id == singer.singer_id), -1)
                    if idx >= 0: self.singers[idx] = s
                else:
                    self.singers.append(s)
                self.update_singers(self.singers, self.placed_singer_ids)
                if singer: return s
                self.singer_added.emit(s)
                return s
        return None
    def on_dc(self, item):
        if item:
            row = item.row()
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer: self.singer_selected.emit(singer)
    def remove_sel(self):
        row = self.table.currentRow()
        if row >= 0:
            singer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if singer:
                idx = next((i for i, x in enumerate(self.singers) if x.singer_id == singer.singer_id), -1)
                if idx >= 0:
                    if singer.affinity:
                        partner = next((p for p in self.singers if p.singer_id == singer.affinity), None)
                        if partner:
                            partner.affinity = ""
                    self.singers.pop(idx)
            self.update_singers(self.singers, self.placed_singer_ids)

class AddSingerDialog(QDialog):
    def __init__(self, p=None, singer=None):
        super().__init__(p); self.singer = singer
        self.setWindowTitle("Sänger bearbeiten" if singer else "Sänger hinzufügen")
        l=QFormLayout(self); self.n=QLineEdit()
        self.n.setPlaceholderText("Nachname, Vorname")
        if singer: self.n.setText(singer.name)
        l.addRow("Name:", self.n); self.v=QComboBox()
        for vg in VoiceGroup: self.v.addItem(vg.value if hasattr(vg,'value') else str(vg), vg)
        if singer:
            vg_val = singer.voice_group.value if hasattr(singer.voice_group, 'value') else str(singer.voice_group)
            idx = self.v.findText(vg_val)
            if idx >= 0: self.v.setCurrentIndex(idx)
        l.addRow("Stimmgruppe:", self.v)
        self.h=QLineEdit()
        if singer and singer.height > 0: self.h.setText(str(singer.height))
        l.addRow("Größe (cm):", self.h)
        bl=QHBoxLayout()
        bl.addWidget(QPushButton("Speichern", clicked=self.accept))
        bl.addWidget(QPushButton("Abbrechen", clicked=self.reject)); l.addRow(bl)
    def get_singer(self):
        n=self.n.text().strip()
        if not n: return None
        h = 0
        try: h = int(self.h.text().strip()) if self.h.text().strip() else 0
        except: pass
        if self.singer:
            return Singer(n, self.v.currentData(), h, self.singer.singer_id)
        return Singer(n, self.v.currentData(), h)

class AffinityDialog(QDialog):
    def __init__(self, p=None, singer=None, all_singers=None):
        super().__init__(p)
        self.singer = singer
        self.all_singers = all_singers or []
        self.setWindowTitle(f"Nähe setzen für {singer.name}")
        self.setMinimumWidth(350)
        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"Singpartner für <b>{singer.name}</b> auswählen:"))
        
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.lineEdit().setPlaceholderText("Name eingeben oder auswählen...")
        
        other_singers = [s for s in self.all_singers if s.singer_id != singer.singer_id]
        for s in other_singers:
            self.combo.addItem(s.name, s.singer_id)
        
        if singer.affinity:
            idx = self.combo.findData(singer.affinity)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        
        completer = QCompleter([s.name for s in other_singers], self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.combo.setCompleter(completer)
        
        l.addWidget(self.combo)
        
        clear_btn = QPushButton("Keine Nähe")
        clear_btn.clicked.connect(self.clear_affinity)
        l.addWidget(clear_btn)
        
        bl = QHBoxLayout()
        bl.addWidget(QPushButton("Speichern", clicked=self.accept))
        bl.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        l.addLayout(bl)
    
    def clear_affinity(self):
        self.combo.setCurrentIndex(-1)
        self.combo.setCurrentText("")
    
    def get_affinity_singer_id(self):
        text = self.combo.currentText().strip()
        data = self.combo.currentData()
        if data:
            return data
        for s in self.all_singers:
            if s.name == text:
                return s.singer_id
        return ""

class VoicingConfigDialog(QDialog):
    def __init__(self, p=None):
        super().__init__(p)
        self.setStyleSheet("QDialog { background: #f9f6f0; }")
        self.setWindowTitle("Besatzung konfigurieren"); self.resize(300,350)
        l=QVBoxLayout(self); l.addWidget(QLabel("Aktive Stimmgruppen:"))
        s=QScrollArea(); s.setWidgetResizable(True); l.addWidget(s)
        c=QWidget(); self.vl=QVBoxLayout(c); s.setWidget(c)
        self.chk={}
        for vg in load_voice_groups_config():
            cb=QCheckBox(vg["id"])
            color = vg["color"]
            cb.setStyleSheet(f"""
                QCheckBox::indicator {{
                    width: 20px;
                    height: 20px;
                    border: 2px solid {color};
                    background-color: white;
                    border-radius: 3px;
                }}
                QCheckBox::indicator:hover {{
                    background-color: #f8f8f8;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {color};
                    border: 2px solid {color};
                    color: white;
                }}
                QCheckBox {{
                    spacing: 12px;
                    font-size: 10pt;
                }}
            """)
            self.chk[vg["id"]]=cb; self.vl.addWidget(cb)
        bl=QHBoxLayout(); bl.addWidget(QPushButton("OK", clicked=self.accept)); bl.addWidget(QPushButton("Abbrechen", clicked=self.reject)); l.addLayout(bl)
    def set_active(self, act):
        for g, c in self.chk.items(): c.setChecked(g in act)
    def get_active(self): return [g for g, c in self.chk.items() if c.isChecked()]

class MainWindow(QMainWindow):
    def __init__(self, chormanager_mode=False, project_name=None, event_date=None, event_name=None, db_path=None, event_id=None, event_type=None):
        super().__init__()
        
        self.chormanager_mode = chormanager_mode
        self.project_name = project_name
        self.event_date = event_date
        self.event_name = event_name
        self.db_path = db_path
        self.event_id = event_id
        self.event_type = event_type or ""
        
        self.storage = FormationStorage()
        self.pdf = PDFExporter()
        self.file = None
        self.singers = []
        self.cfg = get_valid_voice_groups()
        
        self.engine = GridEngine(GridConfig(rows=4, cols=5, staggered=False))
        
        self.is_modified = False
        self.last_manual_save_mtime = 0
        self._loaded_metadata = {
            "project": project_name or "",
            "event": event_name or "",
            "event_date": event_date or "",
            "event_type": event_type or ""
        }
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave_check)
        self.autosave_timer.start(120000)
        
        self.setup_ui()
        self.resize(1100, 750)
        
        if self.chormanager_mode:
            self._load_from_chormanager()
        else:
            self._check_recovery()
        
        settings = load_settings()
        current_theme = settings.get("theme", "light")
        self._apply_theme(current_theme)
        
        if current_theme == "dark":
            self.actionDark.setChecked(True)
        else:
            self.actionLight.setChecked(True)

    def setup_ui(self):
        cen=QWidget(); self.setCentralWidget(cen); ml=QHBoxLayout(cen); sp=QSplitter(Qt.Horizontal)
        lp=QWidget(); ll=QVBoxLayout(lp); self.pool=SingerPool()
        self.pool.singer_selected.connect(self.add_to_grid); self.pool.singer_added.connect(self.add_to_grid)
        self.pool.singer_edit_requested.connect(self.edit_singer)
        self.pool.place_all_requested.connect(self.place_all_singers)
        ll.addWidget(self.pool); sp.addWidget(lp)
        rp=QWidget(); rl=QVBoxLayout(rp); gh=QHBoxLayout(); gh.addWidget(QLabel("<b>Aufstellung</b>"))
        gc=QHBoxLayout(); gc.addWidget(QLabel("Reihen:")); self.rs=QComboBox()
        for i in range(1,10): self.rs.addItem(str(i)); self.rs.setCurrentText("4")
        self.rs.setMinimumWidth(50)
        self.rs.currentTextChanged.connect(self.upd_grid); gc.addWidget(self.rs)
        gc.addWidget(QLabel("Spalten:")); self.cs=QComboBox()
        for i in range(1,31): self.cs.addItem(str(i)); self.cs.setCurrentText("5")
        self.cs.setMinimumWidth(50)
        self.cs.currentTextChanged.connect(self.upd_grid); gc.addWidget(self.cs)
        self.grid_count_label = QLabel("0 Sänger")
        self.grid_count_label.setStyleSheet("color: #666; font-size: 9pt; margin-left: 10px;")
        gc.addWidget(self.grid_count_label)
        gh.addLayout(gc); gh.addStretch(); rl.addLayout(gh)
        
        raster_layout = QHBoxLayout()
        raster_layout.addWidget(QLabel("Raster:"))
        sc=QScrollArea(); sc.setWidgetResizable(False); self.grid=FormationGrid(4,5)
        self.grid.singer_removed_from_grid.connect(self.on_singer_removed_from_grid); self.grid.singer_edit_requested.connect(self.edit_singer); self.grid.singer_affinity_requested.connect(self.set_singer_affinity)
        self.grid.undo_stack.canUndoChanged.connect(self.update_undo_redo)
        self.grid.undo_stack.canRedoChanged.connect(self.update_undo_redo)
        self.grid.selection_changed.connect(self.update_swap_action)
        sc.setWidget(self.grid); rl.addWidget(sc)
        self.std_radio = QRadioButton("Standard")
        self.std_radio.setChecked(not self.grid.staggered)
        self.std_radio.toggled.connect(self.on_raster_mode_changed)
        raster_layout.addWidget(self.std_radio)
        self.stag_radio = QRadioButton("Versetzt")
        self.stag_radio.setChecked(self.grid.staggered)
        self.stag_radio.toggled.connect(self.on_raster_mode_changed)
        raster_layout.addWidget(self.stag_radio)
        raster_layout.addStretch()
        rl.addLayout(raster_layout)
        sr=QHBoxLayout(); sr.addWidget(QLabel("Suche:")); self.search_input=QLineEdit(); self.search_input.setPlaceholderText("Sänger-Name..."); self.search_input.returnPressed.connect(self.do_quick_search); sr.addWidget(self.search_input); sb=QPushButton("🔍"); sb.setFixedWidth(30); sb.clicked.connect(self.do_quick_search); sr.addWidget(sb); rl.addLayout(sr)
        self.leg=QWidget(); self.llay=QHBoxLayout(self.leg); rl.addWidget(self.leg); self.upd_leg()
        sp.addWidget(rp); sp.setSizes([250,800]); ml.addWidget(sp); self.menu()
        self.pool.placed_singer_ids = set()
        self.pool.singers = self.singers
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)

    def menu(self):
        m=self.menuBar()
        f=m.addMenu("Datei")
        f.addAction(QAction("Neu", self, shortcut="Ctrl+N", triggered=self.new_f))
        f.addAction(QAction("Öffnen...", self, shortcut="Ctrl+O", triggered=self.open_f))
        f.addAction(QAction("Speichern", self, shortcut="Ctrl+S", triggered=self.save_f))
        f.addAction(QAction("Speichern unter...", self, shortcut="Ctrl+Shift+S", triggered=self.save_as_f))
        f.addSeparator()
        f.addAction(QAction("PDF Export...", self, shortcut="Ctrl+E", triggered=self.export_pdf))
        f.addSeparator()
        f.addAction(QAction("Beenden", self, shortcut="Ctrl+Q", triggered=self.close))
        e=m.addMenu("Bearbeiten")
        e.addAction(QAction("Sänger hinzufügen", self, shortcut="Ctrl+Shift+A", triggered=self.add_singer_via_menu))
        self.swap_action = QAction("Positionen tauschen", self, shortcut="Ctrl+T", triggered=self.swap_selected_singers)
        self.swap_action.setEnabled(False)
        e.addAction(self.swap_action)
        self.undo_action = QAction("Rückgängig", self, shortcut="Ctrl+Z", triggered=self.undo_last_action)
        self.redo_action = QAction("Wiederholen", self, shortcut="Ctrl+Y", triggered=self.redo_last_action)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        e.addAction(self.undo_action)
        e.addAction(self.redo_action)
        a=m.addMenu("Aufstellen")
        size_action = QAction("Aufstellung nach Größe", self)
        size_action.triggered.connect(self.grid.auto_arrange_by_height)
        a.addAction(size_action)
        men_action = QAction("Männer geteilt außen", self)
        men_action.triggered.connect(self.grid.auto_arrange_men_outer)
        a.addAction(men_action)
        satb_action = QAction("SATB", self)
        satb_action.triggered.connect(self.grid.auto_arrange_satb)
        a.addAction(satb_action)
        sbta_action = QAction("SBTA", self)
        sbta_action.triggered.connect(self.grid.auto_arrange_sbta)
        a.addAction(sbta_action)
        s1s2_action = QAction("S1 S2 B2 B1 T2 T1 A2 A1", self)
        s1s2_action.triggered.connect(self.grid.auto_arrange_s1s2b2b1t2t1a2a1)
        a.addAction(s1s2_action)
        s1s2a1a2_action = QAction("S1 S2 A1 A2 T1 T2 B1 B2", self)
        s1s2a1a2_action.triggered.connect(self.grid.auto_arrange_s1s2a1a2t1t2b1b2)
        a.addAction(s1s2a1a2_action)
        s1s2b1b2_action = QAction("S1 S2 B1 B2 T1 T2 A1 A2", self)
        s1s2b1b2_action.triggered.connect(self.grid.auto_arrange_s1s2b1b2t1t2a1a2)
        a.addAction(s1s2b1b2_action)
        a.addSeparator()
        affinity_action = QAction("Nähe (Singpartner)", self)
        affinity_action.triggered.connect(self.apply_all_affinity_proximity)
        a.addAction(affinity_action)
        a.addSeparator()
        reset_action = QAction("Aufstellung zurücksetzen", self)
        reset_action.triggered.connect(self.reset_formation)
        a.addAction(reset_action)
        a.addSeparator()
        opt_action = QAction("Optimiert aufstellen...", self)
        opt_action.triggered.connect(self.run_optimizer)
        a.addAction(opt_action)
        k=m.addMenu("Konfigurieren")
        cfg_action = QAction("Besetzung konfigurieren...", self)
        cfg_action.setEnabled(True)
        cfg_action.triggered.connect(self.show_cfg)
        k.addAction(cfg_action)
        
        v = m.addMenu("&Ansicht")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        
        self.actionLight = QAction("Light", self)
        self.actionLight.setCheckable(True)
        self.actionLight.triggered.connect(lambda: self._apply_theme("light"))
        v.addAction(self.actionLight)
        self.theme_group.addAction(self.actionLight)
        
        self.actionDark = QAction("Dark", self)
        self.actionDark.setCheckable(True)
        self.actionDark.triggered.connect(lambda: self._apply_theme("dark"))
        v.addAction(self.actionDark)
        self.theme_group.addAction(self.actionDark)
        
        self._menu_legenda()
        h=m.addMenu("&Hilfe")
        h.addAction(QAction("Über", self, triggered=self.show_about))

    def add_to_grid(self, singer):
        if not self.grid.place_singer(singer):
            QMessageBox.warning(self, "Fehler", "Keine freie Position im Raster verfügbar.")
        self.update_grid_count()

    def place_all_singers(self):
        placed = 0
        for singer in self.singers:
            if str(singer.singer_id) not in self.grid.get_placed_singer_ids():
                if self.grid.place_singer(singer):
                    placed += 1
                else:
                    break
        self.update_grid_count()
        if placed > 0:
            self.statusBar().showMessage(f"{placed} Sänger platziert", 3000)
        else:
            QMessageBox.information(self, "Info", "Alle Sänger sind bereits platziert oder das Raster ist voll.")

    def update_grid_count(self):
        placed = len(self.grid.get_placed_singer_ids())
        self.grid_count_label.setText(f"{placed} Sänger")
        self.pool.update_placed_singers(self.grid.get_placed_singer_ids())
    
    def _check_grid_capacity(self, new_rows, new_cols):
        """Check if new grid can hold all placed singers. Returns (is_ok, excess_count)."""
        grid_cells = new_rows * new_cols
        placed_count = len(self.grid.singers)
        excess = placed_count - grid_cells
        return (excess <= 0, excess)
    
    def _show_resize_warning(self, excess):
        """Show warning dialog when shrinking grid would lose singers."""
        placed = len(self.grid.singers)
        msg = (f"In das eingestellte Aufstellungsraster passen die {placed} Sänger "
               f"aus der Aufstellung nicht hinein.\n\n"
               f"{excess} überzählige Sänger müssen in den Sängerpool zurückgesetzt werden, "
               f"oder das Aufstellungsraster muss angepasst werden.")
        
        # Create custom message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Raster zu klein")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        # Create custom buttons
        btn_pool = QPushButton("In Pool zurücksetzen")
        btn_raster = QPushButton("Raster anpassen")
        msg_box.addButton(btn_pool, QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(btn_raster, QMessageBox.ButtonRole.ActionRole)
        msg_box.setDefaultButton(btn_raster)
        
        # Connect and exec
        msg_box.buttonClicked.connect(lambda: None)  # placeholder
        reply = msg_box.exec()
        
        # Check which button was clicked
        clicked = msg_box.clickedButton()
        if clicked == btn_pool:
            self._reset_excess_to_pool(excess)
            return True
        return False
    
    def _reset_excess_to_pool(self, count):
        """Reset excess singers (newest placed) back to pool."""
        singers_to_remove = self.grid.singers[-count:] if count > 0 else []
        for singer in singers_to_remove:
            singer.row = -1
            singer.col = -1
        # Rebuild placed list
        self.grid.singers = [s for s in self.grid.singers if s.row >= 0]
        self.grid.refresh_grid()
        self.pool.placed_singer_ids = self.grid.get_placed_singer_ids()
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)
        self.update_grid_count()
        self.is_modified = True

    def upd_grid(self):
        r = int(self.rs.currentText())
        c = int(self.cs.currentText())
        
        # Check capacity before resizing
        is_ok, excess = self._check_grid_capacity(r, c)
        if not is_ok:
            # Show warning - user chooses to cancel or reset excess
            user_proceeds = self._show_resize_warning(excess)
            if not user_proceeds:
                # Revert ComboBox to current grid values
                self.rs.blockSignals(True)
                self.rs.setCurrentText(str(self.grid.rows))
                self.rs.blockSignals(False)
                self.cs.blockSignals(True)
                self.cs.setCurrentText(str(self.grid.cols))
                self.cs.blockSignals(False)
                return
        
        self.grid.set_dimensions(r, c)

    def on_raster_mode_changed(self):
        self.grid.set_staggered(self.stag_radio.isChecked())

    def undo_last_action(self):
        self.grid.undo_stack.undo()

    def redo_last_action(self):
        self.grid.undo_stack.redo()

    def update_undo_redo(self):
        self.undo_action.setEnabled(self.grid.undo_stack.canUndo())
        self.redo_action.setEnabled(self.grid.undo_stack.canRedo())

    def swap_selected_singers(self):
        self.grid.swap_selected_singers()
        self.update_swap_action()

    def update_swap_action(self):
        self.swap_action.setEnabled(len(self.grid.selected_ids) == 2)

    def reset_formation(self):
        """Reset all placed singers back to pool."""
        r = QMessageBox.question(self, "Zurücksetzen", "Aufstellung zurücksetzen?", 
                           QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        for s in self.singers:
            s.row = -1
            s.col = -1
        self.grid.refresh_grid()
        self.is_modified = True
        self.update_grid_count()

    def apply_all_affinity_proximity(self):
        processed = set()
        moved = 0
        for singer in self.singers:
            if singer.row < 0 or not singer.affinity:
                continue
            if singer.singer_id in processed:
                continue
            partner = next((s for s in self.singers if s.singer_id == singer.affinity), None)
            if not partner or partner.row < 0:
                continue
            if singer.row != partner.row:
                continue
            if abs(singer.col - partner.col) == 1:
                processed.add(singer.singer_id)
                processed.add(partner.singer_id)
                continue
            if self.grid.apply_affinity_proximity(singer):
                moved += 1
            processed.add(singer.singer_id)
            processed.add(partner.singer_id)
        if moved > 0:
            self.statusBar().showMessage(f"{moved} Singpartner nebeneinander platziert", 3000)
            self.is_modified = True
        else:
            QMessageBox.information(self, "Nähe", "Alle Singpartner sind bereits nebeneinander oder nicht in der gleichen Reihe.")

    def new_f(self):
        if self.is_modified:
            r = QMessageBox.question(self, "Ungespeichert", "Änderungen speichern?", QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self.save_f()
            elif r == QMessageBox.StandardButton.Cancel:
                return
        self.grid.singers = []
        self.grid.refresh_grid()
        self.singers = []
        self.file = None
        self.is_modified = False
        self.update_grid_count()

    def open_f(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "JSON (*.json);;Alle (*)")
        if not fp:
            return
        self._open_file(fp)

    def _open_file(self, fp):
        data = self.storage.load_formation(fp)
        if not data:
            return
        self.singers = data.get("singers", [])
        for s in self.singers:
            if not hasattr(s, 'affinity'):
                s.affinity = ""
        self.grid.singers = [s for s in self.singers if s.row >= 0]
        self.grid.refresh_grid()
        self.pool.singers = self.singers
        self.pool.placed_singer_ids = self.grid.get_placed_singer_ids()
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)
        self.file = fp
        self.is_modified = False
        self.update_grid_count()
        self._loaded_metadata = data.get("metadata", {})

    def save_f(self):
        grid_cells = self.grid.rows * self.grid.cols
        placed = len(self.grid.singers)
        if placed > grid_cells:
            excess = placed - grid_cells
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Zu viele Sänger")
            msg_box.setText(f"Die Aufstellung hat {placed} Sänger im Raster, aber nur {grid_cells} Plätze.")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            
            btn_resize = QPushButton("Raster vergrößern")
            btn_pool = QPushButton("In Pool zurücksetzen")
            msg_box.addButton(btn_resize, QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(btn_pool, QMessageBox.ButtonRole.ActionRole)
            
            reply = msg_box.exec()
            if reply == btn_pool:
                self._reset_excess_to_pool(excess)
                return self._save_file(self.file, metadata=self._loaded_metadata)
            return False
        
        if not self.file:
            return self.save_as_f()
        
        return self._save_file(self.file, metadata=self._loaded_metadata)

    def save_as_f(self):
        from config import get_data_dir
        data_dir = get_data_dir()
        auto_name = self.generate_filename(
            self._loaded_metadata.get("event_date", ""),
            self._loaded_metadata.get("event", "")
        )
        fp, _ = QFileDialog.getSaveFileName(self, "Speichern", os.path.join(data_dir, auto_name), "JSON (*.json)")
        if not fp:
            return False
        if not fp.endswith(".json"):
            fp += ".json"
        
        grid_cells = self.grid.rows * self.grid.cols
        placed = len(self.grid.singers)
        if placed > grid_cells:
            excess = placed - grid_cells
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Zu viele Sänger")
            msg_box.setText(f"Die Aufstellung hat {placed} Sänger im Raster, aber nur {grid_cells} Plätze.")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            
            btn_resize = QPushButton("Raster vergrößern")
            btn_pool = QPushButton("In Pool zurücksetzen")
            msg_box.addButton(btn_resize, QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(btn_pool, QMessageBox.ButtonRole.ActionRole)
            
            reply = msg_box.exec()
            if reply == btn_pool:
                self._reset_excess_to_pool(excess)
            else:
                return False
        
        return self._save_file(fp, metadata=self._loaded_metadata)

    def _save_file(self, fp, metadata: dict = None):
        placed = self.grid.get_placed_singers()
        singers = self.singers
        rows = self.grid.rows
        cols = self.grid.cols
        staggered = self.grid.staggered
        
        if self.storage.save_formation(singers, rows, cols, fp, placed, staggered, metadata=metadata):
            self.file = fp
            self.is_modified = False
            import time
            self.last_manual_save_mtime = time.time()
            return True
        return False
    
    def generate_filename(self, event_date: str, event_name: str = None) -> str:
        """Generate auto filename: choraufstellung-DATE-version-DATE.json"""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        name_part = event_name.replace(" ", "-") if event_name else "event"
        date_part = event_date[:10] if event_date else today
        return f"choraufstellung-{date_part}-version-{today}.json"

    def _autosave_check(self):
        if not self.is_modified:
            return
        if not self.file:
            return
        placed = self.grid.get_placed_singer_ids()
        data = {
            "version": "1.0",
            "rows": self.grid.rows,
            "cols": self.grid.cols,
            "staggered": self.grid.staggered,
            "singers": [
                {"name": s.name, "voice_group": s.voice_group.value if hasattr(s.voice_group, 'value') else str(s.voice_group),
                 "height": s.height, "singer_id": s.singer_id, "row": s.row, "col": s.col, "affinity": s.affinity}
                for s in self.singers
            ],
            "placed": list(placed)
        }
        self.storage.save_autosave(data)

    def _check_recovery(self):
        """Check for autosave and offer recovery if newer than last manual save."""
        latest = self.storage.get_latest_autosave_path()
        if not latest:
            return
        if self.storage.get_latest_autosave_mtime() <= self.last_manual_save_mtime:
            return
        
        r = QMessageBox.question(self, "Wiederherstellen", 
                           "Es wurde eine automatisch gespeicherte Aufstellung gefunden, die neuer ist als Ihre letzte manuelle Speicherung.\n\n"
                           "Möchten Sie die automatisch gespeicherte Version wiederherstellen?\n"
                           "(Ihre manuell gespeicherte Version bleibt erhalten.)",
                           QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        
        data = self.storage.load_formation(latest)
        if data:
            self._load_formation_data(data)
            self.file = latest
            self.is_modified = True

    def export_pdf(self):
        from pdf_export_dialog import PDFExportDialog
        from config import get_data_dir
        
        event_date = os.environ.get("CHOR_EVENT_DATE", "") or self.event_date or ""
        event_name = os.environ.get("CHOR_EVENT_NAME", "") or self.event_name or ""
        project_name = os.environ.get("CHOR_PROJECT", "") or self.project_name or ""
        
        if event_date:
            event_date = event_date[:10]
        
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        date_part = event_date if event_date else today
        default_filename = f"choraufstellung-{date_part}-version-{today}.pdf"
        
        event_info = ""
        if event_name:
            event_info = event_name
        if event_date:
            event_info += f" ({event_date})"
        if project_name:
            event_info = f"{project_name}: {event_info}" if event_info else project_name
        
        data_dir = get_data_dir()
        workdir = os.path.join(os.path.dirname(data_dir), "workdir")
        os.makedirs(workdir, exist_ok=True)
        
        dlg = PDFExportDialog(self, default_filename=default_filename, event_info=event_info)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        
        settings = dlg.get_settings()
        
        fp = os.path.join(workdir, settings["filename"])
        if not fp.endswith(".pdf"):
            fp += ".pdf"
        
        title = "Choraufstellung"
        subtitle = ""
        if event_name:
            subtitle = event_name
        if event_date:
            subtitle += f" - {event_date}"
        if project_name:
            subtitle = f"{project_name}: {subtitle}" if subtitle else project_name
        
        success = self.pdf.export_formation(
            self.singers,
            self.grid.rows,
            self.grid.cols,
            fp,
            title=title,
            subtitle=subtitle,
            staggered=self.grid.staggered,
            orientation=settings["orientation"],
            color_mode=settings["color_mode"],
            text_rotation=settings["text_rotation"]
        )
        
        if success:
            QMessageBox.information(self, "PDF Export", f"PDF exportiert nach:\n{fp}")
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(fp)))
        else:
            QMessageBox.warning(self, "Fehler", "PDF-Export fehlgeschlagen.")

    def run_optimizer(self):
        d = OptimizerDialog(self)
        if d.exec() == QDialog.DialogCode.Accepted:
            rules = d.get_selected_rules()
            if rules:
                primary = d.get_primary_rule()
                refinement = d.get_refinement_rules()
                self.grid.optimize(primary, refinement)

    def show_cfg(self):
        d = VoicingConfigDialog(self)
        if d.exec() == QDialog.DialogCode.Accepted:
            pass

    def _apply_theme(self, theme):
        if theme == "dark":
            self.setStyleSheet("""
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
            """)
        else:
            self.setStyleSheet("""
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
            """)
        
        # Clear color cache and refresh grid to apply new theme colors
        clear_color_cache()
        self.grid.refresh_grid()
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)

    def add_singer_via_menu(self):
        s = self.pool.add_dialog()
        if s:
            self.singers.append(s)
            self.is_modified = True

    def edit_singer(self, singer):
        new_singer = self.pool.add_dialog(singer)
        if new_singer:
            idx = next((i for i, s in enumerate(self.singers) if s.singer_id == singer.singer_id), -1)
            if idx >= 0:
                self.singers[idx] = new_singer
            self.is_modified = True

    def set_singer_affinity(self, singer):
        self.pool.set_affinity(singer)

    def on_singer_removed_from_grid(self, singer):
        self.pool.update_singers(self.singers, self.grid.get_placed_singer_ids())
        self.is_modified = True
        self.update_grid_count()

    def do_quick_search(self):
        name = self.search_input.text().strip().lower()
        if not name:
            self.grid.clear_search_highlight()
            return
        for s in self.singers:
            if name in s.name.lower():
                self.grid.highlight_singer(s, self)
                return

    def upd_leg(self):
        while self.llay.count():
            w = self.llay.takeAt(0).widget()
            if w:
                w.deleteLater()
        for vg in self.cfg:
            if isinstance(vg, dict):
                vg_id = vg.get("id", "")
                vg_color = vg.get("color", "#cccccc")
            else:
                vg_id = vg
                vg_color = get_voice_group_color(vg)
            l = QLabel(vg_id)
            l.setStyleSheet(f"background: {vg_color}; padding: 4px; color: #000;")
            self.llay.addWidget(l)
        self.llay.addStretch()

    def _menu_legenda(self):
        for m in self.menuBar().findChildren(QMenu):
            if m.title() == "&Hilfe":
                continue
            for a in m.actions():
                if a.text() == "Über":
                    continue

    def show_about(self):
        QMessageBox.about(self, "Über Choraufstellung", "Choraufstellung 1.0\n\nVerwaltung von Choraufstellungen.")

    def closeEvent(self, e):
        if self.is_modified:
            r = QMessageBox.question(self, "Ungespeichert", "Änderungen speichern?", QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self.save_f()
                e.accept()
            elif r == QMessageBox.StandardButton.Discard:
                e.accept()
            else:
                e.ignore()
        else:
            e.accept()

    def _load_from_chormanager(self):
        """Load singers from ChorManager DB or temp JSON file."""
        import os
        import json
        
        # Check for temp JSON file first (preferred method)
        event_data_file = os.environ.get("CHOR_EVENT_DATA", "")
        
        if event_data_file and os.path.exists(event_data_file):
            try:
                with open(event_data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                event_info = data.get("event", {})
                if event_info:
                    self._loaded_metadata = {
                        "project": data.get("project", ""),
                        "event": event_info.get("name", ""),
                        "event_date": event_info.get("date", "")[:10] if event_info.get("date") else "",
                        "event_type": event_info.get("event_type", "")
                    }
                
                singers_data = data.get("singers", [])
                if singers_data:
                    self.singers = []
                    for s in singers_data:
                        name = s.get("short_name") or s.get("name", "")
                        vg_str = s.get("voice_group", "Sopran")
                        # Convert string to VoiceGroup enum
                        vg = next((v for v in VoiceGroup if hasattr(v,'value') and v.value == vg_str), None)
                        if not vg:
                            vg = VoiceGroup.SOPRAN_1  # Default
                        singer = Singer(
                            name,
                            vg,
                            s.get("height", 0),
                            s.get("singer_id", "")
                        )
                        singer.affinity = s.get("affinity", "")
                        singer.affinity_uuid = s.get("affinity_uuid", "")
                        self.singers.append(singer)
                    
                    self.pool.singers = self.singers
                    self.pool.update_singers(self.singers, set())
                    self.is_modified = False
                    return
            except Exception as e:
                print(f"Error reading event data file: {e}")
        
        # Fallback: Load from DB
        import sqlite3
        
        db_path = os.environ.get("CHOR_DB_PATH", os.path.expanduser("~/.local/share/chormanager/chor.db"))
        event_id = self.event_id or os.environ.get("CHOR_EVENT_ID", "")
        event_date = os.environ.get("CHOR_EVENT_DATE", "")
        
        if not db_path or not os.path.exists(db_path):
            return
        
        if event_date:
            event_date = event_date[:10]
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if event_id:
                cursor.execute("""
                    SELECT s.id, s.full_name, s.short_name, s.voice_group, s.affinity_uuid, s.height
                    FROM singers s
                    JOIN availability a ON s.id = a.singer_id
                    WHERE a.event_id = ? AND a.status IN ('yes', 'conditional')
                    ORDER BY s.full_name
                """, (event_id,))
            else:
                cursor.execute("""
                    SELECT s.id, s.full_name, s.short_name, s.voice_group, s.affinity_uuid, s.height
                    FROM singers s
                    ORDER BY s.full_name
                """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return
            
            vg_to_enum = {}
            for vg in VoiceGroup:
                vg_to_enum[vg.value if hasattr(vg, 'value') else str(vg)] = vg
            
            def find_voice_group(vg_str):
                vg_str = vg_str or "Sopran"
                if vg_str in vg_to_enum:
                    return vg_to_enum[vg_str]
                for vg_name, vg in vg_to_enum.items():
                    if vg_name.startswith(vg_str):
                        return vg
                return VoiceGroup.SOPRAN_1
            
            for row in rows:
                singer_id = row["id"]
                vg_str = row["voice_group"] or "Sopran"
                vg = find_voice_group(vg_str)
                
                name = row["short_name"] or row["full_name"]
                height = row["height"] or 0
                affinity = row["affinity_uuid"] or ""
                
                s = Singer(name, vg, height, singer_id)
                s.affinity = affinity
                self.singers.append(s)
            
            self.pool.singers = self.singers
            self.pool.update_singers(self.singers, set())
            
            self.is_modified = False
            
        except Exception as e:
            print(f"Error loading from chormanager: {e}")
    
    def _load_formation_data(self, data: dict):
        """Load formation data from dict (used when opening saved file)."""
        self.singers = data.get("singers", [])
        for s in self.singers:
            if not hasattr(s, 'affinity'):
                s.affinity = ""
        self.grid.singers = [s for s in self.singers if s.row >= 0]
        self.grid.rows = data.get("rows", 3)
        self.grid.cols = data.get("cols", 4)
        self.grid.staggered = data.get("staggered", False)
        self.grid.refresh_grid()
        self.pool.singers = self.singers
        self.pool.placed_singer_ids = self.grid.get_placed_singer_ids()
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)
        self.is_modified = False
        self.update_grid_count()
        
        # Sync ComboBoxes with loaded grid dimensions
        if hasattr(self, 'rs'):
            self.rs.blockSignals(True)
            self.rs.setCurrentText(str(self.grid.rows))
            self.rs.blockSignals(False)
        if hasattr(self, 'cs'):
            self.cs.blockSignals(True)
            self.cs.setCurrentText(str(self.grid.cols))
            self.cs.blockSignals(False)


def main():
    import os
    event_date = os.environ.get("CHOR_EVENT_DATE", "")
    event_id = os.environ.get("CHOR_EVENT_ID", "")
    event_name = os.environ.get("CHOR_EVENT_NAME", "")
    project_name = os.environ.get("CHOR_PROJECT", "")
    event_type = os.environ.get("CHOR_EVENT_TYPE", "")
    db_path = os.environ.get("CHOR_DB_PATH", "")
    chor_file = os.environ.get("CHOR_FILE", "")
    chormanager_mode = bool(event_date or event_id or db_path or chor_file)
    
    app = QApplication(sys.argv); app.setStyle("Fusion")
    w = MainWindow(chormanager_mode=chormanager_mode, event_id=event_id, event_date=event_date, 
                  event_name=event_name, project_name=project_name, event_type=event_type)
    
    if chor_file and os.path.exists(chor_file):
        w.file = chor_file
        w.storage.filepath = chor_file
        data = w.storage.load_formation(chor_file)
        if data:
            w._load_formation_data(data)
    
    w.show()
    sys.exit(app.exec())