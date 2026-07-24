import json
import os

SETTINGS_FILE = "config/settings.json"

_DEFAULT = {"debug": False}


def _load():
    if not os.path.exists(SETTINGS_FILE):
        return dict(_DEFAULT)
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)


def is_debug_enabled() -> bool:
    return bool(_load().get("debug", False))


def set_debug(value: bool):
    data = _load()
    data["debug"] = bool(value)
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)