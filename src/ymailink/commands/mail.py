"""Mail commands: list, thread, read, write, send, reply, forward, copy, move, delete."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ymailink.config import load_config
from ymailink.output.printer import get_printer


def mail_list(args: argparse.Namespace) -> None:
    """List messages in a folder."""
    asyncio.run(_mail_list(args))


async def _mail_list(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        summaries = await backend.list_summaries(
            folder=args.folder,
            page=args.page,
            page_size=args.page_size,
            query=args.query,
        )
        if not summaries:
            printer.log("No messages found.")
            return
        printer.out(summaries)


def mail_thread(args: argparse.Namespace) -> None:
    """View email thread for a message."""
    asyncio.run(_mail_thread(args))


async def _mail_thread(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        msg = messages[0]
        printer.log(f"Thread for message: {msg.subject}")
        printer.out(messages)


def mail_read(args: argparse.Namespace) -> None:
    """Read a message."""
    asyncio.run(_mail_read(args))


async def _mail_read(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        from ymailink.domain.flag import Flag
        await backend.add_flags(args.folder, [args.id], [Flag.SEEN])

        printer.out(messages[0])


def mail_write(args: argparse.Namespace) -> None:
    """Compose a new message using $EDITOR."""
    asyncio.run(_mail_write(args))


async def _mail_write(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder
    from ymailink.utils.editor import open_editor

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    template = _compose_template(builder.account_email, args)

    content = open_editor(template)
    if not content or content.strip() == template.strip():
        printer.log("Message unchanged, not sent.")
        return

    raw = content.encode()
    send_backend = await builder.build_send_backend()
    async with send_backend:
        await send_backend.send_message(raw)
        printer.log("Message sent.")


def mail_send(args: argparse.Namespace) -> None:
    """Send a raw message."""
    asyncio.run(_mail_send(args))


async def _mail_send(args: argparse.Namespace) -> None:
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
        printer.log("Message sent.")


def mail_reply(args: argparse.Namespace) -> None:
    """Reply to a message."""
    asyncio.run(_mail_reply(args))


async def _mail_reply(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder
    from ymailink.utils.editor import open_editor

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        msg = messages[0]
        template = _reply_template(msg, builder.account_email, reply_all=args.all)

        content = open_editor(template)
        if not content or content.strip() == template.strip():
            printer.log("Reply unchanged, not sent.")
            return

        raw = content.encode()
        send_backend = await builder.build_send_backend()
        async with send_backend:
            await send_backend.send_message(raw)
            printer.log("Reply sent.")


def mail_forward(args: argparse.Namespace) -> None:
    """Forward a message."""
    asyncio.run(_mail_forward(args))


async def _mail_forward(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder
    from ymailink.utils.editor import open_editor

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        msg = messages[0]
        template = _forward_template(msg, builder.account_email)

        content = open_editor(template)
        if not content or content.strip() == template.strip():
            printer.log("Forward unchanged, not sent.")
            return

        raw = content.encode()
        send_backend = await builder.build_send_backend()
        async with send_backend:
            await send_backend.send_message(raw)
            printer.log("Forwarded message sent.")


def mail_copy(args: argparse.Namespace) -> None:
    """Copy messages to another folder."""
    asyncio.run(_mail_copy(args))


async def _mail_copy(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        await backend.copy_messages(args.folder, args.target, args.ids)
        printer.log(f"Copied {len(args.ids)} message(s) to '{args.target}'.")


def mail_move(args: argparse.Namespace) -> None:
    """Move messages to another folder."""
    asyncio.run(_mail_move(args))


async def _mail_move(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        await backend.move_messages(args.folder, args.target, args.ids)
        printer.log(f"Moved {len(args.ids)} message(s) to '{args.target}'.")


def mail_delete(args: argparse.Namespace) -> None:
    """Delete messages."""
    asyncio.run(_mail_delete(args))


async def _mail_delete(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        await backend.delete_messages(args.folder, args.ids)
        printer.log(f"Deleted {len(args.ids)} message(s).")


# ---- Template helpers ----


def _compose_template(from_email: str, args: argparse.Namespace) -> str:
    lines = [f"From: {from_email}"]
    if args.headers:
        for h in args.headers:
            if ":" in h:
                lines.append(h.strip())
    lines.append("To: ")
    lines.append("Subject: ")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def _reply_template(msg, from_email: str, reply_all: bool = False) -> str:
    subject = msg.subject or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    to = str(msg.from_) if msg.from_ else ""
    cc = ""
    if reply_all and msg.to:
        cc_addrs = [str(a) for a in msg.to if a.email != from_email]
        if msg.cc:
            cc_addrs.extend(str(a) for a in msg.cc)
        cc = f"Cc: {', '.join(cc_addrs)}\n" if cc_addrs else ""

    in_reply_to = f"In-Reply-To: {msg.message_id}\n" if msg.message_id else ""
    references = ""
    if msg.references:
        refs = " ".join(msg.references)
        if msg.message_id:
            refs += f" {msg.message_id}"
        references = f"References: {refs}\n"

    quote = ""
    body_text = msg.body.text or ""
    if body_text:
        date_str = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else ""
        quote = f"\n\nOn {date_str}, {msg.from_} wrote:\n"
        quote += "\n".join(f"> {line}" for line in body_text.splitlines())

    return (
        f"From: {from_email}\n"
        f"To: {to}\n"
        f"{cc}"
        f"Subject: {subject}\n"
        f"{in_reply_to}"
        f"{references}"
        f"\n"
        f"{quote}"
    )


def _forward_template(msg, from_email: str) -> str:
    subject = msg.subject or ""
    if not subject.lower().startswith("fwd:"):
        subject = f"Fwd: {subject}"

    body_text = msg.body.text or ""
    fwd_body = (
        f"\n\n---------- Forwarded message ----------\n"
        f"From: {msg.from_}\n"
        f"Date: {msg.date}\n"
        f"Subject: {msg.subject}\n"
        f"To: {', '.join(str(a) for a in msg.to)}\n\n"
        f"{body_text}"
    )

    return (
        f"From: {from_email}\n"
        f"To: \n"
        f"Subject: {subject}\n"
        f"\n"
        f"{fwd_body}"
    )
