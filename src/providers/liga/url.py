"""Canonical Liga Magic URL builder.

Single source of truth for building Liga Magic card search URLs.
All backend code should use ``liga_url_for_card_name`` instead of
building URLs manually.
"""

from __future__ import annotations

from urllib.parse import quote_plus

BASE_URL = "https://www.ligamagic.com.br"


def liga_url_for_card_name(card_name: str) -> str:
    """Build a Liga Magic search URL from a card name.

    Handles split/DFC cards by using only the front face name
    (everything before ``" // "``).
    """
    name = card_name.strip()
    if not name:
        return f"{BASE_URL}/?view=cards/card&card=&show=1"
    # Split/DFC cards: use only the front face
    front_face = name.split(" // ")[0].strip()
    encoded = quote_plus(front_face)
    return f"{BASE_URL}/?view=cards/card&card={encoded}&show=1"
