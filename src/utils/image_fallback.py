"""Fallback image URI construction for cards missing Scryfall bulk data images.

Art series cards (e.g. ``ashob/44a``) are not included in Scryfall's bulk
data export, so their ``image_uri`` is NULL in our catalog.  This module
constructs a Scryfall API redirect URL that the browser can fetch directly.
"""

from __future__ import annotations

import re


def fallback_image_uri(
    set_code: str | None,
    collector_number: str | None,
) -> str | None:
    """Build a Scryfall redirect URL when the stored ``image_uri`` is NULL.

    Args:
        set_code: Liga/catalog set code (e.g. ``"ashob"``).
        collector_number: Collector number, possibly with letter suffix
            (e.g. ``"44a"``).

    Returns:
        A Scryfall ``?format=image`` redirect URL, or ``None`` when inputs
        are insufficient to construct one.
    """
    if not set_code or not collector_number:
        return None

    # Use the original set code — Scryfall accepts variant codes (e.g. smbro)
    scryfall_set = set_code.lower()

    # Strip trailing letter suffix for art cards (e.g. 44a -> 44)
    base_number = re.sub(r"[a-zA-Z]+$", "", collector_number)
    if not base_number:
        return None

    return (
        f"https://api.scryfall.com/cards/{scryfall_set}/{base_number}"
        f"?format=image&version=normal"
    )
