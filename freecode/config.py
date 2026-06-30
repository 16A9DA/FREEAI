import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".freecode" / "config.json"
DEFAULTS = {"active_model": None, "pulled_models": [], "settings": {}}


def load_config():
    if CONFIG_PATH.exists():
        return {**DEFAULTS, **json.loads(CONFIG_PATH.read_text())}
    return {k: (v.copy() if isinstance(v, (list, dict)) else v) for k, v in DEFAULTS.items()}


def save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))
