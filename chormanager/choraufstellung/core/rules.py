# TESTABLE: Arrangement algorithms - pure Python, no Qt dependencies
from dataclasses import dataclass
from typing import List, Callable, Optional, Tuple, Dict, Any


def get_voice_group_value(vg) -> str:
    """Convert voice_group to string, handling both str and enum types."""
    if hasattr(vg, 'value'):
        return vg.value
    return str(vg)


@dataclass
class SingerRef:
    singer_id: str
    name: str
    voice_group: str
    height: int
    row: int
    col: int
    affinity: str = ""

    def to_dict(self):
        return {
            "singer_id": self.singer_id,
            "name": self.name,
            "voice_group": self.voice_group,
            "height": self.height,
            "row": self.row,
            "col": self.col,
            "affinity": self.affinity
        }


@dataclass
class ArrangementResult:
    success: bool
    singers: List[SingerRef]
    swap_count: int = 0
    cost: float = 0.0
    message: str = ""


class ArrangementRule:
    def __init__(self, name: str, is_primary: bool = True):
        self._name = name
        self._is_primary = is_primary

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        raise NotImplementedError


class HeightRule(ArrangementRule):
    def __init__(self):
        super().__init__("Nach Größe", is_primary=True)

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        singers.sort(key=lambda s: (s.height, s.name))

        idx = 0
        for row in range(rows):
            for col in range(cols):
                if idx < len(singers):
                    s = singers[idx]
                    s.row = row
                    s.col = col
                    idx += 1
                else:
                    break

        for s in singers:
            if s not in singers[:idx]:
                s.row = -1
                s.col = -1

        return ArrangementResult(success=True, singers=singers, message=f"{idx} Sänger platziert")


class SATBRule(ArrangementRule):
    def __init__(self):
        super().__init__("SATB (Stimmgruppe)", is_primary=True)

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        vg_getter = get_voice_group_value
        sopran = [s for s in singers if "Sopran" in vg_getter(s.voice_group)]
        alt = [s for s in singers if "Alt" in vg_getter(s.voice_group)]
        tenor = [s for s in singers if "Tenor" in vg_getter(s.voice_group)]
        bass = [s for s in singers if "Bass" in vg_getter(s.voice_group)]

        sopran.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)

        ordered = sopran + alt + tenor + bass
        placed_ids = set()

        idx = 0
        for col in range(cols):
            for row in range(rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    placed_ids.add(s.singer_id)
                    idx += 1
                else:
                    break

        for s in singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1

        return ArrangementResult(success=True, singers=singers, message=f"{idx} Sänger platziert")


class SBTARule(ArrangementRule):
    def __init__(self):
        super().__init__("SBTA (Stimmgruppe)", is_primary=True)

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        vg_getter = get_voice_group_value
        sopran = [s for s in singers if "Sopran" in vg_getter(s.voice_group)]
        alt = [s for s in singers if "Alt" in vg_getter(s.voice_group)]
        tenor = [s for s in singers if "Tenor" in vg_getter(s.voice_group)]
        bass = [s for s in singers if "Bass" in vg_getter(s.voice_group)]

        sopran.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)

        ordered = sopran + bass + tenor + alt

        idx = 0
        for col in range(cols):
            for row in range(rows):
                if idx < len(ordered):
                    s = ordered[idx]
                    s.row = row
                    s.col = col
                    idx += 1
                else:
                    break

        for s in singers:
            if s not in ordered[:idx]:
                s.row = -1
                s.col = -1

        return ArrangementResult(success=True, singers=singers, message=f"{idx} Sänger platziert")


class AffinityCostFunction:
    def __init__(self, staggered: bool = False, same_row_weight: float = 10.0):
        self.staggered = staggered
        self.same_row_weight = same_row_weight

    def compute_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int],
                        row1_parity: int = 0, row2_parity: int = 0) -> float:
        x1 = pos1[1]
        y1 = pos1[0]
        x2 = pos2[1]
        y2 = pos2[0]

        if self.staggered:
            if row1_parity == 1:
                x1 += 0.5
            if row2_parity == 1:
                x2 += 0.5

        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    def compute_cost(self, pairs: List[Tuple[SingerRef, SingerRef]]) -> float:
        total = 0.0
        for s1, s2 in pairs:
            if s1.row >= 0 and s1.col >= 0 and s2.row >= 0 and s2.col >= 0:
                # Base distance
                dist = self.compute_distance(
                    (s1.row, s1.col), (s2.row, s2.col),
                    s1.row % 2, s2.row % 2
                )
                # Add heavy penalty if NOT in same row (same row is preferred)
                if s1.row != s2.row:
                    dist += self.same_row_weight
                total += dist
            else:
                total += float('inf')
        return total


class AffinityRule(ArrangementRule):
    def __init__(self, max_swaps: int = 50, max_iterations: int = 3):
        super().__init__("Nähe (Singpartner)", is_primary=False)
        self.max_swaps = max_swaps
        self.max_iterations = max_iterations

    def apply(self, singers: List[SingerRef], rows: int, cols: int, 
              staggered: bool = False, 
              get_singer_at_fn: Optional[Callable] = None,
              is_occupied_fn: Optional[Callable] = None) -> ArrangementResult:
        pairs = self._build_pairs(singers)

        if not pairs:
            return ArrangementResult(success=True, singers=singers, message="Keine gültigen Paare")

        cost_fn = AffinityCostFunction(staggered)
        swapped = 0
        cost_improved = True
        iteration = 0

        while cost_improved and iteration < self.max_iterations and swapped < self.max_swaps:
            cost_improved = False
            iteration += 1

            current_cost = cost_fn.compute_cost(pairs)

            for s1, s2 in pairs:
                if swapped >= self.max_swaps:
                    break

                distance = cost_fn.compute_distance(
                    (s1.row, s1.col), (s2.row, s2.col),
                    s1.row % 2, s2.row % 2
                )
                if distance < 0.1:
                    continue

                neighbors1 = self._get_neighbor_positions(s1, rows, cols, singers)
                neighbors2 = self._get_neighbor_positions(s2, rows, cols, singers)

                best_swap = None
                best_new_distance = distance

                for nr1, nc1 in neighbors1:
                    for nr2, nc2 in neighbors2:
                        if (nr1, nc1) == (nr2, nc2):
                            continue

                        occ1, occ2 = None, None
                        for s in singers:
                            if s.row == nr1 and s.col == nc1:
                                occ1 = s
                            if s.row == nr2 and s.col == nc2:
                                occ2 = s

                        old_row1, old_col1 = s1.row, s1.col
                        old_row2, old_col2 = s2.row, s2.col

                        s1.row, s2.row = nr1, nr2
                        s1.col, s2.col = nc1, nc2

                        if occ1:
                            occ1.row, occ1.col = old_row1, old_col1
                        if occ2:
                            occ2.row, occ2.col = old_row2, old_col2

                        new_distance = cost_fn.compute_distance(
                            (s1.row, s1.col), (s2.row, s2.col),
                            s1.row % 2, s2.row % 2
                        )

                        if new_distance < best_new_distance:
                            best_new_distance = new_distance
                            best_swap = (occ1, occ2, (old_row1, old_col1), (old_row2, old_col2))
                        else:
                            s1.row, s1.col = old_row1, old_col1
                            s2.row, s2.col = old_row2, old_col2
                            if occ1:
                                occ1.row, occ1.col = nr1, nc1
                            if occ2:
                                occ2.row, occ2.col = nr2, nc2

                if best_swap and best_new_distance < distance:
                    occ1, occ2, pos1, pos2 = best_swap
                    s1.row, s2.row = pos1[0], pos2[0]
                    s1.col, s2.col = pos1[1], pos2[1]

                    if occ1:
                        occ1.row, occ1.col = self._find_empty_for(singers, rows, cols)
                    if occ2:
                        occ2.row, occ2.col = self._find_empty_for(singers, rows, cols)

                    swapped += 1
                    cost_improved = True

        final_cost = cost_fn.compute_cost(pairs)
        return ArrangementResult(success=True, singers=singers, swap_count=swapped, cost=final_cost)

    def _build_pairs(self, singers: List[SingerRef]) -> List[Tuple[SingerRef, SingerRef]]:
        pairs = []
        for s in singers:
            if s.affinity:
                for other in singers:
                    if other.singer_id == s.affinity and other.affinity == s.singer_id:
                        if (s.row >= 0 and s.col >= 0) and (other.row >= 0 and other.col >= 0):
                            pairs.append((s, other))
        return pairs

    def _get_neighbor_positions(self, singer: SingerRef, rows: int, cols: int, 
                                placed: List[SingerRef]) -> List[Tuple[int, int]]:
        positions = []
        row, col = singer.row, singer.col

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    positions.append((nr, nc))

        empty_positions = []
        for r in range(rows):
            for c in range(cols):
                occupied = False
                for s in placed:
                    if s.row == r and s.col == c:
                        occupied = True
                        break
                if not occupied:
                    empty_positions.append((r, c))

        return positions[:8] + empty_positions[:4]

    def _find_empty_for(self, singers: List[SingerRef], rows: int, cols: int) -> Tuple[int, int]:
        occupied = set()
        for s in singers:
            if s.row >= 0 and s.col >= 0:
                occupied.add((s.row, s.col))

        for r in range(rows):
            for c in range(cols):
                if (r, c) not in occupied:
                    return (r, c)
        return (-1, -1)


RULE_REGISTRY = {
    "height": HeightRule(),
    "satb": SATBRule(),
    "sbta": SBTARule(),
    "affinity": AffinityRule(),
}


def get_rule(rule_id: str) -> Optional[ArrangementRule]:
    return RULE_REGISTRY.get(rule_id)


def get_primary_rules() -> List[ArrangementRule]:
    return [r for r in RULE_REGISTRY.values() if r.is_primary]


def get_refinement_rules() -> List[ArrangementRule]:
    return [r for r in RULE_REGISTRY.values() if not r.is_primary]