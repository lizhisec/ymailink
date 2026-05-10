"""$EDITOR integration for composing messages."""

from __future__ import annotations

import os
import subprocess
import tempfile


def open_editor(initial_content: str = "") -> str | None:
    """Open $EDITOR with initial content and return the edited text.

    Returns None if the editor exits with non-zero status or the file is empty.
    """
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".eml", prefix="ymailink_", delete=False
    ) as f:
        f.write(initial_content)
        tmpfile = f.name

    try:
        result = subprocess.run([editor, tmpfile])
        if result.returncode != 0:
            return None

        with open(tmpfile) as f:
            content = f.read()

        return content if content.strip() else None
    finally:
        try:
            os.unlink(tmpfile)
        except OSError:
            pass
