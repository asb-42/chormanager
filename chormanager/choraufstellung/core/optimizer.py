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

        cmd = OptimizeFormationCommand(grid, selected_rules)
        cmd.redo()

        if hasattr(grid, 'undo_stack') and grid.undo_stack:
            grid.undo_stack.push(cmd)

        return cmd
