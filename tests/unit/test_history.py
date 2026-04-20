"""Tests for Undo/Redo history service."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestHistoryService:
    """Tests for HistoryService."""

    def test_add_command(self):
        """Test adding a command to history."""
        from chormanager.history.service import HistoryService
        
        service = HistoryService(max_entries=10)
        
        class TestCommand:
            def __init__(self):
                self.executed = False
                self.undone = False
            
            def execute(self):
                self.executed = True
            
            def undo(self):
                self.undone = True
        
        cmd = TestCommand()
        service.add(cmd)
        
        assert len(service) == 1

    def test_undo(self):
        """Test undoing a command."""
        from chormanager.history.service import HistoryService
        
        service = HistoryService(max_entries=10)
        
        class TestCommand:
            def __init__(self):
                self.executed = False
                self.undone = False
            
            def execute(self):
                self.executed = True
            
            def undo(self):
                self.undone = True
        
        cmd = TestCommand()
        cmd.execute()  # Execute first
        service.add(cmd)
        service.undo()
        
        assert cmd.executed is True
        assert cmd.undone is True
        assert len(service) == 0

    def test_redo(self):
        """Test redoing a command."""
        from chormanager.history.service import HistoryService
        
        service = HistoryService(max_entries=10)
        
        class TestCommand:
            def __init__(self):
                self.executed = False
                self.redone = False
            
            def execute(self):
                self.executed = True
            
            def undo(self):
                pass
            
            def redo(self):
                self.redone = True
        
        cmd = TestCommand()
        service.add(cmd)
        service.undo()
        service.redo()
        
        assert cmd.redone is True

    def test_max_entries(self):
        """Test max entries limit."""
        from chormanager.history.service import HistoryService
        
        service = HistoryService(max_entries=3)
        
        class TestCommand:
            def __init__(self, name):
                self.name = name
            
            def execute(self):
                pass
            
            def undo(self):
                pass
        
        service.add(TestCommand("1"))
        service.add(TestCommand("2"))
        service.add(TestCommand("3"))
        service.add(TestCommand("4"))
        
        assert len(service) == 3

    def test_clear(self):
        """Test clearing history."""
        from chormanager.history.service import HistoryService
        
        service = HistoryService(max_entries=10)
        
        class TestCommand:
            def __init__(self):
                pass
            
            def execute(self):
                pass
            
            def undo(self):
                pass
        
        service.add(TestCommand())
        service.add(TestCommand())
        
        service.clear()
        
        assert len(service) == 0

    def test_can_undo_redo(self):
        """Test can_undo and can_redo properties."""
        from chormanager.history.service import HistoryService
        
        service = HistoryService(max_entries=10)
        
        class TestCommand:
            def __init__(self):
                pass
            
            def execute(self):
                pass
            
            def undo(self):
                pass
        
        assert service.can_undo() is False
        assert service.can_redo() is False
        
        service.add(TestCommand())
        
        assert service.can_undo() is True
        assert service.can_redo() is False
