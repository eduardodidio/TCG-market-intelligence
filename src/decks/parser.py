"""Parse text-format deck lists into structured card data."""

from __future__ import annotations

import re

# Patterns:
# "4 Lightning Bolt"
# "4 Lightning Bolt [LEA]"
# "4 Lightning Bolt [LEA:161]"
# "Lightning Bolt" (qty defaults to 1)
_LINE_RE = re.compile(
    r"^"
    r"(?:(\d+)\s+)?"  # optional quantity
    r"(.+?)"  # card name (non-greedy)
    r"(?:\s+\[([A-Za-z0-9]+)(?::([A-Za-z0-9]+))?\])?"  # optional [SET] or [SET:NUM]
    r"$"
)


def parse_deck_text(content: str) -> list[dict]:
    """Parse a text deck list.

    Returns list of dicts with keys: name_en, quantity, set_code, collector_number.

    Supported formats:
    - ``{qty} {name}``
    - ``{qty} {name} [{set}]``
    - ``{qty} {name} [{set}:{number}]``

    Rules:
    - Lines starting with ``#`` or ``//`` are comments.
    - Empty lines are skipped.
    - Missing quantity defaults to 1.
    - Set codes are lowercased.
    """
    results: list[dict] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        match = _LINE_RE.match(line)
        if not match:
            continue

        qty_str, name, set_code, collector_number = match.groups()

        quantity = int(qty_str) if qty_str else 1
        name = name.strip()
        if not name:
            continue

        results.append(
            {
                "name_en": name,
                "quantity": quantity,
                "set_code": set_code.lower() if set_code else None,
                "collector_number": collector_number if collector_number else None,
            }
        )

    return results
