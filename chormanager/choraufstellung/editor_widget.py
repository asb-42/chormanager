"""Embeddable formation editor widget (Phase 2, M0).

Plan ref: docs/plans/2026-06-11_choraufstellung-migration.md, Phase 2
(Embed the Plugin as a Widget).

:class:`FormationEditorWidget` composes the canonical ``widgets/``
components (:class:`SingerPool` + :class:`FormationGrid`) into a plain
:class:`QWidget`, so :class:`ChorAufstellungTab` can embed the editor
instead of spawning a subprocess. It mirrors the pool/grid core of
``main.MainWindow.setup_ui`` but owns no menus, no file dialogs, no
PDF export and no subprocess calls — those stay in ``main.py`` (and
later Phase-2 increments) until they are ported one by one.
"""
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QWidget,
)

from widgets.formation_grid import FormationGrid
from widgets.singer_pool import SingerPool
from singer_model import Singer


class FormationEditorWidget(QWidget):
    """Pool + grid editor surface without any window chrome."""

    DEFAULT_ROWS = 4
    DEFAULT_COLS = 5

    def __init__(
        self,
        rows: int = DEFAULT_ROWS,
        cols: int = DEFAULT_COLS,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Create the editor with an empty singer list.

        Args:
            rows: Initial grid row count.
            cols: Initial grid column count.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self.singers: List[Singer] = []
        self._is_modified = False
        self._build_layout(rows, cols)
        self._connect_signals()

    # ------------------------------------------------------------------
    # Layout (mirrors main.MainWindow.setup_ui pool/grid core)
    # ------------------------------------------------------------------
    def _build_layout(self, rows: int, cols: int) -> None:
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.pool = SingerPool()
        splitter.addWidget(self.pool)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.grid = FormationGrid(rows, cols)
        scroll.setWidget(self.grid)
        splitter.addWidget(scroll)

        splitter.setSizes([250, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

    def _connect_signals(self) -> None:
        self.pool.singer_selected.connect(self.add_to_grid)
        self.pool.singer_added.connect(self.add_to_grid)
        self.pool.place_all_requested.connect(self.place_all_singers)
        self.grid.singer_removed_from_grid.connect(
            self._on_singer_removed_from_grid
        )

    # ------------------------------------------------------------------
    # Data API
    # ------------------------------------------------------------------
    def set_singers(self, singers: List[Singer]) -> None:
        """Replace the master singer list (placements are kept).

        Args:
            singers: Master list; singers with ``row``/``col >= 0``
                show up as placed in the grid.
        """
        self.singers = list(singers)
        self.grid.singers = [s for s in self.singers if s.row >= 0]
        self.grid.refresh_grid()
        self._sync_pool()
        self._is_modified = False

    def load_formation_data(self, data: Dict) -> None:
        """Load a formation dict (same shape as file_io round-trip).

        Accepts ``Singer`` objects and plain dicts (rehydrated via
        :meth:`Singer.from_dict`) in ``data["singers"]``.

        Args:
            data: Formation dict with ``rows``, ``cols``,
                ``staggered`` and ``singers`` keys.
        """
        raw = data.get("singers", [])
        singers: List[Singer] = []
        for item in raw:
            if isinstance(item, dict):
                try:
                    singers.append(Singer.from_dict(item))
                except (KeyError, ValueError):
                    continue
            else:
                singers.append(item)
        self.grid.rows = int(data.get("rows", self.DEFAULT_ROWS))
        self.grid.cols = int(data.get("cols", self.DEFAULT_COLS))
        self.grid.staggered = bool(data.get("staggered", False))
        self.set_singers(singers)

    def placed_singer_ids(self) -> Set[str]:
        """Return the ids of all singers currently placed on the grid."""
        return set(self.grid.get_placed_singer_ids())

    def is_modified(self) -> bool:
        """Return whether the formation changed since load/set."""
        return self._is_modified

    # ------------------------------------------------------------------
    # Editing ops (dialog-free: callers decide about user feedback)
    # ------------------------------------------------------------------
    def add_to_grid(self, singer: Singer) -> bool:
        """Place one singer on the first free slot.

        Args:
            singer: Singer to place (added to the master list if new).

        Returns:
            True if placed, False if the grid is full.
        """
        if singer not in self.singers:
            self.singers.append(singer)
        placed = bool(self.grid.place_singer(singer))
        if placed:
            self._sync_pool()
            self._is_modified = True
        return placed

    def place_all_singers(self) -> int:
        """Place every unplaced singer until the grid is full.

        Returns:
            Number of newly placed singers.
        """
        placed = 0
        for singer in self.singers:
            if str(singer.singer_id) not in self.grid.get_placed_singer_ids():
                if self.grid.place_singer(singer):
                    placed += 1
                else:
                    break
        if placed:
            self._sync_pool()
            self._is_modified = True
        return placed

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _on_singer_removed_from_grid(self, singer: Singer) -> None:
        self._sync_pool()
        self._is_modified = True

    def _sync_pool(self) -> None:
        self.pool.singers = self.singers
        self.pool.placed_singer_ids = self.grid.get_placed_singer_ids()
        self.pool.update_singers(self.singers, self.pool.placed_singer_ids)
