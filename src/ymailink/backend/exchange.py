"""Exchange (EWS) backend implementation using exchangelib."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from typing import Any

import exchangelib
from exchangelib import (
    Account,
    Configuration,
    Credentials,
)
from exchangelib.folders.base import Folder as EWPFolder
from exchangelib.version import EXCHANGE_2016, EXCHANGE_2019, Version

from ymailink.backend.base import ReadBackend, SendBackend
from ymailink.config.models import ExchangeConfig
from ymailink.domain.attachment import Attachment
from ymailink.domain.summary import Address, Summary
from ymailink.domain.flag import Flag
from ymailink.domain.folder import Folder
from ymailink.domain.message import Message, MessageBody


class ExchangeBackend(ReadBackend, SendBackend):
    """Microsoft Exchange Web Services (EWS) backend via exchangelib."""

    def __init__(self, config: ExchangeConfig):
        self._config = config
        self._account: Account | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, partial(func, *args, **kwargs)
        )

    async def connect(self) -> None:
        credentials = Credentials(
            username=self._config.login,
            password=await self._resolve_password(self._config.auth),
        )

        def _do_connect():
            version = None
            if self._config.version:
                version_map = {
                    "2016": Version(EXCHANGE_2016),
                    "2019": Version(EXCHANGE_2019),
                }
                version = version_map.get(self._config.version, Version(EXCHANGE_2016))
            config = Configuration(
                server=self._config.host,
                credentials=credentials,
                auth_type=self._config.auth_type,
                version=version,
            )
            self._account = Account(
                primary_smtp_address=self._config.email,
                config=config,
                autodiscover=self._config.autodiscover,
                access_type=self._config.access_type,
            )
            # Warm up well-known folder references
            for attr in ("inbox", "sent", "drafts", "trash", "junk"):
                try:
                    getattr(self._account, attr)
                except Exception:
                    pass

        await self._run(_do_connect)

    async def disconnect(self) -> None:
        self._account = None

    # ---- Folder operations ----

    async def list_folders(self) -> list[Folder]:
        def _do_list():
            folders = []
            account = self._account
            if account is None:
                return folders
            # Walk root folder tree
            for folder in account.root.walk():
                fname = folder.name
                if not fname:
                    continue
                # Skip hidden/system folders
                if fname.startswith(":"):
                    continue
                unread = None
                if hasattr(folder, "unread_count") and folder.unread_count:
                    unread = folder.unread_count
                count = None
                if hasattr(folder, "total_count") and folder.total_count:
                    count = folder.total_count
                folders.append(Folder(
                    name=fname,
                    delimiter="/",
                    count=count,
                    unread=unread,
                ))
            return folders

        return await self._run(_do_list)

    async def add_folder(self, name: str) -> None:
        from exchangelib.folders import Messages

        async def _do_add():
            folder = Messages(parent=self._account.root, name=name)
            folder.save()

        await self._run(_do_add)

    async def delete_folder(self, name: str) -> None:
        folder = await self._resolve_folder(name)

        def _do_delete(f: EWPFolder):
            f.delete()

        await self._run(_do_delete, folder)

    async def expunge_folder(self, name: str) -> None:
        # EWS doesn't require expunge; just delete permanently
        pass

    # ---- Summary operations ----

    async def list_summaries(
        self,
        folder: str,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
    ) -> list[Summary]:
        ews_folder = await self._resolve_folder(folder)

        def _do_list():
            q = exchangelib.Q()
            if query:
                q &= exchangelib.Q(subject__contains=query)

            qs = (
                ews_folder.filter(q)
                .order_by("-datetime_received")
                .only(
                    "id",
                    "changekey",
                    "subject",
                    "sender",
                    "to_recipients",
                    "datetime_received",
                    "is_read",
                    "has_attachments",
                    "conversation_id",
                )
            )

            start = (page - 1) * page_size
            page_qs = qs[start : start + page_size]
            return [self._parse_summary(item) for item in page_qs]

        return await self._run(_do_list)

    async def get_messages(self, folder: str, ids: Sequence[str]) -> list[Message]:
        ews_folder = await self._resolve_folder(folder)

        def _do_get():
            messages = []
            for msg_id in ids:
                item = ews_folder.get(id=msg_id)
                if item:
                    messages.append(self._parse_message(item, folder))
            return messages

        return await self._run(_do_get)

    async def add_message(self, folder: str, raw: bytes) -> None:
        ews_folder = await self._resolve_folder(folder)
        from email import message_from_bytes
        from email.message import Message as EMIMEMessage

        def _do_add():
            mime_msg = message_from_bytes(raw)
            ews_folder.add(mime_msg)

        await self._run(_do_add)

    async def copy_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        src_folder = await self._resolve_folder(source)
        tgt_folder = await self._resolve_folder(target)

        def _do_copy():
            for msg_id in ids:
                item = src_folder.get(id=msg_id)
                if item:
                    item.copy(to_folder=tgt_folder)

        await self._run(_do_copy)

    async def move_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        src_folder = await self._resolve_folder(source)
        tgt_folder = await self._resolve_folder(target)

        def _do_move():
            for msg_id in ids:
                item = src_folder.get(id=msg_id)
                if item:
                    item.move(to_folder=tgt_folder)

        await self._run(_do_move)

    async def delete_messages(self, folder: str, ids: Sequence[str]) -> None:
        src_folder = await self._resolve_folder(folder)

        def _do_delete():
            for msg_id in ids:
                item = src_folder.get(id=msg_id)
                if item:
                    item.delete()

        await self._run(_do_delete)

    # ---- Flag operations ----

    async def add_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self._set_flags(folder, ids, flags, add=True)

    async def set_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self._set_flags(folder, ids, flags, add=False)

    async def remove_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self._set_flags(folder, ids, flags, add=False)

    # ---- Send ----

    async def send_message(self, raw: bytes) -> None:
        def _do_send():
            from email import message_from_bytes
            mime_msg = message_from_bytes(raw)
            self._account.send(mime_msg)

        await self._run(_do_send)

    # ---- Helpers ----

    def _parse_mailbox(self, mbox: Any) -> Address | None:
        """Parse an exchangelib Mailbox into an Address."""
        if mbox is None:
            return None
        email = getattr(mbox, "email_address", None) or ""
        name = getattr(mbox, "name", None) or None
        if isinstance(email, str) and email:
            return Address(name=name, email=email)
        return None

    async def _resolve_folder(self, name: str) -> EWPFolder:
        account = self._account
        if account is None:
            raise RuntimeError("Not connected")

        # Well-known folders
        well_known_attr = {
            "INBOX": "inbox", "inbox": "inbox", "INBOX/": "inbox",
            "Sent": "sent", "sent": "sent", "Sent Items": "sent",
            "Drafts": "drafts", "drafts": "drafts",
            "Trash": "trash", "trash": "trash",
            "Deleted": "trash", "Deleted Items": "trash",
        }
        if name in well_known_attr:
            try:
                return getattr(account, well_known_attr[name])
            except Exception:
                pass  # Fall through to search

        def _find():
            for folder in account.root.walk():
                if folder.name == name:
                    return folder
            return None

        folder = await self._run(_find)
        if folder is None:
            raise ValueError(f"Folder not found: {name}")
        return folder

    def _parse_summary(self, item: Any) -> Summary:
        from_ = self._parse_mailbox(item.sender) if hasattr(item, "sender") and item.sender else None

        to = []
        if hasattr(item, "to_recipients") and item.to_recipients:
            for r in item.to_recipients:
                addr = self._parse_mailbox(r)
                if addr:
                    to.append(addr)

        date = None
        if hasattr(item, "datetime_received") and item.datetime_received:
            date = item.datetime_received
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)

        flags = []
        if hasattr(item, "is_read") and item.is_read:
            flags.append(Flag.SEEN)

        thread_id = None
        if hasattr(item, "conversation_id") and item.conversation_id:
            thread_id = str(item.conversation_id.id)

        return Summary(
            id=str(item.id),
            subject=getattr(item, "subject", None),
            from_=from_,
            to=to,
            date=date,
            flags=flags,
            has_attachment=getattr(item, "has_attachments", False),
            thread_id=thread_id,
        )

    def _parse_message(self, item: Any, folder: str) -> Message:
        from_ = self._parse_mailbox(item.sender) if hasattr(item, "sender") and item.sender else None

        to = []
        if hasattr(item, "to_recipients") and item.to_recipients:
            for r in item.to_recipients:
                addr = self._parse_mailbox(r)
                if addr:
                    to.append(addr)

        cc = []
        if hasattr(item, "cc_recipients") and item.cc_recipients:
            for r in item.cc_recipients:
                addr = self._parse_mailbox(r)
                if addr:
                    cc.append(addr)

        date = None
        if hasattr(item, "datetime_received") and item.datetime_received:
            date = item.datetime_received
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)

        flags = []
        if hasattr(item, "is_read") and item.is_read:
            flags.append(Flag.SEEN)
        if hasattr(item, "flag") and item.flag:
            flag_status = getattr(item.flag, "flag_status", None)
            if str(flag_status) == "Flagged":
                flags.append(Flag.FLAGGED)

        body = MessageBody()
        if hasattr(item, "text_body") and item.text_body:
            body.text = item.text_body
        if hasattr(item, "unique_body") and item.unique_body:
            body.html = item.unique_body
        if hasattr(item, "mime_content") and item.mime_content:
            import email
            mime_msg = email.message_from_bytes(item.mime_content)
            if mime_msg.is_multipart():
                for part in mime_msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain" and not body.text:
                        charset = part.get_content_charset() or "utf-8"
                        body.text = part.get_payload(decode=True).decode(charset, errors="replace")
                    elif ct == "text/html" and not body.html:
                        charset = part.get_content_charset() or "utf-8"
                        body.html = part.get_payload(decode=True).decode(charset, errors="replace")

        attachments = []
        if hasattr(item, "attachments") and item.attachments:
            for att in item.attachments:
                att_name = getattr(att, "name", None) or getattr(att, "file_name", None)
                att_name = self._fix_filename(att_name)
                att_size = getattr(att, "size", None)
                att_content_type = getattr(att, "content_type", "application/octet-stream")
                attachments.append(Attachment(
                    filename=att_name,
                    content_type=att_content_type,
                    size=att_size,
                ))

        message_id = None
        if hasattr(item, "internet_message_id") and item.internet_message_id:
            message_id = str(item.internet_message_id)

        in_reply_to = None
        if hasattr(item, "in_reply_to_id") and item.in_reply_to_id:
            in_reply_to = str(item.in_reply_to_id)

        references = []
        if hasattr(item, "references") and item.references:
            references = item.references.split() if isinstance(item.references, str) else []

        raw = None
        if hasattr(item, "mime_content") and item.mime_content:
            raw = item.mime_content

        return Message(
            id=str(item.id),
            folder=folder,
            subject=getattr(item, "subject", None),
            from_=from_,
            to=to,
            cc=cc,
            date=date,
            flags=flags,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references,
            body=body,
            attachments=attachments,
            raw=raw,
        )

    async def _set_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag], add: bool
    ) -> None:
        ews_folder = await self._resolve_folder(folder)

        def _do_set():
            for msg_id in ids:
                try:
                    item = ews_folder.get(id=msg_id)
                    if item is None:
                        continue
                    if Flag.SEEN in flags:
                        item.is_read = add
                    if Flag.FLAGGED in flags:
                        if add:
                            item.flag = exchangelib.Flag(
                                flag_status=exchangelib.FlagStatus.FLAGGED
                            )
                        else:
                            item.flag = exchangelib.Flag(
                                flag_status=exchangelib.FlagStatus.CLEARED
                            )
                    item.save()
                except Exception:
                    continue

        await self._run(_do_set)

    @staticmethod
    def _fix_filename(name: str | None) -> str | None:
        """Fix double-encoded UTF-8 in attachment filenames from Exchange."""
        if not name or not isinstance(name, str):
            return name
        for codec in ("latin-1", "cp1252"):
            try:
                fixed = name.encode(codec).decode("utf-8")
                if fixed.count("�") < name.count("�"):
                    return fixed
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
        return name

    async def _resolve_password(self, auth) -> str:
        from ymailink.utils.password import resolve_password
        return await resolve_password(auth)