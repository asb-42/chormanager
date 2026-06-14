"""ChorAufstellung :class:`SingerPool` widget.

M-2 Schritt 5: extracted the ``SingerPool`` class from
``choraufstellung/main.py`` (formerly Z. 970-1206).

A :class:`SingerPool` is the left-hand panel of the ChorAufstellung
editor: a ``QTableWidget`` showing all singers that are NOT currently
placed in the formation.  The pool is also responsible for the
"auto-shrink" behaviour (the pool collapses to ``EMPTY_POOL_WIDTH``
when empty and grows back when a singer is added).

The pool re-uses the draggable table widget extracted in M-2 Schritt 2
(``widgets.draggable_list.DraggableTableWidget``) and the affinity
dialog extracted in M-2 Schritt 4 (``widgets.dialogs.AffinityDialog``).

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 5.
"""
from __future__ import annotations

# PyQt5/PyQt6 cross-compat via the central ``qt_compat`` layer.
from qt_compat import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFont,
    QColor,
    QMenu,
    QDialog,
    Qt,
    pyqtSignal,
)

# Domain model.
from singer_model import voice_group_color

# Sibling widget modules.
from widgets.dialogs import AddSingerDialog, AffinityDialog
from widgets.draggable_list import DraggableTableWidget


class SingerPool(QWidget):
    """Left-hand panel listing all un-placed singers.

    Emits:

    - ``singer_selected`` (object)       — user double-clicked a row
    - ``singer_added`` (object)          — user created a new singer
    - ``singer_edit_requested`` (object) — user picked "Bearbeiten"
    - ``place_all_requested`` ()         — "Alle Sänger platzieren" button

    The auto-shrink behaviour is opt-in via the ``EMPTY_POOL_WIDTH``
    class constant and ``update_singers``.  See
    ``test_choraufstellung_pool_auto_shrink.py``.
    """

    singer_selected = pyqtSignal(object)
    singer_added = pyqtSignal(object)
    singer_edit_requested = pyqtSignal(object)
    place_all_requested = pyqtSignal()

    # Width (in px) the pool collapses to when no singers are in it.
    EMPTY_POOL_WIDTH = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.singers = []
        # M-2 2026-06-12 (auto-shrink): defer the width clamp until
        # ``update_singers`` has been called with real data.  Calling
        # ``setMaximumWidth(50)`` during the MainWindow constructor
        # (when the pool is inside an unlaid-out QSplitter) causes
        # Qt's offscreen plugin to hang on ``propagateSizeHints``.
        self._pool_width_initialized = False

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<b>Sängerpool</b>"))
        self.pool_count_label = QLabel("0 Sänger")
        self.pool_count_label.setStyleSheet(
            "color: #666; font-size: 9pt;"
        )
        lay.addWidget(self.pool_count_label)
        lay.addWidget(
            QLabel(
                "Doppelklick: automatisch\n"
                "Drag & Drop: manuell\n"
                "Rechtsklick: Bearbeiten / Nähe"
            )
        )

        self.table = DraggableTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Stimmgruppe", "Größe", "Nähe"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.setDragDropMode(QTableWidget.DragDropMode.DragOnly)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        self.table.itemDoubleClicked.connect(self.on_dc)
        self.table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table.customContextMenuRequested.connect(
            self.show_context_menu
        )
        self.table.cellClicked.connect(self.on_cell_clicked)
        lay.addWidget(self.table)

        self.placed_singer_ids = set()

        btn_lay = QVBoxLayout()
        btn_lay.addWidget(
            QPushButton(
                "Alle Sänger platzieren",
                clicked=self.place_all_requested.emit,
            )
        )
        btn_lay.addWidget(
            QPushButton("Einzelner Sänger", clicked=self.add_dialog)
        )
        btn_lay.addWidget(
            QPushButton(
                "Ausgewählten entfernen", clicked=self.remove_sel
            )
        )
        lay.addLayout(btn_lay)

    # ------------------------------------------------------------------
    # Selection / context menu
    # ------------------------------------------------------------------

    def on_cell_clicked(self, row, col):
        singer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if singer:
            self.singer_selected.emit(singer)

    def on_dc(self, item):
        """Handle double-click on a row (= user wants to auto-place
        the singer, which the MainWindow converts into the right
        drag-drop action)."""
        if item:
            row = item.row()
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer:
                self.singer_selected.emit(singer)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            singer = self.table.item(row, 0).data(
                Qt.ItemDataRole.UserRole
            )
            if singer:
                menu = QMenu(self)
                menu.addAction("Bearbeiten")
                menu.addAction("Nähe setzen")
                menu.addAction("Entfernen")
                # Use exec() not exec_() via qt_compat helper.
                from qt_compat import exec_qt
                action = exec_qt(
                    menu, self.table.viewport().mapToGlobal(pos)
                )
                if not action:
                    return
                if action.text() == "Bearbeiten":
                    self.singer_edit_requested.emit(singer)
                elif action.text() == "Nähe setzen":
                    self.set_affinity(singer)
                elif action.text() == "Entfernen":
                    self.table.selectRow(row)
                    self.remove_sel()

    # ------------------------------------------------------------------
    # Affinity
    # ------------------------------------------------------------------

    def set_affinity(self, singer):
        d = AffinityDialog(
            self, singer=singer, all_singers=self.singers
        )
        if d.exec() == QDialog.DialogCode.Accepted:
            new_affinity_id = d.get_affinity_singer_id()
            old_affinity_id = singer.affinity

            if old_affinity_id:
                old_partner = next(
                    (
                        s
                        for s in self.singers
                        if s.singer_id == old_affinity_id
                    ),
                    None,
                )
                if (
                    old_partner
                    and old_partner.affinity == singer.singer_id
                ):
                    old_partner.affinity = ""

            singer.affinity = new_affinity_id

            if new_affinity_id:
                partner = next(
                    (
                        s
                        for s in self.singers
                        if s.singer_id == new_affinity_id
                    ),
                    None,
                )
                if partner:
                    partner.affinity = singer.singer_id

            self.update_singers(self.singers, self.placed_singer_ids)
            if hasattr(self.parent(), "_mark_modified"):
                self.parent()._mark_modified()

    # ------------------------------------------------------------------
    # Pool population
    # ------------------------------------------------------------------

    def update_singers(self, singers, placed_ids=None, deferred: bool = False):
        """Refresh the pool from the master singer list and the set of
        ids that are already placed in the formation grid.

        m3-FIX-A: passing ``deferred=True`` coalesces multiple calls in
        the same frame into a single repaint. The repaint is scheduled
        via ``QTimer.singleShot(0, ...)`` so all callers see the
        freshest data and only one ``setRowCount(0)`` + re-populate
        cycle runs.

        Triggers the auto-shrink logic via ``_apply_pool_width``.
        """
        self.singers = singers
        if placed_ids is not None:
            self.placed_singer_ids = placed_ids
        if deferred:
            # m3-FIX-A: coalesce multiple deferred calls in the same
            # frame into a single repaint on the next event-loop tick.
            if getattr(self, "_populate_pending", False):
                return
            self._populate_pending = True
            try:
                from PyQt6.QtCore import QTimer

                def _run() -> None:
                    self._populate_pending = False
                    self._populate_table()

                QTimer.singleShot(0, _run)
            except Exception:
                # Headless / no event loop: just populate immediately.
                self._populate_pending = False
                self._populate_table()
            return
        self._populate_table()

    def _populate_table(self) -> None:
        """Internal: re-build the QTableWidget from ``self.singers``.

        Split out from ``update_singers`` so the deferred path can
        schedule just this bit on the event loop.
        """
        self.table.setRowCount(0)
        for s in self.singers:
            if str(s.singer_id) in self.placed_singer_ids:
                continue
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)

            vg_val = (
                s.voice_group.value
                if hasattr(s.voice_group, "value")
                else str(s.voice_group)
            )
            vg_color = voice_group_color(s.voice_group)

            name_item = QTableWidgetItem(s.name)
            name_item.setData(Qt.ItemDataRole.UserRole, s)
            name_item.setFont(QFont("SansSerif", 9, QFont.Weight.Bold))
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
                partner = next(
                    (
                        p
                        for p in self.singers
                        if p.singer_id == s.affinity
                    ),
                    None,
                )
                if partner:
                    affinity_name = partner.name
            affinity_item = QTableWidgetItem(affinity_name)
            affinity_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 3, affinity_item)

        pool_count = self.table.rowCount()
        self.pool_count_label.setText(f"{pool_count} Sänger")
        self._apply_pool_width(pool_count)

    def update_placed_singers(self, placed_ids):
        """Just update the placed-id set without touching the master
        singer list (used when the user removes a singer from the
        grid without reloading the pool)."""
        self.placed_singer_ids = placed_ids
        self.update_singers(self.singers, placed_ids)

    def add_singer(self, s):
        self.singers.append(s)
        self.update_singers(self.singers, self.placed_singer_ids)

    def add_dialog(self, singer=None):
        d = AddSingerDialog(self, singer=singer)
        if d.exec() == QDialog.DialogCode.Accepted:
            s = d.get_singer()
            if s:
                if singer:
                    idx = next(
                        (
                            i
                            for i, x in enumerate(self.singers)
                            if x.singer_id == singer.singer_id
                        ),
                        -1,
                    )
                    if idx >= 0:
                        self.singers[idx] = s
                else:
                    self.singers.append(s)
                self.update_singers(
                    self.singers, self.placed_singer_ids
                )
                if singer:
                    return s
                self.singer_added.emit(s)
                return s
        return None

    def remove_sel(self):
        row = self.table.currentRow()
        if row >= 0:
            singer = self.table.item(row, 0).data(
                Qt.ItemDataRole.UserRole
            )
            if singer:
                idx = next(
                    (
                        i
                        for i, x in enumerate(self.singers)
                        if x.singer_id == singer.singer_id
                    ),
                    -1,
                )
                if idx >= 0:
                    if singer.affinity:
                        partner = next(
                            (
                                p
                                for p in self.singers
                                if p.singer_id == singer.affinity
                            ),
                            None,
                        )
                        if partner:
                            partner.affinity = ""
                    self.singers.pop(idx)
        self.update_singers(self.singers, self.placed_singer_ids)

    # ------------------------------------------------------------------
    # Auto-shrink (M-2 2026-06-12 follow-up)
    # ------------------------------------------------------------------

    def _apply_pool_width(self, pool_count: int) -> None:
        """Shrink the pool to ``EMPTY_POOL_WIDTH`` when empty, else
        release the clamp so it can grow back to its natural width.

        Also moves the QSplitter handle to the new pool size, because
        setting only the minimum/maximum on the pool leaves the
        splitter's persistent handle position unchanged (Qt
        keeps the empty space between the shrunk widget and the
        handle).  See the screenshot in the bug report for an
        illustration of the "shrunken pool, old handle" effect.

        Skipped on the very first call (the one inside the
        ``MainWindow.setup_ui()`` path) because the pool is not yet
        fully laid out at that point and calling setMaximumWidth(50)
        causes Qt's offscreen plugin to hang on
        ``propagateSizeHints``.
        """
        if not self._pool_width_initialized:
            # First call (empty pool, just laid out) - just record
            # that we're done, don't change widths.
            self._pool_width_initialized = True
            return
        # Find the QSplitter that contains us.  We need it so we can
        # move the handle along with the pool's width change.
        from qt_compat import QSplitter
        splitter = self.parentWidget()
        while splitter is not None and not isinstance(
            splitter, QSplitter
        ):
            splitter = splitter.parentWidget()
        if pool_count <= 0:
            self.setMinimumWidth(self.EMPTY_POOL_WIDTH)
            self.setMaximumWidth(self.EMPTY_POOL_WIDTH)
            if splitter is not None:
                total = sum(splitter.sizes())
                if total > 0:
                    splitter.setSizes(
                        [
                            self.EMPTY_POOL_WIDTH,
                            max(0, total - self.EMPTY_POOL_WIDTH),
                        ]
                    )
        else:
            # QWIDGETSIZE_MAX is the Qt sentinel for "no upper bound".
            self.setMaximumWidth(16777215)
            # Reset minimum to 0 (no constraint) instead of calling
            # ``minimumSizeHint()`` which would force Qt to recompute
            # layout sizes inside a possibly-not-yet-laid-out parent.
            self.setMinimumWidth(0)
            if splitter is not None:
                sizes = splitter.sizes()
                if sizes and sizes[0] <= self.EMPTY_POOL_WIDTH:
                    total = sum(sizes)
                    if total > 0:
                        # Restore the pool to about 1/3 of the total
                        # width (a reasonable default for a singer
                        # list with 4 columns).
                        natural = max(250, total // 3)
                        splitter.setSizes(
                            [natural, max(0, total - natural)]
                        )
