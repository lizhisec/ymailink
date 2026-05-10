"""Account domain model."""

from __future__ import annotations

from pydantic import BaseModel


class Account(BaseModel):
    """Represents a configured email account for display purposes."""

    name: str
    email: str
    display_name: str | None = None
    backend_type: str
    is_default: bool = False
