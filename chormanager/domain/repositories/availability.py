"""Availability repository."""

from datetime import datetime
from typing import Optional, List

from ...data.database import Database
from ..models import Availability


class AvailabilityRepository:
    """Repository for Availability operations."""

    _AVAILABILITY_COLS = [
        "id", "singer_id", "event_id", "status",
        "created_at", "updated_at"
    ]

    _VALID_COLS = set(_AVAILABILITY_COLS) - {"id", "created_at", "updated_at"}

    def __init__(self, db: Database):
        self.db = db

    def _validate_kwargs(self, kwargs: dict) -> None:
        invalid = set(kwargs.keys()) - self._VALID_COLS
        if invalid:
            raise ValueError(f"Invalid fields for Availability: {invalid}. Valid fields: {self._VALID_COLS}")

    def create(self, **kwargs) -> Availability:
        self._validate_kwargs(kwargs)
        avail_id = self.db.generate_id()
        now = datetime.now().isoformat()
        kwargs["id"] = avail_id
        kwargs["created_at"] = now
        kwargs["updated_at"] = now
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        self.db.execute(
            f"INSERT INTO availability ({columns}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.db.commit()
        return self.get_by_ids(kwargs["singer_id"], kwargs["event_id"])

    def get_by_ids(self, singer_id: str, event_id: str) -> Optional[Availability]:
        result = self.db.execute(
            "SELECT * FROM availability WHERE singer_id = ? AND event_id = ?",
            (singer_id, event_id),
        )
        row = result.fetchone()
        if row is None:
            return None
        return Availability(**dict(row))

    def get_by_event(self, event_id: str) -> List[Availability]:
        result = self.db.execute(
            "SELECT * FROM availability WHERE event_id = ?", (event_id,)
        )
        return [Availability(**dict(row)) for row in result.fetchall()]

    def get_by_singer(self, singer_id: str) -> List[Availability]:
        result = self.db.execute(
            "SELECT * FROM availability WHERE singer_id = ?", (singer_id,)
        )
        return [Availability(**dict(row)) for row in result.fetchall()]

    def update(self, singer_id: str, event_id: str, status: str) -> Optional[Availability]:
        """Update availability status.

        m7-FIX-A: avoid ``ON CONFLICT ... DO UPDATE`` which would create
        a new row (with a freshly generated ``id``) on conflict. Instead
        run ``INSERT OR IGNORE`` first and then a separate ``UPDATE``
        that targets the existing row by the (singer_id, event_id) key.
        This keeps ``id`` stable across repeated calls.
        """
        now = datetime.now().isoformat()

        # Step 1: try to insert a fresh row (idempotent via OR IGNORE).
        self.db.execute(
            """INSERT OR IGNORE INTO availability
                 (id, singer_id, event_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.db.generate_id(), singer_id, event_id, status, now, now),
        )
        # Step 2: update the existing row by key. The id stays untouched.
        self.db.execute(
            """UPDATE availability
                  SET status = ?, updated_at = ?
                WHERE singer_id = ? AND event_id = ?""",
            (status, now, singer_id, event_id),
        )
        self.db.commit()
        return self.get_by_ids(singer_id, event_id)

    def delete(self, singer_id: str, event_id: str) -> bool:
        result = self.db.execute(
            "DELETE FROM availability WHERE singer_id = ? AND event_id = ?",
            (singer_id, event_id),
        )
        self.db.commit()
        return result.rowcount > 0
