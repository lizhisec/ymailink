"""Data assembly helpers for AI API payloads."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ymailink.domain.message import Message


def build_email_xml(msg: Message) -> str:
    """Build an XML fragment from a Message for the AI API."""
    lines = ["<email>"]
    lines.append(f"  <subject>{escape(msg.subject or '')}</subject>")

    from_val = str(msg.from_) if msg.from_ else ""
    lines.append(f"  <from>{escape(from_val)}</from>")

    to_val = ", ".join(str(a) for a in msg.to)
    lines.append(f"  <to>{escape(to_val)}</to>")

    cc_val = ", ".join(str(a) for a in msg.cc)
    if cc_val:
        lines.append(f"  <cc>{escape(cc_val)}</cc>")

    date_val = msg.date.isoformat() if msg.date else ""
    lines.append(f"  <date>{escape(date_val)}</date>")

    body_text = msg.body.text or msg.body.html
    if body_text:
        lines.append(f"  <body><![CDATA[{body_text}]]></body>")

    lines.append("</email>")
    return "\n".join(lines)


def build_variables() -> dict:
    """Build the variables dict for the AI API payload."""
    return {}
