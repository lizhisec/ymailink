"""Template commands: write, reply, forward, save, send."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ymailink.config import load_config
from ymailink.output.printer import get_printer


def template_write(args: argparse.Namespace) -> None:
    """Create a new message template."""
    config = load_config(args.config_paths)
    printer = get_printer(args)

    _, acct = config.get_account(args.account)
    template = f"From: {acct.email}\nTo: \nSubject: \n\n"
    printer.out(template)


def template_reply(args: argparse.Namespace) -> None:
    """Create a reply template."""
    asyncio.run(_template_reply(args))


async def _template_reply(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder
    from ymailink.commands.mail import _reply_template

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        template = _reply_template(messages[0], builder.account_email, reply_all=args.all)
        printer.out(template)


def template_forward(args: argparse.Namespace) -> None:
    """Create a forward template."""
    asyncio.run(_template_forward(args))


async def _template_forward(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder
    from ymailink.commands.mail import _forward_template

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        template = _forward_template(messages[0], builder.account_email)
        printer.out(template)


def template_save(args: argparse.Namespace) -> None:
    """Save template as draft message."""
    asyncio.run(_template_save(args))


async def _template_save(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    if args.raw == "-" or args.raw is None:
        raw = sys.stdin.buffer.read()
    else:
        raw = args.raw.encode()

    backend = await builder.build_read_backend()
    async with backend:
        # Save to Drafts folder
        _, acct = config.get_account(args.account)
        drafts_folder = acct.folder.aliases.drafts
        await backend.add_message(drafts_folder, raw)
        printer.log(f"Template saved to '{drafts_folder}'.")


def template_send(args: argparse.Namespace) -> None:
    """Send a template."""
    asyncio.run(_template_send(args))


async def _template_send(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    if args.raw == "-" or args.raw is None:
        raw = sys.stdin.buffer.read()
    else:
        raw = args.raw.encode()

    send_backend = await builder.build_send_backend()
    async with send_backend:
        await send_backend.send_message(raw)
        printer.log("Template sent.")
