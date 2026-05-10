"""Path utilities and XDG directory helpers."""

from __future__ import annotations

from pathlib import Path

# Re-export config defaults for convenience
from ymailink.config.defaults import (
    get_config_dir,
    get_data_dir,
    get_default_config_path,
    get_token_dir,
    get_token_path,
)


def expand_path(path: str | Path) -> Path:
    """Expand user home and resolve a path."""
    return Path(path).expanduser().resolve()


__all__ = [
    "expand_path",
    "get_config_dir",
    "get_data_dir",
    "get_default_config_path",
    "get_token_dir",
    "get_token_path",
]
