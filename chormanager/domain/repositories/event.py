"""Event repository."""

from datetime import datetime
from typing import Optional, List

from ...data.database import Database
from ..models import Event


class EventRepository:
    """Repository for Event operations."""

    _EVENT_COLS = [
        "id", "name", "date", "event_type", "location", "description",
        "project_id", "created_at", "updated_at"
    ]

    _VALID_COLS = set(_EVENT_COLS) - {"id", "created_at", "updated_at"}

    def __init__(self, db: Database):
        self.db = db

    def _validate_kwargs(self, kwargs: dict) -> None:
        invalid = set(kwargs.keys()) - self._VALID_COLS
        if invalid:
            raise ValueError(f"Invalid fields for Event: {invalid}. Valid fields: {self._VALID_COLS}")

    def create(self, **kwargs) -> Event:
        self._validate_kwargs(kwargs)
        event_id = self.db.generate_id()
        now = datetime.now().isoformat()
        kwargs["id"] = event_id
        kwargs["created_at"] = now
        kwargs["updated_at"] = now
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        self.db.execute(
            f"INSERT INTO events ({columns}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.db.commit()
        return self.get_by_id(event_id)

    def get_by_id(self, event_id: str) -> Optional[Event]:
        result = self.db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = result.fetchone()
        if row is None:
            return None
        return Event(**dict(row))

    def get_all(self) -> List[Event]:
        result = self.db.execute("SELECT * FROM events ORDER BY date DESC")
        return [Event(**dict(row)) for row in result.fetchall()]

    def get_upcoming(self) -> List[Event]:
        now = datetime.now().isoformat()
        result = self.db.execute(
            "SELECT * FROM events WHERE date >= ? ORDER BY date", (now,)
        )
        return [Event(**dict(row)) for row in result.fetchall()]

    def update(self, event_id: str, **kwargs) -> Optional[Event]:
        self._validate_kwargs(kwargs)
        kwargs["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        self.db.execute(
            f"UPDATE events SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (event_id,),
        )
        self.db.commit()
        return self.get_by_id(event_id)

    def delete(self, event_id: str) -> bool:
        result = self.db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.db.commit()
        return result.rowcount > 0
