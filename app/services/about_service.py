from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


ABOUT_FIELDS = ("description", "instructions")


def load_about(path: Path) -> dict[str, str]:
    """Read the site description and instructions; missing or broken files give empty text."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}

    if not isinstance(data, dict):
        data = {}

    return {
        field: data[field] if isinstance(data.get(field), str) else ""
        for field in ABOUT_FIELDS
    }


def save_about(
    path: Path,
    description: str | None,
    instructions: str | None,
    max_chars: int,
) -> dict[str, str]:
    """
    Validate and save the site description and instructions.

    Raises ValueError when a field is too long. The file is replaced in one
    step, so a failed write never leaves half-written text behind.
    """
    content = {
        "description": (description or "").strip(),
        "instructions": (instructions or "").strip(),
    }

    for field, text in content.items():
        if len(text) > max_chars:
            raise ValueError(
                f"The {field} is {len(text):,} characters. "
                f"Shorten it to {max_chars:,} or fewer and save again."
            )

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        **content,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)

    return content
