# // Imports
import os
import sys
import json
from typing import Dict, Any

# // Multiplatform Path Resolvers
def get_default_config_dir() -> str:
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
        return os.path.join(appdata, "FocusShell")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/FocusShell")
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(xdg_config, "focusshell")

def get_default_data_dir() -> str:
    if sys.platform.startswith("win"):
        localappdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        return os.path.join(localappdata, "FocusShell")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/FocusShell")
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        return os.path.join(xdg_data, "focusshell")

# // Default Configuration
DEFAULT_CONFIG_DIR = get_default_config_dir()
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.json")
DEFAULT_DATA_DIR = get_default_data_dir()
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "focus.db")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "sampling_interval_seconds": 2.0,
    "idle_threshold_seconds": 180,
    "db_path": DEFAULT_DB_PATH,
    "data_dir": DEFAULT_DATA_DIR,
    "auto_group_similar_windows": True,
    "min_session_duration_seconds": 1
}

# // Configuration Loader & Writer
def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        save_config(DEFAULT_SETTINGS, config_path)
        return DEFAULT_SETTINGS.copy()
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(user_config)
            return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_config(config: Dict[str, Any], config_path: str = DEFAULT_CONFIG_PATH) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def update_config_key(key: str, value: Any, config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    cfg = load_config(config_path)
    cfg[key] = value
    save_config(cfg, config_path)
    return True
