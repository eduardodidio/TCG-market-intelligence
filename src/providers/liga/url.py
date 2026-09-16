"""Canonical Liga Magic URL builder.

Single source of truth for building Liga Magic card search URLs.
All backend code should use ``liga_url_for_card_name`` instead of
building URLs manually.
"""

from __future__ import annotations

from urllib.parse import quote_plus

BASE_URL = "https://www.ligamagic.com.br"


def liga_url_for_card_name(
    card_name: str,
    *,
    set_code: str | None = None,
) -> str:
    """Build a Liga Magic search URL from a card name.

    Handles split/DFC cards by using only the front face name
    (everything before ``" // "``), **except** for Art Cards —
    Liga treats art cards as separate products and uses the full
    name including ``(Art Card ...)`` annotation (but NOT the back face).

    When *set_code* is provided, appends ``&ed=SIGLA`` so Liga
    pre-selects the correct edition, avoiding wrong-edition prices.
    """
    name = card_name.strip()
    if not name:
        return f"{BASE_URL}/?view=cards/card&card=&show=1"

    # Art Cards: Liga uses front face + art card annotation.
    # For DFC art cards like "The Arkenstone // Seek the Heart (Art Card with Signature)",
    # Liga expects "The Arkenstone (Art Card with Signature)" — no back face.
    if "(Art Card" in name:
        import re

        art_match = re.search(r"\(Art Card[^)]*\)", name)
        annotation = art_match.group(0) if art_match else ""
        front = name.split(" // ")[0].strip()
        # Remove annotation from front if it's already there (non-DFC art card)
        front = re.sub(r"\s*\(Art Card[^)]*\)", "", front).strip()
        search_name = f"{front} {annotation}".strip()
        encoded = quote_plus(search_name)
        ed_param = f"&ed={set_code.lower()}" if set_code else ""
        return f"{BASE_URL}/?view=cards/card&card={encoded}{ed_param}"

    # Split/DFC cards: use only the front face
    front_face = name.split(" // ")[0].strip()
    encoded = quote_plus(front_face)
    ed_param = f"&ed={set_code.lower()}" if set_code else ""
    return f"{BASE_URL}/?view=cards/card&card={encoded}{ed_param}"
