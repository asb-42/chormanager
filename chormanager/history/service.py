"""History service for Undo/Redo functionality."""

from typing import Protocol, Optional, List
from collections import deque


class Command(Protocol):
    """Command protocol for undo/redo."""
    
    def execute(self) -> None:
        """Execute the command."""
        ...
    
    def undo(self) -> None:
        """Undo the command."""
        ...
    
    def redo(self) -> None:
        """Redo the command."""
        ...


class HistoryService:
    """Service for managing undo/redo history."""
    
    def __init__(self, max_entries: int = 100):
        """Initialize history service.
        
        Args:
            max_entries: Maximum number of history entries.
        """
        self._max_entries = max_entries
        self._undo_stack: deque = deque()
        self._redo_stack: deque = deque()
    
    def add(self, command: Command) -> None:
        """Add a command to history.
        
        Args:
            command: Command to add.
        """
        self._undo_stack.append(command)
        self._redo_stack.clear()
        
        while len(self._undo_stack) > self._max_entries:
            self._undo_stack.popleft()
    
    def undo(self) -> Optional[Command]:
        """Undo the last command.
        
        Returns:
            Command that was undone, or None if nothing to undo.
        """
        if not self.can_undo():
            return None
        
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        
        return command
    
    def redo(self) -> Optional[Command]:
        """Redo the last undone command.
        
        Returns:
            Command that was redone, or None if nothing to redo.
        """
        if not self.can_redo():
            return None
        
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        
        return command
    
    def can_undo(self) -> bool:
        """Check if undo is available.
        
        Returns:
            True if undo is available.
        """
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available.
        
        Returns:
            True if redo is available.
        """
        return len(self._redo_stack) > 0
    
    def clear(self) -> None:
        """Clear all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    def __len__(self) -> int:
        """Get number of commands in history."""
        return len(self._undo_stack)


class CreateSingerCommand:
    """Command for creating a singer."""
    
    def __init__(self, repository, singer_data: dict):
        """Initialize command.
        
        Args:
            repository: SingerRepository instance.
            singer_data: Singer data dictionary.
        """
        self._repository = repository
        self._singer_data = singer_data
        self._created_singer = None
    
    def execute(self) -> None:
        """Execute the command."""
        self._created_singer = self._repository.create(**self._singer_data)
    
    def undo(self) -> None:
        """Undo the command."""
        if self._created_singer:
            self._repository.delete(self._created_singer.id)
    
    def redo(self) -> None:
        """Redo the command."""
        if self._created_singer:
            self._created_singer = self._repository.create(**self._singer_data)


class UpdateSingerCommand:
    """Command for updating a singer."""
    
    def __init__(self, repository, singer_id: str, updates: dict):
        """Initialize command.
        
        Args:
            repository: SingerRepository instance.
            singer_id: Singer ID.
            updates: Updates dictionary.
        """
        self._repository = repository
        self._singer_id = singer_id
        self._updates = updates
        self._old_data = None
    
    def execute(self) -> None:
        """Execute the command."""
        self._old_data = self._repository.get_by_id(self._singer_id)
        if self._old_data:
            self._old_data = self._old_data.to_dict()
        self._repository.update(self._singer_id, **self._updates)
    
    def undo(self) -> None:
        """Undo the command."""
        if self._old_data:
            self._repository.update(self._singer_id, **self._old_data)
    
    def redo(self) -> None:
        """Redo the command."""
        self._repository.update(self._singer_id, **self._updates)


class DeleteSingerCommand:
    """Command for deleting a singer."""
    
    def __init__(self, repository, singer_id: str):
        """Initialize command.
        
        Args:
            repository: SingerRepository instance.
            singer_id: Singer ID.
        """
        self._repository = repository
        self._singer_id = singer_id
        self._deleted_singer = None
    
    def execute(self) -> None:
        """Execute the command."""
        self._deleted_singer = self._repository.get_by_id(self._singer_id)
        if self._deleted_singer:
            self._deleted_singer = self._deleted_singer.to_dict()
        self._repository.delete(self._singer_id)
    
    def undo(self) -> None:
        """Undo the command."""
        if self._deleted_singer:
            self._deleted_singer = self._repository.create(**self._deleted_singer)
    
    def redo(self) -> None:
        """Redo the command."""
        self._repository.delete(self._singer_id)
