"""Besetzung repository."""

import json
from datetime import datetime
from typing import Optional, List

from ...data.database import Database
from ..models import Besetzung


class BesetzungRepository:
    """Repository for Besetzung (singer lineups)."""

    _BESETZUNG_COLS = [
        "id", "name", "project_id", "singer_ids",
        "created_at", "updated_at",
    ]

    _VALID_COLS = set(_BESETZUNG_COLS) - {"id", "created_at", "updated_at"}

    def __init__(self, db: Database):
        self.db = db

    def _validate_kwargs(self, kwargs: dict) -> None:
        invalid = set(kwargs.keys()) - self._VALID_COLS
        if invalid:
            raise ValueError(f"Invalid fields for Besetzung: {invalid}. Valid fields: {self._VALID_COLS}")

    def _cols(self, table_columns: List[str]) -> str:
        return ", ".join(table_columns)

    def create(self, name: str, project_id: str, singer_ids: List[str]) -> Besetzung:
        besetzung_id = self.db.generate_id()
        now = datetime.now().isoformat()
        self.db.execute(
            "INSERT INTO besetzung (id, name, project_id, singer_ids, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (besetzung_id, name, project_id, json.dumps(singer_ids), now, now),
        )
        self.db.commit()
        return self.get_by_id(besetzung_id)

    def get_by_id(self, besetzung_id: str) -> Optional[Besetzung]:
        cols = self._cols(self._BESETZUNG_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM besetzung WHERE id = ?", (besetzung_id,)
        )
        row = result.fetchone()
        if row is None:
            return None
        return Besetzung(**dict(row))

    def get_all(self) -> List[Besetzung]:
        cols = self._cols(self._BESETZUNG_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM besetzung ORDER BY updated_at DESC"
        )
        return [Besetzung(**dict(row)) for row in result.fetchall()]

    def get_by_project(self, project_id: str) -> List[Besetzung]:
        cols = self._cols(self._BESETZUNG_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM besetzung WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,),
        )
        return [Besetzung(**dict(row)) for row in result.fetchall()]

    def update(self, besetzung_id: str, **kwargs) -> Optional[Besetzung]:
        self._validate_kwargs(kwargs)
        kwargs["updated_at"] = datetime.now().isoformat()
        if "singer_ids" in kwargs and isinstance(kwargs["singer_ids"], list):
            kwargs["singer_ids"] = json.dumps(kwargs["singer_ids"])
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        self.db.execute(
            f"UPDATE besetzung SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (besetzung_id,),
        )
        self.db.commit()
        return self.get_by_id(besetzung_id)

    def delete(self, besetzung_id: str) -> bool:
        result = self.db.execute("DELETE FROM besetzung WHERE id = ?", (besetzung_id,))
        self.db.commit()
        return result.rowcount > 0

    def set_active(self, project_id: str) -> None:
        """Set active besetzung for a project (most recent)."""
        self.db.execute(
            "UPDATE besetzung SET is_active = 1 WHERE project_id = ?", (project_id,)
        )
        self.db.commit()
