try:
    import time
    from PyQt6.QtWidgets import QUndoCommand
except ImportError:
    import time
    from PyQt5.QtWidgets import QUndoCommand


# OPTIMIZER: Command that wraps the entire optimization sequence for undo/redo
class OptimizeFormationCommand(QUndoCommand):
    def __init__(self, grid, rule_ids):
        super().__init__()
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

        from optimizer_rules import RULE_REGISTRY

        for rule_id in self.rule_ids:
            rule = RULE_REGISTRY.get(rule_id)
            if not rule:
                print(f"OptimizeFormationCommand: Unbekannte Regel '{rule_id}'")
                continue

            rule.apply(self.grid, self.grid.singers)

        self.elapsed_ms = int((time.time() - start) * 1000)

        for s in self.grid.singers:
            self.new_positions[s.singer_id] = (s.row, s.col)

        self.grid.refresh_grid()

    def undo(self):
        for s in self.grid.singers:
            if s.singer_id in self.old_positions:
                s.row, s.col = self.old_positions[s.singer_id]
        self.grid.refresh_grid()


# OPTIMIZER: Engine that validates and runs optimization rules
class FormationOptimizer:
    @staticmethod
    def run(grid, rule_ids):
        if not rule_ids:
            print("FormationOptimizer: Keine Regeln ausgewählt.")
            return None

        from optimizer_rules import RULE_REGISTRY

        selected_rules = [r for r in rule_ids if r]
        if not selected_rules:
            print("FormationOptimizer: Keine Regeln ausgewählt.")
            return None

        primary_count = sum(
            1 for rid in selected_rules
            if rid in RULE_REGISTRY and RULE_REGISTRY[rid].is_primary
        )

        if primary_count > 1:
            print("FormationOptimizer: Mehr als eine Primary-Regel ausgewählt. Nur die erste wird angewendet.")
            first_primary = None
            filtered = []
            found_primary = False
            for rid in selected_rules:
                if rid in RULE_REGISTRY and RULE_REGISTRY[rid].is_primary:
                    if not found_primary:
                        first_primary = rid
                        filtered.append(rid)
                        found_primary = True
                else:
                    filtered.append(rid)
            selected_rules = filtered

        cmd = OptimizeFormationCommand(grid, selected_rules)
        cmd.redo()
        grid.undo_stack.push(cmd)

        return cmd
