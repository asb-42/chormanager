import os
import json
from abc import ABC, abstractmethod


# OPTIMIZER: Base class for all formation optimization rules
class FormationRule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_primary(self) -> bool:
        pass

    @abstractmethod
    def apply(self, grid, singers) -> None:
        pass


# OPTIMIZER: SATB Rule - Primary rule for column-wise arrangement by voice group
class SATBRule(FormationRule):
    @property
    def name(self) -> str:
        return "SATB (Stimmgruppe)"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)

        sopran = [s for s in singers if "Sopran" in get_vg(s.voice_group)]
        alt = [s for s in singers if "Alt" in get_vg(s.voice_group)]
        tenor = [s for s in singers if "Tenor" in get_vg(s.voice_group)]
        bass = [s for s in singers if "Bass" in get_vg(s.voice_group)]

        sopran.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)

        ordered = sopran + alt + tenor + bass

        idx = 0
        for col in range(grid.cols):
            for row in range(grid.rows):
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

        grid.refresh_grid()


# OPTIMIZER: Height Rule - Primary rule for row-wise arrangement by body height
class HeightRule(FormationRule):
    @property
    def name(self) -> str:
        return "Nach Größe"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        def get_vg(vg):
            return vg.value if hasattr(vg, 'value') else str(vg)

        sorted_singers = sorted(
            singers,
            key=lambda s: (s.height, get_vg(s.voice_group), s.name)
        )

        idx = 0
        for row in range(grid.rows):
            for col in range(grid.cols):
                if idx < len(sorted_singers):
                    s = sorted_singers[idx]
                    s.row = row
                    s.col = col
                    idx += 1
                else:
                    break

        for s in singers:
            if s not in sorted_singers[:idx]:
                s.row = -1
                s.col = -1

        grid.refresh_grid()


# OPTIMIZER: Affinity Rule - Refinement rule for minimizing distance between paired singers
class AffinityRule(FormationRule):
    @property
    def name(self) -> str:
        return "Nähe (Singpartner)"

    @property
    def is_primary(self) -> bool:
        return False

    def _compute_distance(self, s1, s2, grid):
        """Berechnet die Distanz - nur gleiche Reihe zählt als 'Nähe'.
        
        Regeln:
        - gleiche Reihe &相邻 = 0 (ideal)
        - gleiche Reihe & nicht相邻 = small cost
        - verschiedene Reihen = high cost (sollte vermieden werden)
        """
        if s1.row < 0 or s1.col < 0 or s2.row < 0 or s2.col < 0:
            return float('inf')
        
        # Gleiche Reihe?
        same_row = (s1.row == s2.row)
        col_diff = abs(s1.col - s2.col)
        
        if same_row and col_diff == 1:
            # Perfekt: nebeneinander in gleicher Reihe
            return 0.0
        elif same_row:
            # Gleiche Reihe, aber nicht direkt nebeneinander
            # Kleinere Distanz ist besser
            return float(col_diff) * 0.5
        else:
            # Verschiedene Reihen - sollte vermieden werden
            # Gibt hohe Kosten zurück, um vertikale Platzierung zu bestrafen
            return 100.0 + col_diff

    def _swap_positions(self, s1, s2):
        """Tauscht die Positionen von zwei Sängern."""
        s1.row, s2.row = s2.row, s1.row
        s1.col, s2.col = s2.col, s1.col

    def _get_neighbor_positions(self, singer, grid):
        """Liefert alle benachbarten und leeren Positionen für einen Sänger."""
        positions = []
        row, col = singer.row, singer.col

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < grid.rows and 0 <= nc < grid.cols:
                    if not grid.is_occupied(nr, nc):
                        positions.append((nr, nc))
                    else:
                        neighbor = grid.get_singer_at(nr, nc)
                        if neighbor:
                            positions.append((nr, nc))

        empty_positions = []
        for r in range(grid.rows):
            for c in range(grid.cols):
                if not grid.is_occupied(r, c):
                    empty_positions.append((r, c))

        return positions[:8] + empty_positions[:4]

    def apply(self, grid, singers) -> None:
        pairs = []

        for s in singers:
            if s.affinity:
                partner = next((p for p in singers if p.singer_id == s.affinity), None)
                if partner and partner.affinity == s.singer_id:
                    if (s.row >= 0 and s.col >= 0) and (partner.row >= 0 and partner.col >= 0):
                        pairs.append((s, partner))

        if not pairs:
            print("AffinityRule: Keine gültigen Paare gefunden.")
            return

        swapped = 0
        max_swaps = 50
        cost_improved = True
        iteration = 0
        max_iterations = 3

        while cost_improved and iteration < max_iterations and swapped < max_swaps:
            cost_improved = False
            iteration += 1

            current_cost = sum(self._compute_distance(s1, s2, grid) for s1, s2 in pairs)

            for s1, s2 in pairs:
                if swapped >= max_swaps:
                    break

                distance = self._compute_distance(s1, s2, grid)
                if distance < 0.1:
                    continue

                best_swap = None
                best_new_distance = distance

                neighbors1 = self._get_neighbor_positions(s1, grid)
                neighbors2 = self._get_neighbor_positions(s2, grid)

                for nr1, nc1 in neighbors1:
                    for nr2, nc2 in neighbors2:
                        if (nr1, nc1) == (nr2, nc2):
                            continue

                        occupied1 = grid.is_occupied(nr1, nc1)
                        occupied2 = grid.is_occupied(nr2, nc2)

                        if occupied1 and occupied2:
                            occ_singer1 = grid.get_singer_at(nr1, nc1)
                            occ_singer2 = grid.get_singer_at(nr2, nc2)
                            if occ_singer1 and occ_singer2:
                                old_row1, old_col1 = s1.row, s1.col
                                old_row2, s2.row = s2.row, nr1
                                s1.row, s1.col = nr1, nc1
                                s2.row, s2.col = nr2, nc2

                                new_distance = self._compute_distance(s1, s2, grid)

                                if new_distance < best_new_distance:
                                    best_new_distance = new_distance
                                    best_swap = (occ_singer1, occ_singer2, (nr1, nc1), (nr2, nc2))
                                elif new_distance >= distance:
                                    s1.row, s1.col = old_row1, old_col1
                                    s2.row, s2.col = old_row2, old_col2

                        elif occupied1:
                            occ_singer1 = grid.get_singer_at(nr1, nc1)
                            if occ_singer1:
                                old_row1, old_col1 = s1.row, s1.col
                                old_row2, old_col2 = s2.row, s2.col
                                s1.row, s1.col = nr1, nc1
                                s2.row, s2.col = nr2, nc2

                                new_distance = self._compute_distance(s1, s2, grid)

                                if new_distance < best_new_distance:
                                    best_new_distance = new_distance
                                    best_swap = (occ_singer1, None, (nr1, nc1), (nr2, nc2))
                                elif new_distance >= distance:
                                    s1.row, s1.col = old_row1, old_col1
                                    s2.row, s2.col = old_row2, old_col2

                        elif occupied2:
                            occ_singer2 = grid.get_singer_at(nr2, nc2)
                            if occ_singer2:
                                old_row1, old_col1 = s1.row, s1.col
                                old_row2, old_col2 = s2.row, s2.col
                                s1.row, s1.col = nr1, nc1
                                s2.row, s2.col = nr2, nc2

                                new_distance = self._compute_distance(s1, s2, grid)

                                if new_distance < best_new_distance:
                                    best_new_distance = new_distance
                                    best_swap = (None, occ_singer2, (nr1, nc1), (nr2, nc2))
                                elif new_distance >= distance:
                                    s1.row, s1.col = old_row1, old_col1
                                    s2.row, s2.col = old_row2, old_col2

                        else:
                            old_row1, old_col1 = s1.row, s1.col
                            old_row2, old_col2 = s2.row, s2.col
                            s1.row, s1.col = nr1, nc1
                            s2.row, s2.col = nr2, nc2

                            new_distance = self._compute_distance(s1, s2, grid)

                            if new_distance < best_new_distance:
                                best_new_distance = new_distance
                                best_swap = (None, None, (nr1, nc1), (nr2, nc2))
                            elif new_distance >= distance:
                                s1.row, s1.col = old_row1, old_col1
                                s2.row, s2.col = old_row2, old_col2

                if best_swap and best_new_distance < distance:
                    occ1, occ2, pos1, pos2 = best_swap

                    self._swap_positions(s1, s2)

                    if occ1:
                        occ1.row, occ1.col = pos1[0], pos1[1]
                    if occ2:
                        occ2.row, occ2.col = pos2[0], pos2[1]

                    swapped += 1
                    cost_improved = True

            grid.refresh_grid()

        print(f"AffinityRule: {swapped} Swaps durchgeführt.")


# OPTIMIZER: Voice Group Cohesion Rule - keeps same voice groups together
class VoiceGroupCohesionRule(FormationRule):
    """Refinement rule to keep singers of same voice group adjacent."""
    
    @property
    def name(self) -> str:
        return "Stimmgruppe zusammenhalten"
    
    @property
    def is_primary(self) -> bool:
        return False
    
    def _get_voice_group(self, singer):
        """Get voice group identifier (e.g., 'Sopran 1', 'Alt 2')."""
        vg = singer.voice_group
        if hasattr(vg, 'value'):
            return vg.value
        return str(vg)
    
    def _compute_distance(self, s1, s2, grid):
        """Compute horizontal/vertical distance - only same row/col matters."""
        if s1.row < 0 or s1.col < 0 or s2.row < 0 or s2.col < 0:
            return float('inf')
        
        # Same position = perfect
        if s1.row == s2.row and s1.col == s2.col:
            return 0.0
        
        # Same row = good (horizontal neighbors)
        if s1.row == s2.row:
            return float(abs(s1.col - s2.col)) * 0.5
        
        # Different row = bad (should be minimized)
        return 50.0 + abs(s1.col - s2.col)
    
    def apply(self, grid, singers) -> None:
        """Group same voice groups together."""
        # Build groups by voice group
        vg_groups = {}
        for s in singers:
            if s.row < 0:
                continue
            vg = self._get_voice_group(s)
            if vg not in vg_groups:
                vg_groups[vg] = []
            vg_groups[vg].append(s)
        
        # For each voice group with multiple singers, minimize distance
        swapped = 0
        max_swaps = 50
        
        for vg, group_singers in vg_groups.items():
            if len(group_singers) < 2:
                continue
            
            # Try to make them adjacent in same row
            for i in range(len(group_singers)):
                for j in range(i + 1, len(group_singers)):
                    if swapped >= max_swaps:
                        break
                    
                    s1 = group_singers[i]
                    s2 = group_singers[j]
                    
                    current_dist = self._compute_distance(s1, s2, grid)
                    if current_dist < 0.1:
                        continue
                    
                    # Try to swap s2 with a neighbor to get closer to s1
                    best_swap = None
                    best_dist = current_dist
                    
                    # Find candidates to swap with
                    for other in singers:
                        if other.singer_id == s1.singer_id or other.singer_id == s2.singer_id:
                            continue
                        if other.row < 0:
                            continue
                        
                        # Swap s2 with other temporarily
                        old_row1, old_col1 = s2.row, s2.col
                        old_row2, old_col2 = other.row, other.col
                        
                        s2.row, other.row = other.row, s2.row
                        s2.col, other.col = other.col, s2.col
                        
                        new_dist = self._compute_distance(s1, s2, grid)
                        
                        if new_dist < best_dist:
                            best_dist = new_dist
                            best_swap = (other, old_row1, old_col1, old_row2, old_col2)
                        else:
                            # Revert
                            s2.row, other.row = old_row1, old_row2
                            s2.col, other.col = old_col1, old_col2
                    
                    if best_swap:
                        other, or1, oc1, or2, oc2 = best_swap
                        swapped += 1


# OPTIMIZER: Registry of all available rules
RULE_REGISTRY = {
    "satb": SATBRule(),
    "height": HeightRule(),
    "affinity": AffinityRule(),
    "voice_group_cohesion": VoiceGroupCohesionRule(),
}
