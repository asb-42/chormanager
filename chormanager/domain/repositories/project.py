"""Project repository."""

from datetime import datetime
from typing import Optional, List

from ...data.database import Database
from ..models import Project


class ProjectRepository:
    """Repository for Project operations."""

    _PROJECT_COLS = [
        "id", "name", "description", "is_active", "spielzeit",
        "created_at", "updated_at"
    ]

    _VALID_COLS = set(_PROJECT_COLS) - {"id", "created_at", "updated_at"}

    def __init__(self, db: Database):
        self.db = db

    def _validate_kwargs(self, kwargs: dict) -> None:
        invalid = set(kwargs.keys()) - self._VALID_COLS
        if invalid:
            raise ValueError(f"Invalid fields for Project: {invalid}. Valid fields: {self._VALID_COLS}")

    def create(self, **kwargs) -> Project:
        self._validate_kwargs(kwargs)
        project_id = self.db.generate_id()
        now = datetime.now().isoformat()
        kwargs["id"] = project_id
        kwargs["created_at"] = now
        kwargs["updated_at"] = now
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        self.db.execute(
            f"INSERT INTO projects ({columns}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.db.commit()
        return self.get_by_id(project_id)

    def get_by_id(self, project_id: str) -> Optional[Project]:
        result = self.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = result.fetchone()
        if row is None:
            return None
        return Project(**dict(row))

    def get_all(self) -> List[Project]:
        result = self.db.execute("SELECT * FROM projects ORDER BY name")
        return [Project(**dict(row)) for row in result.fetchall()]

    def get_active(self) -> Optional[Project]:
        result = self.db.execute("SELECT * FROM projects WHERE is_active = 1")
        row = result.fetchone()
        if row is None:
            return None
        return Project(**dict(row))

    def set_active(self, project_id: str) -> None:
        """Mark the given project as the active one.

        m6-FIX-A: both UPDATEs run inside ``db.transaction()`` so that
        concurrent calls cannot leave the database in a state with zero
        or two active projects.
        """
        with self.db.transaction():
            self.db.execute("UPDATE projects SET is_active = 0")
            self.db.execute("UPDATE projects SET is_active = 1 WHERE id = ?", (project_id,))

    def update(self, project_id: str, **kwargs) -> Optional[Project]:
        self._validate_kwargs(kwargs)
        kwargs["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        self.db.execute(
            f"UPDATE projects SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (project_id,),
        )
        self.db.commit()
        return self.get_by_id(project_id)

    def delete(self, project_id: str) -> bool:
        result = self.db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.db.commit()
        return result.rowcount > 0
