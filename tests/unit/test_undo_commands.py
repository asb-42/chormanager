# TDD: Unit tests for Undo Commands
import pytest
from core.commands import (
    UndoStack, UndoCommand, MoveSingerCommand,
    SwapSingersCommand, MoveGroupCommand, CommandResult
)
from core.grid_engine import SingerRef


class MockSinger:
    def __init__(self, sid, row=-1, col=-1):
        self.singer_id = sid
        self.row = row
        self.col = col


class TestUndoStack:
    def test_empty_stack_cannot_undo(self, empty_undo_stack):
        """Empty stack should not allow undo."""
        assert empty_undo_stack.can_undo() is False

    def test_empty_stack_cannot_redo(self, empty_undo_stack):
        """Empty stack should not allow redo."""
        assert empty_undo_stack.can_redo() is False

    def test_push_enables_undo(self, empty_undo_stack):
        """Pushing a command should enable undo."""
        cmd = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: MockSinger(sid), lambda: None)
        empty_undo_stack.push(cmd)
        assert empty_undo_stack.can_undo() is True

    def test_undo_disables_redo(self, empty_undo_stack):
        """After undo, redo should be enabled (standard undo/redo behavior)."""
        cmd = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: MockSinger(sid), lambda: None)
        empty_undo_stack.push(cmd)
        empty_undo_stack.undo()
        assert empty_undo_stack.can_redo() is True
        assert empty_undo_stack.can_undo() is False

    def test_redo_after_undo(self, empty_undo_stack):
        """After undo, redo should re-execute the command."""
        singer = MockSinger("s1", 0, 0)
        cmd = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: singer, lambda: None)
        empty_undo_stack.push(cmd)
        empty_undo_stack.undo()
        empty_undo_stack.redo()
        assert singer.row == 1
        assert singer.col == 1

    def test_multiple_undo_levels(self, empty_undo_stack):
        """Should support multiple undo levels."""
        singers = {"s1": MockSinger("s1", 0, 0), "s2": MockSinger("s2", 0, 1)}
        cmd1 = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: singers[sid], lambda: None)
        cmd2 = MoveSingerCommand("s2", 0, 1, 2, 2, lambda sid: singers[sid], lambda: None)
        empty_undo_stack.push(cmd1)
        empty_undo_stack.push(cmd2)
        
        empty_undo_stack.undo()
        assert singers["s2"].row == 0
        assert singers["s2"].col == 1
        
        empty_undo_stack.undo()
        assert singers["s1"].row == 0
        assert singers["s1"].col == 0

    def test_push_clears_redo_history(self, empty_undo_stack):
        """Pushing after undo should clear redo history."""
        singers = {"s1": MockSinger("s1", 0, 0)}
        cmd1 = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: singers[sid], lambda: None)
        cmd2 = MoveSingerCommand("s1", 0, 0, 2, 2, lambda sid: singers[sid], lambda: None)
        empty_undo_stack.push(cmd1)
        empty_undo_stack.undo()
        empty_undo_stack.push(cmd2)
        assert empty_undo_stack.can_redo() is False

    def test_stack_count(self, empty_undo_stack):
        """Should return correct stack count."""
        singers = {"s1": MockSinger("s1", 0, 0)}
        cmd1 = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: singers[sid], lambda: None)
        cmd2 = MoveSingerCommand("s1", 0, 0, 2, 2, lambda sid: singers[sid], lambda: None)
        empty_undo_stack.push(cmd1)
        empty_undo_stack.push(cmd2)
        assert empty_undo_stack.count() == 2

    def test_clear_stack(self, empty_undo_stack):
        """Should clear all commands from stack."""
        singers = {"s1": MockSinger("s1", 0, 0)}
        cmd = MoveSingerCommand("s1", 0, 0, 1, 1, lambda sid: singers[sid], lambda: None)
        empty_undo_stack.push(cmd)
        empty_undo_stack.clear()
        assert empty_undo_stack.can_undo() is False
        assert empty_undo_stack.count() == 0


class TestMoveSingerCommand:
    def test_move_singer_redo(self):
        """Redo should move singer to new position."""
        singer = MockSinger("s1", 0, 0)
        refresh_called = False
        def refresh(): nonlocal refresh_called; refresh_called = True
        
        cmd = MoveSingerCommand("s1", 0, 0, 2, 3, lambda sid: singer, refresh)
        cmd.redo()
        
        assert singer.row == 2
        assert singer.col == 3
        assert refresh_called is True

    def test_move_singer_undo(self):
        """Undo should restore original position."""
        singer = MockSinger("s1", 0, 0)
        refresh_called = []
        
        def refresh(): refresh_called.append(1)
        
        cmd = MoveSingerCommand("s1", 0, 0, 2, 3, lambda sid: singer, refresh)
        cmd.redo()
        cmd.undo()
        
        assert singer.row == 0
        assert singer.col == 0

    def test_move_singer_not_found(self):
        """Should handle singer not found gracefully - no refresh called."""
        def get_singer(sid): return None
        refresh_called = []
        def refresh(): refresh_called.append(1)
        
        cmd = MoveSingerCommand("nonexistent", 0, 0, 2, 3, get_singer, refresh)
        cmd.redo()
        cmd.undo()
        assert len(refresh_called) == 0


class TestSwapSingersCommand:
    def test_swap_singers_redo(self):
        """Redo should swap positions of two singers."""
        s1 = MockSinger("s1", 0, 0)
        s2 = MockSinger("s2", 1, 1)
        singers = {"s1": s1, "s2": s2}
        
        refresh_called = []
        def refresh(): refresh_called.append(1)
        
        cmd = SwapSingersCommand("s1", "s2", lambda sid: singers[sid], refresh)
        cmd.redo()
        
        assert s1.row == 1
        assert s1.col == 1
        assert s2.row == 0
        assert s2.col == 0

    def test_swap_singers_undo(self):
        """Undo should restore original positions."""
        s1 = MockSinger("s1", 0, 0)
        s2 = MockSinger("s2", 1, 1)
        singers = {"s1": s1, "s2": s2}
        
        def refresh(): pass
        
        cmd = SwapSingersCommand("s1", "s2", lambda sid: singers[sid], refresh)
        cmd.redo()
        cmd.undo()
        
        assert s1.row == 0
        assert s1.col == 0
        assert s2.row == 1
        assert s2.col == 1

    def test_swap_same_singer_redo(self):
        """Should handle swapping singer with itself."""
        s1 = MockSinger("s1", 0, 0)
        singers = {"s1": s1}
        
        def refresh(): pass
        
        cmd = SwapSingersCommand("s1", "s1", lambda sid: singers[sid], refresh)
        cmd.redo()
        
        assert s1.row == 0
        assert s1.col == 0


class TestMoveGroupCommand:
    def test_move_group_redo(self):
        """Redo should move all singers by delta."""
        singers = {
            "s1": MockSinger("s1", 0, 0),
            "s2": MockSinger("s2", 0, 1),
            "s3": MockSinger("s3", 1, 0),
        }
        refresh_called = []
        def refresh(): refresh_called.append(1)
        
        cmd = MoveGroupCommand(
            ["s1", "s2", "s3"], 1, 1,
            lambda sid: singers[sid],
            lambda: list(singers.values()),
            refresh
        )
        cmd.redo()
        
        assert singers["s1"].row == 1
        assert singers["s1"].col == 1
        assert singers["s2"].row == 1
        assert singers["s2"].col == 2
        assert singers["s3"].row == 2
        assert singers["s3"].col == 1

    def test_move_group_undo(self):
        """Undo should restore all original positions."""
        singers = {
            "s1": MockSinger("s1", 0, 0),
            "s2": MockSinger("s2", 0, 1),
        }
        def refresh(): pass
        
        cmd = MoveGroupCommand(
            ["s1", "s2"], 2, 1,
            lambda sid: singers[sid],
            lambda: list(singers.values()),
            refresh
        )
        cmd.redo()
        cmd.undo()
        
        assert singers["s1"].row == 0
        assert singers["s1"].col == 0
        assert singers["s2"].row == 0
        assert singers["s2"].col == 1

    def test_move_group_partial_not_found(self):
        """Should handle missing singers gracefully."""
        singers = {"s1": MockSinger("s1", 0, 0)}
        def get_singer(sid): return singers.get(sid)
        def get_all(): return list(singers.values())
        def refresh(): pass
        
        cmd = MoveGroupCommand(
            ["s1", "nonexistent"], 1, 1,
            get_singer, get_all, refresh
        )
        cmd.redo()
        cmd.undo()
        
        assert singers["s1"].row == 0
        assert singers["s1"].col == 0

    def test_move_group_stores_old_positions(self):
        """Should store old positions for undo."""
        singers = {"s1": MockSinger("s1", 3, 4)}
        def get_singer(sid): return singers[sid]
        def get_all(): return list(singers.values())
        def refresh(): pass
        
        cmd = MoveGroupCommand(
            ["s1"], 1, 2,
            get_singer, get_all, refresh
        )
        
        old_positions = cmd.get_old_positions()
        assert old_positions["s1"] == (3, 4)


class TestCommandResult:
    def test_command_result_success(self):
        """Should create successful command result."""
        result = CommandResult(success=True, message="OK", data={"x": 1})
        assert result.success is True
        assert result.message == "OK"
        assert result.data == {"x": 1}

    def test_command_result_failure(self):
        """Should create failed command result."""
        result = CommandResult(success=False, message="Error occurred")
        assert result.success is False
        assert result.message == "Error occurred"