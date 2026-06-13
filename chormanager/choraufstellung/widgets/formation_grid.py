"""ChorAufstellung :class:`FormationGrid` widget.

M-2 Schritt 6: Extracted from ``choraufstellung/main.py`` (formerly
Z. 110-848, ~739 LOC) into this dedicated module so the main file
can shrink toward the 750-LOC soft cap from AGENTS.md.

The grid manages the 2D layout of :class:`SingerTile` widgets inside
the choraufstellung editor.  It exposes a :class:`QtUndoStack`
(Schritt 3) so :class:`core.commands.UndoCommand` subclasses can
push/undo/redo placement changes.  It also emits four Qt signals
the surrounding :class:`MainWindow` listens to:

  * ``singer_removed_from_grid(object)`` -- a tile was removed
  * ``singer_edit_requested(object)`` -- the user wants to edit
  * ``singer_affinity_requested(object)`` -- the user wants to set
    the affinity (proximity) of a singer
  * ``selection_changed()`` -- the current selection changed; used
    by the MainWindow to enable / disable the "Positionen tauschen"
    menu action.  Note that this signal is also emitted by
    :class:`SingerTile` (duck-typed) when the user clicks a tile --
    see Schritt 5 commit 12f3c92.

Backward compatibility
----------------------
``choraufstellung.main`` re-exports ``FormationGrid`` so external
callers that did ``from choraufstellung.main import FormationGrid``
keep working unchanged.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from qt_compat import (
    QFrame,
    QLabel,
    QMenu,
    QMessageBox,
    QPoint,
    QRect,
    QRubberBand,
    QTimer,
    QWidget,
    Qt,
    pyqtSignal,
)

from undo_bridge import QtUndoStack
from widgets.singer_tile import SingerTile

# Pure-Python undo commands (Schritt 3): swap/move/group use the
# (singer_id, get_singer_fn, refresh_fn) API defined in core.commands.
from core.commands import (
    MoveGroupCommand,
    MoveSingerCommand,
    SwapSingersCommand,
)


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
        # M-2 Schritt 3: ``QUndoStack`` replaced by ``QtUndoStack``
        # (defined in ``undo_bridge.py``).  ``QtUndoStack`` exposes
        # the same ``canUndo()`` / ``canRedo()`` / ``undo()`` /
        # ``redo()`` / ``push()`` API and emits the same
        # ``canUndoChanged`` / ``canRedoChanged`` signals the rest of
        # this file already uses.
        self.undo_stack = QtUndoStack(self)
        # Closure helpers the pure-Python ``core.commands`` command
        # classes need: a singer-id → Singer lookup and a
        # post-mutation refresh.
        self._undo_get_singer = (
            lambda sid: next(
                (s for s in self.singers if s.singer_id == sid), None
            )
        )
        self._undo_refresh = self.refresh_grid
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

        # M-2 Schritt 3: ``SwapSingersCommand`` is now the pure-Python
        # ``core.commands.SwapSingersCommand``, which takes
        # ``(singer1_id, singer2_id, get_singer_fn, refresh_fn)``
        # instead of the old ``(singer1, singer2, grid)`` triple.
        command = SwapSingersCommand(
            singer1.singer_id, singer2.singer_id,
            self._undo_get_singer, self._undo_refresh,
        )
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

            # M-2 Schritt 3: ``MoveGroupCommand`` is now the
            # pure-Python ``core.commands.MoveGroupCommand`` with the
            # ``(singer_ids, dx, dy, get_singer_fn, get_all_fn,
            # refresh_fn)`` signature.  ``get_all`` is required by
            # that class even though the move logic only uses
            # ``get_singer``.
            command = MoveGroupCommand(
                group_ids, delta_col, delta_row,
                self._undo_get_singer,
                lambda: list(self.singers),
                self._undo_refresh,
            )
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
                # M-2 Schritt 3: ``MoveSingerCommand`` is now the
                # pure-Python ``core.commands.MoveSingerCommand``,
                # which takes ``(singer_id, old_row, old_col,
                # new_row, new_col, get_singer_fn, refresh_fn)``
                # instead of ``(singer, old_row, old_col, new_row,
                # new_col, grid)``.
                command = MoveSingerCommand(
                    dragged_singer.singer_id,
                    old_row, old_col,
                    dragged_singer.row, dragged_singer.col,
                    self._undo_get_singer, self._undo_refresh,
                )
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
