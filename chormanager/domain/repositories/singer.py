"""Singer repository."""

from datetime import datetime
from typing import Optional, List

from ...data.database import Database
from ..models import Singer


class SingerRepository:
    """Repository for Singer operations."""

    _SINGER_COLS = [
        "id", "full_name", "short_name", "birth_date", "voice_group",
        "email", "phone", "gender", "social_contacts",
        "joined_year", "joined_month", "left_year", "left_month",
        "affinity_uuid", "created_at", "updated_at",
        "street", "postal_code", "city",
        "guardian1", "guardian1_phone", "guardian2", "guardian2_phone",
        "height",
    ]

    _VALID_COLS = set(_SINGER_COLS) - {"id", "created_at", "updated_at"}

    def __init__(self, db: Database):
        self.db = db

    def _cols(self, table_columns: List[str]) -> str:
        cols = [c for c in table_columns if c != "is_adult"]
        return ", ".join(cols)

    def _validate_kwargs(self, kwargs: dict) -> None:
        invalid = set(kwargs.keys()) - self._VALID_COLS
        if invalid:
            raise ValueError(f"Invalid fields for Singer: {invalid}. Valid fields: {self._VALID_COLS}")

    def create(self, **kwargs) -> Singer:
        self._validate_kwargs(kwargs)
        singer_id = self.db.generate_id()
        now = datetime.now().isoformat()
        kwargs["id"] = singer_id
        kwargs["created_at"] = now
        kwargs["updated_at"] = now
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        self.db.execute(
            f"INSERT INTO singers ({columns}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.db.commit()
        return self.get_by_id(singer_id)

    def get_by_id(self, singer_id: str) -> Optional[Singer]:
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM singers WHERE id = ?", (singer_id,)
        )
        row = result.fetchone()
        if row is None:
            return None
        return Singer(**dict(row))

    def get_all(self) -> List[Singer]:
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(f"SELECT {cols} FROM singers ORDER BY full_name")
        return [Singer(**dict(row)) for row in result.fetchall()]

    def get_by_voice_group(self, voice_group: str) -> List[Singer]:
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM singers WHERE voice_group = ? ORDER BY full_name",
            (voice_group,),
        )
        return [Singer(**dict(row)) for row in result.fetchall()]

    def get_active(self) -> List[Singer]:
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM singers WHERE left_year IS NULL ORDER BY full_name"
        )
        return [Singer(**dict(row)) for row in result.fetchall()]

    def update(self, singer_id: str, **kwargs) -> Optional[Singer]:
        self._validate_kwargs(kwargs)
        kwargs["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        old_affinity = None
        if "affinity_uuid" in kwargs:
            singer_before = self.get_by_id(singer_id)
            if singer_before:
                old_affinity = singer_before.affinity_uuid
        self.db.execute(
            f"UPDATE singers SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (singer_id,),
        )
        if "affinity_uuid" in kwargs:
            new_affinity = kwargs["affinity_uuid"]
            singer_after = self.get_by_id(singer_id)
            if singer_after:
                if old_affinity and old_affinity != new_affinity:
                    old_partner = self.get_by_id(old_affinity)
                    if old_partner and old_partner.affinity_uuid == singer_id:
                        self.db.execute(
                            "UPDATE singers SET affinity_uuid = NULL, updated_at = ? WHERE id = ?",
                            (datetime.now().isoformat(), old_affinity),
                        )
                if new_affinity:
                    new_partner = self.get_by_id(new_affinity)
                    if new_partner and new_partner.affinity_uuid != singer_id:
                        self.db.execute(
                            "UPDATE singers SET affinity_uuid = ?, updated_at = ? WHERE id = ?",
                            (singer_id, datetime.now().isoformat(), new_affinity),
                        )
        self.db.commit()
        return self.get_by_id(singer_id)

    def delete(self, singer_id: str) -> bool:
        result = self.db.execute("DELETE FROM singers WHERE id = ?", (singer_id,))
        self.db.commit()
        return result.rowcount > 0

    def search(self, query: str) -> List[Singer]:
        search_pattern = f"%{query}%"
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(
            f"""SELECT {cols} FROM singers
               WHERE full_name LIKE ? OR short_name LIKE ? OR email LIKE ?
               ORDER BY full_name""",
            (search_pattern, search_pattern, search_pattern),
        )
        return [Singer(**dict(row)) for row in result.fetchall()]
