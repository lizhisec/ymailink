"""IMAP backend implementation using imapclient."""

from __future__ import annotations

import asyncio
import email
import email.policy
import email.utils
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from functools import partial
from time import localtime

from imapclient import IMAPClient

from ymailink.backend.base import ReadBackend
from ymailink.config.models import ImapConfig
from ymailink.domain.attachment import Attachment
from ymailink.domain.summary import Address, Summary
from ymailink.domain.flag import Flag
from ymailink.domain.folder import Folder
from ymailink.domain.message import Message, MessageBody


class ImapBackend(ReadBackend):
    def __init__(self, config: ImapConfig):
        self._config = config
        self._client: IMAPClient | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def _run(self, func, *args, **kwargs):
        """Run a blocking imapclient call in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, partial(func, *args, **kwargs)
        )

    async def connect(self) -> None:
        use_ssl = self._config.encryption == "tls"
        self._client = await self._run(
            IMAPClient, self._config.host, port=self._config.port, ssl=use_ssl
        )
        if self._config.encryption == "start-tls":
            await self._run(self._client.starttls)

        # Send IMAP ID command — required by 126/163/yeah.net and other
        # NetEase servers before authentication will succeed.
        await self._run(
            self._client.id_,
            {"name": "ymailink", "version": "1.0", "vendor": "ymailink"},
        )

        password = await self._resolve_password(self._config.auth)
        await self._run(self._client.login, self._config.login, password)

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._run(self._client.logout)
            except Exception:
                pass
            self._client = None

    async def list_folders(self) -> list[Folder]:
        raw = await self._run(self._client.list_folders)
        folders = []
        for flags, delimiter, name in raw:
            delim = delimiter.decode() if isinstance(delimiter, bytes) else delimiter
            folder_name = name if isinstance(name, str) else name.decode()
            folders.append(Folder(name=folder_name, delimiter=delim))
        return folders

    async def add_folder(self, name: str) -> None:
        await self._run(self._client.create_folder, name)

    async def delete_folder(self, name: str) -> None:
        await self._run(self._client.delete_folder, name)

    async def expunge_folder(self, name: str) -> None:
        await self._run(self._client.select_folder, name)
        await self._run(self._client.expunge)

    async def list_summaries(
        self,
        folder: str,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
    ) -> list[Summary]:
        await self._run(self._client.select_folder, folder, readonly=True)

        if query:
            criteria = ["TEXT", query]
        else:
            criteria = ["ALL"]

        uids = await self._run(self._client.search, criteria)
        # Reverse for newest first, paginate
        uids = list(reversed(uids))
        start = (page - 1) * page_size
        page_uids = uids[start : start + page_size]

        if not page_uids:
            return []

        # Fetch envelope data
        fetch_data = await self._run(
            self._client.fetch, page_uids, [b"ENVELOPE", b"FLAGS"]
        )

        summaries = []
        for uid, data in fetch_data.items():
            env_data = data.get(b"ENVELOPE")
            imap_flags = data.get(b"FLAGS", ())

            if env_data is None:
                continue

            summary = self._parse_summary(str(uid), env_data, imap_flags)
            summaries.append(summary)

        # Sort by date descending (newest first)
        summaries.sort(key=lambda s: s.date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        return summaries

    async def get_messages(self, folder: str, ids: Sequence[str]) -> list[Message]:
        await self._run(self._client.select_folder, folder, readonly=True)
        int_ids = [int(i) for i in ids]
        fetch_data = await self._run(
            self._client.fetch, int_ids, [b"RFC822", b"FLAGS"]
        )

        messages = []
        for uid, data in fetch_data.items():
            raw_bytes = data.get(b"RFC822", b"")
            imap_flags = data.get(b"FLAGS", ())
            msg = self._parse_message(str(uid), folder, raw_bytes, imap_flags)
            messages.append(msg)

        return messages

    async def add_message(self, folder: str, raw: bytes) -> None:
        await self._run(self._client.append, folder, raw)

    async def copy_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        await self._run(self._client.select_folder, source)
        int_ids = [int(i) for i in ids]
        await self._run(self._client.copy, int_ids, target)

    async def move_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        from imapclient.exceptions import CapabilityError

        await self._run(self._client.select_folder, source)
        int_ids = [int(i) for i in ids]

        # Try MOVE extension first; fall back to COPY + delete if unsupported
        try:
            await self._run(self._client.move, int_ids, target)
        except CapabilityError:
            await self._run(self._client.copy, int_ids, target)
            await self._run(self._client.set_flags, int_ids, [b"\\Deleted"])
            await self._run(self._client.expunge, int_ids)

    async def delete_messages(self, folder: str, ids: Sequence[str]) -> None:
        await self._run(self._client.select_folder, folder)
        int_ids = [int(i) for i in ids]
        await self._run(
            self._client.set_flags, int_ids, [b"\\Deleted"]
        )
        await self._run(self._client.expunge, int_ids)

    async def add_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self._run(self._client.select_folder, folder)
        int_ids = [int(i) for i in ids]
        imap_flags = [f.to_imap().encode() for f in flags]
        await self._run(self._client.add_flags, int_ids, imap_flags)

    async def set_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self._run(self._client.select_folder, folder)
        int_ids = [int(i) for i in ids]
        imap_flags = [f.to_imap().encode() for f in flags]
        await self._run(self._client.set_flags, int_ids, imap_flags)

    async def remove_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self._run(self._client.select_folder, folder)
        int_ids = [int(i) for i in ids]
        imap_flags = [f.to_imap().encode() for f in flags]
        await self._run(self._client.remove_flags, int_ids, imap_flags)

    # ---- helpers ----

    @staticmethod
    def _decode_rfc2047(value: str) -> str:
        """Decode RFC 2047 encoded-word sequences (e.g. =?utf-8?B?dGVzdA==?=).

        Returns the decoded string, or the original value if no encoding is present.
        """
        if value is None:
            return ""
        value = str(value)
        if not value or "=?" not in value:
            return value
        parts = decode_header(value)
        decoded_parts = []
        for data, charset in parts:
            if isinstance(data, bytes):
                decoded_parts.append(data.decode(charset or "utf-8", errors="replace"))
            else:
                decoded_parts.append(data)
        return "".join(decoded_parts)

    @staticmethod
    def _get_header_str(msg, name: str) -> str:
        """Get a header as a plain string from an email.message.Message."""
        val = msg[name]
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        return str(val)

    @staticmethod
    def _get_decoded_header(msg, name: str) -> str:
        """Get a decoded Subject-like header from an email.message.Message.

        Handles raw UTF-8 in headers without RFC 2047 encoding.
        Python's email library stores non-ASCII bytes as surrogate-escaped
        strings when charset='unknown-8bit'. We recover the original UTF-8.
        """
        raw_val = msg[name]
        if raw_val is None:
            return ""

        from email.header import Header
        if not isinstance(raw_val, Header):
            return raw_val

        # Header._chunks contains (data, charset) tuples.
        # When charset is 'unknown-8bit', individual bytes are stored as
        # surrogate-escaped codepoints in the \udc80-\udcff range.
        parts = []
        for chunk, charset in raw_val._chunks:
            if isinstance(chunk, bytes):
                parts.append(chunk.decode(charset or "utf-8", errors="replace"))
            elif isinstance(chunk, str) and charset == "unknown-8bit":
                raw_bytes = bytes(
                    ord(c) & 0xFF for c in chunk
                    if 0xDC80 <= ord(c) <= 0xDCFF
                )
                # Non-surrogate prefix (ASCII part) is already valid
                prefix = "".join(c for c in chunk if not (0xDC80 <= ord(c) <= 0xDCFF))
                parts.append(prefix + raw_bytes.decode("utf-8", errors="replace"))
            else:
                parts.append(chunk)
        return "".join(parts)

    def _parse_summary(
        self, uid: str, env_data, imap_flags: tuple
    ) -> Summary:
        subject = env_data.subject
        if isinstance(subject, bytes):
            subject = subject.decode(errors="replace")
        subject = self._decode_rfc2047(subject) if subject else subject

        from_ = None
        if env_data.from_:
            addr = env_data.from_[0]
            from_ = self._parse_imap_address(addr)

        to = []
        if env_data.to:
            to = [self._parse_imap_address(a) for a in env_data.to]

        date = env_data.date
        if date and date.tzinfo is None:
            # ENVELOPE date often lacks timezone info. Use the local
            # system timezone so the displayed time matches the user's
            # clock regardless of where in the world they are.
            date = date.replace(tzinfo=_local_timezone())

        flags = [Flag.from_imap(f.decode() if isinstance(f, bytes) else f) for f in imap_flags]
        flags = [f for f in flags if isinstance(f, Flag)]

        return Summary(
            id=uid,
            subject=subject,
            from_=from_,
            to=to,
            date=date,
            flags=flags,
        )

    def _parse_imap_address(self, addr) -> Address:
        name = addr.name
        if isinstance(name, bytes):
            name = name.decode(errors="replace")
        if name:
            name = self._decode_rfc2047(name)
        mailbox = addr.mailbox
        if isinstance(mailbox, bytes):
            mailbox = mailbox.decode(errors="replace")
        host = addr.host
        if isinstance(host, bytes):
            host = host.decode(errors="replace")

        email_addr = f"{mailbox}@{host}" if mailbox and host else ""
        return Address(name=name, email=email_addr)

    def _parse_message(
        self, uid: str, folder: str, raw_bytes: bytes, imap_flags: tuple
    ) -> Message:
        msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)

        # Parse headers — use get_header to handle raw bytes correctly
        subject = self._get_decoded_header(msg, "Subject")
        from_header = self._get_header_str(msg, "From")
        to_header = self._get_header_str(msg, "To")
        cc_header = self._get_header_str(msg, "Cc")
        date_header = self._get_header_str(msg, "Date")
        message_id = self._get_header_str(msg, "Message-ID")
        in_reply_to = self._get_header_str(msg, "In-Reply-To") or None
        references_header = self._get_header_str(msg, "References")

        from_ = self._parse_address_header(from_header)
        to = self._parse_address_list(to_header)
        cc = self._parse_address_list(cc_header)

        date = None
        if date_header:
            parsed = email.utils.parsedate_to_datetime(date_header)
            date = parsed if parsed else None

        references = references_header.split() if references_header else []

        flags = [Flag.from_imap(f.decode() if isinstance(f, bytes) else f) for f in imap_flags]
        flags = [f for f in flags if isinstance(f, Flag)]

        # Parse body and attachments
        body = MessageBody()
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition:
                    att = Attachment(
                        filename=part.get_filename(),
                        content_type=content_type,
                        size=len(part.get_payload(decode=True) or b""),
                    )
                    attachments.append(att)
                elif content_type == "text/plain" and not body.text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body.text = payload.decode(charset, errors="replace")
                elif content_type == "text/html" and not body.html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body.html = payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                if msg.get_content_type() == "text/html":
                    body.html = payload.decode(charset, errors="replace")
                else:
                    body.text = payload.decode(charset, errors="replace")

        return Message(
            id=uid,
            folder=folder,
            subject=subject,
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
            raw=raw_bytes,
        )

    def _parse_address_header(self, header: str) -> Address | None:
        header = str(header) if not isinstance(header, str) else header
        if not header:
            return None
        parsed = email.utils.parseaddr(header)
        name = self._decode_rfc2047(parsed[0]) if parsed[0] else None
        return Address(name=name or None, email=parsed[1])

    def _parse_address_list(self, header: str) -> list[Address]:
        header = str(header) if not isinstance(header, str) else header
        if not header:
            return []
        addrs = email.utils.getaddresses([header])
        result = []
        for name, addr in addrs:
            if not addr:
                continue
            decoded_name = self._decode_rfc2047(name) if name else None
            result.append(Address(name=decoded_name, email=addr))
        return result

    async def _resolve_password(self, auth) -> str:
        from ymailink.utils.password import resolve_password
        return await resolve_password(auth)


def _local_timezone() -> timezone:
    """Return the local system timezone as a datetime.timezone."""
    t = localtime()
    # localtime returns a struct_time; tm_gmtoff is the UTC offset in seconds
    return timezone(timedelta(seconds=t.tm_gmtoff))
