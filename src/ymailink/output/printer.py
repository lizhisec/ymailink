"""Printer abstraction for output formatting."""

from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel
from rich.console import Console

from ymailink.domain.summary import Summary
from ymailink.domain.folder import Folder
from ymailink.domain.account import Account
from ymailink.domain.message import Message


class OutputFormat(str, Enum):
    PLAIN = "plain"
    JSON = "json"


class Printer(ABC):
    @abstractmethod
    def out(self, data: Any) -> None:
        ...

    @abstractmethod
    def log(self, message: str) -> None:
        ...

    @abstractmethod
    def error(self, message: str) -> None:
        ...


class StdoutPrinter(Printer):
    def __init__(self, format: OutputFormat, quiet: bool = False):
        self.format = format
        self.quiet = quiet
        self._console = Console(stderr=True, legacy_windows=False)
        # Ensure stdout uses UTF-8 on Windows to avoid GBK encoding errors
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

    def out(self, data: Any) -> None:
        if self.format == OutputFormat.JSON:
            self._out_json(data)
        else:
            self._out_plain(data)

    def _out_json(self, data: Any) -> None:
        if isinstance(data, list):
            items = [
                item.model_dump(mode="json") if isinstance(item, BaseModel) else item
                for item in data
            ]
            print(json.dumps(items, default=str, ensure_ascii=False, indent=2))
        elif isinstance(data, BaseModel):
            print(data.model_dump_json(indent=2))
        else:
            print(json.dumps(data, default=str, ensure_ascii=False, indent=2))

    def _out_plain(self, data: Any) -> None:
        from ymailink.output.table import (
            render_account_table,
            render_folder_table,
            render_message,
            render_summary_table,
        )

        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, Summary):
                render_summary_table(data)
            elif isinstance(first, Folder):
                render_folder_table(data)
            elif isinstance(first, Account):
                render_account_table(data)
            else:
                for item in data:
                    print(str(item))
        elif isinstance(data, Message):
            render_message(data)
        elif isinstance(data, BaseModel):
            print(str(data))
        elif isinstance(data, str):
            print(data)
        else:
            print(str(data))

    def log(self, message: str) -> None:
        if not self.quiet:
            self._console.print(f"[dim]{message}[/dim]")

    def error(self, message: str) -> None:
        self._console.print(f"[red]Error:[/red] {message}", style="bold")
        sys.exit(1)


def get_printer(args) -> StdoutPrinter:
    """Create a printer from parsed args."""
    fmt = OutputFormat(getattr(args, "output", "plain"))
    quiet = getattr(args, "quiet", False)
    return StdoutPrinter(format=fmt, quiet=quiet)
