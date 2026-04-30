# UI: Grid widget components - SingerTile and FormationGrid
# Extracted from main.py for better separation of concerns
try:
    from PyQt6.QtWidgets import (
        QFrame, QLabel, QPushButton, QVBoxLayout, QMenu, QMessageBox,
        QGraphicsDropShadowEffect, QRubberBand, QWidget
    )
    from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QRect, QTimer
    from PyQt6.QtGui import QDrag, QColor, QFont
except ImportError:
    from PyQt5.QtWidgets import (
        QFrame, QLabel, QPushButton, QVBoxLayout, QMenu, QMessageBox,
        QGraphicsDropShadowEffect, QRubberBand, QWidget
    )
    from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QRect, QTimer
    from PyQt5.QtGui import QDrag, QColor, QFont

from qt_compat import exec_qt
from singer_model import voice_group_color


def get_text_color() -> str:
    """Get current theme text color."""
    try:
        from config import load_settings
        theme = load_settings().get("theme", "light")
        color = "#F0F0F0" if theme == "dark" else "#1A1A1A"
        print(f"DEBUG get_text_color: theme={theme}, color={color}")
        return color
    except Exception as e:
        print(f"get_text_color error: {e}")
        return "#1A1A1A"


def get_secondary_text_color() -> str:
    """Get current theme secondary text color."""
    try:
        from config import load_settings
        theme = load_settings().get("theme", "light")
        return "#CCCCCC" if theme == "dark" else "#555555"
    except Exception:
        return "#555555"


class SingerTile(QFrame):
    """Tile widget displaying a single singer in the formation grid."""
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
        self._setup_ui()
        self._setup_shadow()
    
    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(0)
        
        txt_color = get_text_color()
        sec_color = get_secondary_text_color()
        
        name_with_affinity = f"{self.singer.name} 👥" if self.singer.affinity else self.singer.name
        n = QLabel(f"<b>{name_with_affinity}</b>")
        n.setAlignment(Qt.AlignCenter)
        n.setWordWrap(True)
        n.setStyleSheet(f"background: transparent; color: {txt_color}; font-size: 9pt;")
        lay.addWidget(n)
        
        vg = self.singer.voice_group.value if hasattr(self.singer.voice_group, 'value') else str(self.singer.voice_group)
        v = QLabel(vg)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet(f"background: transparent; color: {sec_color}; font-size: 8pt;")
        lay.addWidget(v)
        
        if self.singer.height > 0:
            h = QLabel(f"{self.singer.height} cm")
            h.setAlignment(Qt.AlignCenter)
            h.setStyleSheet(f"background: transparent; color: {sec_color}; font-size: 7pt;")
            lay.addWidget(h)
        
        btn = QPushButton("×")
        btn.setFixedSize(14, 14)
        btn.setStyleSheet("font-size: 10pt; padding: 0; background: transparent; border: none;")
        btn.clicked.connect(self.on_remove)
        lay.addWidget(btn, alignment=Qt.AlignRight | Qt.AlignTop)
    
    def _setup_shadow(self):
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
        """Visuelle Hervorhebung – robust gegen GraphicsDropShadowEffect."""
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
            from PyQt6.QtWidgets import QApplication
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
            from PyQt6.QtWidgets import QApplication
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


class FormationGrid(QWidget):
    """Grid widget for displaying and arranging singers."""
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
        
        # Gruppen-Drag
        self.rubber_band = None
        self.drag_start_pos = None
        self.is_group_dragging = False
        self.undo_stack = None  # Set by MainWindow
        
        self.setAcceptDrops(True)
        self.setMinimumSize(
            self.cols * self.CELL_WIDTH + self.MARGIN_LEFT + 50,
            self.rows * self.CELL_HEIGHT + self.MARGIN_TOP + 50
        )
    
    def set_undo_stack(self, stack):
        """Set the undo stack for this grid."""
        self.undo_stack = stack
    
    def set_dimensions(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.setMinimumSize(
            cols * self.CELL_WIDTH + self.MARGIN_LEFT + 50,
            rows * self.CELL_HEIGHT + self.MARGIN_TOP + 50
        )
        self.refresh_grid()
    
    def set_staggered(self, v):
        self.staggered = v
        self.refresh_grid()
    
    def update_selection_visuals(self):
        """Aktualisiert die visuelle Markierung aller Tiles."""
        for tile in list(self.tiles.values()):
            if isinstance(tile, SingerTile):
                tile.set_selected(tile.singer.singer_id in self.selected_ids)
    
    def highlight_singer(self, singer, parent_window):
        """Highlightet einen Sänger im Grid mit 5-mal Pulsieren."""
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
        
        if is_odd:
            tile.setStyleSheet("""
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
        """Entfernt alle Such-Hervorhebungen."""
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
            from PyQt6.QtWidgets import QApplication
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
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
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
        # Don't add if already in singers list
        if singer not in self.singers:
            self.singers.append(singer)
        singer.row = r
        singer.col = c
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
        # Only unplace - don't remove from singers list!
        # The pool will filter based on placed_ids
        singer.row = -1
        singer.col = -1
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
    
    # --- Auto-arrange methods ---
    
    def auto_arrange_by_height(self):
        if not self.singers:
            return
        sorted_singers = sorted(
            self.singers,
            key=lambda s: (-s.height, (s.voice_group.value if hasattr(s.voice_group, 'value') else str(s.voice_group)), s.name)
        )
        placed_ids = set()
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if idx < len(sorted_singers):
                    s = sorted_singers[idx]
                    s.row = r
                    s.col = c
                    placed_ids.add(s.singer_id)
                    idx += 1
                else:
                    break
        for s in self.singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1
        self.refresh_grid()
    
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
        placed_ids = set()
        idx = 0
        for s in basses[:len(basses)//2]:
            s.row = idx % self.rows
            s.col = 0
            placed_ids.add(s.singer_id)
            idx += 1
        for s in tenors[:len(tenors)//2]:
            s.row = idx % self.rows
            s.col = 1
            placed_ids.add(s.singer_id)
            idx += 1
        for s in basses[len(basses)//2:]:
            s.row = idx % self.rows
            s.col = self.cols - 1
            placed_ids.add(s.singer_id)
            idx += 1
        for s in tenors[len(tenors)//2:]:
            s.row = idx % self.rows
            s.col = self.cols - 2
            placed_ids.add(s.singer_id)
            idx += 1
        mid_col_start = 2
        mid_col_end = self.cols - 3
        for s in others:
            s.row = idx % self.rows
            s.col = mid_col_start + (idx % (mid_col_end - mid_col_start + 1))
            placed_ids.add(s.singer_id)
            idx += 1
        for s in self.singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1
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
    
    def optimize(self, primary_rule=None, refinement_rules=None):
        """Run optimizer with given rules."""
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
    
    # --- Drag & Drop handlers ---
    
    def dragEnterEvent(self, e):
        if e.mimeData().hasText() and e.mimeData().text().startswith("singer:"):
            e.acceptProposedAction()
    
    def dragMoveEvent(self, e):
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

        pos = e.pos()
        row = (pos.y() - self.MARGIN_TOP) // self.CELL_HEIGHT
        col_offset = self.OFFSET if (self.staggered and row % 2 == 1) else 0
        col = (pos.x() - self.MARGIN_LEFT - col_offset) // self.CELL_WIDTH

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

            can_move = all(
                0 <= (next((s for s in self.singers if s.singer_id == sid), None).row or 0) + delta_row < self.rows and
                0 <= (next((s for s in self.singers if s.singer_id == sid), None).col or 0) + delta_col < self.cols
                for sid in group_ids
            )
            if not can_move:
                QMessageBox.warning(self, "Rand erreicht", "Die Gruppe würde teilweise außerhalb des Rasters landen.")
                self.refresh_grid()
                return

            self._move_group(group_ids, delta_col, delta_row)
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
                self._move_singer(dragged_singer, old_row, old_col, row, col)

        self.refresh_grid()
    
    def _move_group(self, group_ids, delta_col, delta_row):
        """Verschiebt eine Gruppe von Sängern."""
        from core.commands import MoveGroupCommand
        command = MoveGroupCommand(group_ids, delta_col, delta_row, self)
        if self.undo_stack:
            self.undo_stack.push(command)
        else:
            command.redo()
    
    def _move_singer(self, singer, old_row, old_col, new_row, new_col):
        """Verschiebt einen einzelnen Sänger."""
        from core.commands import MoveSingerCommand
        command = MoveSingerCommand(singer, old_row, old_col, new_row, new_col, self)
        if self.undo_stack:
            self.undo_stack.push(command)
        else:
            command.redo()
    
    def swap_selected_singers(self):
        """Positionen von genau zwei ausgewählten Sängern tauschen."""
        if len(self.selected_ids) != 2:
            QMessageBox.warning(self, "Fehler", "Bitte genau zwei Sänger auswählen (Ctrl+Klick).")
            return

        sid1, sid2 = list(self.selected_ids)
        singer1 = next((s for s in self.singers if s.singer_id == sid1), None)
        singer2 = next((s for s in self.singers if s.singer_id == sid2), None)

        if not singer1 or not singer2:
            return

        from core.commands import SwapSingersCommand
        command = SwapSingersCommand(singer1, singer2, self)
        if self.undo_stack:
            self.undo_stack.push(command)
        else:
            command.redo()

        self.selected_ids.clear()
        self.refresh_grid()
