"""Shared voice-group theme colors (``config/voice_groups.json``).

Single source for the config router and the formation PDF
(Analyse §5.4: eine Quelle; Formatfrage egal). Always read fresh
from disk so admin edits apply without restart.
"""
import json
from pathlib import Path
from typing import Dict

FALLBACK_COLOR = "#cccccc"


def config_file() -> Path:
    """Path to ``config/voice_groups.json`` next to this repo."""
    return Path(__file__).resolve().parents[2] / "config" / "voice_groups.json"


def load_theme_colors() -> Dict[str, Dict[str, str]]:
    """Return ``{group_id: {"light": hex, "dark": hex}}``.

    Returns:
        Nested color dict; empty when the file is missing/broken.
    """
    try:
        data = json.loads(config_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    themes = data.get("themes", {}) if isinstance(data, dict) else {}
    colors: Dict[str, Dict[str, str]] = {}
    for theme in ("light", "dark"):
        entries = (themes.get(theme, {}) or {}).get("colors", []) or []
        for entry in entries:
            if isinstance(entry, dict) and "id" in entry:
                colors.setdefault(entry["id"], {})[theme] = entry.get(
                    "color", FALLBACK_COLOR
                )
    return colors


def voice_color(group_id: str, theme: str = "light") -> str:
    """Return the hex color for a group (fallback gray)."""
    return load_theme_colors().get(group_id or "", {}).get(
        theme, FALLBACK_COLOR
    )
