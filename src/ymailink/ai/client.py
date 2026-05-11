"""Async HTTP client for the ymailink AI API."""

from __future__ import annotations

from ymailink.config.models import AiConfig


async def call_ai(payload: dict, config: AiConfig, endpoint: str) -> dict:
    """POST to the AI API and return the parsed JSON response.

    Compatible with both ``result.xxx`` and ``choices[0].message.content``
    response shapes.
    """
    if not config.api_key:
        raise ValueError("AI API key is not configured.")

    import httpx

    url = f"{config.base_url.rstrip('/')}/api/v1/apps/youmail/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()
