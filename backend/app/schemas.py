"""Pydantic response/request schemas (Pydantic v2)."""
from typing import Optional

from pydantic import BaseModel


class SingerOut(BaseModel):
    """Public singer shape for ``GET /api/singers*``."""

    id: str
    full_name: str
    short_name: Optional[str] = None
    voice_group: Optional[str] = None
    height: Optional[int] = None
    email: Optional[str] = None
    affinity_uuid: Optional[str] = None
