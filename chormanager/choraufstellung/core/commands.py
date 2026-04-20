# TESTABLE: Pure Python undo/redo commands, Qt-agnostic where possible
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any


@dataclass
class CommandResult:
    success: bool
    message: str = ""
    data: Any = None


class UndoCommand(ABC):
    def __init__(self, description: str = ""):
        self.description = description
        self._executed = False

    @abstractmethod
    def redo(self) -> None:
        pass

    @abstractmethod
    def undo(self) -> None:
        pass

    def execute(self) -> CommandResult:
        try:
            self.redo()
            self._executed = True
            return CommandResult(success=True)
        except Exception as e:
            return CommandResult(success=False, message=str(e))


class MoveSingerCommand(UndoCommand):
    def __init__(self, singer_id: str, old_row: int, old_col: int, 
                 new_row: int, new_col: int, get_singer_fn, refresh_fn):
        super().__init__("Sänger verschoben")
        self.singer_id = singer_id
        self.old_row = old_row
        self.old_col = old_col
        self.new_row = new_row
        self.new_col = new_col
        self._get_singer = get_singer_fn
        self._refresh = refresh_fn

    def redo(self) -> None:
        singer = self._get_singer(self.singer_id)
        if singer:
            singer.row = self.new_row
            singer.col = self.new_col
            self._refresh()

    def undo(self) -> None:
        singer = self._get_singer(self.singer_id)
        if singer:
            singer.row = self.old_row
            singer.col = self.old_col
            self._refresh()


class SwapSingersCommand(UndoCommand):
    def __init__(self, singer1_id: str, singer2_id: str, get_singer_fn, refresh_fn):
        super().__init__("Positionen getauscht")
        self.singer1_id = singer1_id
        self.singer2_id = singer2_id
        self._get_singer = get_singer_fn
        self._refresh = refresh_fn

        s1 = self._get_singer(singer1_id)
        s2 = self._get_singer(singer2_id)
        self._old_row1 = s1.row if s1 else -1
        self._old_col1 = s1.col if s1 else -1
        self._old_row2 = s2.row if s2 else -1
        self._old_col2 = s2.col if s2 else -1

    def redo(self) -> None:
        s1 = self._get_singer(self.singer1_id)
        s2 = self._get_singer(self.singer2_id)
        if s1 and s2:
            s1.row, s2.row = self._old_row2, self._old_row1
            s1.col, s2.col = self._old_col2, self._old_col1
            self._refresh()

    def undo(self) -> None:
        s1 = self._get_singer(self.singer1_id)
        s2 = self._get_singer(self.singer2_id)
        if s1 and s2:
            s1.row, s2.row = self._old_row1, self._old_row2
            s1.col, s2.col = self._old_col1, self._old_col2
            self._refresh()


@dataclass
class MoveGroupState:
    singer_id: str
    old_row: int
    old_col: int


class MoveGroupCommand(UndoCommand):
    def __init__(self, singer_ids: List[str], dx: int, dy: int, 
                 get_singer_fn, all_singers_getter, refresh_fn):
        super().__init__("Gruppe verschoben")
        self.singer_ids = singer_ids
        self.dx = dx
        self.dy = dy
        self._get_singer = get_singer_fn
        self._get_all_singers = all_singers_getter
        self._refresh = refresh_fn
        self._old_positions: Dict[str, Tuple[int, int]] = {}

        for sid in self.singer_ids:
            singer = self._get_singer(sid)
            if singer:
                self._old_positions[sid] = (singer.row, singer.col)

    def redo(self) -> None:
        for sid in self.singer_ids:
            singer = self._get_singer(sid)
            if singer:
                singer.row += self.dy
                singer.col += self.dx
        self._refresh()

    def undo(self) -> None:
        for sid in self.singer_ids:
            singer = self._get_singer(sid)
            if singer and sid in self._old_positions:
                singer.row, singer.col = self._old_positions[sid]
        self._refresh()

    def get_old_positions(self) -> Dict[str, Tuple[int, int]]:
        return self._old_positions.copy()

    def get_delta(self) -> Tuple[int, int]:
        return (self.dx, self.dy)


class UndoStack:
    def __init__(self):
        self._stack: List[UndoCommand] = []
        self._index: int = 0
        self._clean_state: int = 0
        self._can_undo_changed: bool = False
        self._can_redo_changed: bool = False

    def push(self, command: UndoCommand) -> None:
        while len(self._stack) > self._index:
            self._stack.pop()

        self._stack.append(command)
        self._index += 1

        if self._can_undo_changed:
            self._can_undo_changed = len(self._stack) > 0 and self._index > 0
        if self._can_redo_changed:
            self._can_redo_changed = self._index < len(self._stack)

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self._index -= 1
        self._stack[self._index].undo()
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self._stack[self._index].redo()
        self._index += 1
        return True

    def can_undo(self) -> bool:
        return self._index > 0

    def can_redo(self) -> bool:
        return self._index < len(self._stack)

    def clear(self) -> None:
        self._stack.clear()
        self._index = 0

    def set_clean_state(self) -> None:
        self._clean_state = self._index

    def is_clean(self) -> bool:
        return self._index == self._clean_state

    def count(self) -> int:
        return len(self._stack)

    def index(self) -> int:
        return self._index

    def get_command(self, idx: int) -> Optional[UndoCommand]:
        if 0 <= idx < len(self._stack):
            return self._stack[idx]
        return None

    def on_can_undo_changed(self, callback) -> None:
        self._can_undo_changed = callback

    def on_can_redo_changed(self, callback) -> None:
        self._can_redo_changed = callback