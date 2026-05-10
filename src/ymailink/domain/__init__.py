"""Domain models package."""

from ymailink.domain.account import Account
from ymailink.domain.attachment import Attachment
from ymailink.domain.flag import Flag
from ymailink.domain.folder import Folder
from ymailink.domain.message import Message, MessageBody
from ymailink.domain.summary import Address, Summary

__all__ = [
    "Account",
    "Address",
    "Attachment",
    "Flag",
    "Folder",
    "Message",
    "MessageBody",
    "Summary",
]
