import json
import os
from typing import Dict, Optional

# Theme-aware voice group colors
_THEME_COLORS = {
    "light": [
        {"id": "Sopran 1", "color": "#E5C84B"}, {"id": "Sopran 2", "color": "#B8A23A"},
        {"id": "Alt 1", "color": "#C75B5B"}, {"id": "Alt 2", "color": "#9B5B6B"},
        {"id": "Tenor 1", "color": "#6BA888"}, {"id": "Tenor 2", "color": "#5B8A6B"},
        {"id": "Bass 1", "color": "#6B8AA8"}, {"id": "Bass 2", "color": "#5B6B8A"}
    ],
    "dark": [
        {"id": "Sopran 1", "color": "#8A7A3A"}, {"id": "Sopran 2", "color": "#6B5B2A"},
        {"id": "Alt 1", "color": "#8A4A3A"}, {"id": "Alt 2", "color": "#6B3A4A"},
        {"id": "Tenor 1", "color": "#3A6B5A"}, {"id": "Tenor 2", "color": "#2A5B4A"},
        {"id": "Bass 1", "color": "#3A4A6B"}, {"id": "Bass 2", "color": "#2A3A5B"}
    ]
}

# Cache for loaded colors
_cached_colors: Optional[list] = None
_current_theme: Optional[str] = None


def get_data_dir() -> str:
    """Gibt das Daten-Verzeichnis im Programmordner zurück."""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_settings_path() -> str:
    """Gibt den Pfad zur Settings-Datei zurück."""
    return os.path.join(get_data_dir(), "app_settings.json")


def load_settings() -> Dict[str, str]:
    """Lädt die Anwendungseinstellungen. Gibt Fallback bei Fehler zurück."""
    default = {"theme": "light"}
    try:
        path = get_settings_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "theme" in data:
                    if data["theme"] in ("light", "dark"):
                        return data
        return default
    except (IOError, json.JSONDecodeError) as e:
        print(f"Settings load error: {e}")
        return default


def save_settings(settings: Dict[str, str]) -> bool:
    """Speichert die Einstellungen atomar. Gibt Erfolg zurück."""
    try:
        path = get_settings_path()
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        return True
    except IOError as e:
        print(f"Settings save error: {e}")
        return False


# Voice groups configuration - use absolute path from chormanager root
_config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_GROUPS_CONFIG_FILE = os.path.join(_config_dir, "config", "voice_groups.json")


def load_voice_groups_config() -> list:
    """Lädt die Stimmgruppen-Konfiguration mit Theme-Unterstützung."""
    global _cached_colors, _current_theme
    
    current_theme = load_settings().get("theme", "light")
    
    # Reload only if theme changed
    if _current_theme != current_theme:
        _current_theme = current_theme
        _cached_colors = None
    
    if _cached_colors is not None:
        return _cached_colors
    
    try:
        if os.path.exists(VOICE_GROUPS_CONFIG_FILE):
            with open(VOICE_GROUPS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # New format: {"themes": {"light": {...}, "dark": {...}}}
                if "themes" in data:
                    theme_data = data["themes"].get(current_theme, {})
                    colors = theme_data.get("colors", [])
                    if colors:
                        _cached_colors = colors
                        return colors
                # Old format: {"voice_groups": [...]} - fallback
                if "voice_groups" in data:
                    _cached_colors = data["voice_groups"]
                    return _cached_colors
    except Exception as e:
        print(f"Config load error: {e}")
    
    # Use built-in theme colors
    _cached_colors = _THEME_COLORS.get(current_theme, _THEME_COLORS["light"])
    return _cached_colors


def get_valid_voice_groups() -> list:
    """Gibt Liste gültiger Stimmgruppen-IDs zurück."""
    return [vg["id"] for vg in load_voice_groups_config()]


def get_voice_group_color(vid: str) -> str:
    """Gibt Hex-Farbcode für Stimmgruppe zurück (theme-aware)."""
    for vg in load_voice_groups_config():
        if vg["id"] == vid:
            return vg["color"]
    return "#cccccc"


def clear_color_cache():
    """Clear cached colors - call when theme changes."""
    global _cached_colors, _current_theme
    _cached_colors = None
    _current_theme = None