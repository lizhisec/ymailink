"""Message and MessageBody domain models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ymailink.domain.attachment import Attachment
from ymailink.domain.summary import Address
from ymailink.domain.flag import Flag


class MessageBody(BaseModel):
    """Message body content."""

    text: str | None = None
    html: str | None = None


class Message(BaseModel):
    """Full message with headers and body."""

    id: str
    folder: str | None = None
    subject: str | None = None
    from_: Address | None = None
    to: list[Address] = []
    cc: list[Address] = []
    bcc: list[Address] = []
    reply_to: list[Address] = []
    date: datetime | None = None
    flags: list[Flag] = []
    message_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] = []
    body: MessageBody = MessageBody()
    attachments: list[Attachment] = []
    raw: bytes | None = None
