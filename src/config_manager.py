import copy
import os
from pathlib import Path

import yaml

CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/config/settings.yaml"))
DEFAULTS_PATH = Path(os.environ.get("DEFAULTS_PATH", "/app/config/defaults.yaml"))

_config_cache: dict | None = None


def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return copy.deepcopy(_config_cache)
    defaults = yaml.safe_load(DEFAULTS_PATH.read_text())
    if CONFIG_PATH.exists():
        user_cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        _config_cache = _deep_merge(defaults, user_cfg)
    else:
        _config_cache = defaults
    return copy.deepcopy(_config_cache)


def save_config(new_config: dict) -> None:
    global _config_cache
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(new_config, default_flow_style=False, allow_unicode=True))
    tmp.replace(CONFIG_PATH)
    _config_cache = None


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result
