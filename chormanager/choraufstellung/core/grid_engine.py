# TESTABLE: Pure Python grid placement logic, Qt-agnostic
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class GridConfig:
    rows: int
    cols: int
    staggered: bool = False
    cell_width: int = 130
    cell_height: int = 80
    offset: int = 65
    margin_left: int = 80
    margin_top: int = 20


@dataclass
class SingerRef:
    singer_id: str
    row: int
    col: int


class GridEngine:
    def __init__(self, config: GridConfig):
        self.config = config

    def stagger_offset(self, row: int) -> int:
        """Berechnet den x-Offset für eine gegebene Reihe bei staggered-Modus."""
        if self.config.staggered and row % 2 == 1:
            return self.config.offset
        return 0

    def pixel_pos(self, row: int, col: int) -> Tuple[int, int]:
        """Berechnet Pixel-Koordinaten für eine Grid-Position."""
        x = self.config.margin_left + col * self.config.cell_width + self.stagger_offset(row)
        y = self.config.margin_top + row * self.config.cell_height
        return x, y

    def is_valid_position(self, row: int, col: int) -> bool:
        """Prüft ob eine Position innerhalb der Grid-Grenzen liegt."""
        return 0 <= row < self.config.rows and 0 <= col < self.config.cols

    def is_occupied(self, row: int, col: int, placed: List[SingerRef]) -> bool:
        """Prüft ob eine Position bereits besetzt ist."""
        for s in placed:
            if s.row == row and s.col == col:
                return True
        return False

    def is_occupied_by_singer(self, row: int, col: int, placed: List[SingerRef], singer_id: str) -> bool:
        """Prüft ob eine Position von einem bestimmten Sänger besetzt ist."""
        for s in placed:
            if s.row == row and s.col == col and s.singer_id == singer_id:
                return True
        return False

    def find_empty_slot(self, placed: List[SingerRef]) -> Optional[Tuple[int, int]]:
        """Findet das erste freie Grid-Feld (row-major order)."""
        for row in range(self.config.rows):
            for col in range(self.config.cols):
                if not self.is_occupied(row, col, placed):
                    return (row, col)
        return None

    def can_place(self, row: int, col: int, placed: List[SingerRef]) -> bool:
        """Prüft ob ein Sänger an einer Position platziert werden kann."""
        return self.is_valid_position(row, col) and not self.is_occupied(row, col, placed)

    def occupied_positions(self, placed: List[SingerRef]) -> List[Tuple[int, int]]:
        """Liefert Liste aller besetzten Positionen."""
        return [(s.row, s.col) for s in placed]

    def all_positions(self) -> List[Tuple[int, int]]:
        """Liefert alle möglichen Grid-Positionen."""
        positions = []
        for row in range(self.config.rows):
            for col in range(self.config.cols):
                positions.append((row, col))
        return positions

    def compute_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int], row1_parity: int = 0, row2_parity: int = 0) -> float:
        """Berechnet euklidische Distanz zwischen zwei Positionen mit optionalem Staggered-Offset."""
        x1 = pos1[1]
        y1 = pos1[0]
        x2 = pos2[1]
        y2 = pos2[0]

        if self.config.staggered:
            if row1_parity == 1:
                x1 += 0.5
            if row2_parity == 1:
                x2 += 0.5

        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    def positions_equal(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """Vergleicht zwei Positionen auf Gleichheit."""
        return pos1[0] == pos2[0] and pos1[1] == pos2[1]

    def get_neighbors(self, row: int, col: int, placed: List[SingerRef]) -> List[SingerRef]:
        """Liefert alle Sänger in den 8 Nachbarpositionen."""
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if self.is_valid_position(nr, nc):
                    for s in placed:
                        if s.row == nr and s.col == nc:
                            neighbors.append(s)
        return neighbors

    def get_singer_at(self, row: int, col: int, placed: List[SingerRef]) -> Optional[SingerRef]:
        """Liefert den Sänger an einer bestimmten Position."""
        for s in placed:
            if s.row == row and s.col == col:
                return s
        return None

    def unplace_singer(self, singer_id: str, placed: List[SingerRef]) -> None:
        """Entfernt einen Sänger aus den platzierten Sängern."""
        for i, s in enumerate(placed):
            if s.singer_id == singer_id:
                placed.pop(i)
                return

    def get_placed_count(self, placed: List[SingerRef]) -> int:
        """Liefert die Anzahl platzierter Sänger."""
        return len(placed)