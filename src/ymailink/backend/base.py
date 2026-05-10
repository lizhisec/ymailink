"""Abstract base classes for mail backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Self

from ymailink.domain.summary import Summary
from ymailink.domain.flag import Flag
from ymailink.domain.folder import Folder
from ymailink.domain.message import Message


class ReadBackend(ABC):
    """Abstract read backend (IMAP / Outlook / Gmail)."""

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    # Folder operations
    @abstractmethod
    async def list_folders(self) -> list[Folder]:
        ...

    @abstractmethod
    async def add_folder(self, name: str) -> None:
        ...

    @abstractmethod
    async def delete_folder(self, name: str) -> None:
        ...

    @abstractmethod
    async def expunge_folder(self, name: str) -> None:
        ...

    # Summary operations
    @abstractmethod
    async def list_summaries(
        self,
        folder: str,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
    ) -> list[Summary]:
        ...

    # Message operations
    @abstractmethod
    async def get_messages(self, folder: str, ids: Sequence[str]) -> list[Message]:
        ...

    @abstractmethod
    async def add_message(self, folder: str, raw: bytes) -> None:
        ...

    @abstractmethod
    async def copy_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        ...

    @abstractmethod
    async def move_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        ...

    @abstractmethod
    async def delete_messages(self, folder: str, ids: Sequence[str]) -> None:
        ...

    # Flag operations
    @abstractmethod
    async def add_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        ...

    @abstractmethod
    async def set_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        ...

    @abstractmethod
    async def remove_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        ...

    # Context manager
    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.disconnect()


class SendBackend(ABC):
    """Abstract send backend (SMTP / Outlook / Gmail)."""

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def send_message(self, raw: bytes) -> None:
        ...

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.disconnect()
