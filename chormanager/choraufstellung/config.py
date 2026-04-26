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


# Voice groups configuration
VOICE_GROUPS_CONFIG_FILE = "config/voice_groups.json"

def load_voice_groups_config() -> list:
    """Lädt die Stimmgruppen-Konfiguration. Gibt Fallback zurück."""
    try:
        if os.path.exists(VOICE_GROUPS_CONFIG_FILE):
            with open(VOICE_GROUPS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get("voice_groups", [])
    except Exception as e:
        print(f"Config load error: {e}")
    return [
        {"id": "Sopran 1", "color": "#ff9999"}, {"id": "Sopran 2", "color": "#ff6666"},
        {"id": "Alt 1", "color": "#99ccff"}, {"id": "Alt 2", "color": "#6699ff"},
        {"id": "Tenor 1", "color": "#99ff99"}, {"id": "Tenor 2", "color": "#66cc66"},
        {"id": "Bass 1", "color": "#ffff99"}, {"id": "Bass 2", "color": "#ffff66"}
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