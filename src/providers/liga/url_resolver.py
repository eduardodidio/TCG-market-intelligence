"""Liga URL resolver — uses Playwright to resolve the correct Liga page URL.

Given a card name, navigates to the Liga search page and returns
the final URL after any redirects.  Uses sync Playwright API.
"""

from __future__ import annotations


def resolve_liga_page_url_sync(card_name: str, page: object) -> str | None:
    """Navigate to Liga search for *card_name* and return the final page URL.

    Uses an existing Playwright **sync** page object.  Returns the final URL
    after redirects, or ``None`` if the page could not be loaded.
    """
    from src.providers.liga.url import liga_url_for_card_name

    search_url = liga_url_for_card_name(card_name)
    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        return page.url  # type: ignore[union-attr]
    except Exception:
        return None
