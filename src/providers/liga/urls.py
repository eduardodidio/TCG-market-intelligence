"""Liga URL helpers: single source of truth for LigaMagic card URLs.

Pure functions with no Playwright dependency so they can be imported
and unit-tested without a browser.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import parse_qs, quote_plus, urlsplit

LIGA_BASE_URL = "https://www.ligamagic.com.br"

_VALID_HOSTS = {"www.ligamagic.com.br", "ligamagic.com.br"}
_MAX_URL_LENGTH = 1000


def build_liga_card_url(card_name: str) -> str:
    """Build a LigaMagic card search URL from a card name."""
    encoded = quote_plus(card_name.strip())
    return f"{LIGA_BASE_URL}/?view=cards/card&card={encoded}&show=1"


def is_valid_liga_card_url(url: str | None) -> bool:
    """Return True when ``url`` is a well-formed LigaMagic card page URL."""
    if not isinstance(url, str) or not url or len(url) > _MAX_URL_LENGTH:
        return False

    try:
        parts = urlsplit(url)
    except ValueError:
        return False

    if parts.scheme != "https":
        return False
    if parts.netloc not in _VALID_HOSTS:
        return False

    query = parse_qs(parts.query)
    return query.get("view") == ["cards/card"]


def liga_external_id(card_id: int, is_foil: bool) -> str:
    """Build the external_id used for Liga sweep price rows."""
    return f"liga_{card_id}_foil" if is_foil else f"liga_{card_id}"


def resolve_liga_card_url(
    card_id: int | None,
    *,
    is_foil: bool,
    fallback_name: str,
    lookup: Callable[[str], str | None],
) -> str | None:
    """Resolve the best Liga URL for a card.

    Prefers the stored URL of the page the price was actually fetched from
    (foil key first for foil entries, then the non-foil key), and only falls
    back to a name-based search URL when no valid stored URL exists. Stored
    values are validated with :func:`is_valid_liga_card_url` so a foreign or
    malformed URL is never returned.

    ``lookup`` maps an external_id to a stored URL (typically
    ``Repository.get_liga_card_url``), keeping this module free of any DB
    dependency.
    """
    if card_id is not None:
        keys = (
            [liga_external_id(card_id, True), liga_external_id(card_id, False)]
            if is_foil
            else [liga_external_id(card_id, False)]
        )
        for key in keys:
            stored = lookup(key)
            if is_valid_liga_card_url(stored):
                return stored
    return build_liga_card_url(fallback_name) if fallback_name else None
