"""TOML config loader with path resolution and multi-file merge."""

from __future__ import annotations

import tomllib
from pathlib import Path

from ymailink.config.defaults import get_default_config_path
from ymailink.config.models import YmailConfig


def load_config(paths: list[str] | None = None) -> YmailConfig:
    """Load and merge config from one or more TOML files.

    If no paths given, uses the default config path.
    Pass an empty list to get an empty config without reading any file.
    Multiple files are merged left-to-right (later overrides earlier).
    """
    if paths is None:
        default_path = get_default_config_path()
        if default_path.exists():
            paths = [str(default_path)]
        else:
            # Return empty config
            return YmailConfig()

    merged: dict = {}
    for p in paths:
        path = Path(p).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        merged = _deep_merge(merged, data)

    return YmailConfig.model_validate(merged)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
