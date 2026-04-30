"""Repository layer for ChorManager."""

from datetime import datetime
from typing import Optional, List

from ..data.database import Database
from .models import Singer, Event, Availability, Project, Besetzung, Repertoire


class SingerRepository:
    """Repository for Singer operations."""

    _SINGER_COLS = [
        "id",
        "full_name",
        "short_name",
        "birth_date",
        "voice_group",
        "email",
        "phone",
        "gender",
        "social_contacts",
        "joined_year",
        "joined_month",
        "left_year",
        "left_month",
        "affinity_uuid",
        "created_at",
        "updated_at",
        "street",
        "postal_code",
        "city",
        "guardian1",
        "guardian1_phone",
        "guardian2",
        "guardian2_phone",
    ]

    def __init__(self, db: Database):
        """Initialize repository."""
        self.db = db

    def _cols(self, table_columns: List[str]) -> str:
        cols = [c for c in table_columns if c != "is_adult"]
        return ", ".join(cols)

    def create(self, **kwargs) -> Singer:
        """Create a new singer.

        Args:
            **kwargs: Singer fields.

        Returns:
            Singer: Created singer.
        """
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
        """Get singer by ID."""
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM singers WHERE id = ?", (singer_id,)
        )
        row = result.fetchone()

        if row is None:
            return None

        return Singer(**dict(row))

    def get_all(self) -> List[Singer]:
        """Get all singers."""
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
        """Update a singer.

        Args:
            singer_id: Singer ID.
            **kwargs: Fields to update.

        Returns:
            Singer or None if not found.
        """
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
        self.db.commit()

        # Handle bidirectional affinity synchronization
        if "affinity_uuid" in kwargs:
            new_affinity = kwargs["affinity_uuid"]
            singer_after = self.get_by_id(singer_id)
            if singer_after:
                # If there was an old affinity and it's different from new, clear the old partner's affinity
                if old_affinity and old_affinity != new_affinity:
                    old_partner = self.get_by_id(old_affinity)
                    if old_partner and old_partner.affinity_uuid == singer_id:
                        self.db.execute(
                            "UPDATE singers SET affinity_uuid = NULL, updated_at = ? WHERE id = ?",
                            (datetime.now().isoformat(), old_affinity),
                        )
                # If there is a new affinity, set the partner's affinity to this singer
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
        """Delete a singer.

        Args:
            singer_id: Singer ID.

        Returns:
            True if deleted, False if not found.
        """
        result = self.db.execute("DELETE FROM singers WHERE id = ?", (singer_id,))
        self.db.commit()

        return result.rowcount > 0

    def search(self, query: str) -> List[Singer]:
        """Search singers by name or email.

        Args:
            query: Search query.

        Returns:
            List of matching singers.
        """
        search_pattern = f"%{query}%"
        cols = self._cols(self._SINGER_COLS)
        result = self.db.execute(
            f"""SELECT {cols} FROM singers 
               WHERE full_name LIKE ? OR short_name LIKE ? OR email LIKE ?
               ORDER BY full_name""",
            (search_pattern, search_pattern, search_pattern),
        )

        return [Singer(**dict(row)) for row in result.fetchall()]


class EventRepository:
    """Repository for Event operations."""

    def __init__(self, db: Database):
        """Initialize repository.

        Args:
            db: Database instance.
        """
        self.db = db

    def create(self, **kwargs) -> Event:
        """Create a new event.

        Args:
            **kwargs: Event fields.

        Returns:
            Event: Created event.
        """
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
        """Get event by ID."""
        result = self.db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = result.fetchone()

        if row is None:
            return None

        return Event(**dict(row))

    def get_all(self) -> List[Event]:
        """Get all events."""
        result = self.db.execute("SELECT * FROM events ORDER BY date DESC")

        return [Event(**dict(row)) for row in result.fetchall()]

    def get_upcoming(self) -> List[Event]:
        """Get upcoming events."""
        now = datetime.now().isoformat()
        result = self.db.execute(
            "SELECT * FROM events WHERE date >= ? ORDER BY date", (now,)
        )

        return [Event(**dict(row)) for row in result.fetchall()]

    def update(self, event_id: str, **kwargs) -> Optional[Event]:
        """Update an event."""
        kwargs["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])

        self.db.execute(
            f"UPDATE events SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (event_id,),
        )
        self.db.commit()

        return self.get_by_id(event_id)

    def delete(self, event_id: str) -> bool:
        """Delete an event."""
        result = self.db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.db.commit()

        return result.rowcount > 0


class AvailabilityRepository:
    """Repository for Availability operations."""

    def __init__(self, db: Database):
        """Initialize repository."""
        self.db = db

    def create(self, **kwargs) -> Availability:
        """Create availability entry."""
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
        """Get availability by singer and event IDs."""
        result = self.db.execute(
            "SELECT * FROM availability WHERE singer_id = ? AND event_id = ?",
            (singer_id, event_id),
        )
        row = result.fetchone()

        if row is None:
            return None

        return Availability(**dict(row))

    def get_by_event(self, event_id: str) -> List[Availability]:
        """Get all availability for an event."""
        result = self.db.execute(
            "SELECT * FROM availability WHERE event_id = ?", (event_id,)
        )

        return [Availability(**dict(row)) for row in result.fetchall()]

    def get_by_singer(self, singer_id: str) -> List[Availability]:
        """Get all availability for a singer."""
        result = self.db.execute(
            "SELECT * FROM availability WHERE singer_id = ?", (singer_id,)
        )

        return [Availability(**dict(row)) for row in result.fetchall()]

    def update(
        self, singer_id: str, event_id: str, status: str
    ) -> Optional[Availability]:
        """Update availability status."""
        now = datetime.now().isoformat()

        result = self.db.execute(
            """INSERT INTO availability (id, singer_id, event_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(singer_id, event_id) DO UPDATE SET status = ?, updated_at = ?""",
            (self.db.generate_id(), singer_id, event_id, status, now, now, status, now),
        )
        self.db.commit()

        return self.get_by_ids(singer_id, event_id)

    def delete(self, singer_id: str, event_id: str) -> bool:
        """Delete availability entry."""
        result = self.db.execute(
            "DELETE FROM availability WHERE singer_id = ? AND event_id = ?",
            (singer_id, event_id),
        )
        self.db.commit()

        return result.rowcount > 0


class ProjectRepository:
    """Repository for Project operations."""

    def __init__(self, db: Database):
        """Initialize repository."""
        self.db = db

    def create(self, **kwargs) -> Project:
        """Create a new project."""
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
        """Get project by ID."""
        result = self.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = result.fetchone()

        if row is None:
            return None

        return Project(**dict(row))

    def get_all(self) -> List[Project]:
        """Get all projects."""
        result = self.db.execute("SELECT * FROM projects ORDER BY name")

        return [Project(**dict(row)) for row in result.fetchall()]

    def get_active(self) -> Optional[Project]:
        """Get active project."""
        result = self.db.execute("SELECT * FROM projects WHERE is_active = 1")
        row = result.fetchone()

        if row is None:
            return None

        return Project(**dict(row))

    def set_active(self, project_id: str) -> None:
        """Set a project as active."""
        self.db.execute("UPDATE projects SET is_active = 0")
        self.db.execute("UPDATE projects SET is_active = 1 WHERE id = ?", (project_id,))
        self.db.commit()

    def update(self, project_id: str, **kwargs) -> Optional[Project]:
        """Update a project."""
        kwargs["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])

        self.db.execute(
            f"UPDATE projects SET {set_clause} WHERE id = ?",
            tuple(kwargs.values()) + (project_id,),
        )
        self.db.commit()

        return self.get_by_id(project_id)

    def delete(self, project_id: str) -> bool:
        """Delete a project."""
        result = self.db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.db.commit()

        return result.rowcount > 0


class BesetzungRepository:
    """Repository for Besetzung (singer lineups)."""

    _BESETZUNG_COLS = [
        "id",
        "name",
        "project_id",
        "singer_ids",
        "created_at",
        "updated_at",
    ]

    def __init__(self, db: Database):
        """Initialize repository."""
        self.db = db

    def _cols(self, table_columns: List[str]) -> str:
        return ", ".join(table_columns)

    def create(self, name: str, project_id: str, singer_ids: List[str]) -> Besetzung:
        """Create a new besetzung.

        Args:
            name: Name of the besetzung.
            project_id: Associated project ID.
            singer_ids: List of singer IDs.

        Returns:
            Besetzung: Created besetzung.
        """
        import json

        besetzung_id = self.db.generate_id()
        now = datetime.now().isoformat()

        self.db.execute(
            "INSERT INTO besetzung (id, name, project_id, singer_ids, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (besetzung_id, name, project_id, json.dumps(singer_ids), now, now),
        )
        self.db.commit()

        return self.get_by_id(besetzung_id)

    def get_by_id(self, besetzung_id: str) -> Optional[Besetzung]:
        """Get besetzung by ID."""
        cols = self._cols(self._BESETZUNG_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM besetzung WHERE id = ?", (besetzung_id,)
        )
        row = result.fetchone()

        if row is None:
            return None

        return Besetzung(**dict(row))

    def get_all(self) -> List[Besetzung]:
        """Get all besetzungen."""
        cols = self._cols(self._BESETZUNG_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM besetzung ORDER BY updated_at DESC"
        )

        return [Besetzung(**dict(row)) for row in result.fetchall()]

    def get_by_project(self, project_id: str) -> List[Besetzung]:
        """Get all besetzungen for a project."""
        cols = self._cols(self._BESETZUNG_COLS)
        result = self.db.execute(
            f"SELECT {cols} FROM besetzung WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,),
        )

        return [Besetzung(**dict(row)) for row in result.fetchall()]

    def update(self, besetzung_id: str, **kwargs) -> Optional[Besetzung]:
        """Update a besetzung."""
        import json

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
        """Delete a besetzung."""
        result = self.db.execute("DELETE FROM besetzung WHERE id = ?", (besetzung_id,))
        self.db.commit()

        return result.rowcount > 0

    def set_active(self, project_id: str) -> None:
        """Set active besetzung for a project (most recent)."""
        self.db.execute(
            "UPDATE besetzung SET is_active = 1 WHERE project_id = ?", (project_id,)
        )
        self.db.commit()


class RepertoireRepository:
    _REPERTOIRE_COLS = [
        "id",
        "composer",
        "title",
        "dates",
        "country",
        "publisher",
        "arrangement",
        "location",
        "program",
        "created_at",
        "updated_at",
    ]

    def __init__(self, db: Database):
        self.db = db

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
        program: str = "",
    ) -> Repertoire:
        """Create a new repertoire entry.

        Args:
            composer: Composer name.
            title: Piece title.
            dates: Composer life dates.
            country: Composer country.
            publisher: Publisher name.
            arrangement: Arrangement type.
            location: Sheet music location.
            program: Associated program name.

        Returns:
            Repertoire: Created repertoire entry.
        """
        repertoire_id = self.db.generate_id()
        now = datetime.now().isoformat()

        self.db.execute(
            "INSERT INTO repertoire (id, composer, title, dates, country, publisher, arrangement, location, program, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                repertoire_id,
                composer,
                title,
                dates,
                country,
                publisher,
                arrangement,
                location,
                program,
                now,
                now,
            ),
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

    def update(self, repertoire_id: str, **kwargs) -> Optional[Repertoire]:
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
