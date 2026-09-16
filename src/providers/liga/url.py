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

    Uses the **full** card name (including ``" // "`` for DFC/split cards)
    because Liga requires the complete name to show the detailed card page
    with edition dropdown.  Using only the front face causes Liga to show
    an aggregated summary with wrong prices.

    When *set_code* is provided, appends ``&ed=SIGLA`` so Liga
    pre-selects the correct edition, avoiding wrong-edition prices.
    """
    name = card_name.strip()
    if not name:
        return f"{BASE_URL}/?view=cards/card&card=&show=1"

    encoded = quote_plus(name)
    ed_param = f"&ed={set_code.lower()}" if set_code else ""
    return f"{BASE_URL}/?view=cards/card&card={encoded}{ed_param}"
