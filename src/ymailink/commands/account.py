"""Account commands: list, doctor, configure."""

from __future__ import annotations

import argparse
import asyncio

from ymailink.config import load_config
from ymailink.domain.account import Account
from ymailink.output.printer import get_printer


def account_list(args: argparse.Namespace) -> None:
    """List all configured accounts."""
    config = load_config(args.config_paths)
    printer = get_printer(args)

    accounts = []
    for name, acct in config.accounts.items():
        accounts.append(Account(
            name=name,
            email=acct.email,
            display_name=acct.display_name,
            backend_type=acct.backend.type,
            is_default=acct.default,
        ))

    if not accounts:
        printer.log("No accounts configured. Run 'ymailink account configure' to add one.")
        return

    printer.out(accounts)


def account_doctor(args: argparse.Namespace) -> None:
    """Diagnose account connection."""
    config = load_config(args.config_paths)
    printer = get_printer(args)

    asyncio.run(_doctor(config, args, printer))


async def _doctor(config, args, printer) -> None:
    from ymailink.backend.builder import BackendBuilder

    builder = BackendBuilder(config, args.account)
    printer.log(f"Testing connection for account: {builder.account_name}")

    try:
        backend = await builder.build_read_backend()
        async with backend:
            folders = await backend.list_folders()
            printer.log(f"Connection successful. Found {len(folders)} folders.")
            printer.out(f"Account '{builder.account_name}' is working correctly.")
    except Exception as e:
        printer.error(f"Connection failed: {e}")


def account_configure(args: argparse.Namespace) -> None:
    """Interactively configure a new account."""
    printer = get_printer(args)
    printer.log("Interactive account configuration")

    # Interactive prompts
    print("\n--- New Account Configuration ---")
    name = input("Account name: ").strip()
    email_addr = input("Email address: ").strip()
    display_name = input("Display name (optional): ").strip() or None

    print("\nBackend type:")
    print("  1. IMAP + SMTP")
    print("  2. Outlook (Microsoft Graph)")
    print("  3. Gmail (Google API)")
    choice = input("Choice [1/2/3]: ").strip()

    if choice == "1":
        _configure_imap(name, email_addr, display_name)
    elif choice == "2":
        _configure_outlook(name, email_addr, display_name)
    elif choice == "3":
        _configure_gmail(name, email_addr, display_name)
    else:
        print("Invalid choice.")
        return

    print(f"\nAccount '{name}' configured. Add the above to your config.toml.")


def _configure_imap(name: str, email_addr: str, display_name: str | None) -> None:
    imap_host = input("IMAP host: ").strip()
    imap_port = input("IMAP port [993]: ").strip() or "993"
    smtp_host = input("SMTP host: ").strip()
    smtp_port = input("SMTP port [587]: ").strip() or "587"
    login = input(f"Login [{email_addr}]: ").strip() or email_addr

    print(f"\n# Add to config.toml:\n")
    print(f"[accounts.{name}]")
    print(f'email = "{email_addr}"')
    if display_name:
        print(f'display-name = "{display_name}"')
    print(f'\nbackend.type = "imap"')
    print(f'backend.host = "{imap_host}"')
    print(f"backend.port = {imap_port}")
    print(f'backend.login = "{login}"')
    print(f'backend.auth.type = "password"')
    print(f'backend.auth.cmd = "pass show email/{name}"')
    print(f'\nmessage.send.backend.type = "smtp"')
    print(f'message.send.backend.host = "{smtp_host}"')
    print(f"message.send.backend.port = {smtp_port}")
    print(f'message.send.backend.login = "{login}"')
    print(f'message.send.backend.auth.type = "password"')
    print(f'message.send.backend.auth.cmd = "pass show email/{name}"')


def _configure_outlook(name: str, email_addr: str, display_name: str | None) -> None:
    client_id = input("Azure App Client ID: ").strip()
    tenant_id = input("Tenant ID [common]: ").strip() or "common"

    print(f"\n# Add to config.toml:\n")
    print(f"[accounts.{name}]")
    print(f'email = "{email_addr}"')
    if display_name:
        print(f'display-name = "{display_name}"')
    print(f'\nbackend.type = "outlook"')
    print(f'backend.client-id = "{client_id}"')
    print(f'backend.tenant-id = "{tenant_id}"')
    print(f'\nmessage.send.backend.type = "outlook"')
    print(f'message.send.backend.client-id = "{client_id}"')
    print(f'message.send.backend.tenant-id = "{tenant_id}"')


def _configure_gmail(name: str, email_addr: str, display_name: str | None) -> None:
    client_id = input("Google Cloud Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()

    print(f"\n# Add to config.toml:\n")
    print(f"[accounts.{name}]")
    print(f'email = "{email_addr}"')
    if display_name:
        print(f'display-name = "{display_name}"')
    print(f'\nbackend.type = "gmail"')
    print(f'backend.client-id = "{client_id}"')
    print(f'backend.client-secret = "{client_secret}"')
    print(f'\nmessage.send.backend.type = "gmail"')
    print(f'message.send.backend.client-id = "{client_id}"')
    print(f'message.send.backend.client-secret = "{client_secret}"')
