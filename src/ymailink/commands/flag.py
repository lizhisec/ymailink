"""Flag commands: add, set, remove."""

from __future__ import annotations

import argparse
import asyncio

from ymailink.config import load_config
from ymailink.domain.flag import Flag
from ymailink.output.printer import get_printer


def flag_add(args: argparse.Namespace) -> None:
    """Add flags to messages."""
    asyncio.run(_flag_add(args))


async def _flag_add(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    flags = [Flag.parse(f) for f in args.flags]

    backend = await builder.build_read_backend()
    async with backend:
        await backend.add_flags(args.folder, args.ids, flags)
        printer.log(f"Added flags {[f.value for f in flags]} to {len(args.ids)} message(s).")


def flag_set(args: argparse.Namespace) -> None:
    """Set flags on messages (replace existing)."""
    asyncio.run(_flag_set(args))


async def _flag_set(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    flags = [Flag.parse(f) for f in args.flags]

    backend = await builder.build_read_backend()
    async with backend:
        await backend.set_flags(args.folder, args.ids, flags)
        printer.log(f"Set flags {[f.value for f in flags]} on {len(args.ids)} message(s).")


def flag_remove(args: argparse.Namespace) -> None:
    """Remove flags from messages."""
    asyncio.run(_flag_remove(args))


async def _flag_remove(args: argparse.Namespace) -> None:
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)
    builder = BackendBuilder(config, args.account)

    flags = [Flag.parse(f) for f in args.flags]

    backend = await builder.build_read_backend()
    async with backend:
        await backend.remove_flags(args.folder, args.ids, flags)
        printer.log(f"Removed flags {[f.value for f in flags]} from {len(args.ids)} message(s).")
