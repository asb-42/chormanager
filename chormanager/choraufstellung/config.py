import json
import os
from typing import Dict

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
    """Lädt die Stimmgruppen-Konfiguration. Gibt Fallback zurück."""
    try:
        if os.path.exists(VOICE_GROUPS_CONFIG_FILE):
            with open(VOICE_GROUPS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get("voice_groups", [])
    except Exception as e:
        print(f"Config load error: {e}")
    return [
        {"id": "Sopran 1", "color": "#F4D03F"}, {"id": "Sopran 2", "color": "#D4AC0D"},
        {"id": "Alt 1", "color": "#E74C3C"}, {"id": "Alt 2", "color": "#922B21"},
        {"id": "Tenor 1", "color": "#2ECC71"}, {"id": "Tenor 2", "color": "#1E8449"},
        {"id": "Bass 1", "color": "#3498DB"}, {"id": "Bass 2", "color": "#1F618D"}
    ]


def get_valid_voice_groups() -> list:
    """Gibt Liste gültiger Stimmgruppen-IDs zurück."""
    return [vg["id"] for vg in load_voice_groups_config()]


def get_voice_group_color(vid: str) -> str:
    """Gibt Hex-Farbcode für Stimmgruppe zurück."""
    for vg in load_voice_groups_config():
        if vg["id"] == vid:
            return vg["color"]
    return "#cccccc"