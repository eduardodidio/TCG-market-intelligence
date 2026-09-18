"""Canonical Liga Magic URL builder.

Single source of truth for building Liga Magic card search URLs.
All backend code should use ``liga_url_for_card_name`` instead of
building URLs manually.
"""

from __future__ import annotations

from urllib.parse import parse_qs, quote_plus, unquote_plus, urlparse

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


def parse_liga_card_url(url: str) -> tuple[str, str | None]:
    """Parse a Liga Magic card URL and return ``(card_name, set_code | None)``.

    Accepts URLs of the form::

        https://www.ligamagic.com.br/?view=cards/card&card=Ajani+Goldmane
        https://www.ligamagic.com.br/?view=cards/card&card=Ajani+Goldmane&ed=m14

    Raises :class:`ValueError` when *url* is not a valid Liga Magic card URL
    or when the ``card`` query parameter is missing/empty.
    """
    parsed = urlparse(url)

    # Validate domain
    if "ligamagic.com.br" not in (parsed.hostname or ""):
        raise ValueError("URL must be from ligamagic.com.br")

    params = parse_qs(parsed.query)

    # Extract card name — parse_qs returns lists, take the first value
    card_values = params.get("card")
    if not card_values or not card_values[0].strip():
        raise ValueError("URL is missing the 'card' parameter")

    card_name = unquote_plus(card_values[0]).strip()

    # Extract optional set/edition code
    ed_values = params.get("ed")
    set_code = ed_values[0].strip() if ed_values and ed_values[0].strip() else None

    return card_name, set_code
