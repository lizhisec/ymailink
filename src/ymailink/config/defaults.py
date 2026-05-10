"""Default paths and XDG directory resolution."""

from __future__ import annotations

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Return the ymailink config directory following XDG on Linux/macOS."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "ymailink"
    return Path.home() / ".config" / "ymailink"


def get_data_dir() -> Path:
    """Return the ymailink data directory."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "ymailink"
    return Path.home() / ".local" / "share" / "ymailink"


def get_default_config_path() -> Path:
    """Return the default config file path."""
    return get_config_dir() / "config.toml"


def get_token_dir() -> Path:
    """Return the directory for storing OAuth tokens."""
    d = get_config_dir() / "tokens"
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    return d


def get_token_path(provider: str, account_name: str) -> Path:
    """Return the token file path for a specific provider/account."""
    return get_token_dir() / f"{provider}_{account_name}.json"
