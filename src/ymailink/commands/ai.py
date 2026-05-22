"""AI-powered email commands: short-summary, summary, rapid-reply."""

from __future__ import annotations

import argparse
import asyncio

from ymailink.config import load_config
from ymailink.config.models import AiConfig, YmailConfig
from ymailink.domain.message import Message
from ymailink.output.printer import Printer, get_printer


def ai_short_summary(args: argparse.Namespace) -> None:
    """Generate a one-line short summary of an email."""
    asyncio.run(_ai_short_summary(args))


async def _ai_short_summary(args: argparse.Namespace) -> None:
    from ymailink.ai.client import call_ai
    from ymailink.ai.prompts import build_email_xml, build_variables

    config, printer, ai_cfg, msg = await _resolve_email(args)
    if msg is None:
        return

    payload = {
        "model": ai_cfg.model,
        "email_content": build_email_xml(msg),
        "variables": build_variables(),
    }

    data = await call_ai(payload, ai_cfg, "short_summary")
    result = data.get("result") or data
    text = result.get("short_summary") or _extract_choice_content(data)
    printer.out(text or "No summary returned.")


def ai_summary(args: argparse.Namespace) -> None:
    """Generate a detailed summary of an email."""
    asyncio.run(_ai_summary(args))


async def _ai_summary(args: argparse.Namespace) -> None:
    from ymailink.ai.client import call_ai
    from ymailink.ai.prompts import build_email_xml, build_variables

    config, printer, ai_cfg, msg = await _resolve_email(args)
    if msg is None:
        return

    payload = {
        "model": ai_cfg.model,
        "email_content": build_email_xml(msg),
        "variables": build_variables(),
    }

    data = await call_ai(payload, ai_cfg, "summary")
    result = data.get("result") or data
    text = result.get("summary") or _extract_choice_content(data)
    printer.out(text or "No summary returned.")


def ai_rapid_reply(args: argparse.Namespace) -> None:
    """Generate quick reply suggestions for an email."""
    asyncio.run(_ai_rapid_reply(args))


async def _ai_rapid_reply(args: argparse.Namespace) -> None:
    from ymailink.ai.client import call_ai
    from ymailink.ai.prompts import build_variables

    config, printer, ai_cfg, msg = await _resolve_email(args)
    if msg is None:
        return

    payload = {
        "model": ai_cfg.model,
        "mail_body": msg.body.text or msg.body.html or "",
        "mail_subject": msg.subject or "",
        "count": 3,
        "variables": build_variables(),
    }

    data = await call_ai(payload, ai_cfg, "rapid-reply-topics")

    content = data.get("content")
    if isinstance(content, list):
        for i, reply in enumerate(content, 1):
            printer.out(f"{i}. {reply}")
    else:
        text = _extract_choice_content(data)
        printer.out(text or "No reply suggestions returned.")


async def _resolve_email(
    args: argparse.Namespace,
) -> tuple[YmailConfig, Printer, AiConfig, Message | None]:
    """Load config + AI config + fetch the target message. Returns None for
    message on any error (caller should return immediately)."""
    from ymailink.backend.builder import BackendBuilder

    config = load_config(args.config_paths)
    printer = get_printer(args)

    ai_cfg = config.ai
    if not ai_cfg or not ai_cfg.api_key:
        # Fallback: try ~/.taiji/config.json first, then env vars
        from ymailink.utils.taiji import load_taiji_config

        taiji = load_taiji_config()
        if taiji["api_key"]:
            ai_cfg = AiConfig(
                base_url=taiji["base_url"] or "https://ai.ymailink.com",
                api_key=taiji["api_key"],
            )
        else:
            printer.error("AI config is missing or api-key is not set.")
            return config, printer, ai_cfg, None  # unreachable but defensive

    builder = BackendBuilder(config, args.account)
    backend = await builder.build_read_backend()
    async with backend:
        messages = await backend.get_messages(args.folder, [args.id])

    if not messages:
        printer.error(f"Message {args.id} not found.")
        return config, printer, ai_cfg, None

    return config, printer, ai_cfg, messages[0]


def _extract_choice_content(data: dict) -> str | None:
    """Fallback: extract text from OpenAI-style choices array."""
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        return message.get("content")
    return None
