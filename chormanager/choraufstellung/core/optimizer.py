# INTEGRATION: Optimizer Engine - uses core/rules.py and core/commands.py
import time
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QUndoStack


class OptimizeFormationCommand:
    def __init__(self, grid, rule_ids: List[str]):
        self.grid = grid
        self.rule_ids = rule_ids
        self.old_positions = {}
        self.new_positions = {}
        self.swap_count = 0
        self.elapsed_ms = 0

        for s in self.grid.singers:
            self.old_positions[s.singer_id] = (s.row, s.col)

    def redo(self):
        start = time.time()
        self.swap_count = 0

        from core.rules import RULE_REGISTRY

        for rule_id in self.rule_ids:
            rule = RULE_REGISTRY.get(rule_id)
            if not rule:
                print(f"OptimizeFormationCommand: Unknown rule '{rule_id}'")
                continue

            result = rule.apply(
                self.grid.singers,
                self.grid.rows,
                self.grid.cols,
                self.grid.staggered
            )

            if hasattr(result, 'swap_count'):
                self.swap_count += result.swap_count

        self.elapsed_ms = int((time.time() - start) * 1000)

        for s in self.grid.singers:
            self.new_positions[s.singer_id] = (s.row, s.col)

        self.grid.refresh_grid()

    def undo(self):
        # R-3 Fix: tiles.clear() vor refresh_grid(), um stale-Tile-Referenzen
        # zu vermeiden, falls die Singer-Objekte zwischen redo() und undo()
        # ersetzt wurden (z. B. durch externes Reload).
        if hasattr(self.grid, "tiles") and isinstance(self.grid.tiles, dict):
            self.grid.tiles.clear()
        for s in self.grid.singers:
            if s.singer_id in self.old_positions:
                s.row, s.col = self.old_positions[s.singer_id]
        self.grid.refresh_grid()


class FormationOptimizer:
    @staticmethod
    def run(grid, rule_ids: List[str]) -> Optional[OptimizeFormationCommand]:
        if not rule_ids:
            print("FormationOptimizer: No rules selected.")
            return None

        from core.rules import RULE_REGISTRY

        selected_rules = [r for r in rule_ids if r]
        if not selected_rules:
            print("FormationOptimizer: No rules selected.")
            return None

        primary_count = sum(
            1 for rid in selected_rules
            if rid in RULE_REGISTRY and RULE_REGISTRY[rid].is_primary
        )

        if primary_count > 1:
            filtered = []
            found_primary = False
            for rid in selected_rules:
                if rid in RULE_REGISTRY and RULE_REGISTRY[rid].is_primary:
                    if not found_primary:
                        filtered.append(rid)
                        found_primary = True
                else:
                    filtered.append(rid)
            selected_rules = filtered

        # C-2 Fix: cmd.redo() wird hier NICHT mehr explizit aufgerufen.
        # ``grid.undo_stack.push(cmd)`` ruft ``cmd.redo()`` genau einmal auf
        # (via QtUndoStack.push, das die QUndoStack-Konvention emuliert).
        # Der frühere Doppel-Redo fuehrte zu swap_count=2*N und
        # inkonsistenten old/new_positions.
        cmd = OptimizeFormationCommand(grid, selected_rules)

        if hasattr(grid, 'undo_stack') and grid.undo_stack:
            grid.undo_stack.push(cmd)

        return cmd
