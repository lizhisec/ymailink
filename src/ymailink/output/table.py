"""Rich table rendering for domain models."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

from ymailink.domain.account import Account
from ymailink.domain.folder import Folder
from ymailink.domain.flag import Flag
from ymailink.domain.message import Message
from ymailink.domain.summary import Summary


console = Console(legacy_windows=False)


def render_summary_table(summaries: list[Summary]) -> None:
    """Render a list of summaries as a Rich table."""
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("ID", style="dim", width=16)
    table.add_column("Flags", width=5)
    table.add_column("From", min_width=20)
    table.add_column("Subject", min_width=30)
    table.add_column("Date", width=16)

    for s in summaries:
        flags = _format_flags(s.flags)
        from_str = str(s.from_) if s.from_ else ""
        date_str = s.date.strftime("%Y-%m-%d %H:%M") if s.date else ""
        subject = s.subject or "(no subject)"

        # Dim read messages
        style = "dim" if Flag.SEEN in s.flags else ""

        table.add_row(
            s.id[:16],
            flags,
            from_str,
            subject,
            date_str,
            style=style,
        )

    console.print(table)


def render_folder_table(folders: list[Folder]) -> None:
    """Render a list of folders as a Rich table."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", min_width=20)
    table.add_column("Messages", justify="right", width=10)
    table.add_column("Unread", justify="right", width=10)

    for folder in folders:
        count = str(folder.count) if folder.count is not None else "-"
        unread = str(folder.unread) if folder.unread is not None else "-"
        table.add_row(folder.name, count, unread)

    console.print(table)


def render_account_table(accounts: list[Account]) -> None:
    """Render a list of accounts as a Rich table."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", min_width=12)
    table.add_column("Email", min_width=25)
    table.add_column("Backend", width=10)
    table.add_column("Default", width=8)

    for acct in accounts:
        default_mark = "*" if acct.is_default else ""
        table.add_row(acct.name, acct.email, acct.backend_type, default_mark)

    console.print(table)


def render_message(message: Message) -> None:
    """Render a full message with headers and body."""
    console.print()
    console.print(f"[bold]Subject:[/bold] {message.subject or '(no subject)'}")
    console.print(f"[bold]From:[/bold]    {message.from_ or ''}")

    if message.to:
        to_str = ", ".join(str(a) for a in message.to)
        console.print(f"[bold]To:[/bold]      {to_str}")

    if message.cc:
        cc_str = ", ".join(str(a) for a in message.cc)
        console.print(f"[bold]Cc:[/bold]      {cc_str}")

    if message.date:
        console.print(f"[bold]Date:[/bold]    {message.date.strftime('%Y-%m-%d %H:%M:%S %z')}")

    if message.attachments:
        att_str = ", ".join(a.filename or "unnamed" for a in message.attachments)
        console.print(f"[bold]Attach:[/bold]  {att_str}")

    console.print("─" * 60)

    # Body
    if message.body.text:
        console.print(message.body.text)
    elif message.body.html:
        # Attempt to render as markdown (basic conversion)
        console.print(Text(message.body.html))
    else:
        console.print("[dim](empty body)[/dim]")

    console.print()


def _format_flags(flags: list[Flag]) -> str:
    """Format flags as compact indicators."""
    parts = []
    if Flag.FLAGGED in flags:
        parts.append("!")
    if Flag.ANSWERED in flags:
        parts.append("R")
    if Flag.DRAFT in flags:
        parts.append("D")
    if Flag.SEEN not in flags:
        parts.append("N")  # New/unread
    return "".join(parts)
