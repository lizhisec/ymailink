"""SMTP backend implementation using aiosmtplib."""

from __future__ import annotations

import asyncio
import email as email_lib
import email.utils

import aiosmtplib

from ymailink.backend.base import SendBackend
from ymailink.config.models import PasswordAuth, SmtpConfig


class SmtpBackend(SendBackend):
    def __init__(self, config: SmtpConfig):
        self._config = config
        self._client: aiosmtplib.SMTP | None = None

    async def connect(self) -> None:
        use_tls = self._config.encryption == "tls"
        start_tls = self._config.encryption == "start-tls"

        self._client = aiosmtplib.SMTP(
            hostname=self._config.host,
            port=self._config.port,
            use_tls=use_tls,
            start_tls=start_tls,
        )
        await self._client.connect()

        password = await self._resolve_password(self._config.auth)
        await self._client.login(self._config.login, password)

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.quit()
            except Exception:
                pass
            self._client = None

    async def send_message(self, raw: bytes) -> None:
        if not self._client:
            raise RuntimeError("SMTP not connected")

        # Parse recipients and envelope-from from the raw MIME message
        msg = email_lib.message_from_bytes(raw)
        sender = msg.get("From", self._config.login)
        recipients: list[str] = []

        to_header = msg.get("To", "")
        if to_header:
            recipients.extend(
                addr for _, addr in email_lib.utils.getaddresses([to_header]) if addr
            )
        cc_header = msg.get("Cc", "")
        if cc_header:
            recipients.extend(
                addr for _, addr in email_lib.utils.getaddresses([cc_header]) if addr
            )
        bcc_header = msg.get("Bcc", "")
        if bcc_header:
            recipients.extend(
                addr for _, addr in email_lib.utils.getaddresses([bcc_header]) if addr
            )

        if not recipients:
            raise RuntimeError("No recipients found in the message")

        raw = self._ensure_header_encoding(msg, raw)
        await self._client.sendmail(sender, recipients, raw)

    @staticmethod
    def _ensure_header_encoding(msg, raw: bytes) -> bytes:
        """Check for non-ASCII headers and RFC 2047 encode them if needed."""
        for key in msg.keys():
            for val in msg.get_all(key) or []:
                try:
                    str(val).encode("ascii")
                except UnicodeEncodeError:
                    # non-ASCII found -> rebuild with SMTP policy
                    from email.message import EmailMessage
                    from email import policy as email_policy

                    fixed = EmailMessage(policy=email_policy.SMTP)
                    for k in msg.keys():
                        for v in msg.get_all(k) or []:
                            fixed[k] = str(v)
                    if msg.is_multipart():
                        for part in msg.iter_parts():
                            payload = part.get_payload(decode=True)
                            if payload is not None:
                                content_type = part.get_content_type()
                                main, sub = content_type.split("/", 1)
                                fixed.add_attachment(
                                    payload,
                                    maintype=main,
                                    subtype=sub,
                                    filename=part.get_filename(),
                                )
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset = msg.get_content_charset() or "utf-8"
                            fixed.set_content(payload.decode(charset, errors="replace"))
                    return fixed.as_bytes()
        return raw

    async def _resolve_password(self, auth: PasswordAuth) -> str:
        from ymailink.utils.password import resolve_password
        return await resolve_password(auth)
