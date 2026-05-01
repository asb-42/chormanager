from abc import ABC, abstractmethod


def get_voice_group_value(vg) -> str:
    if hasattr(vg, 'value'):
        return vg.value
    return str(vg)


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


def _place_singers_column_wise(grid, singers, ordered_groups):
    idx = 0
    for col in range(grid.cols):
        for row in range(grid.rows):
            if idx < len(ordered_groups):
                s = ordered_groups[idx]
                s.row = row
                s.col = col
                idx += 1
            else:
                break
    
    for s in singers:
        if s not in ordered_groups[:idx]:
            s.row = -1
            s.col = -1
    
    grid.refresh_grid()


class SATBRule(FormationRule):
    @property
    def name(self) -> str:
        return "SATB (Stimmgruppe)"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        sopran = [s for s in singers if "Sopran" in get_voice_group_value(s.voice_group)]
        alt = [s for s in singers if "Alt" in get_voice_group_value(s.voice_group)]
        tenor = [s for s in singers if "Tenor" in get_voice_group_value(s.voice_group)]
        bass = [s for s in singers if "Bass" in get_voice_group_value(s.voice_group)]

        sopran.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)

        ordered = sopran + alt + tenor + bass
        _place_singers_column_wise(grid, singers, ordered)


class S1S2A1A2T1T2B1B2Rule(FormationRule):
    @property
    def name(self) -> str:
        return "S1 S2 A1 A2 T1 T2 B1 B2"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        s1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Sopran 1"]
        s2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Sopran 2"]
        a1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Alt 1"]
        a2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Alt 2"]
        t1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Tenor 1"]
        t2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Tenor 2"]
        b1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Bass 1"]
        b2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Bass 2"]

        for group in [s1, s2, a1, a2, t1, t2, b1, b2]:
            group.sort(key=lambda s: s.name)

        ordered = s1 + s2 + a1 + a2 + t1 + t2 + b1 + b2
        _place_singers_column_wise(grid, singers, ordered)


class S1S2B1B2T1T2A1A2Rule(FormationRule):
    @property
    def name(self) -> str:
        return "S1 S2 B1 B2 T1 T2 A1 A2"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        s1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Sopran 1"]
        s2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Sopran 2"]
        b1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Bass 1"]
        b2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Bass 2"]
        t1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Tenor 1"]
        t2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Tenor 2"]
        a1 = [s for s in singers if get_voice_group_value(s.voice_group) == "Alt 1"]
        a2 = [s for s in singers if get_voice_group_value(s.voice_group) == "Alt 2"]

        for group in [s1, s2, b1, b2, t1, t2, a1, a2]:
            group.sort(key=lambda s: s.name)

        ordered = s1 + s2 + b1 + b2 + t1 + t2 + a1 + a2
        _place_singers_column_wise(grid, singers, ordered)


class HeightRule(FormationRule):
    @property
    def name(self) -> str:
        return "Nach Größe"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        sorted_singers = sorted(
            singers,
            key=lambda s: (s.height, get_voice_group_value(s.voice_group), s.name)
        )
        _place_singers_column_wise(grid, singers, sorted_singers)


class SBTARule(FormationRule):
    @property
    def name(self) -> str:
        return "SBTA (Stimmgruppe)"

    @property
    def is_primary(self) -> bool:
        return True

    def apply(self, grid, singers) -> None:
        sopran = [s for s in singers if "Sopran" in get_voice_group_value(s.voice_group)]
        bass = [s for s in singers if "Bass" in get_voice_group_value(s.voice_group)]
        tenor = [s for s in singers if "Tenor" in get_voice_group_value(s.voice_group)]
        alt = [s for s in singers if "Alt" in get_voice_group_value(s.voice_group)]

        sopran.sort(key=lambda s: s.name)
        bass.sort(key=lambda s: s.name)
        tenor.sort(key=lambda s: s.name)
        alt.sort(key=lambda s: s.name)

        ordered = sopran + bass + tenor + alt
        _place_singers_column_wise(grid, singers, ordered)


class AffinityRule(FormationRule):
    @property
    def name(self) -> str:
        return "Nähe (Singpartner)"

    @property
    def is_primary(self) -> bool:
        return False

    def _compute_distance(self, s1, s2, grid):
        if s1.row < 0 or s1.col < 0 or s2.row < 0 or s2.col < 0:
            return float('inf')
        
        same_row = (s1.row == s2.row)
        col_diff = abs(s1.col - s2.col)
        
        if same_row and col_diff == 1:
            return 0.0
        elif same_row:
            return float(col_diff) * 0.5
        else:
            return 100.0 + col_diff

    def _get_neighbor_positions(self, singer, grid):
        positions = []
        row, col = singer.row, singer.col

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < grid.rows and 0 <= nc < grid.cols:
                    positions.append((nr, nc))

        return positions

    def apply(self, grid, singers) -> None:
        pairs = []

        for s in singers:
            if s.affinity:
                partner = next((p for p in singers if p.singer_id == s.affinity), None)
                if partner and partner.affinity == s.singer_id:
                    if (s.row >= 0 and s.col >= 0) and (partner.row >= 0 and partner.col >= 0):
                        pairs.append((s, partner))

        if not pairs:
            return

        swapped = 0
        max_swaps = 50
        cost_improved = True
        iteration = 0
        max_iterations = 3

        while cost_improved and iteration < max_iterations and swapped < max_swaps:
            cost_improved = False
            iteration += 1

            for s1, s2 in pairs:
                if swapped >= max_swaps:
                    break

                distance = self._compute_distance(s1, s2, grid)
                if distance < 0.1:
                    continue

                best_swap = None
                best_new_distance = distance

                neighbors = self._get_neighbor_positions(s1, grid)
                for nr, nc in neighbors:
                    if grid.is_occupied(nr, nc):
                        occupant = grid.get_singer_at(nr, nc)
                        if occupant and occupant.singer_id != s2.singer_id:
                            old_row, old_col = s1.row, s1.col
                            s1.row, s1.col = nr, nc
                            occupant.row, occupant.col = old_row, old_col

                            new_distance = self._compute_distance(s1, s2, grid)
                            if new_distance < best_new_distance:
                                best_new_distance = new_distance
                                best_swap = (occupant, old_row, old_col, nr, nc)
                            
                            s1.row, s1.col = old_row, old_col
                            occupant.row, occupant.col = nr, nc

                if best_swap and best_new_distance < distance:
                    occupant, old_row, old_col, nr, nc = best_swap
                    s1.row, s1.col = nr, nc
                    occupant.row, occupant.col = old_row, old_col
                    swapped += 1
                    cost_improved = True

            grid.refresh_grid()


class VoiceGroupCohesionRule(FormationRule):
    @property
    def name(self) -> str:
        return "Stimmgruppe zusammenhalten"
    
    @property
    def is_primary(self) -> bool:
        return False
    
    def _get_voice_group(self, singer):
        vg = singer.voice_group
        if hasattr(vg, 'value'):
            return vg.value
        return str(vg)
    
    def _compute_cohesion_cost(self, s1, s2, grid):
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
    
    def _compute_total_cost(self, vg_groups, grid):
        total = 0.0
        for vg, group in vg_groups.items():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    total += self._compute_cohesion_cost(group[i], group[j], grid)
        return total
    
    def apply(self, grid, singers) -> None:
        vg_groups = {}
        for s in singers:
            if s.row < 0:
                continue
            vg = self._get_voice_group(s)
            if vg not in vg_groups:
                vg_groups[vg] = []
            vg_groups[vg].append(s)
        
        swapped = 0
        max_swaps = 200
        cost_improved = True
        iteration = 0
        max_iterations = 10
        
        while cost_improved and iteration < max_iterations and swapped < max_swaps:
            cost_improved = False
            iteration += 1
            
            current_total_cost = self._compute_total_cost(vg_groups, grid)
            
            for vg, group in vg_groups.items():
                if len(group) < 2:
                    continue
                
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        if swapped >= max_swaps:
                            break
                        
                        s1 = group[i]
                        s2 = group[j]
                        
                        empty_positions = []
                        for r in range(grid.rows):
                            for c in range(grid.cols):
                                if not grid.is_occupied(r, c):
                                    empty_positions.append((r, c))
                        
                        for empty_r, empty_c in empty_positions:
                            old_row, old_col = s2.row, s2.col
                            s2.row, s2.col = empty_r, empty_c
                            
                            new_total_cost = self._compute_total_cost(vg_groups, grid)
                            
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
                            
                            new_total_cost = self._compute_total_cost(vg_groups, grid)
                            
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
        
        grid.refresh_grid()


RULE_REGISTRY = {
    "satb": SATBRule(),
    "sbta": SBTARule(),
    "s1s2a1a2t1t2b1b2": S1S2A1A2T1T2B1B2Rule(),
    "s1s2b1b2t1t2a1a2": S1S2B1B2T1T2A1A2Rule(),
    "height": HeightRule(),
    "affinity": AffinityRule(),
    "voice_group_cohesion": VoiceGroupCohesionRule(),
}
