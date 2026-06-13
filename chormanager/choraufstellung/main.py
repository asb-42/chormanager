import sys
import os
import json

# PyQt5/PyQt6 cross-compatibility, enum aliases (QFrame.Panel, Qt.AlignCenter)
# and fallback classes (FallbackSinger, FallbackOptimizerDialog, FallbackGridEngine)
# all live in ``qt_compat``. ``main.py`` no longer needs a try/except block
# for any of those concerns.
from qt_compat import (
    # Cross-compat helper
    exec_qt,
    QT_VERSION,
    # Re-exported Qt classes used below
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QMenuBar, QMenu,
    QFileDialog, QDialog, QFormLayout, QLineEdit, QComboBox, QListWidget,
    QListWidgetItem, QScrollArea, QMessageBox, QFrame, QCheckBox, QSplitter,
    QGraphicsDropShadowEffect, QRubberBand,
    QCompleter, QTableWidget, QTableWidgetItem, QHeaderView,
    QRadioButton,
    Qt, QMimeData, pyqtSignal, QRect, QTimer, QPoint,
    QPrinter, QPrintDialog,
    QDrag, QColor, QPalette, QFont, QAction, QActionGroup,
    # NOTE (M-2 Schritt 3): QUndoStack / QUndoCommand removed from
    # the qt_compat re-export.  Undo/redo now lives in the
    # pure-Python ``core.commands`` module, with a thin Qt-signal
    # bridge in ``undo_bridge.QtUndoStack`` imported below.
)

# M-2 Schritt 3: undo/redo logic now lives in the Qt-agnostic
# ``core.commands`` module.  ``undo_bridge.QtUndoStack`` is a thin
# QObject wrapper that exposes the same ``canUndo()`` / ``canRedo()``
# / ``canUndoChanged`` / ``canRedoChanged`` API the rest of main.py
# already uses.
#
# These imports are sibling-module imports (no leading
# ``chormanager.``) on purpose: the choraufstellung subshell launches
# this file as ``__main__`` with only the choraufstellung directory
# on ``sys.path``.  In that mode an absolute
# ``from chormanager.choraufstellung.undo_bridge import …`` raises
# ``ModuleNotFoundError: No module named 'chormanager'`` — the same
# trap M-2 Schritt 2 hit for ``widgets.draggable_list``.
from undo_bridge import QtUndoStack
from core.commands import (
    MoveSingerCommand,
    SwapSingersCommand,
    MoveGroupCommand,
)

# Domain modules (choraufstellung-specific). These were previously inside
# a try/except block, but every module listed here is a hard dependency
# of the choraufstellung subapp, so a plain import is fine and clearer.
from config import (
    load_settings, save_settings, load_voice_groups_config,
    get_valid_voice_groups, get_voice_group_color, get_data_dir,
    clear_color_cache,
)
from singer_model import Singer, VoiceGroup, voice_group_color
from storage import FormationStorage
from pdf_export import PDFExporter
from core.optimizer import FormationOptimizer
from core.grid_engine import GridEngine, GridConfig
from ui.optimizer_dialog import OptimizerDialog

# M-2 Schritt 2: Draggable widgets were extracted from this file (formerly
# Z. 42-78) into ``widgets/draggable_list.py``. The two local names are
# re-exported here for backward compatibility with any external caller
# that did ``from chormanager.choraufstellung.main import DraggableListWidget``.
#
# The choraufstellung subshell is launched as a standalone script
# (``python __main__.py`` from inside the choraufstellung directory,
# see ``choraufstellung_launcher.py``) — in that mode the top-level
# ``chormanager`` package is NOT on ``sys.path``, so an absolute
# ``from chormanager.choraufstellung.widgets...`` import fails with
# ``ModuleNotFoundError: No module named 'chormanager'``.  We must
# therefore use the relative import.  In test/package-import mode
# (``chormanager.choraufstellung.main``) the relative import still
# works because the package's parent directory is on ``sys.path``.
from widgets.draggable_list import (
    DraggableListWidget,
    DraggableTableWidget,
)

# M-2 Schritt 5: ``SingerTile`` was extracted from this file (formerly
# Z. 84-208) into ``widgets/singer_tile.py``.  The class name is
# re-exported from that module below so any external caller that did
# ``from choraufstellung.main import SingerTile`` keeps working.
#
# Note: ``SingerTile`` references ``FormationGrid`` via a runtime
# ``isinstance`` check (forward-declared via TYPE_CHECKING in the
# new module).  The class therefore does NOT need to be imported
# into this file at all — but we keep the re-export so old call
# sites keep working.
from widgets.singer_tile import SingerTile  # noqa: F401

# M-2 Schritt 3: The local ``MoveSingerCommand`` / ``SwapSingersCommand``
# / ``MoveGroupCommand`` classes that used to live here were deleted.
# The active implementations now live in the pure-Python
# ``core.commands`` module and are imported at the top of this file
# (see the ``from core.commands import …`` block).
#
# The three class names are re-exported from this module so any
# external caller that did
# ``from chormanager.choraufstellung.main import MoveSingerCommand``
# keeps working — they just get the new core.commands class now.
#
# (No code is needed here; the import at the top of the file
# already binds the names into this module's namespace.)

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

# M-2 Schritt 5: SingerPool was extracted from this file (formerly
# Z. ~857-1092) into widgets/singer_pool.py. The class name is
# re-exported from that module below so any external caller that did
# from choraufstellung.main import SingerPool keeps working.
from widgets.singer_pool import SingerPool  # noqa: F401


# M-2 Schritt 4: AddSingerDialog / AffinityDialog / VoicingConfigDialog
# were extracted from this file (formerly Z. 1207-1327) into
# ``widgets/dialogs.py``.  The three class names are re-exported from
# that module below so any external caller that did
# ``from choraufstellung.main import AddSingerDialog`` (etc.) keeps
# working unchanged.
from widgets.dialogs import (
    AddSingerDialog,
    AffinityDialog,
    VoicingConfigDialog,
)


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
        self.resize(1280, 768)
        
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
        sc=QScrollArea(); sc.setWidgetResizable(False)
        # M-2 bug-fix 2026-06-12: the QScrollArea must be told it can
        # grow horizontally, otherwise the splitter's left side (pool)
        # consumes all the resize-room and the grid stays stuck at
        # ~5 columns. sizePolicy=Expanding/Preferred lets the right
        # side claim leftover space when the user enlarges the window.
        from PyQt6.QtWidgets import QSizePolicy
        sc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # The viewport size is set once at construction and does not
        # grow with the QScrollArea because setWidgetResizable(False).
        # We install a resize listener that resizes the inner grid
        # widget to match the viewport width, so that enlarging the
        # MainWindow actually gives the grid more horizontal room.
        # (The grid keeps its own minimum width via setMinimumSize in
        # FormationGrid, so the scrollbar appears when the grid is
        # wider than the viewport - which is the correct behavior for
        # very wide formations like 2x16.)
        def _resize_grid_to_viewport():
            viewport_w = sc.viewport().width()
            # The grid's natural width (cols * 130 + 80 + 50) is
            # already its minimum; if the viewport is smaller we let
            # the grid overflow (scrollbar appears). If the viewport
            # is bigger we expand the grid so the columns fill the
            # available space.
            grid_w = max(self.grid.minimumWidth(), viewport_w)
            self.grid.setFixedWidth(grid_w)
        # Defer the first call until the scroll area is laid out.
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, _resize_grid_to_viewport)
        sc.viewport().installEventFilter(self)
        # Stash the resizer on the scroll area so we can call it from
        # the eventFilter when the viewport size changes.
        self._resize_grid_to_viewport = _resize_grid_to_viewport
        self.grid=FormationGrid(4,5)
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
        sp.addWidget(rp)
        # M-2 bug-fix 2026-06-12: the splitter must grow with the
        # MainWindow. Without the size-policy + stretch factors below,
        # it stays at its Preferred size (~640x480) even when the user
        # enlarges the window to 2500x900. The result: the grid's
        # QScrollArea is stuck at ~5 columns.
        from PyQt6.QtWidgets import QSizePolicy
        sp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sp.setSizes([250, 800])
        sp.setStretchFactor(0, 0)  # pool: keeps its initial 250 px
        sp.setStretchFactor(1, 1)  # grid: takes the leftover space
        # Stretch=1 in addWidget tells the surrounding QHBoxLayout
        # to give the splitter all leftover space when the window grows.
        ml.addWidget(sp, 1); self.menu()
        self.pool.placed_singer_ids = set()
        self.pool.singers = self.singers
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)

    def eventFilter(self, obj, event):
        """Resize the inner grid when the QScrollArea viewport changes size.

        This is the M-2 2026-06-12 follow-up to the resize-bug fix.
        Without it the grid stays at its construction-time size even
        when the user enlarges the MainWindow.
        """
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Resize:
            # Find the QScrollArea viewport in our tree and resize the
            # grid when its size changes.  The QScrollArea itself is
            # the parent of the viewport and the grid is the widget.
            sc = obj.parent() if obj is not None else None
            if sc is not None and hasattr(sc, "viewport") and obj is sc.viewport():
                if hasattr(self, "_resize_grid_to_viewport"):
                    self._resize_grid_to_viewport()
        return super().eventFilter(obj, event)

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