"""Logging configuration."""

from __future__ import annotations

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure logging for ymailink."""
    level = logging.DEBUG if debug else logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    # Quiet noisy libraries
    if not debug:
        logging.getLogger("imapclient").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("googleapiclient").setLevel(logging.WARNING)
        logging.getLogger("msal").setLevel(logging.WARNING)
