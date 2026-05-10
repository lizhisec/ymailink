"""Attachment domain model."""

from __future__ import annotations

from pydantic import BaseModel


class Attachment(BaseModel):
    """Email attachment metadata."""

    id: str | None = None
    filename: str | None = None
    content_type: str = "application/octet-stream"
    size: int | None = None
    data: bytes | None = None
