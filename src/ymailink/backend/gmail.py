"""Gmail backend implementation using Google Gmail API."""

from __future__ import annotations

import asyncio
import base64
import email as email_lib
import email.utils
from collections.abc import Sequence
from datetime import datetime, timezone

from ymailink.backend.base import ReadBackend, SendBackend
from ymailink.backend.oauth import OAuthManager
from ymailink.config.models import GmailConfig
from ymailink.domain.attachment import Attachment
from ymailink.domain.summary import Address, Summary
from ymailink.domain.flag import Flag
from ymailink.domain.folder import Folder
from ymailink.domain.message import Message, MessageBody


class GmailBackend(ReadBackend, SendBackend):
    """Google Gmail API backend."""

    def __init__(self, config: GmailConfig, account_name: str):
        self._config = config
        self._account_name = account_name
        self._oauth = OAuthManager(
            provider="gmail",
            account_name=account_name,
            client_id=config.client_id,
            client_secret=config.client_secret,
            scopes=config.scopes,
        )
        self._service = None

    async def _run(self, request):
        """Execute a googleapiclient request in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(request.execute)

    async def connect(self) -> None:
        import os
        import logging
        from urllib.parse import urlparse

        logger = logging.getLogger(__name__)

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "google-api-python-client required for Gmail. Install with: pip install ymailink[gmail]"
            )

        try:
            import httplib2
            from google_auth_httplib2 import AuthorizedHttp
        except ImportError:
            raise RuntimeError(
                "httplib2 and google-auth-httplib2 required for Gmail. Install with: pip install ymailink[gmail]"
            )

        token_data = self._oauth._load_token()
        if not token_data:
            token_data = await self._oauth._authorize()
            self._oauth._save_token(token_data)

        expiry_str = token_data.get("expiry")
        expiry = datetime.fromisoformat(expiry_str) if expiry_str else None

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self._config.client_id,
            client_secret=self._config.client_secret,
            scopes=self._config.scopes,
            expiry=expiry,
        )

        # Refresh if expired or about to expire
        if creds.expired or not creds.valid:
            import requests as req_lib

            session = req_lib.Session()
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            if proxy:
                session.proxies = {"https": proxy, "http": proxy}

            refresh_req = Request(session=session)
            try:
                creds.refresh(refresh_req)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to refresh Gmail token for account '{self._account_name}'. "
                    f"Re-authentication may be required. Error: {e}"
                ) from e
            self._oauth._save_token({
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            })

        # Build HTTP transport with proxy support
        http = httplib2.Http(timeout=30)
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            try:
                parsed = urlparse(proxy)
                host = parsed.hostname
                port = parsed.port
                if not host:
                    raise ValueError(f"Could not parse proxy host from URL: {proxy}")
                proxy_type = _get_proxy_type(parsed.scheme)
                pi = httplib2.ProxyInfo(proxy_type, host, port or 8080)
                http = httplib2.Http(proxy_info=pi, timeout=30)
            except Exception as e:
                logger.warning(
                    "Failed to configure proxy from %s=%s: %s. Proceeding without proxy.",
                    "HTTPS_PROXY" if os.environ.get("HTTPS_PROXY") else "https_proxy",
                    proxy, e,
                )

        authorized_http = AuthorizedHttp(creds, http=http)
        self._service = build("gmail", "v1", http=authorized_http)

    async def disconnect(self) -> None:
        self._service = None

    # ---- Folder operations ----

    async def list_folders(self) -> list[Folder]:
        results = await self._run(
            self._service.users().labels().list(userId="me")
        )
        folders = []
        for label in results.get("labels", []):
            detail = await self._run(
                self._service.users()
                .labels()
                .get(userId="me", id=label["id"])
            )
            folders.append(Folder(
                name=label["name"],
                count=detail.get("messagesTotal"),
                unread=detail.get("messagesUnread"),
            ))
        return folders

    async def add_folder(self, name: str) -> None:
        await self._run(
            self._service.users().labels().create(
                userId="me", body={"name": name}
            )
        )

    async def delete_folder(self, name: str) -> None:
        label_id = await self._resolve_label_id(name)
        await self._run(
            self._service.users().labels().delete(userId="me", id=label_id)
        )

    async def expunge_folder(self, name: str) -> None:
        # Gmail doesn't have expunge - trash is auto-cleaned
        pass

    # ---- Summary operations ----

    async def list_summaries(
        self,
        folder: str,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
    ) -> list[Summary]:
        label_id = await self._resolve_label_id(folder)
        q = query or ""

        results = await self._run(
            self._service.users()
            .messages()
            .list(userId="me", labelIds=[label_id], maxResults=page_size, q=q)
        )

        messages = results.get("messages", [])
        summaries = []

        for msg_ref in messages:
            msg = await self._run(
                self._service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="metadata",
                     metadataHeaders=["Subject", "From", "To", "Date"])
            )
            summaries.append(self._parse_summary(msg))

        return summaries

    # ---- Message operations ----

    async def get_messages(self, folder: str, ids: Sequence[str]) -> list[Message]:
        messages = []
        for msg_id in ids:
            msg = await self._run(
                self._service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
            )
            messages.append(self._parse_message(msg, folder))
        return messages

    async def add_message(self, folder: str, raw: bytes) -> None:
        label_id = await self._resolve_label_id(folder)
        encoded = base64.urlsafe_b64encode(raw).decode()
        await self._run(
            self._service.users().messages().insert(
                userId="me", body={"raw": encoded, "labelIds": [label_id]}
            )
        )

    async def copy_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        target_id = await self._resolve_label_id(target)
        for msg_id in ids:
            await self._run(
                self._service.users().messages().modify(
                    userId="me", id=msg_id,
                    body={"addLabelIds": [target_id]},
                )
            )

    async def move_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        source_id = await self._resolve_label_id(source)
        target_id = await self._resolve_label_id(target)
        for msg_id in ids:
            await self._run(
                self._service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"addLabelIds": [target_id], "removeLabelIds": [source_id]},
                )
            )

    async def delete_messages(self, folder: str, ids: Sequence[str]) -> None:
        for msg_id in ids:
            await self._run(
                self._service.users().messages().trash(userId="me", id=msg_id)
            )

    # ---- Flag operations ----

    async def add_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        add_labels, remove_labels = self._flags_to_label_changes(flags, add=True)
        for msg_id in ids:
            await self._run(
                self._service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"addLabelIds": add_labels, "removeLabelIds": remove_labels},
                )
            )

    async def set_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        await self.add_flags(folder, ids, flags)

    async def remove_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        add_labels, remove_labels = self._flags_to_label_changes(flags, add=False)
        for msg_id in ids:
            await self._run(
                self._service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"addLabelIds": add_labels, "removeLabelIds": remove_labels},
                )
            )

    # ---- Send ----

    async def send_message(self, raw: bytes) -> None:
        encoded = base64.urlsafe_b64encode(raw).decode()
        await self._run(
            self._service.users().messages().send(
                userId="me", body={"raw": encoded}
            )
        )

    # ---- Helpers ----

    async def _resolve_label_id(self, name: str) -> str:
        """Resolve folder name to Gmail label ID."""
        well_known = {
            "INBOX": "INBOX",
            "Sent": "SENT",
            "Drafts": "DRAFT",
            "Trash": "TRASH",
            "Junk": "SPAM",
            "Spam": "SPAM",
        }
        if name in well_known:
            return well_known[name]

        results = await self._run(
            self._service.users().labels().list(userId="me")
        )
        for label in results.get("labels", []):
            if label["name"] == name:
                return label["id"]
        raise ValueError(f"Label not found: {name}")

    def _parse_summary(self, msg: dict) -> Summary:
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        from_ = None
        if "from" in headers:
            parsed = email_lib.utils.parseaddr(headers["from"])
            from_ = Address(name=parsed[0] or None, email=parsed[1])

        to = []
        if "to" in headers:
            addrs = email_lib.utils.getaddresses([headers["to"]])
            to = [Address(name=n or None, email=a) for n, a in addrs if a]

        date = None
        if "date" in headers:
            try:
                date = email_lib.utils.parsedate_to_datetime(headers["date"])
            except (ValueError, TypeError):
                pass

        # Gmail labels to flags
        label_ids = msg.get("labelIds", [])
        flags = []
        if "UNREAD" not in label_ids:
            flags.append(Flag.SEEN)
        if "STARRED" in label_ids:
            flags.append(Flag.FLAGGED)
        if "DRAFT" in label_ids:
            flags.append(Flag.DRAFT)

        return Summary(
            id=msg["id"],
            subject=headers.get("subject"),
            from_=from_,
            to=to,
            date=date,
            flags=flags,
            thread_id=msg.get("threadId"),
        )

    def _parse_message(self, msg: dict, folder: str) -> Message:
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        from_ = None
        if "from" in headers:
            parsed = email_lib.utils.parseaddr(headers["from"])
            from_ = Address(name=parsed[0] or None, email=parsed[1])

        to = []
        if "to" in headers:
            addrs = email_lib.utils.getaddresses([headers["to"]])
            to = [Address(name=n or None, email=a) for n, a in addrs if a]

        cc = []
        if "cc" in headers:
            addrs = email_lib.utils.getaddresses([headers["cc"]])
            cc = [Address(name=n or None, email=a) for n, a in addrs if a]

        date = None
        if "date" in headers:
            try:
                date = email_lib.utils.parsedate_to_datetime(headers["date"])
            except (ValueError, TypeError):
                pass

        label_ids = msg.get("labelIds", [])
        flags = []
        if "UNREAD" not in label_ids:
            flags.append(Flag.SEEN)
        if "STARRED" in label_ids:
            flags.append(Flag.FLAGGED)

        # Parse body
        body = MessageBody()
        attachments = []
        self._extract_parts(msg.get("payload", {}), body, attachments)

        return Message(
            id=msg["id"],
            folder=folder,
            subject=headers.get("subject"),
            from_=from_,
            to=to,
            cc=cc,
            date=date,
            flags=flags,
            message_id=headers.get("message-id"),
            in_reply_to=headers.get("in-reply-to"),
            body=body,
            attachments=attachments,
        )

    def _extract_parts(
        self, payload: dict, body: MessageBody, attachments: list[Attachment]
    ) -> None:
        """Recursively extract body text and attachments from payload."""
        mime_type = payload.get("mimeType", "")
        parts = payload.get("parts", [])

        if parts:
            for part in parts:
                self._extract_parts(part, body, attachments)
        else:
            # Leaf part
            data = payload.get("body", {}).get("data", "")
            if payload.get("filename"):
                attachments.append(Attachment(
                    id=payload.get("body", {}).get("attachmentId"),
                    filename=payload.get("filename"),
                    content_type=mime_type,
                    size=payload.get("body", {}).get("size"),
                ))
            elif mime_type == "text/plain" and not body.text:
                body.text = base64.urlsafe_b64decode(data).decode(errors="replace") if data else None
            elif mime_type == "text/html" and not body.html:
                body.html = base64.urlsafe_b64decode(data).decode(errors="replace") if data else None

    def _flags_to_label_changes(
        self, flags: Sequence[Flag], add: bool
    ) -> tuple[list[str], list[str]]:
        """Convert flags to Gmail label add/remove lists."""
        add_labels: list[str] = []
        remove_labels: list[str] = []

        for flag in flags:
            if flag == Flag.SEEN:
                if add:
                    remove_labels.append("UNREAD")
                else:
                    add_labels.append("UNREAD")
            elif flag == Flag.FLAGGED:
                if add:
                    add_labels.append("STARRED")
                else:
                    remove_labels.append("STARRED")

        return add_labels, remove_labels


def _get_proxy_type(scheme: str) -> int:
    """Map a proxy URL scheme to an httplib2/socks proxy type constant."""
    import httplib2

    if scheme in ("socks5", "socks"):
        return httplib2.socks.PROXY_TYPE_SOCKS5
    if scheme == "socks4":
        return httplib2.socks.PROXY_TYPE_SOCKS4
    return httplib2.socks.PROXY_TYPE_HTTP

