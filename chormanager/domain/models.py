"""Domain models for ChorManager."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any


@dataclass
class Singer:
    """Singer model."""

    id: str = ""
    full_name: str = ""
    short_name: Optional[str] = None
    birth_date: Optional[str] = None
    voice_group: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    guardian1: Optional[str] = None
    guardian1_phone: Optional[str] = None
    guardian2: Optional[str] = None
    guardian2_phone: Optional[str] = None
    _is_adult: Optional[int] = None
    social_contacts: Optional[str] = None
    joined_year: Optional[int] = None
    joined_month: Optional[int] = None
    left_year: Optional[int] = None
    left_month: Optional[int] = None
    affinity_uuid: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    address: Optional[str] = None  # Legacy: Kombination aus street + city

    def is_adult(self) -> bool:
        """Check if singer is 18 years or older."""
        if self._is_adult is not None:
            return bool(self._is_adult)
        if not self.birth_date:
            return False
        try:
            birth = datetime.strptime(self.birth_date[:10], "%Y-%m-%d")
            age = (datetime.now() - birth).days / 365.25
            return age >= 18
        except (ValueError, OSError):
            return False

    def age(self) -> Optional[int]:
        """Return age in years, or None if no birth_date."""
        if not self.birth_date:
            return None
        try:
            birth = datetime.strptime(self.birth_date[:10], "%Y-%m-%d")
            return int((datetime.now() - birth).days / 365.25)
        except (ValueError, OSError):
            return None

    def compute_is_adult(self) -> int:
        """Compute is_adult from birth_date."""
        if not self.birth_date:
            return 0
        try:
            birth = datetime.strptime(self.birth_date[:10], "%Y-%m-%d")
            age = (datetime.now() - birth).days / 365.25
            return 1 if age >= 18 else 0
        except (ValueError, OSError):
            return 0

    def __post_init__(self):
        """Set timestamps if not set."""
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def joined_display(self) -> str:
        """Get display string for joined date."""
        if self.joined_year and self.joined_month:
            return f"{self.joined_month:02d}/{self.joined_year}"
        elif self.joined_year:
            return str(self.joined_year)
        return ""

    @property
    def left_display(self) -> str:
        """Get display string for left date."""
        if self.left_year and self.left_month:
            return f"{self.left_month:02d}/{self.left_year}"
        elif self.left_year:
            return str(self.left_year)
        return ""

    @property
    def social_contacts_dict(self) -> dict:
        """Get social contacts as dictionary."""
        if not self.social_contacts:
            return {}
        try:
            return json.loads(self.social_contacts)
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            dict: Dictionary representation.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Singer":
        """Create Singer from dictionary.

        Args:
            data: Dictionary with singer data.

        Returns:
            Singer: Singer instance.
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Event:
    """Event model for rehearsals and concerts."""

    id: str = ""
    name: str = ""
    date: str = ""
    event_type: str = ""
    location: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        """Set timestamps if not set."""
        from datetime import datetime

        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def is_past(self) -> bool:
        """Check if event is in the past."""
        try:
            event_date = datetime.fromisoformat(self.date)
            return event_date < datetime.now()
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """Create Event from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Project:
    """Project model for managing concert projects."""

    id: str = ""
    name: str = ""
    description: Optional[str] = None
    is_active: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        """Set timestamps and ID if not set."""
        from datetime import datetime

        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())

    def __post_init__(self):
        """Set timestamps if not set."""
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def is_past(self) -> bool:
        """Check if event is in the past."""
        try:
            event_date = datetime.fromisoformat(self.date)
            return event_date < datetime.now()
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """Create Event from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Availability:
    """Availability for an event."""

    id: str = ""
    singer_id: str = ""
    event_id: str = ""
    status: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        """Set timestamps if not set."""
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Availability":
        """Create Availability from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
