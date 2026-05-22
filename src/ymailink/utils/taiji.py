"""Load AI config from ~/.taiji/config.json as a fallback source."""

from __future__ import annotations

import json
import pathlib
import sys


def load_taiji_config() -> dict[str, str | None]:
    """Load AI config from ~/.taiji/config.json.

    Returns dict with ``base_url`` and ``api_key`` keys.
    ``api_key`` may be ``None`` if the file doesn't exist or lacks credentials.
    """
    config_path = pathlib.Path.home() / ".taiji" / "config.json"
    base_url: str | None = None
    api_key: str | None = None

    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8", errors="ignore"))
            gw = cfg.get("gateway", {})
            base_url = gw.get("server")
            api_key = gw.get("apiKey") or gw.get("api_key")
        except Exception as e:
            sys.stderr.write(f"Warning: failed to read {config_path}: {e}\n")

    return {"base_url": base_url, "api_key": api_key}
