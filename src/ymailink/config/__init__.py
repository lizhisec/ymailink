"""Configuration package."""

from ymailink.config.loader import load_config
from ymailink.config.models import YmailConfig

__all__ = ["load_config", "YmailConfig"]
