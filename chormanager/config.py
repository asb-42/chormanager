"""Configuration management for ChorManager."""

import yaml
import json
from pathlib import Path
from functools import lru_cache

CONFIG_DIR = Path(__file__).parent.parent / "config"


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
    
    Args:
        state: State dictionary to save.
    """
    state_file = get_state_file()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


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


def load_voice_groups():
    """Load voice groups from YAML configuration.
    
    Returns:
        list: List of voice group dictionaries sorted by order.
    """
    config_file = CONFIG_DIR / "voice_groups.yaml"
    with open(config_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    groups = data.get("voice_groups", [])
    return sorted(groups, key=lambda g: g.get("order", 0))


def load_fields():
    """Load field definitions from YAML configuration.
    
    Returns:
        list: List of field dictionaries sorted by order.
    """
    config_file = CONFIG_DIR / "fields.yaml"
    with open(config_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    fields = data.get("fields", [])
    return sorted(fields, key=lambda f: f.get("order", 0))


def load_app_config():
    """Load application configuration from YAML.
    
    Returns:
        dict: Application configuration dictionary.
    """
    config_file = CONFIG_DIR / "app.yaml"
    with open(config_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
