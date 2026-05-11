"""Backend builder factory - creates backends from configuration."""

from __future__ import annotations

from ymailink.backend.base import ReadBackend, SendBackend
from ymailink.config.models import (
    ExchangeConfig,
    GmailConfig,
    ImapConfig,
    OutlookConfig,
    SmtpConfig,
    YmailConfig,
)


class BackendBuilder:
    """Factory for creating backend instances from config."""

    def __init__(self, config: YmailConfig, account_name: str | None = None):
        self._config = config
        self._account_name, self._account = config.get_account(account_name)

    async def build_read_backend(self) -> ReadBackend:
        """Build the read backend based on account config."""
        backend_cfg = self._account.backend

        if isinstance(backend_cfg, ImapConfig):
            from ymailink.backend.imap import ImapBackend
            return ImapBackend(backend_cfg)

        elif isinstance(backend_cfg, OutlookConfig):
            from ymailink.backend.outlook import OutlookBackend
            self._check_outlook_deps()
            return OutlookBackend(backend_cfg, self._account_name)

        elif isinstance(backend_cfg, GmailConfig):
            from ymailink.backend.gmail import GmailBackend
            self._check_gmail_deps()
            return GmailBackend(backend_cfg, self._account_name)

        elif isinstance(backend_cfg, ExchangeConfig):
            from ymailink.backend.exchange import ExchangeBackend
            self._check_exchange_deps()
            return ExchangeBackend(backend_cfg)

        raise ValueError(f"Unknown backend type: {type(backend_cfg)}")

    async def build_send_backend(self) -> SendBackend:
        """Build the send backend based on account config."""
        if self._account.send is None:
            raise ValueError(
                f"No send backend configured for account '{self._account_name}'"
            )

        send_cfg = self._account.send.backend

        if isinstance(send_cfg, SmtpConfig):
            from ymailink.backend.smtp import SmtpBackend
            return SmtpBackend(send_cfg)

        elif isinstance(send_cfg, OutlookConfig):
            from ymailink.backend.outlook import OutlookBackend
            return OutlookBackend(send_cfg, self._account_name)

        elif isinstance(send_cfg, GmailConfig):
            from ymailink.backend.gmail import GmailBackend
            return GmailBackend(send_cfg, self._account_name)

        elif isinstance(send_cfg, ExchangeConfig):
            from ymailink.backend.exchange import ExchangeBackend
            return ExchangeBackend(send_cfg)

        raise ValueError(f"Unknown send backend type: {type(send_cfg)}")

    @staticmethod
    def _check_outlook_deps() -> None:
        try:
            import httpx  # noqa: F401
            import msal  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "Missing Outlook dependencies. Install with: pip install ymailink[outlook]"
            ) from e

    @staticmethod
    def _check_exchange_deps() -> None:
        try:
            import exchangelib  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "Missing Exchange dependencies. Install with: pip install exchangelib"
            ) from e

    @staticmethod
    def _check_gmail_deps() -> None:
        try:
            from googleapiclient.discovery import build  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "Missing Gmail dependencies. Install with: pip install ymailink[gmail]"
            ) from e

    @property
    def account_name(self) -> str:
        return self._account_name

    @property
    def account_email(self) -> str:
        return self._account.email
