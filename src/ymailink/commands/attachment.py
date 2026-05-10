"""Attachment commands: download."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ymailink.config import load_config
from ymailink.output.printer import get_printer


def attachment_download(args: argparse.Namespace) -> None:
    """Download attachments from a message."""
    asyncio.run(_attachment_download(args))


async def _attachment_download(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    # Determine download directory
    download_dir = Path(args.dir) if args.dir else None
    if download_dir is None:
        _, acct = config.get_account(args.account)
        download_dir = acct.downloads_dir or config.downloads_dir
    if download_dir is None:
        download_dir = Path.home() / "Downloads"
    download_dir = Path(download_dir).expanduser()
    download_dir.mkdir(parents=True, exist_ok=True)

    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])
        if not messages:
            printer.error(f"Message {args.id} not found.")
            return

        msg = messages[0]
        if not msg.attachments:
            printer.log("No attachments found.")
            return

        for att in msg.attachments:
            if att.data:
                filename = att.filename or f"attachment_{att.id}"
                filepath = download_dir / filename
                filepath.write_bytes(att.data)
                printer.log(f"Downloaded: {filepath}")
            else:
                printer.log(f"Attachment '{att.filename}' has no data (download from server not yet supported for this backend).")
