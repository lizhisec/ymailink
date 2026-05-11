"""Pydantic configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field


# ---- Auth models ----


class PasswordAuth(BaseModel):
    type: Literal["password"] = "password"
    raw: str | None = None
    cmd: str | None = None
    keyring: str | None = None


# ---- Backend configs ----


class ImapConfig(BaseModel):
    type: Literal["imap"] = "imap"
    host: str
    port: int = 993
    encryption: Literal["none", "start-tls", "tls"] = "tls"
    login: str
    auth: PasswordAuth


class OutlookConfig(BaseModel):
    type: Literal["outlook"] = "outlook"
    client_id: str = Field(alias="client-id")
    client_secret: str | None = Field(default=None, alias="client-secret")
    tenant_id: str = Field(default="common", alias="tenant-id")
    scopes: list[str] = Field(default_factory=lambda: ["Mail.ReadWrite", "Mail.Send"])

    model_config = {"populate_by_name": True}


class GmailConfig(BaseModel):
    type: Literal["gmail"] = "gmail"
    client_id: str = Field(alias="client-id")
    client_secret: str = Field(alias="client-secret")
    scopes: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.modify"]
    )

    model_config = {"populate_by_name": True}


class ExchangeConfig(BaseModel):
    type: Literal["exchange"] = "exchange"
    host: str
    email: str
    login: str
    auth: PasswordAuth
    auth_type: str = "NTLM"
    autodiscover: bool = False
    access_type: str = "delegate"
    version: str | None = None  # e.g. "2016", "2019" — skips Version.guess()


class SmtpConfig(BaseModel):
    type: Literal["smtp"] = "smtp"
    host: str
    port: int = 587
    encryption: Literal["none", "start-tls", "tls"] = "tls"
    login: str
    auth: PasswordAuth


# Discriminated union types
BackendConfig = Annotated[
    ImapConfig | OutlookConfig | GmailConfig | ExchangeConfig,
    Field(discriminator="type"),
]

SendBackendConfig = Annotated[
    SmtpConfig | OutlookConfig | GmailConfig | ExchangeConfig,
    Field(discriminator="type"),
]


# ---- Folder config ----


class FolderAliases(BaseModel):
    inbox: str = "INBOX"
    sent: str = "Sent"
    drafts: str = "Drafts"
    trash: str = "Trash"
    junk: str = "Junk"


class FolderConfig(BaseModel):
    aliases: FolderAliases = Field(default_factory=FolderAliases)


# ---- Account config ----


class SendConfig(BaseModel):
    backend: SendBackendConfig


class AccountConfig(BaseModel):
    default: bool = False
    email: str
    display_name: str | None = Field(default=None, alias="display-name")
    signature: str | None = None
    downloads_dir: Path | None = Field(default=None, alias="downloads-dir")
    backend: BackendConfig
    send: SendConfig | None = None
    folder: FolderConfig = Field(default_factory=FolderConfig)

    model_config = {"populate_by_name": True}


# ---- AI config ----


class AiConfig(BaseModel):
    base_url: str = "https://ai.ymailink.com"
    api_key: str | None = Field(default=None, alias="api-key")
    model: str = "auto"

    model_config = {"populate_by_name": True}


# ---- Top-level config ----


class YmailConfig(BaseModel):
    downloads_dir: Path | None = Field(default=None, alias="downloads-dir")
    accounts: dict[str, AccountConfig] = Field(default_factory=dict)
    ai: AiConfig | None = None

    model_config = {"populate_by_name": True}

    def get_account(self, name: str | None = None) -> tuple[str, AccountConfig]:
        """Get account by name, or the default account."""
        if not self.accounts:
            raise ValueError("No accounts configured")

        if name:
            if name not in self.accounts:
                raise ValueError(f"Account '{name}' not found")
            return name, self.accounts[name]

        # Find default account
        for acct_name, acct in self.accounts.items():
            if acct.default:
                return acct_name, acct

        # Fall back to first account
        first_name = next(iter(self.accounts))
        return first_name, self.accounts[first_name]
