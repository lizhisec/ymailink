"""Password resolution utilities for backend authentication."""

from __future__ import annotations

import asyncio
import subprocess

from ymailink.config.models import PasswordAuth


async def resolve_password(auth: PasswordAuth) -> str:
    """Resolve a password from the configured auth method.

    Supports raw strings, shell commands, and system keyring.
    All blocking operations run in a thread to avoid blocking the event loop.
    """
    if auth.raw:
        return auth.raw
    if auth.cmd:
        result = await asyncio.to_thread(
            subprocess.run,
            auth.cmd, shell=True, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Password command failed: {result.stderr}")
        return result.stdout.strip()
    if auth.keyring:
        try:
            import keyring as kr
            password = await asyncio.to_thread(kr.get_password, "ymailink", auth.keyring)
            if password is None:
                raise RuntimeError(f"No password found in keyring for: {auth.keyring}")
            return password
        except ImportError:
            raise RuntimeError("keyring package not installed")
    raise RuntimeError("No password authentication method configured")
