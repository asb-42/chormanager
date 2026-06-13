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
from autosave import AutoSaveController
from file_io import FormationFileIO
from pdf_export_integration import PDFExportBridge
from chormanager_bridge import ChorManagerBridge
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



# M-2 Schritt 6: FormationGrid was extracted from this file
# (formerly Z. 110-848, ~739 LOC) into
# ``widgets/formation_grid.py``.  The class name is re-exported
# from that module so external callers that did
# ``from choraufstellung.main import FormationGrid`` keep working.
from widgets.formation_grid import FormationGrid  # noqa: F401

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
        
        self._is_modified = False
        self.last_manual_save_mtime = 0
        self._loaded_metadata = {
            "project": project_name or "",
            "event": event_name or "",
            "event_date": event_date or "",
            "event_type": event_type or ""
        }
        # M-2 Schritt 7: autosave timer / save-decision moved to
        # ``AutoSaveController``.  The window only exposes the three
        # protocol methods the controller needs (is_modified / has_file
        # / build_data) and owns the source-of-truth flags
        # (``is_modified``, ``file``).  ``self.autosave_timer`` is
        # gone -- use ``self.autosave.timer`` if you ever need raw
        # QTimer access.
        self.autosave = AutoSaveController(
            window=self,
            storage=self.storage,
            interval_ms=120_000,
        )

        # File-IO bridge (M-2 Schritt 8): delegates new/open/save to
        # the standalone FormationFileIO class. The window only owns
        # the dialog-heavy bits (resize warning etc.); the storage
        # round-trip and filename logic live in file_io.py.
        self.file_io = FormationFileIO(self.storage)

        # PDF-Export-Bridge (M-2 Schritt 9): encapsulates the dialog
        # + write + result-feedback cycle.  The window only needs to
        # pass itself; the bridge reads the grid / pdf / singers via
        # duck typing.
        self.pdf_bridge = PDFExportBridge(self)

        # ChorManager-Bridge (M-2 Schritt 10): seeds the host with
        # singers from the parent ChorManager app (temp JSON or DB).
        self.cm_bridge = ChorManagerBridge(self)

        self._finish_init()

    # ------------------------------------------------------------------
    # AutoSaveController protocol (M-2 Schritt 7)
    # ------------------------------------------------------------------
    #
    # These three methods are the only contract the controller needs
    # from the window.  They are duck-typed (the controller uses
    # ``_AutoSaveWindow`` protocol) so we don't have to subclass
    # or import MainWindow from autosave.py.

    def is_modified(self) -> bool:
        return self._is_modified

    def has_file(self) -> bool:
        return self.file is not None

    def build_data(self) -> dict:
        placed = self.grid.get_placed_singer_ids()
        return {
            "version": "1.0",
            "rows": self.grid.rows,
            "cols": self.grid.cols,
            "staggered": self.grid.staggered,
            "singers": [
                {
                    "name": s.name,
                    "voice_group": s.voice_group.value if hasattr(s.voice_group, "value") else str(s.voice_group),
                    "height": s.height,
                    "singer_id": s.singer_id,
                    "row": s.row,
                    "col": s.col,
                    "affinity": s.affinity,
                }
                for s in self.singers
            ],
            "placed": list(placed),
        }

    def _finish_init(self) -> None:
        """Continue the constructor body.

        These statements were stranded inside ``build_data`` after
        an earlier botched refactor; M-2 Schritt 7 lifts them back
        to a class-level helper so the constructor's actual
        end-of-init sequence runs in a well-defined order.
        """
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
        self._is_modified = True

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
        self._is_modified = True
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
            self._is_modified = True
        else:
            QMessageBox.information(self, "Nähe", "Alle Singpartner sind bereits nebeneinander oder nicht in der gleichen Reihe.")

    # ------------------------------------------------------------------
    # File-IO (M-2 Schritt 8) -- thin delegates around FormationFileIO
    # ------------------------------------------------------------------
    #
    # The dialog-heavy paths (resize-warning when there are more placed
    # singers than grid cells) stay on MainWindow; the storage round-trip
    # and the auto-filename generator live in file_io.py.

    def new_f(self):
        # Backward-compat: menu wiring calls this method.
        return self.file_io.new(parent=self, is_modified=self._is_modified)

    def open_f(self):
        # Backward-compat: menu wiring calls this method.
        return self.file_io.open(parent=self)

    def _open_file(self, fp):
        """Backward-compat helper: load the formation at ``fp`` into self."""
        data = self.storage.load_formation(fp)
        if not data:
            return
        self.file_io.load_formation_data(self, data)
        self.file = fp
        self._loaded_metadata = data.get("metadata", {})

    def _exceeds_grid_capacity(self):
        """Return ``excess`` (>=1) when more singers are placed than the grid holds."""
        grid_cells = self.grid.rows * self.grid.cols
        placed = len(self.grid.singers)
        if placed <= grid_cells:
            return 0
        return placed - grid_cells

    def _ask_resize_or_reset(self, excess: int) -> bool:
        """Show the resize/reset dialog. Returns True if the user picked
        'In Pool zurücksetzen' (excess singers should be reset to the pool)."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Zu viele Sänger")
        msg_box.setText(
            f"Die Aufstellung hat {len(self.grid.singers)} Sänger im Raster, "
            f"aber nur {self.grid.rows * self.grid.cols} Plätze."
        )
        msg_box.setIcon(QMessageBox.Icon.Warning)

        btn_resize = QPushButton("Raster vergrößern")
        btn_pool = QPushButton("In Pool zurücksetzen")
        msg_box.addButton(btn_resize, QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(btn_pool, QMessageBox.ButtonRole.ActionRole)
        return msg_box.exec() == btn_pool

    def save_f(self):
        excess = self._exceeds_grid_capacity()
        if excess:
            if not self._ask_resize_or_reset(excess):
                return False
            self._reset_excess_to_pool(excess)
        if not self.file:
            return self.save_as_f()
        return self._save_file(self.file, metadata=self._loaded_metadata)

    def save_as_f(self):
        excess = self._exceeds_grid_capacity()
        if excess:
            if not self._ask_resize_or_reset(excess):
                return False
            self._reset_excess_to_pool(excess)
        return self.file_io.save_as(parent=self, grid=self.grid)

    def _save_file(self, fp, metadata: dict = None):
        if self.file_io.save_to_path(fp, self.grid, metadata=metadata):
            self.file = fp
            self._is_modified = False
            import time
            self.last_manual_save_mtime = time.time()
            return True
        return False

    def generate_filename(self, event_date: str, event_name: str = None) -> str:
        """Delegate to FormationFileIO for backward compatibility."""
        return self.file_io.generate_filename(event_date, event_name)

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
            self._is_modified = True

    def export_pdf(self):
        # Backward-compat: menu wiring calls this method.
        # All work is delegated to self.pdf_bridge (M-2 Schritt 9).
        return self.pdf_bridge.run()

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
            self._is_modified = True

    def edit_singer(self, singer):
        new_singer = self.pool.add_dialog(singer)
        if new_singer:
            idx = next((i for i, s in enumerate(self.singers) if s.singer_id == singer.singer_id), -1)
            if idx >= 0:
                self.singers[idx] = new_singer
            self._is_modified = True

    def set_singer_affinity(self, singer):
        self.pool.set_affinity(singer)

    def on_singer_removed_from_grid(self, singer):
        self.pool.update_singers(self.singers, self.grid.get_placed_singer_ids())
        self._is_modified = True
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
        """Backward-compat: delegate to self.cm_bridge (M-2 Schritt 10)."""
        return self.cm_bridge.load_from_env()
    
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
        self._is_modified = False
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