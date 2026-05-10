"""OAuth2 token management for Outlook and Gmail backends."""

from __future__ import annotations

import json
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from ymailink.config.defaults import get_token_path


class OAuthManager:
    """Manages OAuth2 token acquisition, caching, and refresh."""

    def __init__(
        self,
        provider: str,
        account_name: str,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        tenant_id: str = "common",
    ):
        self.provider = provider
        self.account_name = account_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []
        self.tenant_id = tenant_id
        self.token_path = get_token_path(provider, account_name)

    async def get_token(self) -> str:
        """Get a valid access token, refreshing or re-authorizing as needed."""
        token_data = self._load_token()

        if token_data and token_data.get("access_token"):
            # Try refresh if we have a refresh token
            if self._is_expired(token_data):
                token_data = await self._refresh_token(token_data)
                if token_data:
                    self._save_token(token_data)
                    return token_data["access_token"]
                # Refresh failed, re-authorize
                token_data = await self._authorize()
                self._save_token(token_data)
            return token_data["access_token"]

        # No token, need to authorize
        token_data = await self._authorize()
        self._save_token(token_data)
        return token_data["access_token"]

    async def _authorize(self) -> dict:
        """Start OAuth2 authorization flow."""
        if self.provider == "outlook":
            return await self._authorize_outlook()
        elif self.provider == "gmail":
            return await self._authorize_gmail()
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _authorize_outlook(self) -> dict:
        """Outlook OAuth2 authorization via MSAL."""
        try:
            import msal
        except ImportError:
            raise RuntimeError(
                "msal package required for Outlook auth. Install with: pip install ymailink[outlook]"
            )

        app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
        )

        flow = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to create device flow: {flow}")

        print(f"\nTo sign in, visit: {flow['verification_uri']}")
        print(f"Enter code: {flow['user_code']}\n")
        webbrowser.open(flow["verification_uri"])

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")

        return result

    async def _authorize_gmail(self) -> dict:
        """Gmail OAuth2 authorization via google-auth-oauthlib."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise RuntimeError(
                "google-auth-oauthlib required for Gmail auth. Install with: pip install ymailink[gmail]"
            )

        client_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
        creds = flow.run_local_server(port=0)

        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }

    async def _refresh_token(self, token_data: dict) -> dict | None:
        """Attempt to refresh the token."""
        if self.provider == "outlook":
            return await self._refresh_outlook(token_data)
        elif self.provider == "gmail":
            return await self._refresh_gmail(token_data)
        return None

    async def _refresh_outlook(self, token_data: dict) -> dict | None:
        try:
            import msal
        except ImportError:
            return None

        app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
        )

        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(self.scopes, account=accounts[0])
            if result and "access_token" in result:
                return result
        return None

    async def _refresh_gmail(self, token_data: dict) -> dict | None:
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            return None

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError:
            return None

        expiry_str = token_data.get("expiry")
        expiry = datetime.fromisoformat(expiry_str) if expiry_str else None

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=refresh_token,
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self.client_id,
            client_secret=self.client_secret,
            expiry=expiry,
        )

        if creds.expired and creds.refresh_token:
            import os
            import requests as req_lib

            session = req_lib.Session()
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            if proxy:
                session.proxies = {"https": proxy, "http": proxy}
            creds.refresh(Request(session=session))
            return {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            }
        return None

    def _is_expired(self, token_data: dict) -> bool:
        """Check if token appears expired."""
        expiry = token_data.get("expiry")
        if not expiry:
            return False
        try:
            exp_dt = datetime.fromisoformat(expiry)
            return exp_dt < datetime.now(timezone.utc)
        except (ValueError, TypeError):
            return False

    def _save_token(self, token_data: dict) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            json.dump(token_data, f, default=str)
        self.token_path.chmod(0o600)

    def _load_token(self) -> dict | None:
        if not self.token_path.exists():
            return None
        try:
            with open(self.token_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
