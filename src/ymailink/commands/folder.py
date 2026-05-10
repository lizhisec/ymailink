"""Folder commands: list, add, delete, expunge, purge."""

from __future__ import annotations

import argparse
import asyncio

from ymailink.config import load_config
from ymailink.output.printer import get_printer


def folder_list(args: argparse.Namespace) -> None:
    """List all folders."""
    asyncio.run(_folder_list(args))


async def _folder_list(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        folders = await backend.list_folders()
        printer.out(folders)


def folder_add(args: argparse.Namespace) -> None:
    """Create a new folder."""
    asyncio.run(_folder_add(args))


async def _folder_add(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        await backend.add_folder(args.name)
        printer.log(f"Folder '{args.name}' created.")


def folder_delete(args: argparse.Namespace) -> None:
    """Delete a folder."""
    asyncio.run(_folder_delete(args))


async def _folder_delete(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        await backend.delete_folder(args.name)
        printer.log(f"Folder '{args.name}' deleted.")


def folder_expunge(args: argparse.Namespace) -> None:
    """Expunge deleted messages in a folder."""
    asyncio.run(_folder_expunge(args))


async def _folder_expunge(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        await backend.expunge_folder(args.name)
        printer.log(f"Folder '{args.name}' expunged.")


def folder_purge(args: argparse.Namespace) -> None:
    """Purge all messages in a folder."""
    asyncio.run(_folder_purge(args))


async def _folder_purge(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    backend = await builder.build_read_backend()
    async with backend:
        # Paginate through all messages and delete them
        page_size = 500
        page = 1
        total = 0
        while True:
            summaries = await backend.list_summaries(args.name, page=page, page_size=page_size)
            if not summaries:
                break
            ids = [s.id for s in summaries]
            await backend.delete_messages(args.name, ids)
            total += len(ids)
            if len(summaries) < page_size:
                break
            page += 1
        if total:
            printer.log(f"Purged {total} messages from '{args.name}'.")
        else:
            printer.log(f"Folder '{args.name}' is already empty.")
