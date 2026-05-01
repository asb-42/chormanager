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
        sopran1 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 1"]
        sopran2 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 2"]
        alt1 = [s for s in singers if vg_getter(s.voice_group) == "Alt 1"]
        alt2 = [s for s in singers if vg_getter(s.voice_group) == "Alt 2"]
        tenor1 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 1"]
        tenor2 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 2"]
        bass1 = [s for s in singers if vg_getter(s.voice_group) == "Bass 1"]
        bass2 = [s for s in singers if vg_getter(s.voice_group) == "Bass 2"]

        sopran1.sort(key=lambda s: s.name)
        sopran2.sort(key=lambda s: s.name)
        alt1.sort(key=lambda s: s.name)
        alt2.sort(key=lambda s: s.name)
        tenor1.sort(key=lambda s: s.name)
        tenor2.sort(key=lambda s: s.name)
        bass1.sort(key=lambda s: s.name)
        bass2.sort(key=lambda s: s.name)

        groups = [
            sopran1, sopran2, alt1, alt2, tenor1, tenor2, bass1, bass2
        ]
        
        import math
        placed_ids = set()
        col = 0
        for group in groups:
            if not group:
                continue
            
            cols_needed = math.ceil(len(group) / rows)
            
            for i, s in enumerate(group):
                row = i % rows
                s.row = row
                s.col = col + (i // rows)
                placed_ids.add(s.singer_id)
            
            col += cols_needed

        for s in singers:
            if s.singer_id not in placed_ids:
                s.row = -1
                s.col = -1

        return ArrangementResult(success=True, singers=singers, message=f"{len(placed_ids)} Sänger platziert")


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


class S1S2B2B1T2T1A2A1Rule(ArrangementRule):
    def __init__(self):
        super().__init__("S1 S2 B2 B1 T2 T1 A2 A1", is_primary=True)

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        vg_getter = get_voice_group_value
        
        s1 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 1"]
        s2 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 2"]
        b2 = [s for s in singers if vg_getter(s.voice_group) == "Bass 2"]
        b1 = [s for s in singers if vg_getter(s.voice_group) == "Bass 1"]
        t2 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 2"]
        t1 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 1"]
        a2 = [s for s in singers if vg_getter(s.voice_group) == "Alt 2"]
        a1 = [s for s in singers if vg_getter(s.voice_group) == "Alt 1"]

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


class S1S2A1A2T1T2B1B2Rule(ArrangementRule):
    def __init__(self):
        super().__init__("S1 S2 A1 A2 T1 T2 B1 B2", is_primary=True)

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        vg_getter = get_voice_group_value
        
        s1 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 1"]
        s2 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 2"]
        a1 = [s for s in singers if vg_getter(s.voice_group) == "Alt 1"]
        a2 = [s for s in singers if vg_getter(s.voice_group) == "Alt 2"]
        t1 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 1"]
        t2 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 2"]
        b1 = [s for s in singers if vg_getter(s.voice_group) == "Bass 1"]
        b2 = [s for s in singers if vg_getter(s.voice_group) == "Bass 2"]

        for group in [s1, s2, a1, a2, t1, t2, b1, b2]:
            group.sort(key=lambda s: s.name)

        ordered = s1 + s2 + a1 + a2 + t1 + t2 + b1 + b2

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


class S1S2B1B2T1T2A1A2Rule(ArrangementRule):
    def __init__(self):
        super().__init__("S1 S2 B1 B2 T1 T2 A1 A2", is_primary=True)

    def apply(self, singers: List[SingerRef], rows: int, cols: int, staggered: bool = False) -> ArrangementResult:
        vg_getter = get_voice_group_value
        
        s1 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 1"]
        s2 = [s for s in singers if vg_getter(s.voice_group) == "Sopran 2"]
        b1 = [s for s in singers if vg_getter(s.voice_group) == "Bass 1"]
        b2 = [s for s in singers if vg_getter(s.voice_group) == "Bass 2"]
        t1 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 1"]
        t2 = [s for s in singers if vg_getter(s.voice_group) == "Tenor 2"]
        a1 = [s for s in singers if vg_getter(s.voice_group) == "Alt 1"]
        a2 = [s for s in singers if vg_getter(s.voice_group) == "Alt 2"]

        for group in [s1, s2, b1, b2, t1, t2, a1, a2]:
            group.sort(key=lambda s: s.name)

        ordered = s1 + s2 + b1 + b2 + t1 + t2 + a1 + a2

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


class AffinityCostFunction:
    def __init__(self, staggered: bool = False, same_row_weight: float = 100.0):
        self.staggered = staggered
        self.same_row_weight = same_row_weight

    def compute_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int],
                        row1_parity: int = 0, row2_parity: int = 0) -> float:
        r1, c1 = pos1
        r2, c2 = pos2
        
        # NUR Positionen in gleicher Reihe zählen als "Nähe"
        same_row = (r1 == r2)
        col_diff = abs(c1 - c2)
        
        if same_row and col_diff == 1:
            # Perfekt: nebeneinander in gleicher Reihe
            return 0.0
        elif same_row:
            # Gleiche Reihe, aber nicht direkt nebeneinander
            return float(col_diff) * 0.5
        else:
            # Verschiedene Reihen - sollte vermieden werden
            return self.same_row_weight + col_diff

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


# OPTIMIZER: Voice Group Cohesion Rule - keeps same voice groups together
class VoiceGroupCohesionRule(ArrangementRule):
    def __init__(self, max_swaps: int = 200, max_iterations: int = 10):
        super().__init__("Stimmgruppe zusammenhalten", is_primary=False)
        self.max_swaps = max_swaps
        self.max_iterations = max_iterations
    
    def _get_voice_group(self, singer):
        vg = singer.voice_group
        if hasattr(vg, 'value'):
            return vg.value
        return str(vg)
    
    def _compute_cohesion_cost(self, s1, s2):
        if s1.row < 0 or s1.col < 0 or s2.row < 0 or s2.col < 0:
            return float('inf')
        
        vg1 = self._get_voice_group(s1)
        vg2 = self._get_voice_group(s2)
        
        if vg1 != vg2:
            if s1.row == s2.row and abs(s1.col - s2.col) == 1:
                return 1000.0
            elif s1.row == s2.row:
                return 500.0 + abs(s1.col - s2.col) * 10.0
            else:
                return 200.0 + abs(s1.col - s2.col)
        
        if s1.row == s2.row and s1.col == s2.col:
            return 0.0
        
        if s1.row == s2.row:
            return float(abs(s1.col - s2.col)) * 0.5
        
        return 50.0 + abs(s1.col - s2.col)
    
    def _compute_group_cohesion(self, group):
        if len(group) < 2:
            return 0.0
        
        total_cost = 0.0
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                total_cost += self._compute_cohesion_cost(group[i], group[j])
        
        return total_cost
    
    def _compute_total_cost(self, vg_groups):
        total = 0.0
        for vg, group in vg_groups.items():
            total += self._compute_group_cohesion(group)
        return total
    
    def apply(self, singers: List[SingerRef], rows: int, cols: int,
              staggered: bool = False,
              get_singer_at_fn: Optional[Callable] = None,
              is_occupied_fn: Optional[Callable] = None) -> ArrangementResult:
        
        vg_groups = {}
        for s in singers:
            if s.row < 0:
                continue
            vg = self._get_voice_group(s)
            if vg not in vg_groups:
                vg_groups[vg] = []
            vg_groups[vg].append(s)
        
        swapped = 0
        cost_improved = True
        iteration = 0
        
        while cost_improved and iteration < self.max_iterations and swapped < self.max_swaps:
            cost_improved = False
            iteration += 1
            
            current_total_cost = self._compute_total_cost(vg_groups)
            
            for vg, group in vg_groups.items():
                if len(group) < 2:
                    continue
                
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        if swapped >= self.max_swaps:
                            break
                        
                        s1 = group[i]
                        s2 = group[j]
                        
                        occupied = set()
                        for s in singers:
                            if s.row >= 0 and s.col >= 0:
                                occupied.add((s.row, s.col))
                        
                        empty_positions = []
                        for r in range(rows):
                            for c in range(cols):
                                if (r, c) not in occupied:
                                    empty_positions.append((r, c))
                        
                        for empty_r, empty_c in empty_positions:
                            old_row, old_col = s2.row, s2.col
                            s2.row, s2.col = empty_r, empty_c
                            
                            new_total_cost = self._compute_total_cost(vg_groups)
                            
                            if new_total_cost < current_total_cost:
                                current_total_cost = new_total_cost
                                swapped += 1
                                cost_improved = True
                                break
                            else:
                                s2.row, s2.col = old_row, old_col
                        
                        if cost_improved:
                            break
                        
                        for other in singers:
                            if other.row < 0:
                                continue
                            if other.singer_id in (s1.singer_id, s2.singer_id):
                                continue
                            
                            old_row2, old_col2 = s2.row, s2.col
                            old_other_row, old_other_col = other.row, other.col
                            
                            s2.row, other.row = other.row, s2.row
                            s2.col, other.col = other.col, s2.col
                            
                            new_total_cost = self._compute_total_cost(vg_groups)
                            
                            if new_total_cost < current_total_cost:
                                current_total_cost = new_total_cost
                                swapped += 1
                                cost_improved = True
                                break
                            else:
                                s2.row, s2.col = old_row2, old_col2
                                other.row, other.col = old_other_row, old_other_col
                        
                        if cost_improved:
                            break
                    if cost_improved:
                        break
                if cost_improved:
                    break
        
        return ArrangementResult(success=True, singers=singers, message="Stimmgruppen zusammengehalten")


RULE_REGISTRY = {
    "height": HeightRule(),
    "satb": SATBRule(),
    "sbta": SBTARule(),
    "s1s2a1a2t1t2b1b2": S1S2A1A2T1T2B1B2Rule(),
    "s1s2b1b2t1t2a1a2": S1S2B1B2T1T2A1A2Rule(),
    "affinity": AffinityRule(),
    "voice_group_cohesion": VoiceGroupCohesionRule(),
    "s1s2b2b1t2t1a2a1": S1S2B2B1T2T1A2A1Rule(),
}


def get_rule(rule_id: str) -> Optional[ArrangementRule]:
    return RULE_REGISTRY.get(rule_id)


def get_primary_rules() -> List[ArrangementRule]:
    return [r for r in RULE_REGISTRY.values() if r.is_primary]


def get_refinement_rules() -> List[ArrangementRule]:
    return [r for r in RULE_REGISTRY.values() if not r.is_primary]