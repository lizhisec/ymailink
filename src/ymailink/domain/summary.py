"""Summary and Address domain models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ymailink.domain.flag import Flag


class Address(BaseModel):
    """An email address with optional display name."""

    name: str | None = None
    email: str

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class Summary(BaseModel):
    """Message summary - lightweight info for listings."""

    id: str
    subject: str | None = None
    from_: Address | None = None
    to: list[Address] = []
    date: datetime | None = None
    flags: list[Flag] = []
    has_attachment: bool = False
    thread_id: str | None = None
