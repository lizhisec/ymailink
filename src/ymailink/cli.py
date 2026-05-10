"""CLI main dispatcher - argparse with thin dispatchers and lazy imports."""

from __future__ import annotations

import argparse
import sys

from ymailink import __version__


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ymailink",
        description="CLI email management tool",
    )

    # Global options
    parser.add_argument("-c", "--config", dest="config_paths", action="append", help="config file path (repeatable)")
    parser.add_argument("-o", "--output", choices=["plain", "json"], default="plain")
    parser.add_argument("-a", "--account", default=None, help="account name")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    # ---- account ----
    _register_account(subparsers)

    # ---- folder ----
    _register_folder(subparsers)

    # ---- mail ----
    _register_mail(subparsers)

    # ---- flag ----
    _register_flag(subparsers)


    # ---- attachment ----
    _register_attachment(subparsers)

    # ---- template ----
    _register_template(subparsers)

    args = parser.parse_args(argv)

    # Configure logging
    if args.debug:
        from ymailink.utils.logging import configure_logging
        configure_logging(debug=True)

    # Default: no subcommand → mail list
    if args.command is None:
        args.folder = "INBOX"
        args.page = 1
        args.page_size = 20
        args.query = None
        cmd_mail_list(args)
        return

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


# ==============================================================
# Subcommand registration
# ==============================================================


def _register_account(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("account", aliases=["accounts"], help="manage accounts")
    sub = p.add_subparsers(dest="subcommand")

    ls = sub.add_parser("list", help="list all accounts")
    ls.set_defaults(func=cmd_account_list)

    doctor = sub.add_parser("doctor", help="diagnose account connection")
    doctor.set_defaults(func=cmd_account_doctor)

    configure = sub.add_parser("configure", help="interactively configure account")
    configure.set_defaults(func=cmd_account_configure)


def _register_folder(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("folder", aliases=["folders"], help="manage folders")
    sub = p.add_subparsers(dest="subcommand")

    ls = sub.add_parser("list", help="list folders")
    ls.set_defaults(func=cmd_folder_list)

    add = sub.add_parser("add", help="create folder")
    add.add_argument("name", help="folder name")
    add.set_defaults(func=cmd_folder_add)

    delete = sub.add_parser("delete", help="delete folder")
    delete.add_argument("name", help="folder name")
    delete.set_defaults(func=cmd_folder_delete)

    expunge = sub.add_parser("expunge", help="expunge deleted messages in folder")
    expunge.add_argument("name", help="folder name")
    expunge.set_defaults(func=cmd_folder_expunge)

    purge = sub.add_parser("purge", help="purge all messages in folder")
    purge.add_argument("name", help="folder name")
    purge.set_defaults(func=cmd_folder_purge)


def _register_mail(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("mail", help="manage mail")
    sub = p.add_subparsers(dest="subcommand")

    ls = sub.add_parser("list", help="list messages")
    ls.add_argument("-f", "--folder", default="INBOX", help="folder name")
    ls.add_argument("-p", "--page", type=int, default=1, help="page number")
    ls.add_argument("-s", "--page-size", type=int, default=20, help="page size")
    ls.add_argument("-q", "--query", default=None, help="search query")
    ls.set_defaults(func=cmd_mail_list)

    thread = sub.add_parser("thread", help="view email thread")
    thread.add_argument("id", help="message id")
    thread.add_argument("-f", "--folder", default="INBOX", help="folder name")
    thread.set_defaults(func=cmd_mail_thread)

    read = sub.add_parser("read", help="read message")
    read.add_argument("id", help="message id")
    read.add_argument("-f", "--folder", default="INBOX", help="folder name")
    read.add_argument("--html", action="store_true", help="prefer HTML body")
    read.set_defaults(func=cmd_mail_read)

    write = sub.add_parser("write", help="compose new message")
    write.add_argument("--headers", nargs="*", help="headers as Key:Value")
    write.set_defaults(func=cmd_mail_write)

    send = sub.add_parser("send", help="send raw message")
    send.add_argument("raw", nargs="?", help="raw message or - for stdin")
    send.set_defaults(func=cmd_mail_send)

    reply = sub.add_parser("reply", help="reply to message")
    reply.add_argument("id", help="message id")
    reply.add_argument("-f", "--folder", default="INBOX", help="folder name")
    reply.add_argument("--all", action="store_true", help="reply all")
    reply.set_defaults(func=cmd_mail_reply)

    forward = sub.add_parser("forward", help="forward message")
    forward.add_argument("id", help="message id")
    forward.add_argument("-f", "--folder", default="INBOX", help="folder name")
    forward.set_defaults(func=cmd_mail_forward)

    copy = sub.add_parser("copy", help="copy messages")
    copy.add_argument("ids", nargs="+", help="message ids")
    copy.add_argument("-t", "--target", required=True, help="target folder")
    copy.add_argument("-f", "--folder", default="INBOX", help="source folder")
    copy.set_defaults(func=cmd_mail_copy)

    move = sub.add_parser("move", help="move messages")
    move.add_argument("ids", nargs="+", help="message ids")
    move.add_argument("-t", "--target", required=True, help="target folder")
    move.add_argument("-f", "--folder", default="INBOX", help="source folder")
    move.set_defaults(func=cmd_mail_move)

    delete = sub.add_parser("delete", help="delete messages")
    delete.add_argument("ids", nargs="+", help="message ids")
    delete.add_argument("-f", "--folder", default="INBOX", help="folder name")
    delete.set_defaults(func=cmd_mail_delete)


def _register_flag(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("flag", aliases=["flags"], help="manage flags")
    sub = p.add_subparsers(dest="subcommand")

    add = sub.add_parser("add", help="add flags")
    add.add_argument("ids", nargs="+", help="message ids")
    add.add_argument("-g", "--flags", nargs="+", required=True, help="flags to add")
    add.add_argument("-f", "--folder", default="INBOX", help="folder name")
    add.set_defaults(func=cmd_flag_add)

    st = sub.add_parser("set", help="set flags (replace)")
    st.add_argument("ids", nargs="+", help="message ids")
    st.add_argument("-g", "--flags", nargs="+", required=True, help="flags to set")
    st.add_argument("-f", "--folder", default="INBOX", help="folder name")
    st.set_defaults(func=cmd_flag_set)

    rm = sub.add_parser("remove", help="remove flags")
    rm.add_argument("ids", nargs="+", help="message ids")
    rm.add_argument("-g", "--flags", nargs="+", required=True, help="flags to remove")
    rm.add_argument("-f", "--folder", default="INBOX", help="folder name")
    rm.set_defaults(func=cmd_flag_remove)


def _register_attachment(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("attachment", aliases=["attachments"], help="manage attachments")
    sub = p.add_subparsers(dest="subcommand")

    dl = sub.add_parser("download", help="download attachments")
    dl.add_argument("id", help="message id")
    dl.add_argument("-f", "--folder", default="INBOX", help="folder name")
    dl.add_argument("-d", "--dir", default=None, help="download directory")
    dl.set_defaults(func=cmd_attachment_download)


def _register_template(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("template", aliases=["templates"], help="manage templates")
    sub = p.add_subparsers(dest="subcommand")

    write = sub.add_parser("write", help="create template")
    write.set_defaults(func=cmd_template_write)

    reply = sub.add_parser("reply", help="create reply template")
    reply.add_argument("id", help="message id")
    reply.add_argument("-f", "--folder", default="INBOX", help="folder name")
    reply.add_argument("--all", action="store_true", help="reply all")
    reply.set_defaults(func=cmd_template_reply)

    forward = sub.add_parser("forward", help="create forward template")
    forward.add_argument("id", help="message id")
    forward.add_argument("-f", "--folder", default="INBOX", help="folder name")
    forward.set_defaults(func=cmd_template_forward)

    save = sub.add_parser("save", help="save template as draft")
    save.add_argument("raw", nargs="?", help="raw template or - for stdin")
    save.set_defaults(func=cmd_template_save)

    send = sub.add_parser("send", help="send template")
    send.add_argument("raw", nargs="?", help="raw template or - for stdin")
    send.set_defaults(func=cmd_template_send)


# ==============================================================
# Thin dispatchers (lazy import)
# ==============================================================


def cmd_account_list(args: argparse.Namespace) -> None:
    from ymailink.commands.account import account_list
    account_list(args)


def cmd_account_doctor(args: argparse.Namespace) -> None:
    from ymailink.commands.account import account_doctor
    account_doctor(args)


def cmd_account_configure(args: argparse.Namespace) -> None:
    from ymailink.commands.account import account_configure
    account_configure(args)


def cmd_folder_list(args: argparse.Namespace) -> None:
    from ymailink.commands.folder import folder_list
    folder_list(args)


def cmd_folder_add(args: argparse.Namespace) -> None:
    from ymailink.commands.folder import folder_add
    folder_add(args)


def cmd_folder_delete(args: argparse.Namespace) -> None:
    from ymailink.commands.folder import folder_delete
    folder_delete(args)


def cmd_folder_expunge(args: argparse.Namespace) -> None:
    from ymailink.commands.folder import folder_expunge
    folder_expunge(args)


def cmd_folder_purge(args: argparse.Namespace) -> None:
    from ymailink.commands.folder import folder_purge
    folder_purge(args)


def cmd_mail_list(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_list
    mail_list(args)


def cmd_mail_thread(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_thread
    mail_thread(args)


def cmd_mail_read(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_read
    mail_read(args)


def cmd_mail_write(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_write
    mail_write(args)


def cmd_mail_send(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_send
    mail_send(args)


def cmd_mail_reply(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_reply
    mail_reply(args)


def cmd_mail_forward(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_forward
    mail_forward(args)


def cmd_mail_copy(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_copy
    mail_copy(args)


def cmd_mail_move(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_move
    mail_move(args)


def cmd_mail_delete(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_delete
    mail_delete(args)


def cmd_flag_add(args: argparse.Namespace) -> None:
    from ymailink.commands.flag import flag_add
    flag_add(args)


def cmd_flag_set(args: argparse.Namespace) -> None:
    from ymailink.commands.flag import flag_set
    flag_set(args)


def cmd_flag_remove(args: argparse.Namespace) -> None:
    from ymailink.commands.flag import flag_remove
    flag_remove(args)


def cmd_attachment_download(args: argparse.Namespace) -> None:
    from ymailink.commands.attachment import attachment_download
    attachment_download(args)


def cmd_template_write(args: argparse.Namespace) -> None:
    from ymailink.commands.template import template_write
    template_write(args)


def cmd_template_reply(args: argparse.Namespace) -> None:
    from ymailink.commands.template import template_reply
    template_reply(args)


def cmd_template_forward(args: argparse.Namespace) -> None:
    from ymailink.commands.template import template_forward
    template_forward(args)


def cmd_template_save(args: argparse.Namespace) -> None:
    from ymailink.commands.template import template_save
    template_save(args)


def cmd_template_send(args: argparse.Namespace) -> None:
    from ymailink.commands.template import template_send
    template_send(args)
