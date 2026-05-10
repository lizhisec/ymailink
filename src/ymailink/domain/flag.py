"""Flag enum for message flags."""

from __future__ import annotations

from enum import Enum


class Flag(str, Enum):
    """Standard email message flags."""

    SEEN = "seen"
    ANSWERED = "answered"
    FLAGGED = "flagged"
    DELETED = "deleted"
    DRAFT = "draft"

    @classmethod
    def from_imap(cls, imap_flag: str) -> Flag | str:
        """Convert IMAP flag string to Flag enum."""
        mapping = {
            "\\Seen": cls.SEEN,
            "\\Answered": cls.ANSWERED,
            "\\Flagged": cls.FLAGGED,
            "\\Deleted": cls.DELETED,
            "\\Draft": cls.DRAFT,
        }
        return mapping.get(imap_flag, imap_flag)

    def to_imap(self) -> str:
        """Convert Flag to IMAP flag string."""
        mapping = {
            self.SEEN: "\\Seen",
            self.ANSWERED: "\\Answered",
            self.FLAGGED: "\\Flagged",
            self.DELETED: "\\Deleted",
            self.DRAFT: "\\Draft",
        }
        return mapping.get(self, self.value)

    @classmethod
    def parse(cls, value: str) -> Flag:
        """Parse a flag from user input string."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Unknown flag: {value}. Valid flags: {[f.value for f in cls]}")
