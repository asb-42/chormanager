"""Config endpoints: voice groups merged (M1 read).

Gruppenliste aus ``config/voice_groups.yaml``
(``chormanager.config.load_voice_groups``), Theme-Farben aus
``config/voice_groups.json``. Schreibende Pflege (PUT + Admin-UI)
folgt mit dem M1-Config-Ausbau; Formatfrage ist per §5.4 egal.
"""
import json
from typing import List, Optional

from chormanager.config import CONFIG_DIR, load_voice_groups
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.engine import Connection

from ..deps import get_db

router = APIRouter(prefix="/api/config", tags=["config"])

_FALLBACK_COLOR = "#cccccc"


class VoiceGroupOut(BaseModel):
    """Stimmgruppe mit Hell/Dunkel-Farben."""

    id: str
    short: Optional[str] = None
    order: Optional[int] = None
    color_light: str = _FALLBACK_COLOR
    color_dark: str = _FALLBACK_COLOR


def _theme_colors() -> dict:
    try:
        data = json.loads(
            (CONFIG_DIR / "voice_groups.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return {}
    themes = data.get("themes", {}) if isinstance(data, dict) else {}
    colors = {}
    for theme in ("light", "dark"):
        entries = (themes.get(theme, {}) or {}).get("colors", []) or []
        for entry in entries:
            if isinstance(entry, dict) and "id" in entry:
                colors.setdefault(entry["id"], {})[theme] = entry.get(
                    "color", _FALLBACK_COLOR
                )
    return colors


@router.get("/voice-groups", response_model=List[VoiceGroupOut])
def voice_groups(
    _db: Connection = Depends(get_db),
) -> List[VoiceGroupOut]:
    """Merged voice groups (DB-Dependency hält den Pfad M1-typisch
    offen für die spätere DB-Tabelle)."""
    colors = _theme_colors()
    return [
        VoiceGroupOut(
            id=group.get("name", ""),
            short=group.get("short"),
            order=group.get("order"),
            color_light=colors.get(group.get("name"), {}).get(
                "light", _FALLBACK_COLOR
            ),
            color_dark=colors.get(group.get("name"), {}).get(
                "dark", _FALLBACK_COLOR
            ),
        )
        for group in load_voice_groups()
    ]
