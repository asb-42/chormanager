"""Configuration management for ChorManager."""

import logging
import os
import yaml
import json
from pathlib import Path
from functools import lru_cache

CONFIG_DIR = Path(__file__).parent.parent / "config"

# m8-FIX-A: get a module-level logger for YAML loaders.
_logger = logging.getLogger(__name__)


def _safe_yaml_load(config_path: Path, default: object) -> object:
    """Load ``config_path`` as YAML; return ``default`` on any failure.

    Covers:
        * ``OSError`` / ``FileNotFoundError`` (missing or unreadable file)
        * ``yaml.YAMLError`` (malformed YAML of any subtype)
    Always logs a warning so misconfiguration is visible.
    """
    if not config_path.exists():
        _logger.warning(
            "Config file %s does not exist; falling back to default %r",
            config_path, default,
        )
        return default
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or default
    except (OSError, yaml.YAMLError) as exc:
        _logger.warning(
            "Failed to parse YAML %s (%s: %s); falling back to default %r",
            config_path, type(exc).__name__, exc, default,
        )
        return default


def get_state_file():
    """Get the state file for storing runtime state (e.g., last active project).
    
    Returns:
        Path: Path to state.json file.
    """
    return get_data_dir() / "state.json"


def load_state():
    """Load application state from JSON file.
    
    Returns:
        dict: State dictionary.
    """
    state_file = get_state_file()
    if state_file.exists():
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """Save application state to JSON file.

    M-4 Fix: Atomic write via tmp + os.replace, damit ``state.json``
    bei einem Crash waehrend des Schreibens nicht korrupt wird.
    ``state.json`` enthaelt last_active_project_id / event_id /
    besetzung_id und theme -- ein Korruptionsverlust wuerde den
    User-Zustand (welches Projekt war aktiv?) zerschlagen.

    Args:
        state: State dictionary to save.

    Raises:
        OSError: If the parent directory cannot be created or the
            write fails despite the atomic-write fallback below.
    """
    state_file = get_state_file()
    # PR-Review R1 (2026-09-09): On a pristine checkout ``data/`` may
    # not exist yet (nothing ran the Database constructor). Creating
    # the parent here keeps every early state write -- e.g.
    # ``EventsTab._restore_active_event`` dropping a stale event id
    # on first launch -- from raising FileNotFoundError.
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = str(state_file) + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, state_file)
    except Exception:
        # Bei Crash bleibt state.json (alter Stand) unangetastet;
        # die .tmp-Datei wird beim naechsten erfolgreichen Save ueberschrieben.
        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        except OSError:
            pass
        raise


def get_last_active_project_id():
    """Get the ID of the last active project.
    
    Returns:
        str: Project ID or None.
    """
    state = load_state()
    return state.get("last_active_project_id")


def set_last_active_project_id(project_id: str):
    """Set the ID of the last active project.
    
    Args:
        project_id: Project ID to store.
    """
    state = load_state()
    state["last_active_project_id"] = project_id
    save_state(state)


def get_last_active_event_id():
    """Get the ID of the last active event."""
    state = load_state()
    return state.get("last_active_event_id")


def set_last_active_event_id(event_id: str):
    """Set the ID of the last active event."""
    state = load_state()
    state["last_active_event_id"] = event_id
    save_state(state)


def get_last_active_besetzung_id():
    """Get the ID of the last active besetzung."""
    state = load_state()
    return state.get("last_active_besetzung_id")


def set_last_active_besetzung_id(besetzung_id: str):
    """Set the ID of the last active besetzung."""
    state = load_state()
    state["last_active_besetzung_id"] = besetzung_id
    save_state(state)


def get_theme():
    """Get the selected theme (light or dark).
    
    Returns:
        str: Theme name ("light" or "dark").
    """
    state = load_state()
    return state.get("theme", "light")


def set_theme(theme: str):
    """Set the selected theme.
    
    Args:
        theme: Theme name ("light" or "dark").
    """
    state = load_state()
    state["theme"] = theme
    save_state(state)


def get_app_dir() -> Path:
    """Get the application directory (where chormanager is installed).
    
    Returns:
        Path: The application directory.
    """
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Get the data directory for storing app data.
    
    By default, uses a 'data' subdirectory within the app directory.
    This ensures all data stays with the program.
    
    Returns:
        Path: The data directory.
    """
    return get_app_dir() / "data"


@lru_cache(maxsize=1)
def load_voice_groups():
    """Load voice groups from YAML configuration.
    
    The result is cached for the lifetime of the process. The cache
    can be invalidated by calling ``load_voice_groups.cache_clear()``,
    e.g. after the YAML file is edited at runtime.
    
    Returns:
        list: List of voice group dictionaries sorted by order.
    """
    config_file = CONFIG_DIR / "voice_groups.yaml"
    data = _safe_yaml_load(config_file, default={"voice_groups": []})
    if not isinstance(data, dict):
        data = {"voice_groups": []}
    groups = data.get("voice_groups", []) or []
    return sorted(groups, key=lambda g: g.get("order", 0))


@lru_cache(maxsize=1)
def load_fields():
    """Load field definitions from YAML configuration.
    
    Cached for the lifetime of the process; invalidate via
    ``load_fields.cache_clear()`` after the YAML file is edited.
    
    Returns:
        list: List of field dictionaries sorted by order.
    """
    config_file = CONFIG_DIR / "fields.yaml"
    data = _safe_yaml_load(config_file, default={"fields": []})
    if not isinstance(data, dict):
        data = {"fields": []}
    fields = data.get("fields", []) or []
    return sorted(fields, key=lambda f: f.get("order", 0))


@lru_cache(maxsize=1)
def load_app_config():
    """Load application configuration from YAML.
    
    Cached for the lifetime of the process; invalidate via
    ``load_app_config.cache_clear()`` after the YAML file is edited.
    
    Returns:
        dict: Application configuration dictionary.
    """
    config_file = CONFIG_DIR / "app.yaml"
    data = _safe_yaml_load(config_file, default={}) or {}
    # If YAML parsed successfully but returned a scalar (e.g. a stray string),
    # fall back to an empty dict instead of letting callers see ``str``.
    if not isinstance(data, dict):
        _logger.warning(
            "Config %s did not contain a mapping; falling back to empty dict",
            config_file,
        )
        data = {}
    return data


def get_voice_group_choices():
    """Get voice groups as choices for dropdown.
    
    Returns:
        list: List of (name, display_name) tuples.
    """
    groups = load_voice_groups()
    return [(g["name"], g["name"]) for g in groups]


def get_field_by_name(name: str):
    """Get field definition by name.
    
    Args:
        name: Field name.
        
    Returns:
        dict: Field definition or None.
    """
    fields = load_fields()
    for field in fields:
        if field["name"] == name:
            return field
    return None


def get_required_fields():
    """Get list of required field names.
    
    Returns:
        list: List of required field names.
    """
    fields = load_fields()
    return [f["name"] for f in fields if f.get("required", False)]


# Voice group color cache (theme-aware)
_vg_color_cache: dict = {}
_vg_color_theme: str | None = None


def _load_voice_group_colors() -> list:
    """Load voice group colors from voice_groups.json (theme-aware).
    
    Returns:
        list: List of voice group color dicts with 'id' and 'color' keys.
    """
    global _vg_color_cache, _vg_color_theme

    current_theme = get_theme()

    if _vg_color_theme == current_theme and _vg_color_cache:
        return _vg_color_cache

    config_file = CONFIG_DIR / "voice_groups.json"
    try:
        with open(config_file, encoding="utf-8") as f:
            data = json.load(f)
        theme_data = data.get("themes", {}).get(current_theme, {})
        colors = theme_data.get("colors", [])
        if colors:
            _vg_color_cache = colors
            _vg_color_theme = current_theme
            return colors
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    # Hardcoded fallback (light theme)
    _vg_color_cache = [
        {"id": "Sopran 1", "color": "#E5C84B"}, {"id": "Sopran 2", "color": "#B8A23A"},
        {"id": "Alt 1", "color": "#C75B5B"}, {"id": "Alt 2", "color": "#9B5B6B"},
        {"id": "Tenor 1", "color": "#6BA888"}, {"id": "Tenor 2", "color": "#5B8A6B"},
        {"id": "Bass 1", "color": "#6B8AA8"}, {"id": "Bass 2", "color": "#5B6B8A"},
    ]
    _vg_color_theme = current_theme
    return _vg_color_cache


def get_voice_group_color(voice_group_id: str, theme: str | None = None) -> str:
    """Get hex color for a voice group (theme-aware, cached).
    
    Args:
        voice_group_id: Voice group name (e.g. "Sopran 1").
        theme: Optional theme override ("light"/"dark"). Defaults to current theme.
    
    Returns:
        str: Hex color code (e.g. "#E5C84B").
    """
    if theme is not None:
        _clear_vg_color_cache()
        global _vg_color_theme
        _vg_color_theme = theme

    colors = _load_voice_group_colors()
    for vg in colors:
        if vg.get("id") == voice_group_id:
            return vg["color"]
    return "#cccccc"


def _clear_vg_color_cache():
    """Clear the voice group color cache."""
    global _vg_color_cache, _vg_color_theme
    _vg_color_cache = {}
    _vg_color_theme = None


def get_text_color() -> str:
    """Get the current theme text color.
    
    Returns:
        str: Hex text color.
    """
    current_theme = get_theme()
    config_file = CONFIG_DIR / "voice_groups.json"
    try:
        with open(config_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("themes", {}).get(current_theme, {}).get("text", "#1A1A1A")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return "#1A1A1A"
