"""Folder domain model."""

from __future__ import annotations

from pydantic import BaseModel


class Folder(BaseModel):
    """Represents a mail folder/mailbox."""

    name: str
    delimiter: str = "/"
    count: int | None = None
    unread: int | None = None
