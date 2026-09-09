"""Repertoire repository."""

from datetime import datetime
from typing import Optional, List

from ...data.database import Database
from ..models import Repertoire


class RepertoireRepository:
    """Repository for Repertoire operations."""

    _REPERTOIRE_COLS = [
        "id", "composer", "title", "dates", "country",
        "publisher", "arrangement", "location", "project_id",
        "created_at", "updated_at",
    ]

    _VALID_COLS = set(_REPERTOIRE_COLS) - {"id", "created_at", "updated_at"}

    def __init__(self, db: Database):
        self.db = db

    def _validate_kwargs(self, kwargs: dict) -> None:
        invalid = set(kwargs.keys()) - self._VALID_COLS
        if invalid:
            raise ValueError(f"Invalid fields for Repertoire: {invalid}. Valid fields: {self._VALID_COLS}")

    def _cols(self, table_columns: List[str]) -> str:
        return ", ".join(table_columns)

    def create(
        self,
        composer: str,
        title: str,
        dates: str = "",
        country: str = "",
        publisher: str = "",
        arrangement: str = "",
        location: str = "",
        project_id: str = "",
    ) -> Repertoire:
        repertoire_id = self.db.generate_id()
        now = datetime.now().isoformat()
        self.db.execute(
            "INSERT INTO repertoire (id, composer, title, dates, country, publisher, arrangement, location, project_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (repertoire_id, composer, title, dates, country, publisher, arrangement, location, project_id, now, now),
        )
        self.db.commit()
        return self.get_by_id(repertoire_id)

    def get_by_id(self, repertoire_id: str) -> Optional[Repertoire]:
        cols = self._cols(self._REPERTOIRE_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM repertoire WHERE id = ?", (repertoire_id,)
        )
        row = result.fetchone()
        if row is None:
            return None
        return Repertoire(**dict(row))

    def get_all(self) -> List[Repertoire]:
        cols = self._cols(self._REPERTOIRE_COLS)
        result = self.db.execute(f"SELECT {cols} FROM repertoire ORDER BY title ASC")
        return [Repertoire(**dict(row)) for row in result.fetchall()]

    def get_by_project_id(self, project_id: str) -> List[Repertoire]:
        cols = self._cols(self._REPERTOIRE_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM repertoire WHERE project_id = ? ORDER BY composer, title",
            (project_id,),
        )
        return [Repertoire(**dict(row)) for row in result.fetchall()]

    def update(self, repertoire_id: str, **kwargs) -> Optional[Repertoire]:
        self._validate_kwargs(kwargs)
        kwargs["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        self.db.execute(
            f"UPDATE repertoire SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (repertoire_id,),
        )
        self.db.commit()
        return self.get_by_id(repertoire_id)

    def delete(self, repertoire_id: str) -> bool:
        result = self.db.execute(
            "DELETE FROM repertoire WHERE id = ?", (repertoire_id,)
        )
        self.db.commit()
        return result.rowcount > 0
