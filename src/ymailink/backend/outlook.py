"""Outlook backend implementation using Microsoft Graph API."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from datetime import datetime, timezone

from ymailink.backend.base import ReadBackend, SendBackend
from ymailink.backend.oauth import OAuthManager
from ymailink.config.models import OutlookConfig
from ymailink.domain.attachment import Attachment
from ymailink.domain.summary import Address, Summary
from ymailink.domain.flag import Flag
from ymailink.domain.folder import Folder
from ymailink.domain.message import Message, MessageBody


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OutlookBackend(ReadBackend, SendBackend):
    """Microsoft Graph API backend for Outlook."""

    def __init__(self, config: OutlookConfig, account_name: str):
        self._config = config
        self._account_name = account_name
        self._oauth = OAuthManager(
            provider="outlook",
            account_name=account_name,
            client_id=config.client_id,
            client_secret=config.client_secret,
            scopes=config.scopes,
            tenant_id=config.tenant_id,
        )
        self._token: str | None = None
        self._session = None

    async def connect(self) -> None:
        import os

        self._token = await self._oauth.get_token()
        try:
            import httpx
        except ImportError:
            raise RuntimeError(
                "httpx package required for Outlook backend. Install with: pip install httpx"
            )

        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        proxies = {"https://": proxy, "http://": proxy} if proxy else None

        self._session = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._token}"},
            base_url=GRAPH_BASE,
            proxies=proxies,
            timeout=30.0,
        )

    async def disconnect(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None

    async def _get(self, path: str, params: dict | None = None) -> dict:
        resp = await self._session.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, json: dict | None = None) -> dict | None:
        resp = await self._session.post(path, json=json)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return None

    async def _patch(self, path: str, json: dict) -> dict:
        resp = await self._session.patch(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, path: str) -> None:
        resp = await self._session.delete(path)
        resp.raise_for_status()

    # ---- Folder operations ----

    async def list_folders(self) -> list[Folder]:
        data = await self._get("/me/mailFolders", params={"$top": "100"})
        folders = []
        for item in data.get("value", []):
            folders.append(Folder(
                name=item["displayName"],
                count=item.get("totalItemCount"),
                unread=item.get("unreadItemCount"),
            ))
        return folders

    async def add_folder(self, name: str) -> None:
        await self._post("/me/mailFolders", json={"displayName": name})

    async def delete_folder(self, name: str) -> None:
        folder_id = await self._resolve_folder_id(name)
        await self._delete(f"/me/mailFolders/{folder_id}")

    async def expunge_folder(self, name: str) -> None:
        # Graph API doesn't have a direct expunge; skip deleted messages
        pass

    # ---- Summary operations ----

    async def list_summaries(
        self,
        folder: str,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
    ) -> list[Summary]:
        folder_id = await self._resolve_folder_id(folder)
        skip = (page - 1) * page_size
        params = {
            "$top": str(page_size),
            "$skip": str(skip),
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,flag,hasAttachments",
        }
        if query:
            params["$search"] = f'"{query}"'

        data = await self._get(f"/me/mailFolders/{folder_id}/messages", params=params)
        summaries = []
        for item in data.get("value", []):
            summaries.append(self._parse_summary(item))
        return summaries

    # ---- Message operations ----

    async def get_messages(self, folder: str, ids: Sequence[str]) -> list[Message]:
        messages = []
        for msg_id in ids:
            data = await self._get(f"/me/messages/{msg_id}")
            attachments = []
            if data.get("hasAttachments"):
                att_data = await self._get(f"/me/messages/{msg_id}/attachments")
                for att in att_data.get("value", []):
                    attachments.append(Attachment(
                        id=att["id"],
                        filename=att.get("name"),
                        content_type=att.get("contentType", "application/octet-stream"),
                        size=att.get("size"),
                    ))
            messages.append(self._parse_message(data, folder, attachments))
        return messages

    async def add_message(self, folder: str, raw: bytes) -> None:
        # Upload as MIME content
        folder_id = await self._resolve_folder_id(folder)
        resp = await self._session.post(
            f"/me/mailFolders/{folder_id}/messages",
            content=raw,
            headers={"Content-Type": "text/plain"},
        )
        resp.raise_for_status()

    async def copy_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        target_id = await self._resolve_folder_id(target)
        for msg_id in ids:
            await self._post(
                f"/me/messages/{msg_id}/copy",
                json={"destinationId": target_id},
            )

    async def move_messages(
        self, source: str, target: str, ids: Sequence[str]
    ) -> None:
        target_id = await self._resolve_folder_id(target)
        for msg_id in ids:
            await self._post(
                f"/me/messages/{msg_id}/move",
                json={"destinationId": target_id},
            )

    async def delete_messages(self, folder: str, ids: Sequence[str]) -> None:
        for msg_id in ids:
            await self._delete(f"/me/messages/{msg_id}")

    # ---- Flag operations ----

    async def add_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        updates = self._flags_to_graph_patch(flags, add=True)
        for msg_id in ids:
            await self._patch(f"/me/messages/{msg_id}", json=updates)

    async def set_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        updates = self._flags_to_graph_patch(flags, add=True)
        for msg_id in ids:
            await self._patch(f"/me/messages/{msg_id}", json=updates)

    async def remove_flags(
        self, folder: str, ids: Sequence[str], flags: Sequence[Flag]
    ) -> None:
        updates = self._flags_to_graph_patch(flags, add=False)
        for msg_id in ids:
            await self._patch(f"/me/messages/{msg_id}", json=updates)

    # ---- Send ----

    async def send_message(self, raw: bytes) -> None:
        # Send via Graph API using MIME
        resp = await self._session.post(
            "/me/sendMail",
            content=raw,
            headers={"Content-Type": "text/plain"},
        )
        resp.raise_for_status()

    # ---- Helpers ----

    async def _resolve_folder_id(self, name: str) -> str:
        """Resolve folder display name to Graph API folder ID."""
        # Well-known folder names map directly
        well_known = {
            "INBOX": "inbox",
            "Sent": "sentitems",
            "Drafts": "drafts",
            "Trash": "deleteditems",
            "Junk": "junkemail",
        }
        if name in well_known:
            return well_known[name]

        # Search by display name
        data = await self._get(
            "/me/mailFolders",
            params={"$filter": f"displayName eq '{name}'"},
        )
        items = data.get("value", [])
        if items:
            return items[0]["id"]
        raise ValueError(f"Folder not found: {name}")

    def _parse_summary(self, item: dict) -> Summary:
        from_ = None
        if item.get("from"):
            addr_data = item["from"].get("emailAddress", {})
            from_ = Address(
                name=addr_data.get("name"),
                email=addr_data.get("address", ""),
            )

        to = []
        for r in item.get("toRecipients", []):
            addr_data = r.get("emailAddress", {})
            to.append(Address(
                name=addr_data.get("name"),
                email=addr_data.get("address", ""),
            ))

        date = None
        if item.get("receivedDateTime"):
            date = datetime.fromisoformat(item["receivedDateTime"].replace("Z", "+00:00"))

        flags = []
        if item.get("isRead"):
            flags.append(Flag.SEEN)
        if item.get("flag", {}).get("flagStatus") == "flagged":
            flags.append(Flag.FLAGGED)

        return Summary(
            id=item["id"],
            subject=item.get("subject"),
            from_=from_,
            to=to,
            date=date,
            flags=flags,
            has_attachment=item.get("hasAttachments", False),
        )

    def _parse_message(
        self, item: dict, folder: str, attachments: list[Attachment]
    ) -> Message:
        from_ = None
        if item.get("from"):
            addr_data = item["from"].get("emailAddress", {})
            from_ = Address(
                name=addr_data.get("name"),
                email=addr_data.get("address", ""),
            )

        to = []
        for r in item.get("toRecipients", []):
            addr_data = r.get("emailAddress", {})
            to.append(Address(name=addr_data.get("name"), email=addr_data.get("address", "")))

        cc = []
        for r in item.get("ccRecipients", []):
            addr_data = r.get("emailAddress", {})
            cc.append(Address(name=addr_data.get("name"), email=addr_data.get("address", "")))

        date = None
        if item.get("receivedDateTime"):
            date = datetime.fromisoformat(item["receivedDateTime"].replace("Z", "+00:00"))

        flags = []
        if item.get("isRead"):
            flags.append(Flag.SEEN)
        if item.get("flag", {}).get("flagStatus") == "flagged":
            flags.append(Flag.FLAGGED)

        body_data = item.get("body", {})
        body = MessageBody()
        if body_data.get("contentType") == "html":
            body.html = body_data.get("content")
        else:
            body.text = body_data.get("content")

        return Message(
            id=item["id"],
            folder=folder,
            subject=item.get("subject"),
            from_=from_,
            to=to,
            cc=cc,
            date=date,
            flags=flags,
            message_id=item.get("internetMessageId"),
            body=body,
            attachments=attachments,
        )

    def _flags_to_graph_patch(self, flags: Sequence[Flag], add: bool) -> dict:
        patch: dict = {}
        if Flag.SEEN in flags:
            patch["isRead"] = add
        if Flag.FLAGGED in flags:
            patch["flag"] = {"flagStatus": "flagged" if add else "notFlagged"}
        return patch
